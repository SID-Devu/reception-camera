"""
Reception Greeter – Face matcher (cosine similarity against DB).

Loads all enrolled embeddings into memory for fast lookup, with
a hot-reload mechanism when new persons are enrolled.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from numpy.linalg import norm as np_norm

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    person_id: int
    name: str
    similarity: float


class FaceMatcher:
    """
    Match a query embedding against the enrolled face database.

    Maintains an in-memory matrix of all embeddings for fast vectorised
    cosine similarity.  Call ``reload()`` after enrollment changes.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.40,
    ) -> None:
        self.threshold = similarity_threshold

        # These are populated by reload()
        self._emb_matrix: np.ndarray = np.empty((0, 512), dtype=np.float32)
        self._person_ids: List[int] = []
        self._id_to_name: Dict[int, str] = {}
        self._lock = threading.Lock()

        logger.info("FaceMatcher initialised  threshold=%.3f", self.threshold)

    # ------------------------------------------------------------------ #
    #  Load / reload from DB
    # ------------------------------------------------------------------ #

    def reload(self, db) -> None:
        """
        Reload embedding matrix and name map from the database.
        ``db`` must be an instance of ``app.db.storage.FaceDB``.
        """
        emb_matrix, person_ids = db.get_all_embeddings_flat()
        id_name = db.build_id_name_map()

        with self._lock:
            self._emb_matrix = emb_matrix
            self._person_ids = person_ids
            self._id_to_name = id_name

        logger.info(
            "Matcher reloaded: %d embeddings for %d persons",
            len(person_ids), len(id_name),
        )

    @property
    def is_empty(self) -> bool:
        return len(self._person_ids) == 0

    # ------------------------------------------------------------------ #
    #  Matching
    # ------------------------------------------------------------------ #

    def match(self, query_embedding: np.ndarray) -> Optional[MatchResult]:
        """
        Find the best-matching person for a query embedding.

        Returns ``MatchResult`` if similarity ≥ threshold, else ``None``.
        """
        with self._lock:
            if self._emb_matrix.shape[0] == 0:
                return None

            # Cosine similarity: dot product of L2-normalised vectors
            query_norm = query_embedding / (np_norm(query_embedding) + 1e-10)
            db_norms = self._emb_matrix / (
                np_norm(self._emb_matrix, axis=1, keepdims=True) + 1e-10
            )
            sims = db_norms @ query_norm  # shape (N,)

            best_idx = int(np.argmax(sims))
            best_sim = float(sims[best_idx])

            if best_sim < self.threshold:
                return None

            pid = self._person_ids[best_idx]
            name = self._id_to_name.get(pid, "Unknown")
            return MatchResult(person_id=pid, name=name, similarity=best_sim)

    def match_top_k(
        self, query_embedding: np.ndarray, k: int = 3
    ) -> List[MatchResult]:
        """Return top-k matches above threshold (useful for debugging)."""
        with self._lock:
            if self._emb_matrix.shape[0] == 0:
                return []

            query_norm = query_embedding / (np_norm(query_embedding) + 1e-10)
            db_norms = self._emb_matrix / (
                np_norm(self._emb_matrix, axis=1, keepdims=True) + 1e-10
            )
            sims = db_norms @ query_norm

            top_indices = np.argsort(sims)[::-1][:k]
            results = []
            for idx in top_indices:
                sim = float(sims[idx])
                if sim < self.threshold:
                    break
                pid = self._person_ids[idx]
                name = self._id_to_name.get(pid, "Unknown")
                results.append(MatchResult(person_id=pid, name=name, similarity=sim))
            return results
