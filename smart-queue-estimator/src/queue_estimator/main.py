from __future__ import annotations

"""Main orchestrator for camera loop and API server."""

import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
import sys

import uvicorn
from loguru import logger

from queue_estimator.analyzer.queue_state import QueueStateTracker
from queue_estimator.analyzer.wait_time import WaitTimeEstimator
from queue_estimator.api.app import create_app
from queue_estimator.camera import make_camera
from queue_estimator.config import Settings, get_settings
from queue_estimator.database import create_db_and_tables, get_session
from queue_estimator.db_models import PersonEvent, QueueSnapshot
from queue_estimator.detection.detector import PersonDetector
from queue_estimator.detection.zone import QueueZone
from queue_estimator.display import make_display
from queue_estimator.schemas import QueueStatusResponse


class SharedState:
    """Thread-safe wrapper around latest queue status."""

    def __init__(self) -> None:
        """Initialize state container."""

        self._lock = threading.Lock()
        self._status: QueueStatusResponse | None = None
        self._broadcaster: Callable[[dict[str, object]], None] | None = None

    def set_broadcaster(self, broadcaster: Callable[[dict[str, object]], None]) -> None:
        """Set optional sync broadcaster callback."""

        self._broadcaster = broadcaster

    def broadcast(self, status: QueueStatusResponse) -> None:
        """Broadcast current status to websocket clients when available."""

        if self._broadcaster is None:
            return
        self._broadcaster(status.model_dump(mode="json"))

    def update(self, status: QueueStatusResponse) -> None:
        """Store latest queue status."""

        with self._lock:
            self._status = status

    def get(self) -> QueueStatusResponse | None:
        """Get latest queue status."""

        with self._lock:
            return self._status


def _humanize_wait(seconds: float) -> str:
    """Convert seconds to approximate human-readable text."""

    total = max(int(seconds), 0)
    minutes, rem_seconds = divmod(total, 60)
    return f"~{minutes} min {rem_seconds} sec"


def _persist_person_events(events: list[PersonEvent]) -> None:
    """Persist completed person events in a short-lived session."""

    if not events:
        return
    try:
        with get_session() as session:
            session.add_all(events)
            session.commit()
    except Exception:
        logger.warning("Person event write failed; retrying once")
        with get_session() as session:
            session.add_all(events)
            session.commit()


def _persist_snapshot(snapshot: QueueSnapshot) -> None:
    """Persist one queue snapshot."""

    try:
        with get_session() as session:
            session.add(snapshot)
            session.commit()
    except Exception:
        logger.warning("Snapshot write failed; retrying once")
        with get_session() as session:
            session.add(snapshot)
            session.commit()


