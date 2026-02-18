"""
Reception Greeter – Centroid-based face tracker.

Assigns stable integer IDs to faces across consecutive frames using
a simple centroid-distance approach.  This is lightweight and works
well for a reception scenario with a handful of people at a time.

Each track stores a short history of center-points so the
door-line crossing module can determine direction of travel.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.spatial.distance import cdist

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """A tracked identity over time."""
    track_id: int
    center: Tuple[float, float]
    bbox: np.ndarray
    person_id: Optional[int] = None   # filled when recognised
    name: str = "Unknown"
    similarity: float = 0.0
    frames_since_seen: int = 0
    # Rolling history of centre-points (newest last)
    center_history: List[Tuple[float, float]] = field(default_factory=list)
    # How many consecutive frames this track matched the same person
    identity_streak: int = 0
    _last_person_id: Optional[int] = None

    def update_position(self, center: Tuple[float, float], bbox: np.ndarray) -> None:
        self.center = center
        self.bbox = bbox
        self.frames_since_seen = 0
        self.center_history.append(center)
        # Keep last 60 positions
        if len(self.center_history) > 60:
            self.center_history = self.center_history[-60:]

    def update_identity(
        self, person_id: Optional[int], name: str, similarity: float
    ) -> None:
        if person_id is not None and person_id == self._last_person_id:
            self.identity_streak += 1
        else:
            self.identity_streak = 1
        self._last_person_id = person_id
        self.person_id = person_id
        self.name = name
        self.similarity = similarity


class CentroidTracker:
    """
    Track faces across frames using centroid distance.

    Parameters
    ----------
    max_link_distance : float
        Maximum pixel distance between centroids to consider them the same track.
    max_frames_missing : int
        Delete a track after this many frames without a detection.
    """

    def __init__(
        self,
        max_link_distance: float = 120.0,
        max_frames_missing: int = 15,
    ) -> None:
        self._next_id = 0
        self._tracks: OrderedDict[int, Track] = OrderedDict()
        self._max_dist = max_link_distance
        self._max_missing = max_frames_missing

    @property
    def tracks(self) -> Dict[int, Track]:
        return dict(self._tracks)

    def _new_track(
        self, center: Tuple[float, float], bbox: np.ndarray
    ) -> Track:
        t = Track(
            track_id=self._next_id,
            center=center,
            bbox=bbox,
            center_history=[center],
        )
        self._next_id += 1
        return t

    def update(
        self,
        detections: List[Tuple[Tuple[float, float], np.ndarray]],
    ) -> Tuple[List[Track], List[Track]]:
        """
        Update tracks with new detections.

        Parameters
        ----------
        detections : list of (center, bbox)
            Each entry is ((cx, cy), bbox_array).

        Returns
        -------
        (active_tracks, lost_tracks)
            active_tracks – tracks that are still alive after this update.
            lost_tracks   – tracks that were just deleted (face left view).
        """
        lost: List[Track] = []

        if len(detections) == 0:
            # Age all existing tracks
            lost_ids = []
            for tid, track in self._tracks.items():
                track.frames_since_seen += 1
                if track.frames_since_seen > self._max_missing:
                    lost_ids.append(tid)
            for tid in lost_ids:
                lost.append(self._tracks.pop(tid))
            return list(self._tracks.values()), lost

        det_centers = np.array([d[0] for d in detections])

        if len(self._tracks) == 0:
            # No existing tracks – create one per detection
            for center, bbox in detections:
                t = self._new_track(center, bbox)
                self._tracks[t.track_id] = t
            return list(self._tracks.values()), lost

        # Compute distance matrix: tracks × detections
        track_ids = list(self._tracks.keys())
        track_centers = np.array([self._tracks[tid].center for tid in track_ids])
        dist_matrix = cdist(track_centers, det_centers)

        # Greedy assignment (Hungarian is overkill for ≤10 faces)
        used_tracks = set()
        used_dets = set()
        assignments: List[Tuple[int, int]] = []

        # Sort all pairs by distance
        flat_indices = np.argsort(dist_matrix, axis=None)
        for flat_idx in flat_indices:
            ti = int(flat_idx // dist_matrix.shape[1])
            di = int(flat_idx % dist_matrix.shape[1])
            if ti in used_tracks or di in used_dets:
                continue
            if dist_matrix[ti, di] > self._max_dist:
                continue
            assignments.append((ti, di))
            used_tracks.add(ti)
            used_dets.add(di)
            if len(used_tracks) == len(track_ids) or len(used_dets) == len(detections):
                break

        # Apply assignments
        for ti, di in assignments:
            tid = track_ids[ti]
            center, bbox = detections[di]
            self._tracks[tid].update_position(center, bbox)

        # Create new tracks for unmatched detections
        for di in range(len(detections)):
            if di not in used_dets:
                center, bbox = detections[di]
                t = self._new_track(center, bbox)
                self._tracks[t.track_id] = t

        # Age and purge unmatched tracks
        lost_ids = []
        for i, tid in enumerate(track_ids):
            if i not in used_tracks:
                self._tracks[tid].frames_since_seen += 1
                if self._tracks[tid].frames_since_seen > self._max_missing:
                    lost_ids.append(tid)
        for tid in lost_ids:
            lost.append(self._tracks.pop(tid))

        return list(self._tracks.values()), lost

    def get_track(self, track_id: int) -> Optional[Track]:
        return self._tracks.get(track_id)

    def remove_track(self, track_id: int) -> None:
        self._tracks.pop(track_id, None)

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 0
