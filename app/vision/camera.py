"""
Reception Greeter – Threaded camera capture.

Reads frames from USB/RTSP camera in a background thread so the main
pipeline never blocks on I/O.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Camera:
    """Thread-safe, non-blocking camera reader."""

    def __init__(
        self,
        source: Union[int, str] = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
    ) -> None:
        self._source = source
        self._width = width
        self._height = height
        self._fps = fps

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        if self._running:
            return
        self._cap = cv2.VideoCapture(self._source)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera source: {self._source}")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        self._cap.set(cv2.CAP_PROP_FPS, self._fps)

        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        logger.info(
            "Camera opened: %s  resolution=%dx%d  fps=%.1f",
            self._source, actual_w, actual_h, actual_fps,
        )

        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._cap:
            self._cap.release()
            self._cap = None
        logger.info("Camera stopped. Total frames read: %d", self._frame_count)

    # ------------------------------------------------------------------ #
    #  Background reader
    # ------------------------------------------------------------------ #

    def _reader_loop(self) -> None:
        """Continuously read frames in background thread."""
        while self._running:
            if self._cap is None:
                break
            ok, frame = self._cap.read()
            if not ok:
                logger.warning("Frame read failed – retrying in 0.1s")
                time.sleep(0.1)
                continue
            with self._lock:
                self._frame = frame
                self._frame_count += 1

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def read(self) -> Optional[np.ndarray]:
        """Return the latest frame (or None if not available yet)."""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def resolution(self) -> tuple:
        if self._cap:
            return (
                int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
        return (self._width, self._height)
