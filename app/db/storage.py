"""
Reception Greeter – Database storage layer (SQLite).

Handles all persistence: persons, embeddings, and audit events.
Thread-safe via connection-per-call pattern.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

_DIR = Path(__file__).resolve().parent
_SCHEMA_FILE = _DIR / "schema.sql"


class FaceDB:
    """SQLite-backed storage for persons, embeddings and events."""

    def __init__(self, db_path: str) -> None:
        self._db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    # ------------------------------------------------------------------ #
    #  Connection helpers
    # ------------------------------------------------------------------ #

    def _conn(self) -> sqlite3.Connection:
        """Return a thread-local connection."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        with open(_SCHEMA_FILE, "r") as f:
            schema_sql = f.read()
        conn = self._conn()
        conn.executescript(schema_sql)
        conn.commit()

    # ------------------------------------------------------------------ #
    #  Person CRUD
    # ------------------------------------------------------------------ #

    def add_person(self, name: str, role: str = "") -> int:
        """Insert a new person. Returns person_id."""
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO persons (name, role) VALUES (?, ?)",
            (name, role),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_person_by_name(self, name: str) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT * FROM persons WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None

    def get_person_by_id(self, person_id: int) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT * FROM persons WHERE person_id = ?", (person_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_persons(self) -> List[dict]:
        rows = self._conn().execute("SELECT * FROM persons ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def delete_person(self, person_id: int) -> None:
        """Delete person and their embeddings (CASCADE)."""
        conn = self._conn()
        conn.execute("DELETE FROM persons WHERE person_id = ?", (person_id,))
        conn.commit()

    def person_exists(self, name: str) -> bool:
        return self.get_person_by_name(name) is not None

    # ------------------------------------------------------------------ #
    #  Embedding CRUD
    # ------------------------------------------------------------------ #

    @staticmethod
    def _serialize_embedding(emb: np.ndarray) -> bytes:
        return emb.astype(np.float32).tobytes()

    @staticmethod
    def _deserialize_embedding(blob: bytes, dim: int = 512) -> np.ndarray:
        return np.frombuffer(blob, dtype=np.float32).copy().reshape(dim)

    def add_embedding(
        self,
        person_id: int,
        embedding: np.ndarray,
        quality_score: float = 0.0,
    ) -> int:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO embeddings (person_id, embedding, dim, quality_score) VALUES (?, ?, ?, ?)",
            (person_id, self._serialize_embedding(embedding), embedding.shape[0], quality_score),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def add_embeddings_bulk(
        self,
        person_id: int,
        embeddings: List[np.ndarray],
        quality_scores: Optional[List[float]] = None,
    ) -> None:
        conn = self._conn()
        if quality_scores is None:
            quality_scores = [0.0] * len(embeddings)
        conn.executemany(
            "INSERT INTO embeddings (person_id, embedding, dim, quality_score) VALUES (?, ?, ?, ?)",
            [
                (person_id, self._serialize_embedding(e), e.shape[0], q)
                for e, q in zip(embeddings, quality_scores)
            ],
        )
        conn.commit()

    def get_embeddings_for_person(self, person_id: int) -> List[np.ndarray]:
        rows = self._conn().execute(
            "SELECT embedding, dim FROM embeddings WHERE person_id = ?",
            (person_id,),
        ).fetchall()
        return [self._deserialize_embedding(r["embedding"], r["dim"]) for r in rows]

    def get_all_embeddings(self) -> Dict[int, List[np.ndarray]]:
        """Return {person_id: [emb1, emb2, ...]} for all persons."""
        rows = self._conn().execute(
            "SELECT person_id, embedding, dim FROM embeddings ORDER BY person_id"
        ).fetchall()
        result: Dict[int, List[np.ndarray]] = {}
        for r in rows:
            pid = r["person_id"]
            result.setdefault(pid, []).append(
                self._deserialize_embedding(r["embedding"], r["dim"])
            )
        return result

    def get_all_embeddings_flat(self) -> Tuple[np.ndarray, List[int]]:
        """
        Return (matrix NxD, person_ids list) for fast batch matching.
        Returns empty arrays when no embeddings exist.
        """
        rows = self._conn().execute(
            "SELECT person_id, embedding, dim FROM embeddings"
        ).fetchall()
        if not rows:
            return np.empty((0, 512), dtype=np.float32), []
        embs = []
        pids = []
        for r in rows:
            embs.append(self._deserialize_embedding(r["embedding"], r["dim"]))
            pids.append(r["person_id"])
        return np.vstack(embs), pids

    def count_embeddings(self, person_id: int) -> int:
        row = self._conn().execute(
            "SELECT COUNT(*) as cnt FROM embeddings WHERE person_id = ?",
            (person_id,),
        ).fetchone()
        return row["cnt"]

    def delete_embeddings_for_person(self, person_id: int) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM embeddings WHERE person_id = ?", (person_id,))
        conn.commit()

    # ------------------------------------------------------------------ #
    #  Audit events
    # ------------------------------------------------------------------ #

    def log_event(
        self,
        event_type: str,
        person_id: Optional[int] = None,
        person_name: str = "Unknown",
        confidence: float = 0.0,
    ) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT INTO events (person_id, person_name, event_type, confidence) VALUES (?, ?, ?, ?)",
            (person_id, person_name, event_type, confidence),
        )
        conn.commit()

    def get_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        since: Optional[str] = None,
    ) -> List[dict]:
        query = "SELECT * FROM events WHERE 1=1"
        params: list = []
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self._conn().execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  ID ↔ name helpers
    # ------------------------------------------------------------------ #

    def build_id_name_map(self) -> Dict[int, str]:
        rows = self._conn().execute("SELECT person_id, name FROM persons").fetchall()
        return {r["person_id"]: r["name"] for r in rows}

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn:
            conn.close()
            self._local.conn = None
