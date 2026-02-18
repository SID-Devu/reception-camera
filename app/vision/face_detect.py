"""
Reception Greeter – Face detection using InsightFace (RetinaFace / SCRFD).

Wraps the InsightFace ``FaceAnalysis`` model to return bounding boxes,
landmarks, and quality scores for each detected face in a frame.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    """Container for a single detected face."""
    bbox: np.ndarray            # [x1, y1, x2, y2]
    landmarks: np.ndarray       # 5x2 keypoints
    det_score: float            # detection confidence
    aligned_face: Optional[np.ndarray] = None   # 112x112 aligned crop
    embedding: Optional[np.ndarray] = None       # filled later by Embedder
    quality: float = 0.0

    @property
    def center(self) -> tuple:
        cx = (self.bbox[0] + self.bbox[2]) / 2
        cy = (self.bbox[1] + self.bbox[3]) / 2
        return (cx, cy)

    @property
    def width(self) -> float:
        return float(self.bbox[2] - self.bbox[0])

    @property
    def height(self) -> float:
        return float(self.bbox[3] - self.bbox[1])


class FaceDetector:
    """
    Detect and align faces using InsightFace.

    Internally uses ``insightface.app.FaceAnalysis`` which bundles
    SCRFD / RetinaFace detection + 2-D landmark alignment.
    """

    def __init__(
        self,
        model_pack: str = "buffalo_l",
        min_confidence: float = 0.5,
        min_face_size: int = 60,
        detection_resize_width: int = 640,
        use_gpu: bool = False,
    ) -> None:
        import insightface
        from insightface.app import FaceAnalysis

        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu else ["CPUExecutionProvider"]
        self._app = FaceAnalysis(
            name=model_pack,
            providers=providers,
        )
        self._app.prepare(ctx_id=0 if use_gpu else -1, det_size=(detection_resize_width, detection_resize_width))

        self._min_conf = min_confidence
        self._min_face_size = min_face_size
        logger.info(
            "FaceDetector ready  model=%s  min_conf=%.2f  min_face=%dpx  gpu=%s",
            model_pack, min_confidence, min_face_size, use_gpu,
        )

    def detect(self, frame: np.ndarray) -> List[DetectedFace]:
        """
        Detect faces in a BGR frame.

        Returns list of ``DetectedFace`` with aligned crops and embeddings
        pre-populated by InsightFace.
        """
        faces_raw = self._app.get(frame)
        results: List[DetectedFace] = []

        for f in faces_raw:
            score = float(f.det_score)
            if score < self._min_conf:
                continue
            bbox = f.bbox.astype(int)
            w = bbox[2] - bbox[0]
            if w < self._min_face_size:
                continue

            det = DetectedFace(
                bbox=bbox,
                landmarks=f.kps if hasattr(f, "kps") else f.landmark_2d_106[:5] if hasattr(f, "landmark_2d_106") else np.zeros((5, 2)),
                det_score=score,
                embedding=f.embedding if hasattr(f, "embedding") and f.embedding is not None else None,
            )

            # Quality: Laplacian variance of the face crop
            x1, y1, x2, y2 = bbox
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
            crop = frame[y1:y2, x1:x2]
            if crop.size > 0:
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                det.quality = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            results.append(det)

        return results
