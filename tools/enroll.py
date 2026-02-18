"""
Reception Greeter – Enrollment tool.

Captures face samples from the camera, runs quality checks, extracts
embeddings via InsightFace, and stores them in the database.

Usage:
    python -m tools.enroll --name "Sudheer" [--samples 20] [--config app/config.yaml]
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import cv2
import numpy as np
import yaml

# Ensure project root is on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from app.db.storage import FaceDB
from app.vision.face_detect import FaceDetector


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def quality_check(
    face,
    frame: np.ndarray,
    min_face_width: int,
    max_yaw: float,
    max_pitch: float,
    min_blur: float,
    min_brightness: int,
    max_brightness: int,
) -> tuple[bool, str]:
    """
    Run quality checks on a detected face.
    Returns (passed, reason_if_failed).
    """
    # Check face size
    w = face.width
    if w < min_face_width:
        return False, f"Face too small ({w:.0f}px < {min_face_width}px)"

    # Check blur (Laplacian variance)
    x1, y1, x2, y2 = face.bbox
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return False, "Empty face crop"

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_score < min_blur:
        return False, f"Too blurry (score={blur_score:.1f} < {min_blur:.1f})"

    # Check brightness
    mean_brightness = float(np.mean(gray))
    if mean_brightness < min_brightness:
        return False, f"Too dark (brightness={mean_brightness:.0f})"
    if mean_brightness > max_brightness:
        return False, f"Too bright (brightness={mean_brightness:.0f})"

    # Check face pose via landmark positions (approximate yaw/pitch)
    if face.landmarks is not None and len(face.landmarks) >= 5:
        # 5-point landmarks: left_eye, right_eye, nose, left_mouth, right_mouth
        le, re, nose = face.landmarks[0], face.landmarks[1], face.landmarks[2]
        eye_center_x = (le[0] + re[0]) / 2
        eye_dist = abs(re[0] - le[0])
        if eye_dist > 0:
            # Approximate yaw: nose offset from eye center
            yaw_ratio = abs(nose[0] - eye_center_x) / eye_dist
            yaw_approx = yaw_ratio * 90  # rough degrees
            if yaw_approx > max_yaw:
                return False, f"Yaw too large ({yaw_approx:.0f}° > {max_yaw:.0f}°)"

            # Approximate pitch: nose y relative to eyes
            eye_center_y = (le[1] + re[1]) / 2
            pitch_ratio = abs(nose[1] - eye_center_y) / eye_dist
            pitch_approx = pitch_ratio * 90
            if pitch_approx > max_pitch:
                return False, f"Pitch too large ({pitch_approx:.0f}° > {max_pitch:.0f}°)"

    # Check embedding exists
    if face.embedding is None:
        return False, "No embedding extracted"

    return True, "OK"


def enroll(
    name: str,
    config: dict,
    db: FaceDB,
    detector: FaceDetector,
    num_samples: int = 20,
    no_display: bool = False,
) -> bool:
    """
    Enrollment: open camera, capture face samples with quality checks.
    When no_display=True, runs headless without GUI windows.
    """
    if db.person_exists(name):
        print(f"[!] Person '{name}' already enrolled. Use --force to re-enroll.")
        return False

    enroll_cfg = config.get("enrollment", {})
    cam_cfg = config.get("camera", {})

    min_face_width = enroll_cfg.get("min_face_width_px", 80)
    max_yaw = enroll_cfg.get("max_yaw_degrees", 35)
    max_pitch = enroll_cfg.get("max_pitch_degrees", 25)
    min_blur = enroll_cfg.get("min_blur_laplacian", 50.0)
    min_brightness = enroll_cfg.get("min_brightness", 40)
    max_brightness = enroll_cfg.get("max_brightness", 220)

    source = cam_cfg.get("source", 0)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera source: {source}")
        return False

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg.get("width", 1280))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg.get("height", 720))

    print(f"\n=== ENROLLMENT: {name} ===")
    print(f"Capturing {num_samples} high-quality face samples.")
    if not no_display:
        print("Look at the camera. Slowly turn your head left/right/up/down.")
        print("Press 'q' to abort.\n")
    else:
        print("Running headless (no GUI). Face the camera and hold still.\n")

    embeddings = []
    quality_scores = []
    captured = 0
    frame_count = 0
    last_capture_time = 0.0
    max_empty_frames = 300  # bail after this many frames with no face

    try:
        while captured < num_samples:
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Failed to read frame, retrying...")
                time.sleep(0.1)
                continue

            frame_count += 1

            # In headless mode, skip frames to let camera auto-adjust
            if no_display and frame_count < 15:
                continue

            # Safety bail-out in headless mode
            if no_display and frame_count > max_empty_frames and captured == 0:
                print("[ERROR] No face detected after many frames. Aborting.")
                return False

            # Detect faces
            faces = detector.detect(frame)

            if not no_display:
                # Draw info on frame
                display = frame.copy()
                cv2.putText(
                    display,
                    f"Enrolling: {name}  [{captured}/{num_samples}]",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
                )

            if len(faces) == 0:
                if not no_display:
                    cv2.putText(display, "No face detected", (10, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            elif len(faces) > 1:
                if not no_display:
                    cv2.putText(display, "Multiple faces - show only yours", (10, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                # In headless mode, pick the largest face
                if no_display:
                    faces = [max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))]
                else:
                    faces = []  # skip frame in GUI mode

            if len(faces) == 1:
                face = faces[0]

                if not no_display:
                    x1, y1, x2, y2 = face.bbox
                    cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Rate-limit: at least 0.3s between captures
                now = time.time()
                if now - last_capture_time < 0.3:
                    if not no_display:
                        cv2.putText(display, "Hold still...", (10, 70),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                else:
                    passed, reason = quality_check(
                        face, frame,
                        min_face_width, max_yaw, max_pitch,
                        min_blur, min_brightness, max_brightness,
                    )
                    if passed:
                        # Normalise embedding
                        emb = face.embedding
                        emb = emb / (np.linalg.norm(emb) + 1e-10)
                        embeddings.append(emb)
                        quality_scores.append(face.quality)
                        captured += 1
                        last_capture_time = now
                        if not no_display:
                            cv2.putText(
                                display,
                                f"CAPTURED {captured}/{num_samples}",
                                (10, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
                            )
                        print(f"  [{captured}/{num_samples}] quality={face.quality:.1f}")
                    else:
                        if not no_display:
                            cv2.putText(display, f"Skip: {reason}", (10, 70),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        elif frame_count % 30 == 0:
                            print(f"  [skip] {reason}")

            if not no_display:
                cv2.imshow("Enrollment", display)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("\n[ABORT] Enrollment cancelled by user.")
                    return False
            else:
                # Small delay in headless mode to not hog CPU
                time.sleep(0.05)
    finally:
        cap.release()
        if not no_display:
            cv2.destroyAllWindows()

    if captured < num_samples:
        print(f"[WARN] Only captured {captured}/{num_samples} samples.")
        if captured < 3:
            print("[ERROR] Too few samples. Enrollment aborted.")
            return False

    # Save to database
    person_id = db.add_person(name)
    db.add_embeddings_bulk(person_id, embeddings, quality_scores)
    print(f"\n[OK] Enrolled '{name}' with {len(embeddings)} embeddings (person_id={person_id})")
    return True


def re_enroll(
    name: str,
    config: dict,
    db: FaceDB,
    detector: FaceDetector,
    num_samples: int = 20,
    no_display: bool = False,
) -> bool:
    """Delete existing enrollment and re-enroll."""
    person = db.get_person_by_name(name)
    if person:
        db.delete_person(person["person_id"])
        print(f"[INFO] Deleted existing enrollment for '{name}'")
    return enroll(name, config, db, detector, num_samples, no_display=no_display)


def main():
    parser = argparse.ArgumentParser(description="Enroll a person into the face database")
    parser.add_argument("--name", required=True, help="Person's name")
    parser.add_argument("--samples", type=int, default=None, help="Number of face samples")
    parser.add_argument("--config", default="app/config.yaml", help="Config file path")
    parser.add_argument("--force", action="store_true", help="Re-enroll if already exists")
    parser.add_argument("--role", default="", help="Person's role (e.g., 'employee', 'visitor')")
    parser.add_argument("--no-display", action="store_true", help="Headless mode (no GUI window)")
    args = parser.parse_args()

    config = load_config(args.config)
    num_samples = args.samples or config.get("enrollment", {}).get("num_samples", 20)

    db_path = config.get("database", {}).get("path", "../data/faces.db")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.abspath(args.config)), db_path)
    db = FaceDB(db_path)

    det_cfg = config.get("face_detection", {})
    perf_cfg = config.get("performance", {})
    detector = FaceDetector(
        model_pack=det_cfg.get("model_pack", "buffalo_l"),
        min_confidence=det_cfg.get("min_confidence", 0.5),
        min_face_size=det_cfg.get("min_face_size", 60),
        detection_resize_width=perf_cfg.get("detection_resize_width", 640),
        use_gpu=perf_cfg.get("use_gpu", False),
    )

    if args.force:
        success = re_enroll(args.name, config, db, detector, num_samples, no_display=args.no_display)
    else:
        success = enroll(args.name, config, db, detector, num_samples, no_display=args.no_display)

    db.close()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
