"""
Reception Greeter – Threaded camera capture.

Reads frames from USB/RTSP/CSI camera in a background thread so the main
pipeline never blocks on I/O.

Supports:
- USB cameras (V4L2, DirectShow, AVFoundation)
- CSI ribbon cameras via GStreamer (RPi libcamerasrc, RB5 qtiqmmfsrc)
- RTSP / CCTV network cameras via GStreamer or OpenCV
- Auto-discovery: pass source="auto" to scan for best camera
- Automatic reconnection on frame-read failures
"""

from __future__ import annotations

import logging
import threading
import time
from typing import List, Optional, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Camera:
    """Thread-safe, non-blocking camera reader with auto-discovery."""

    def __init__(
        self,
        source: Union[int, str] = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        use_gstreamer: bool = False,
        gstreamer_pipeline: Optional[str] = None,
        reconnect_delay: float = 2.0,
        max_reconnect_attempts: int = 5,
    ) -> None:
        self._source = source
        self._width = width
        self._height = height
        self._fps = fps
        self._use_gstreamer = use_gstreamer
        self._gstreamer_pipeline = gstreamer_pipeline
        self._reconnect_delay = reconnect_delay
        self._max_reconnect = max_reconnect_attempts

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._consecutive_failures = 0

        # Resolved source after auto-discovery
        self._resolved_source: Optional[object] = None

    # ------------------------------------------------------------------ #
    #  Auto-discovery
    # ------------------------------------------------------------------ #

    def _auto_discover_source(self) -> object:
        """Find the best available camera automatically."""
        try:
            from app.hardware.camera_discovery import discover_cameras
            cameras = discover_cameras(validate=True, scan_network=False)
            if cameras:
                best = cameras[0]
                logger.info("Auto-discovered camera: %s (source=%s)", best.name, best.source)
                return best.source
        except ImportError:
            logger.debug("Hardware discovery module not available, falling back to index 0")
        except Exception as e:
            logger.warning("Camera auto-discovery failed: %s – falling back to index 0", e)
        return 0

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    def _open_capture(self) -> cv2.VideoCapture:
        """Open the VideoCapture with appropriate backend."""
        # Resolve "auto" source
        if isinstance(self._source, str) and self._source.lower() == "auto":
            self._resolved_source = self._auto_discover_source()
        else:
            self._resolved_source = self._source

        source = self._resolved_source

        # GStreamer pipeline (for CSI cameras on RPi/RB5 or RTSP)
        if self._gstreamer_pipeline:
            logger.info("Opening GStreamer pipeline: %s", self._gstreamer_pipeline)
            return cv2.VideoCapture(self._gstreamer_pipeline, cv2.CAP_GSTREAMER)

        if self._use_gstreamer and isinstance(source, str) and source.startswith("rtsp"):
            # Build a GStreamer pipeline for RTSP
            from app.hardware.camera_discovery import CameraInfo, CameraType, build_gstreamer_pipeline
            cam_info = CameraInfo(camera_type=CameraType.RTSP, source=source)
            pipeline = build_gstreamer_pipeline(cam_info, self._width, self._height, self._fps)
            if pipeline:
                logger.info("Opening RTSP via GStreamer: %s", pipeline)
                return cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

        # Standard OpenCV capture
        return cv2.VideoCapture(source)

    def start(self) -> None:
        if self._running:
            return
        self._cap = self._open_capture()
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
            self._resolved_source, actual_w, actual_h, actual_fps,
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
    #  Background reader (with auto-reconnect)
    # ------------------------------------------------------------------ #

    def _reader_loop(self) -> None:
        """Continuously read frames in background thread with reconnection."""
        while self._running:
            if self._cap is None:
                break
            ok, frame = self._cap.read()
            if not ok:
                self._consecutive_failures += 1
                if self._consecutive_failures >= 30:
                    logger.warning(
                        "Camera lost (%d failures) – attempting reconnect...",
                        self._consecutive_failures,
                    )
                    self._reconnect()
                else:
                    time.sleep(0.1)
                continue

            self._consecutive_failures = 0
            with self._lock:
                self._frame = frame
                self._frame_count += 1

    def _reconnect(self) -> None:
        """Attempt to reconnect to the camera."""
        for attempt in range(1, self._max_reconnect + 1):
            logger.info("Reconnect attempt %d/%d...", attempt, self._max_reconnect)
            try:
                if self._cap:
                    self._cap.release()
                time.sleep(self._reconnect_delay)
                self._cap = self._open_capture()
                if self._cap.isOpened():
                    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
                    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
                    self._cap.set(cv2.CAP_PROP_FPS, self._fps)
                    self._consecutive_failures = 0
                    logger.info("Camera reconnected successfully")
                    return
            except Exception as e:
                logger.warning("Reconnect attempt %d failed: %s", attempt, e)

        logger.error("All reconnect attempts failed – camera reader stopping")
        self._running = False

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
