"""
Reception Greeter – Pipeline benchmark.

Measures face detection + recognition throughput on live camera
or a pre-recorded video file.

Usage:
    python scripts/benchmark.py [--source 0] [--frames 100] [--config app/config.yaml]
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import cv2
import numpy as np

# Ensure project root on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from app.vision.face_detect import FaceDetector
from app.vision.embedder import Embedder
from app.vision.matcher import FaceMatcher
from app.db.storage import FaceDB


def run_benchmark(source, num_frames: int, config: dict) -> None:
    det_cfg = config.get("face_detection", {})
    perf_cfg = config.get("performance", {})
    rec_cfg = config.get("recognition", {})
    db_path = config.get("database", {}).get("path", "../data/faces.db")
    if not os.path.isabs(db_path):
        db_path = os.path.join(_PROJECT_ROOT, "app", db_path.removeprefix("../"))

    detector = FaceDetector(
        model_pack=det_cfg.get("model_pack", "buffalo_l"),
        min_confidence=det_cfg.get("min_confidence", 0.5),
        min_face_size=det_cfg.get("min_face_size", 60),
        detection_resize_width=perf_cfg.get("detection_resize_width", 640),
        use_gpu=perf_cfg.get("use_gpu", False),
    )
    embedder = Embedder()

    db = FaceDB(db_path)
    matcher = FaceMatcher(
        similarity_threshold=rec_cfg.get("similarity_threshold", 0.40),
    )
    matcher.reload(db)

    # Resolve auto source
    if isinstance(source, str) and source.lower() == "auto":
        source = 0
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open source: {source}")
        sys.exit(1)

    print(f"\n=== Pipeline Benchmark ({num_frames} frames) ===")
    print(f"Source: {source}")
    print(f"Model:  {det_cfg.get('model_pack', 'buffalo_l')}")
    print()

    detect_times = []
    embed_times = []
    match_times = []
    total_faces = 0

    for i in range(num_frames):
        ret, frame = cap.read()
        if not ret:
            print(f"[WARN] End of stream after {i} frames")
            break

        t0 = time.perf_counter()
        faces = detector.detect(frame)
        t1 = time.perf_counter()
        detect_times.append(t1 - t0)

        t2 = time.perf_counter()
        faces = embedder.extract(faces)
        t3 = time.perf_counter()
        embed_times.append(t3 - t2)

        t4 = time.perf_counter()
        for f in faces:
            if f.embedding is not None:
                matcher.match(f.embedding)
        t5 = time.perf_counter()
        match_times.append(t5 - t4)

        total_faces += len(faces)
        if (i + 1) % 20 == 0:
            print(f"  Frame {i+1}/{num_frames} - {len(faces)} faces")

    cap.release()
    db.close()

    n = len(detect_times)
    if n == 0:
        print("No frames processed.")
        return

    total_pipeline = sum(detect_times) + sum(embed_times) + sum(match_times)
    print(f"\n=== Results ({n} frames) ===")
    print(f"  Total faces detected:   {total_faces}")
    print(f"  Avg faces/frame:        {total_faces / n:.1f}")
    print(f"  Detection  avg: {1000*np.mean(detect_times):7.1f} ms  "
          f"p95: {1000*np.percentile(detect_times, 95):7.1f} ms")
    print(f"  Embedding  avg: {1000*np.mean(embed_times):7.1f} ms  "
          f"p95: {1000*np.percentile(embed_times, 95):7.1f} ms")
    print(f"  Matching   avg: {1000*np.mean(match_times):7.1f} ms  "
          f"p95: {1000*np.percentile(match_times, 95):7.1f} ms")
    avg_total_ms = 1000 * total_pipeline / n
    print(f"  Total pipeline avg: {avg_total_ms:.1f} ms/frame  "
          f"(~{1000/avg_total_ms:.1f} FPS theoretical)")


def main():
    import yaml

    parser = argparse.ArgumentParser(description="Pipeline benchmark")
    parser.add_argument("--source", default=0, help="Camera index or video file")
    parser.add_argument("--frames", type=int, default=100, help="Number of frames")
    parser.add_argument("--config", default="app/config.yaml", help="Config file")
    args = parser.parse_args()

    try:
        source = int(args.source)
    except ValueError:
        source = args.source

    with open(args.config) as f:
        config = yaml.safe_load(f)

    run_benchmark(source, args.frames, config)


if __name__ == "__main__":
    main()