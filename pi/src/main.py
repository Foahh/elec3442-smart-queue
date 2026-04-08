from __future__ import annotations

"""Main orchestrator for camera loop and API server."""

import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
import sys
import cv2
import uvicorn
import numpy as np
from loguru import logger

from analyzer.queue_state import QueueStateTracker
from analyzer.wait_time import WaitTimeEstimator
from api.app import create_app
from camera import make_camera
from config import Settings, get_settings, preview_targets
from database import create_db_and_tables, get_session
from db_models import PersonEvent, QueueSnapshot
from detection.detector import PersonDetector
from detection.zone import QueueZone
from analyzer.comfort import compute_comfort_score
from display import make_display
from display.base import SiteDisplay
from schemas import QueueStatusResponse, SensorReading
from sync.hub_sync import HubSyncAgent, PeerCache


class SharedState:
    """Thread-safe wrapper around latest queue status."""

    def __init__(self) -> None:
        """Initialize state container."""

        self._lock = threading.Lock()
        self._status: QueueStatusResponse | None = None
        self._preview_jpeg: bytes | None = None
        self._sensors: SensorReading | None = None
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

    def set_preview_jpeg(self, data: bytes) -> None:
        """Store latest encoded preview frame for HTTP MJPEG clients."""

        with self._lock:
            self._preview_jpeg = data

    def get_preview_jpeg(self) -> bytes | None:
        """Return latest JPEG preview bytes if any."""

        with self._lock:
            return self._preview_jpeg

    def update_sensors(self, sensors: SensorReading) -> None:
        """Store latest sensor reading."""

        with self._lock:
            self._sensors = sensors

    def get_sensors(self) -> SensorReading | None:
        """Return latest sensor reading, or None if unavailable."""

        with self._lock:
            return self._sensors


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


