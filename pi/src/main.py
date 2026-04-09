from __future__ import annotations

"""Main orchestrator for the camera loop and preview server."""

import threading
import time
from datetime import UTC, datetime
from pathlib import Path
import sys
import cv2
import numpy as np
from loguru import logger

from analyzer.queue_state import QueueStateTracker
from analyzer.wait_time import WaitTimeEstimator
from camera import make_camera
from config import Settings, get_settings
from database import create_db_and_tables, get_session
from db_models import PersonEvent, QueueSnapshot
from detection.detector import PersonDetector
from detection.zone import QueueZone
from analyzer.comfort import compute_comfort_score
from display import make_display
from display.base import SiteDisplay
from preview_server import create_preview_http_server
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


def _center_square_crop(frame: np.ndarray) -> np.ndarray:
    """Return a center-cropped 1:1 square image (mandatory ROI)."""

    h, w = frame.shape[:2]
    size = int(min(h, w))
    if size <= 0:
        return frame
    x0 = (w - size) // 2
    y0 = (h - size) // 2
    return frame[y0 : y0 + size, x0 : x0 + size]


def _zone_polygon_pixels(
    zone_points_normalized: list[tuple[float, float]],
    frame_shape: tuple[int, int],
) -> np.ndarray | None:
    """Convert normalized zone polygon points to pixel coordinates for drawing."""

    if not zone_points_normalized or len(zone_points_normalized) < 3:
        return None
    h, w = frame_shape
    pts = np.array(zone_points_normalized, dtype=np.float32)
    pts[:, 0] *= float(w)
    pts[:, 1] *= float(h)
    return pts.reshape((-1, 1, 2)).astype(np.int32)


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
    """Run the queue estimation processing loop until exit."""

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

                    # Enforced ROI: always use center 1:1 crop for the entire pipeline.
                    frame = _center_square_crop(frame)

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
                    # ROI border (ROI == full cropped frame).
                    h_vis, w_vis = vis_frame.shape[:2]
                    cv2.rectangle(
                        vis_frame,
                        (0, 0),
                        (max(w_vis - 1, 0), max(h_vis - 1, 0)),
                        color=(255, 0, 255),
                        thickness=2,
                    )

                    zone_pts = _zone_polygon_pixels(
                        settings.queue_zone, vis_frame.shape[:2]
                    )
                    if zone_pts is not None:
                        cv2.polylines(
                            vis_frame,
                            [zone_pts],
                            True,
                            color=(0, 255, 255),
                            thickness=2,
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
                    ok, buf = cv2.imencode(
                        ".jpg", resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
                    )
                    if ok:
                        state.set_preview_jpeg(buf.tobytes())

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
    """Run queue estimator orchestrator and preview server."""

    _configure_logging()
    settings = get_settings()
    logger.info(
        "Open http://127.0.0.1:{}/preview for local video preview",
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

    preview_http_server = create_preview_http_server(
        settings.api_host,
        settings.api_port,
        shared_state,
    )
    preview_http_thread = threading.Thread(
        target=preview_http_server.serve_forever,
        daemon=True,
        name="preview-http-thread",
    )
    preview_http_thread.start()
    logger.info(
        "Preview server listening on http://{}:{}",
        settings.api_host,
        settings.api_port,
    )

    camera_loop(settings, shared_state, peer_cache)


if __name__ == "__main__":
    main()
