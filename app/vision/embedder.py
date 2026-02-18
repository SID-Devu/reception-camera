"""
Reception Greeter – Face embedding extractor.

InsightFace's FaceAnalysis already computes embeddings during detect().
This module exists as an explicit step in the pipeline and provides
utilities for normalisation and batch extraction, plus a fallback
for cases where InsightFace didn't populate the embedding.
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from app.vision.face_detect import DetectedFace

logger = logging.getLogger(__name__)


class Embedder:
    """
    Extract / normalise face embeddings.

    The primary path is that ``FaceDetector.detect()`` already fills
    ``DetectedFace.embedding`` via InsightFace.  This class normalises
    them (L2) and provides batch helpers.
    """

    def __init__(self) -> None:
        logger.info("Embedder initialised (uses InsightFace inline embeddings)")

    @staticmethod
    def normalise(embedding: np.ndarray) -> np.ndarray:
        """L2-normalise an embedding vector."""
        norm = np.linalg.norm(embedding)
        if norm < 1e-10:
            return embedding
        return embedding / norm

    def extract(self, faces: List[DetectedFace]) -> List[DetectedFace]:
        """
        Ensure every DetectedFace has a normalised embedding.
        Faces without an embedding are dropped with a warning.
        """
        valid: List[DetectedFace] = []
        for f in faces:
            if f.embedding is None:
                logger.debug("Face at %s has no embedding – skipping", f.bbox)
                continue
            f.embedding = self.normalise(f.embedding)
            valid.append(f)
        return valid
