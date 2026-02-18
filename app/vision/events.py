"""
Reception Greeter – Entry / Exit event detection.

Two modes:
  * **presence** (default) – fire ENTRY when a confirmed identity first
    appears; fire EXIT when the track is lost (face leaves camera view).
  * **door_line** – fire events when a tracked face crosses a virtual
    line drawn across the frame.

Both modes respect per-person cooldowns to avoid repeated greetings.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from app.vision.tracker import Track

logger = logging.getLogger(__name__)


class EventType(Enum):
    ENTRY = "entry"
    EXIT = "exit"


@dataclass
class CrossingEvent:
    event_type: EventType
    track_id: int
    person_id: Optional[int]
    name: str
    similarity: float
    timestamp: float


# ====================================================================== #
#  Presence-based detector (default)
# ====================================================================== #

class PresenceEventDetector:
    """
    Fire ENTRY when a person is first recognised (identity_streak
    reaches *consecutive_frames_required*).  Fire EXIT when the
    track disappears (face leaves the camera view).

    This is the recommended mode for reception cameras / webcams
    where people don't physically walk across a line.
    """

    def __init__(
        self,
        cooldown_seconds: float = 300.0,
        consecutive_frames_required: int = 3,
    ) -> None:
        self._cooldown = cooldown_seconds
        self._consecutive = consecutive_frames_required

        # track_id → info of tracks that already fired an ENTRY
        self._greeted_tracks: Dict[int, _GreetedInfo] = {}
        # person-name:event_type → last-fire timestamp (cooldown)
        self._last_event_time: Dict[str, float] = {}

        logger.info(
            "PresenceEventDetector ready  cooldown=%ds  streak_required=%d",
            cooldown_seconds, consecutive_frames_required,
        )

    # ---- cooldown helpers ---- #

    def _ck(self, name: str, et: EventType) -> str:
        return f"{name}:{et.value}"

    def _is_cooled_down(self, name: str, et: EventType) -> bool:
        return (time.time() - self._last_event_time.get(self._ck(name, et), 0.0)) > self._cooldown

    def _record(self, name: str, et: EventType) -> None:
        self._last_event_time[self._ck(name, et)] = time.time()

    # ---- main API ---- #

    def check_tracks(
        self,
        active_tracks: List[Track],
        lost_tracks: List[Track],
    ) -> List[CrossingEvent]:
        """
        Call every detection frame.

        Parameters
        ----------
        active_tracks : current tracks returned by the tracker.
        lost_tracks   : tracks that were just removed from the tracker
                        (face left the view).
        """
        events: List[CrossingEvent] = []

        # --- ENTRY: recognised person whose identity streak just reached threshold ---
        for track in active_tracks:
            if track.track_id in self._greeted_tracks:
                continue  # already greeted

            # Require confirmed identity
            if track.person_id is None:
                continue
            if track.identity_streak < self._consecutive:
                continue

            name = track.name
            if not self._is_cooled_down(name, EventType.ENTRY):
                continue

            event = CrossingEvent(
                event_type=EventType.ENTRY,
                track_id=track.track_id,
                person_id=track.person_id,
                name=name,
                similarity=track.similarity,
                timestamp=time.time(),
            )
            events.append(event)
            self._greeted_tracks[track.track_id] = _GreetedInfo(
                person_id=track.person_id, name=name, similarity=track.similarity,
            )
            self._record(name, EventType.ENTRY)
            logger.info(
                "EVENT ENTRY  track=%d  name=%s  sim=%.3f",
                track.track_id, name, track.similarity,
            )

        # --- EXIT: greeted tracks that have just disappeared ---
        for track in lost_tracks:
            info = self._greeted_tracks.pop(track.track_id, None)
            if info is None:
                continue  # was never greeted (unknown / too brief)

            name = info.name
            if not self._is_cooled_down(name, EventType.EXIT):
                continue

            event = CrossingEvent(
                event_type=EventType.EXIT,
                track_id=track.track_id,
                person_id=info.person_id,
                name=name,
                similarity=info.similarity,
                timestamp=time.time(),
            )
            events.append(event)
            self._record(name, EventType.EXIT)
            logger.info(
                "EVENT EXIT  track=%d  name=%s  sim=%.3f",
                track.track_id, name, info.similarity,
            )

        # Clean greeted-tracks for IDs that are no longer active
        active_ids = {t.track_id for t in active_tracks}
        for tid in list(self._greeted_tracks):
            if tid not in active_ids:
                # Track might have been purged without showing up in lost_tracks
                # (shouldn't happen, but be safe)
                info = self._greeted_tracks.pop(tid)
                name = info.name
                if self._is_cooled_down(name, EventType.EXIT):
                    events.append(CrossingEvent(
                        event_type=EventType.EXIT,
                        track_id=tid,
                        person_id=info.person_id,
                        name=name,
                        similarity=info.similarity,
                        timestamp=time.time(),
                    ))
                    self._record(name, EventType.EXIT)
                    logger.info("EVENT EXIT (cleanup)  track=%d  name=%s", tid, name)

        return events

    def force_goodbye_all(self) -> List[CrossingEvent]:
        """
        Force EXIT events for every currently-greeted track, ignoring cooldown.
        Used during pipeline shutdown to say goodbye to everyone still visible.
        """
        events: List[CrossingEvent] = []
        for tid, info in list(self._greeted_tracks.items()):
            event = CrossingEvent(
                event_type=EventType.EXIT,
                track_id=tid,
                person_id=info.person_id,
                name=info.name,
                similarity=info.similarity,
                timestamp=time.time(),
            )
            events.append(event)
            logger.info("EVENT EXIT (shutdown)  track=%d  name=%s", tid, info.name)
        self._greeted_tracks.clear()
        return events


@dataclass
class _GreetedInfo:
    person_id: Optional[int]
    name: str
    similarity: float


# ====================================================================== #
#  Door-line crossing detector (optional advanced mode)
# ====================================================================== #

class DoorLineCrossingDetector:
    """
    Detect entry / exit by watching tracks cross a virtual line.

    The line can be horizontal (splits top/bottom) or vertical (left/right).
    """

    def __init__(
        self,
        frame_width: int,
        frame_height: int,
        orientation: str = "horizontal",
        position_frac: float = 0.50,
        inside_direction: str = "below",
        cooldown_seconds: float = 300.0,
        consecutive_frames_required: int = 3,
    ) -> None:
        self._orientation = orientation
        self._inside_dir = inside_direction
        self._cooldown = cooldown_seconds
        self._consecutive = consecutive_frames_required

        if orientation == "horizontal":
            self._line_pos = int(frame_height * position_frac)
        else:
            self._line_pos = int(frame_width * position_frac)

        self._last_event_time: Dict[str, float] = {}
        self._fired_tracks: Dict[int, EventType] = {}

        logger.info(
            "DoorLine detector: %s at pixel %d, inside=%s, cooldown=%ds",
            orientation, self._line_pos, inside_direction, cooldown_seconds,
        )

    @property
    def line_position(self) -> int:
        return self._line_pos

    @property
    def orientation(self) -> str:
        return self._orientation

    def _get_coord(self, center: Tuple[float, float]) -> float:
        if self._orientation == "horizontal":
            return center[1]
        return center[0]

    def _is_inside(self, coord: float) -> bool:
        if self._inside_dir in ("below", "right"):
            return coord > self._line_pos
        return coord < self._line_pos

    def _ck(self, name: str, et: EventType) -> str:
        return f"{name}:{et.value}"

    def _is_cooled_down(self, name: str, et: EventType) -> bool:
        return (time.time() - self._last_event_time.get(self._ck(name, et), 0.0)) > self._cooldown

    def _record(self, name: str, et: EventType) -> None:
        self._last_event_time[self._ck(name, et)] = time.time()

    def check_tracks(
        self,
        active_tracks: List[Track],
        lost_tracks: List[Track] | None = None,
    ) -> List[CrossingEvent]:
        events: List[CrossingEvent] = []

        for track in active_tracks:
            if len(track.center_history) < 2:
                continue

            is_known = (
                track.person_id is not None
                and track.identity_streak >= self._consecutive
            )
            name = track.name if is_known else "Unknown"

            old_coord = self._get_coord(track.center_history[-2])
            new_coord = self._get_coord(track.center_history[-1])

            if self._is_inside(old_coord) == self._is_inside(new_coord):
                continue

            event_type = EventType.ENTRY if (not self._is_inside(old_coord) and self._is_inside(new_coord)) else EventType.EXIT

            if self._fired_tracks.get(track.track_id) == event_type:
                continue
            if not self._is_cooled_down(name, event_type):
                continue

            event = CrossingEvent(
                event_type=event_type,
                track_id=track.track_id,
                person_id=track.person_id if is_known else None,
                name=name,
                similarity=track.similarity,
                timestamp=time.time(),
            )
            events.append(event)
            self._fired_tracks[track.track_id] = event_type
            self._record(name, event_type)
            logger.info("EVENT: %s  track=%d  name=%s  sim=%.3f", event_type.value, track.track_id, name, track.similarity)

        active_ids = {t.track_id for t in active_tracks}
        self._fired_tracks = {k: v for k, v in self._fired_tracks.items() if k in active_ids}

        return events

    def draw_line(self, frame, color=(0, 255, 255), thickness=2):
        """Draw the door line on a frame for visualisation."""
        import cv2
        h, w = frame.shape[:2]
        if self._orientation == "horizontal":
            cv2.line(frame, (0, self._line_pos), (w, self._line_pos), color, thickness)
            cv2.putText(
                frame, "DOOR LINE", (10, self._line_pos - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
            )
        else:
            cv2.line(frame, (self._line_pos, 0), (self._line_pos, h), color, thickness)
            cv2.putText(
                frame, "DOOR LINE", (self._line_pos + 5, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
            )
