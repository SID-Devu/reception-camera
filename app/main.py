"""
Reception Greeter – Main real-time pipeline.

Orchestrates: Camera → Detection → Embedding → Matching → Tracking →
Door-line events → TTS greeting/bye.

Usage:
    python app/main.py [--config app/config.yaml] [--no-display] [--no-tts]
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml

# Ensure project root on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from app.audio.tts import TTSEngine
from app.db.storage import FaceDB
from app.vision.camera import Camera
from app.vision.embedder import Embedder
from app.vision.events import (
    CrossingEvent,
    DoorLineCrossingDetector,
    EventType,
    PresenceEventDetector,
)
from app.vision.face_detect import FaceDetector
from app.vision.matcher import FaceMatcher
from app.vision.tracker import CentroidTracker


def setup_logging(config: dict) -> None:
    log_cfg = config.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)

    log_file = log_cfg.get("file", "../logs/reception.log")
    if not os.path.isabs(log_file):
        log_file = os.path.join(_PROJECT_ROOT, log_file.lstrip("../"))
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def setup_audit_log(config: dict) -> logging.Logger:
    """Separate audit logger for entry/exit events."""
    log_cfg = config.get("logging", {})
    audit_file = log_cfg.get("audit_file", "../logs/audit.log")
    if not os.path.isabs(audit_file):
        audit_file = os.path.join(_PROJECT_ROOT, audit_file.lstrip("../"))
    os.makedirs(os.path.dirname(audit_file), exist_ok=True)

    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    fh = logging.FileHandler(audit_file, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    audit_logger.addHandler(fh)
    return audit_logger


class ReceptionPipeline:
    """
    The main real-time recognition + greeting pipeline.
    """

    def __init__(self, config: dict, no_display: bool = False, no_tts: bool = False):
        self.config = config
        self.no_display = no_display
        self.no_tts = no_tts
        self._running = False
        self.logger = logging.getLogger("pipeline")
        self.audit = setup_audit_log(config)

        # ---- Database ----
        db_path = config.get("database", {}).get("path", "../data/faces.db")
        if not os.path.isabs(db_path):
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                db_path,
            )
        self.db = FaceDB(db_path)

        # ---- Camera ----
        cam_cfg = config.get("camera", {})
        self.camera = Camera(
            source=cam_cfg.get("source", 0),
            width=cam_cfg.get("width", 1280),
            height=cam_cfg.get("height", 720),
            fps=cam_cfg.get("fps", 30),
        )
        self.detect_every_n = cam_cfg.get("detect_every_n_frames", 3)

        # ---- Face detection ----
        det_cfg = config.get("face_detection", {})
        perf_cfg = config.get("performance", {})
        self.detector = FaceDetector(
            model_pack=det_cfg.get("model_pack", "buffalo_l"),
            min_confidence=det_cfg.get("min_confidence", 0.5),
            min_face_size=det_cfg.get("min_face_size", 60),
            detection_resize_width=perf_cfg.get("detection_resize_width", 640),
            use_gpu=perf_cfg.get("use_gpu", False),
        )

        # ---- Embedder ----
        self.embedder = Embedder()

        # ---- Matcher ----
        rec_cfg = config.get("recognition", {})
        self.matcher = FaceMatcher(
            similarity_threshold=rec_cfg.get("similarity_threshold", 0.40),
        )
        self.matcher.reload(self.db)
        self.consecutive_required = rec_cfg.get("consecutive_frames_required", 3)

        # ---- Tracker ----
        trk_cfg = config.get("tracking", {})
        self.tracker = CentroidTracker(
            max_link_distance=trk_cfg.get("max_link_distance", 120),
            max_frames_missing=trk_cfg.get("max_frames_missing", 15),
        )

        # ---- Event detector (presence or door_line mode) ----
        self.greeting_mode = config.get("greeting", {}).get("mode", "presence")
        self.event_detector = None  # initialised in start()

        # ---- TTS ----
        self.tts: Optional[TTSEngine] = None
        if not no_tts:
            tts_cfg = config.get("tts", {})
            self.tts = TTSEngine(
                rate=tts_cfg.get("rate", 170),
                volume=tts_cfg.get("volume", 0.9),
            )

        # ---- Greeting templates ----
        greet_cfg = config.get("greeting", {})
        self.entry_tpl = greet_cfg.get("entry_template", "Hey {name}, welcome!")
        self.exit_tpl = greet_cfg.get("exit_template", "Bye {name}, see you later!")
        self.unknown_entry = greet_cfg.get("unknown_entry", "Hello! Please check in at reception.")
        self.unknown_exit = greet_cfg.get("unknown_exit", "Goodbye! Have a nice day.")
        self.cooldown_seconds = greet_cfg.get("cooldown_seconds", 300)

        # ---- Stats ----
        self._frame_count = 0       # monotonic, used for detect_every_n
        self._fps_frame_count = 0   # reset every second, only for FPS display
        self._fps_time = time.time()
        self._fps = 0.0

        # ---- Visual event banner ----
        self._event_banner: Optional[str] = None
        self._event_banner_until: float = 0.0

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        self.camera.start()
        time.sleep(0.5)  # let camera warm up

        w, h = self.camera.resolution

        if self.greeting_mode == "door_line":
            door_cfg = self.config.get("door_line", {})
            self.event_detector = DoorLineCrossingDetector(
                frame_width=w,
                frame_height=h,
                orientation=door_cfg.get("orientation", "horizontal"),
                position_frac=door_cfg.get("position", 0.50),
                inside_direction=door_cfg.get("inside_direction", "below"),
                cooldown_seconds=self.cooldown_seconds,
                consecutive_frames_required=self.consecutive_required,
            )
        else:
            self.event_detector = PresenceEventDetector(
                cooldown_seconds=self.cooldown_seconds,
                consecutive_frames_required=self.consecutive_required,
            )

        self._running = True
        self.logger.info(
            "Pipeline started  resolution=%dx%d  greeting_mode=%s",
            w, h, self.greeting_mode,
        )

    def stop(self) -> None:
        self._running = False

        # ---- Force goodbye for anyone still visible (bypasses cooldown) ----
        if self.event_detector and isinstance(self.event_detector, PresenceEventDetector):
            events = self.event_detector.force_goodbye_all()
            if events:
                self.logger.info(
                    "Flushing goodbye for %d greeted track(s) on shutdown",
                    len(events),
                )
                for event in events:
                    self._handle_event(event)

        # ---- Camera ----
        self.camera.stop()

        # ---- TTS – wait for queued messages to finish ----
        if self.tts:
            self.tts.wait_and_shutdown()

        # ---- DB ----
        self.db.close()

        # ---- Display ----
        if not self.no_display:
            cv2.destroyAllWindows()
        self.logger.info("Pipeline stopped")

    # ------------------------------------------------------------------ #
    #  Main loop
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """Main blocking loop. Press 'q' in the display window to exit."""
        self.start()
        signal.signal(signal.SIGINT, lambda *_: self._signal_stop())

        self.logger.info("Entering main loop. Press 'q' to quit.")

        try:
            while self._running:
                frame = self.camera.read()
                if frame is None:
                    time.sleep(0.01)
                    continue

                self._frame_count += 1
                self._fps_frame_count += 1
                self._update_fps()

                # --- Detection (every N frames for performance) ---
                if self._frame_count % self.detect_every_n == 0:
                    faces = self.detector.detect(frame)
                    faces = self.embedder.extract(faces)

                    # Build detection list for tracker
                    detections = [(f.center, f.bbox) for f in faces]
                    tracks, lost_tracks = self.tracker.update(detections)

                    # Match identities
                    for track in tracks:
                        best_face = None
                        best_dist = float("inf")
                        for f in faces:
                            d = np.linalg.norm(
                                np.array(f.center) - np.array(track.center)
                            )
                            if d < best_dist:
                                best_dist = d
                                best_face = f

                        if best_face is not None and best_face.embedding is not None:
                            result = self.matcher.match(best_face.embedding)
                            if result:
                                track.update_identity(
                                    result.person_id, result.name, result.similarity
                                )
                            else:
                                track.update_identity(None, "Unknown", 0.0)

                    # Check for greeting / goodbye events
                    if self.event_detector:
                        if isinstance(self.event_detector, PresenceEventDetector):
                            events = self.event_detector.check_tracks(tracks, lost_tracks)
                        else:
                            events = self.event_detector.check_tracks(tracks, lost_tracks)
                        for event in events:
                            self._handle_event(event)
                else:
                    # Between detection frames, don't update tracker
                    # (tracks keep their current state)
                    tracks = list(self.tracker.tracks.values())
                    lost_tracks = []

                # --- Display ---
                if not self.no_display:
                    display = self._draw_overlay(frame, tracks)
                    cv2.imshow("Reception Greeter", display)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        self.logger.info("Quit key pressed")
                        break
                    elif key == ord("r"):
                        # Reload matcher (hot-reload after enrollment)
                        self.matcher.reload(self.db)
                        self.logger.info("Matcher reloaded (hot-reload)")

        finally:
            self.stop()

    def _signal_stop(self) -> None:
        self.logger.info("SIGINT received – stopping")
        self._running = False

    # ------------------------------------------------------------------ #
    #  Event handling
    # ------------------------------------------------------------------ #

    def _handle_event(self, event: CrossingEvent) -> None:
        """Process a crossing event: log, audit, TTS."""
        if event.event_type == EventType.ENTRY:
            if event.person_id is not None:
                msg = self.entry_tpl.format(name=event.name)
            else:
                msg = self.unknown_entry
        else:
            if event.person_id is not None:
                msg = self.exit_tpl.format(name=event.name)
            else:
                msg = self.unknown_exit

        # Audit log
        self.audit.info(
            "%s | %s | sim=%.3f | track=%d",
            event.event_type.value.upper(),
            event.name,
            event.similarity,
            event.track_id,
        )

        # Database event log
        self.db.log_event(
            event_type=event.event_type.value,
            person_id=event.person_id,
            person_name=event.name,
            confidence=event.similarity,
        )

        # TTS
        if self.tts:
            self.tts.speak(msg)

        # Visual banner (show on screen for 4 seconds)
        self._event_banner = msg
        self._event_banner_until = time.time() + 4.0

        # Console output so user sees it immediately
        print(f"\n{'='*50}")
        print(f"  >> {event.event_type.value.upper()}: {msg}")
        print(f"{'='*50}\n")

        self.logger.info("GREETING: %s", msg)

    # ------------------------------------------------------------------ #
    #  Visualisation
    # ------------------------------------------------------------------ #

    def _draw_overlay(self, frame: np.ndarray, tracks) -> np.ndarray:
        display = frame.copy()

        # Draw door line (only in door_line mode)
        if isinstance(self.event_detector, DoorLineCrossingDetector):
            self.event_detector.draw_line(display)

        # Draw tracks
        for track in tracks:
            x1, y1, x2, y2 = track.bbox
            # Color: green for known, red for unknown
            color = (0, 255, 0) if track.person_id else (0, 0, 255)
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

            label = f"{track.name}"
            if track.similarity > 0:
                label += f" ({track.similarity:.2f})"
            label += f" [T{track.track_id}]"

            # Background for text
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(display, (x1, y1 - th - 10), (x1 + tw, y1), color, -1)
            cv2.putText(
                display, label, (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
            )

            # Draw center history (motion trail)
            pts = track.center_history[-20:]
            for i in range(1, len(pts)):
                cv2.line(
                    display,
                    (int(pts[i - 1][0]), int(pts[i - 1][1])),
                    (int(pts[i][0]), int(pts[i][1])),
                    (255, 255, 0), 1,
                )

        # FPS counter
        cv2.putText(
            display,
            f"FPS: {self._fps:.1f}  Tracks: {len(tracks)}",
            (10, display.shape[0] - 15),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2,
        )

        # Event banner (large text across top of frame)
        if self._event_banner and time.time() < self._event_banner_until:
            banner = self._event_banner
            (bw, bh), _ = cv2.getTextSize(banner, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
            bx = (display.shape[1] - bw) // 2
            by = 50
            # Semi-transparent dark background
            overlay = display.copy()
            cv2.rectangle(overlay, (bx - 20, by - bh - 15), (bx + bw + 20, by + 15), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, display, 0.4, 0, display)
            cv2.putText(
                display, banner, (bx, by),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3,
            )

        # Matcher info
        if self.matcher.is_empty:
            cv2.putText(
                display,
                "NO ENROLLED FACES - Run enrollment first!",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
            )

        # Instructions
        cv2.putText(
            display,
            "q=quit  r=reload-db",
            (display.shape[1] - 220, display.shape[0] - 15),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1,
        )

        return display

    def _update_fps(self) -> None:
        now = time.time()
        elapsed = now - self._fps_time
        if elapsed >= 1.0:
            self._fps = self._fps_frame_count / elapsed
            self._fps_frame_count = 0
            self._fps_time = now


# ====================================================================== #
#  CLI entry point
# ====================================================================== #

def main():
    parser = argparse.ArgumentParser(description="Reception Greeter – Real-time pipeline")
    parser.add_argument("--config", default="app/config.yaml", help="Config YAML path")
    parser.add_argument("--no-display", action="store_true", help="Run headless (no GUI)")
    parser.add_argument("--no-tts", action="store_true", help="Disable text-to-speech")
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    setup_logging(config)
    pipeline = ReceptionPipeline(config, no_display=args.no_display, no_tts=args.no_tts)
    pipeline.run()


if __name__ == "__main__":
    main()