def camera_loop(settings: Settings, state: SharedState, peer_cache: PeerCache) -> None:
    """Run queue estimation processing loop in a daemon thread."""

    use_opencv, use_http = preview_targets(settings)
    opencv_used = False
    detector = PersonDetector(settings)
    zone = QueueZone(settings.queue_zone)
    tracker = QueueStateTracker(settings)
    estimator = WaitTimeEstimator(settings)
    display = make_display(queue_max_display=settings.queue_max_display)
    snapshot_interval_seconds = 60.0 / max(settings.snapshots_per_minute, 1)
    last_snapshot_time = time.monotonic()
    last_level: str | None = None

    # to set the real-time output window size
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 600

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

                    # Sensor read (Sense HAT only; NullDisplay has no read_sensors)
                    if hasattr(display, "read_sensors"):
                        try:
                            raw_temp, hum, pres = display.read_sensors()
                            temp = raw_temp + settings.temp_offset
                            sensor = SensorReading(
                                temperature_c=temp,
                                humidity_pct=hum,
                                pressure_hpa=pres,
                            )
                            state.update_sensors(sensor)
                        except Exception:
                            logger.debug("Sensor read failed; skipping")
                            sensor = state.get_sensors()
                    else:
                        sensor = state.get_sensors()

                    tracking_started_at = time.monotonic()
                    in_zone_persons = zone.filter_persons(persons, frame.shape[:2])
                    completed_events = tracker.update(in_zone_persons, frame_time)
                    tracking_ms = (time.monotonic() - tracking_started_at) * 1000.0

                    persistence_ms = 0.0
                    persistence_started_at = time.monotonic()
                    _persist_person_events(completed_events)
                    persistence_ms += (
                        time.monotonic() - persistence_started_at
                    ) * 1000.0
                    for event in completed_events:
                        estimator.add_event(event)

                    queue_length = tracker.current_queue_length
                    throughput = estimator.throughput_per_minute
                    wait_seconds = estimator.estimate_wait_seconds(queue_length)
                    level = estimator.busyness_level(queue_length)

                    sensors_now = state.get_sensors()
                    comfort_score, comfort_label = compute_comfort_score(
                        wait_seconds=wait_seconds,
                        temperature_c=sensors_now.temperature_c
                        if sensors_now
                        else None,
                        humidity_pct=sensors_now.humidity_pct if sensors_now else None,
                        pressure_hpa=sensors_now.pressure_hpa if sensors_now else None,
                    )

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

                    end_to_end_latency_ms = (
                        time.monotonic() - loop_started_at
                    ) * 1000.0
                    effective_fps = 1000.0 / max(end_to_end_latency_ms, 0.001)

                    if level != last_level:
                        logger.info(
                            "Busyness level transition: {} -> {}", last_level, level
                        )
                        last_level = level

                    status = QueueStatusResponse(
                        timestamp=frame_time,
                        queue_length=queue_length,
                        estimated_wait_seconds=wait_seconds,
                        estimated_wait_human=_humanize_wait(wait_seconds),
                        throughput_per_minute=throughput,
                        busyness_level=level,
                        comfort_score=comfort_score,
                        comfort_label=comfort_label,
                        inference_ms=inference_ms,
                        tracking_ms=tracking_ms,
                        persistence_ms=persistence_ms,
                        end_to_end_latency_ms=end_to_end_latency_ms,
                        effective_fps=effective_fps,
                    )
                    state.update(status)

                    # create visualization frame with bounding boxes and zone
                    vis_frame = frame.copy()
                    zone_points = settings.queue_zone
                    if zone_points and len(zone_points) >= 3:
                        pts = np.array(zone_points, np.int32).reshape((-1, 1, 2))
                        cv2.polylines(
                            vis_frame, [pts], True, color=(0, 255, 255), thickness=2
                        )

                    # draw boxes for all persons
                    for person in persons:
                        x1, y1, x2, y2 = [int(coord) for coord in person.bbox_xyxy]
                        color = (
                            (0, 255, 0) if person in in_zone_persons else (0, 0, 255)
                        )
                        cv2.rectangle(
                            vis_frame, (x1, y1), (x2, y2), color=color, thickness=2
                        )
                        # add track ID
                        if hasattr(person, "track_id") and person.track_id is not None:
                            cv2.putText(
                                vis_frame,
                                f"ID {person.track_id}",
                                (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                color,
                                1,
                            )

                    # Add status overlay
                    status_text = f"Queue: {queue_length} | Wait: {wait_seconds:.0f}s | Level: {level.upper()} | FPS: {effective_fps:.1f}"
                    cv2.putText(
                        vis_frame,
                        status_text,
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2,
                    )
                    time_str = frame_time.strftime("%Y-%m-%d %H:%M:%S")
                    cv2.putText(
                        vis_frame,
                        time_str,
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                    )

                    resized_frame = cv2.resize(
                        vis_frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT)
                    )
                    if use_http:
                        ok, buf = cv2.imencode(
                            ".jpg", resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
                        )
                        if ok:
                            state.set_preview_jpeg(buf.tobytes())
                    if use_opencv:
                        opencv_used = True
                        cv2.imshow("Queue Estimator - Press ESC to exit", resized_frame)
                        if cv2.waitKey(1) & 0xFF == 27:  # ESC key
                            logger.info("ESC pressed, shutting down...")
                            break

                    if (
                        time.monotonic() - last_snapshot_time
                    ) >= snapshot_interval_seconds:
                        snapshot = QueueSnapshot(
                            timestamp=frame_time,
                            queue_length=queue_length,
                            estimated_wait_seconds=wait_seconds,
                            throughput_per_minute=throughput,
                            busyness_level=level,
                        )
                        snapshot_write_started_at = time.monotonic()
                        _persist_snapshot(snapshot)
                        persistence_ms += (
                            time.monotonic() - snapshot_write_started_at
                        ) * 1000.0
                        end_to_end_latency_ms = (
                            time.monotonic() - loop_started_at
                        ) * 1000.0
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

                    peers = peer_cache.get_all()
                    local_snap = SiteDisplay(
                        busyness_level=level,
                        queue_length=queue_length,
                        stale=False,
                    )
                    peer_snaps = [
                        SiteDisplay(
                            busyness_level=p.busyness_level,
                            queue_length=p.queue_length,
                            stale=p.stale,
                        )
                        for p in sorted(peers, key=lambda x: x.site_id)
                        if p.site_id != settings.site_id
                    ]
                    display.show_sites([local_snap] + peer_snaps)
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

    finally:
        if opencv_used:
            cv2.destroyAllWindows()


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
    logger.add(
        "logs/queue_estimator.log",
        rotation="10 MB",
        level="DEBUG",
        backtrace=True,
        diagnose=True,
    )


def main() -> None:
    """Run queue estimator orchestrator and API server."""

    _configure_logging()
    settings = get_settings()
    use_ocv, use_http = preview_targets(settings)
    logger.info(
        "Preview QE_PREVIEW_MODE={} -> opencv_window={} http_stream={}",
        settings.preview_mode,
        use_ocv,
        use_http,
    )
    if use_http:
        logger.info(
            "Open http://127.0.0.1:{}/api/v1/queue/preview for live video",
            settings.api_port,
        )
    create_db_and_tables()

    shared_state = SharedState()
    peer_cache = PeerCache()

    if settings.hub_url:
        sync_agent = HubSyncAgent(settings, shared_state, peer_cache)
        sync_thread = threading.Thread(
            target=sync_agent.run, daemon=True, name="hub-sync-thread"
        )
        sync_thread.start()
        logger.info("Hub sync started → {}", settings.hub_url)
    else:
        logger.info("QE_HUB_URL not set — hub sync disabled")

    app = create_app(shared_state=shared_state, peer_cache=peer_cache)
    shared_state.set_broadcaster(app.state.ws_hub.enqueue)

    camera_thread = threading.Thread(
        target=camera_loop,
        args=(settings, shared_state, peer_cache),
        daemon=True,
        name="camera-loop-thread",
    )
    camera_thread.start()
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