def camera_loop(settings: Settings, state: SharedState) -> None:
    """Run queue estimation processing loop in a daemon thread."""

    detector = PersonDetector(settings)
    zone = QueueZone(settings.queue_zone)
    tracker = QueueStateTracker(settings)
    estimator = WaitTimeEstimator(settings)
    display = make_display()
    snapshot_interval_seconds = 60.0 / max(settings.snapshots_per_minute, 1)
    last_snapshot_time = time.monotonic()
    last_level: str | None = None

    try:
        with make_camera(settings) as camera:
            while True:
                loop_started_at = time.monotonic()
                try:
                    frame_time = datetime.now(UTC)
                    frame = camera.read_frame()
                    if frame is None:
                        logger.warning("Frame read failure from camera source")
                        time.sleep(0.1)
                        continue

                    inference_started_at = time.monotonic()
                    persons = detector.detect(frame)
                    inference_ms = (time.monotonic() - inference_started_at) * 1000.0

                    tracking_started_at = time.monotonic()
                    in_zone_persons = zone.filter_persons(persons, frame.shape[:2])
                    completed_events = tracker.update(in_zone_persons, frame_time)
                    tracking_ms = (time.monotonic() - tracking_started_at) * 1000.0

                    persistence_ms = 0.0
                    persistence_started_at = time.monotonic()
                    _persist_person_events(completed_events)
                    persistence_ms += (time.monotonic() - persistence_started_at) * 1000.0
                    for event in completed_events:
                        estimator.add_event(event)

                    queue_length = tracker.current_queue_length
                    throughput = estimator.throughput_per_minute
                    wait_seconds = estimator.estimate_wait_seconds(queue_length)
                    level = estimator.busyness_level(queue_length)

                    logger.debug(
                        (
                            "level={} tracks={} in_zone={} wait_seconds={:.2f} "
                            "inference_ms={:.2f} tracking_ms={:.2f} persistence_ms={:.2f}"
                        ),
                        level.upper(),
                        len(persons),
                        len(in_zone_persons),
                        wait_seconds,
                        inference_ms,
                        tracking_ms,
                        persistence_ms,
                    )

                    end_to_end_latency_ms = (time.monotonic() - loop_started_at) * 1000.0
                    effective_fps = 1000.0 / max(end_to_end_latency_ms, 0.001)

                    if level != last_level:
                        logger.info("Busyness level transition: {} -> {}", last_level, level)
                        last_level = level

                    status = QueueStatusResponse(
                        timestamp=frame_time,
                        queue_length=queue_length,
                        estimated_wait_seconds=wait_seconds,
                        estimated_wait_human=_humanize_wait(wait_seconds),
                        throughput_per_minute=throughput,
                        busyness_level=level,
                        inference_ms=inference_ms,
                        tracking_ms=tracking_ms,
                        persistence_ms=persistence_ms,
                        end_to_end_latency_ms=end_to_end_latency_ms,
                        effective_fps=effective_fps,
                    )
                    state.update(status)

                    if (time.monotonic() - last_snapshot_time) >= snapshot_interval_seconds:
                        snapshot = QueueSnapshot(
                            timestamp=frame_time,
                            queue_length=queue_length,
                            estimated_wait_seconds=wait_seconds,
                            throughput_per_minute=throughput,
                            busyness_level=level,
                        )
                        snapshot_write_started_at = time.monotonic()
                        _persist_snapshot(snapshot)
                        persistence_ms += (time.monotonic() - snapshot_write_started_at) * 1000.0
                        end_to_end_latency_ms = (time.monotonic() - loop_started_at) * 1000.0
                        effective_fps = 1000.0 / max(end_to_end_latency_ms, 0.001)
                        status = status.model_copy(
                            update={
                                "persistence_ms": persistence_ms,
                                "end_to_end_latency_ms": end_to_end_latency_ms,
                                "effective_fps": effective_fps,
                            }
                        )
                        state.update(status)
                        state.broadcast(status)
                        logger.info(
                            (
                                "Snapshot written | queue_length={} wait_seconds={:.2f} throughput={:.2f} "
                                "inference_ms={:.2f} tracking_ms={:.2f} persistence_ms={:.2f} "
                                "latency_ms={:.2f} fps={:.2f}"
                            ),
                            queue_length,
                            wait_seconds,
                            throughput,
                            inference_ms,
                            tracking_ms,
                            persistence_ms,
                            end_to_end_latency_ms,
                            effective_fps,
                        )
                        last_snapshot_time = time.monotonic()

                    display.show_level(level)
                    elapsed = time.monotonic() - loop_started_at
                    target = 1.0 / max(settings.camera_fps, 1)
                    sleep_duration = max(0.0, target - elapsed)
                    time.sleep(sleep_duration)
                except Exception:
                    logger.exception("Unexpected camera loop error")
                    time.sleep(0.1)
                    continue
    except Exception:
        logger.exception("Camera source failure")


def _configure_logging() -> None:
    """Configure Loguru outputs and file rotation."""

    Path("logs").mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sink=sys.stderr,
        level="DEBUG",
        backtrace=True,
        diagnose=True,
    )
    logger.add("logs/queue_estimator.log", rotation="10 MB", level="DEBUG", backtrace=True, diagnose=True)


def main() -> None:
    """Run queue estimator orchestrator and API server."""

    _configure_logging()
    settings = get_settings()
    create_db_and_tables()

    shared_state = SharedState()
    app = create_app(shared_state=shared_state)
    shared_state.set_broadcaster(app.state.ws_hub.enqueue)

    camera_thread = threading.Thread(
        target=camera_loop,
        args=(settings, shared_state),
        daemon=True,
        name="camera-loop-thread",
    )
    camera_thread.start()
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()

