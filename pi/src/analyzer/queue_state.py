from __future__ import annotations

"""Queue state machine for tracked persons."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from loguru import logger

from config import Settings
from db_models import PersonEvent


class TrackedPerson(Protocol):
    """Protocol for tracked person-like objects."""

    track_id: int


@dataclass(slots=True)
class TrackRecord:
    """Represents one active in-zone track."""

    track_id: int
    first_seen: datetime
    last_seen: datetime


class QueueStateTracker:
    """Track active queue members and emit completed person events."""

    def __init__(self, settings: Settings) -> None:
        """Initialize queue state tracker."""

        self._settings = settings
        self._active_tracks: dict[int, TrackRecord] = {}

    def update(
        self, in_zone_persons: list[TrackedPerson], frame_time: datetime
    ) -> list[PersonEvent]:
        """Update active tracks and return completed events."""

        current_track_ids = {person.track_id for person in in_zone_persons}
        for person in in_zone_persons:
            record = self._active_tracks.get(person.track_id)
            if record is None:
                self._active_tracks[person.track_id] = TrackRecord(
                    track_id=person.track_id,
                    first_seen=frame_time,
                    last_seen=frame_time,
                )
            else:
                record.last_seen = frame_time

        completed: list[PersonEvent] = []
        departed_ids = [
            track_id
            for track_id in self._active_tracks
            if track_id not in current_track_ids
        ]
        for track_id in departed_ids:
            record = self._active_tracks.pop(track_id)
            exit_time = frame_time
            dwell = (exit_time - record.first_seen).total_seconds()
            if dwell >= self._settings.min_dwell_seconds:
                event = PersonEvent(
                    track_id=track_id,
                    entry_time=record.first_seen,
                    exit_time=exit_time,
                    dwell_seconds=dwell,
                    date_hour=exit_time.strftime("%Y-%m-%dT%H"),
                )
                completed.append(event)
                logger.info(
                    "Person exited queue zone | track_id={} dwell_seconds={:.2f}",
                    track_id,
                    dwell,
                )
        return completed

    @property
    def current_queue_length(self) -> int:
        """Return current active queue length."""

        return len(self._active_tracks)
