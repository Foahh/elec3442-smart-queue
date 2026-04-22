from __future__ import annotations

"""Camera loop orchestration."""

import time
from datetime import UTC, datetime

from loguru import logger

from analyzer.comfort import compute_comfort_score
from analyzer.queue_state import QueueStateTracker
from analyzer.wait_time import WaitTimeEstimator
from camera import make_camera
from camera.base import CameraSource
from config import Settings
from db_models import PersonEvent
from db_models import QueueSnapshot
from detection.detector import PersonDetector
from detection.zone import QueueZone
from display import make_display
from display.base import SiteDisplay
from hub_sync import PeerCache
from runtime.persistence import persist_person_events, persist_snapshot
from runtime.preview import PreviewRenderer, center_square_crop, humanize_wait
from runtime.shared_state import SharedState
from schemas import QueueStatusResponse, SensorReading


class CameraLoopRunner:
    """Run the queue estimation camera loop."""

    def __init__(
        self,
        settings: Settings,
        state: SharedState,
        peer_cache: PeerCache,
    ) -> None:
        """Initialize loop dependencies."""

        self._settings = settings
        self._state = state
        self._peer_cache = peer_cache
        self._detector = PersonDetector(settings)
        self._zone = QueueZone(settings.queue_zone)
        self._tracker = QueueStateTracker(settings)
        self._estimator = WaitTimeEstimator(settings)
        self._display = make_display(queue_max_display=settings.queue_max_display)
        self._preview = PreviewRenderer(settings)
        self._snapshot_interval_seconds = 60.0 / max(settings.snapshots_per_minute, 1)
        self._last_snapshot_time = time.monotonic()
        self._last_level: str | None = None

    def run(self) -> None:
        """Process frames until shutdown."""

        try:
            try:
                with make_camera(self._settings) as camera:
                    while True:
                        loop_started_at = time.monotonic()
                        try:
                            self._process_frame(camera, loop_started_at)
                        except Exception:
                            logger.exception("Unexpected camera loop error")
                            time.sleep(0.1)
            except Exception:
                logger.exception("Camera source failure")
        finally:
            self._preview.shutdown()

    def _process_frame(self, camera: CameraSource, loop_started_at: float) -> None:
        frame_time = datetime.now(UTC)
        frame = camera.read_frame()
        if frame is None:
            logger.warning("Frame read failure from camera source")
            time.sleep(0.1)
            return

        if camera.poll_rewound():
            logger.info(
                "Video input rewound; resetting tracker and wait estimator to avoid replay double-counting"
            )
            self._tracker.reset()
            self._estimator.reset(preserve_throughput=True)
            self._last_level = None

        frame = center_square_crop(frame)

        inference_started_at = time.monotonic()
        persons = self._detector.detect(frame, input_color_space=camera.color_space)
        inference_ms = (time.monotonic() - inference_started_at) * 1000.0

        self._read_sensors()

        tracking_started_at = time.monotonic()
        in_zone_persons = self._zone.filter_persons(persons, frame.shape[:2])
        completed_events = self._tracker.update(in_zone_persons, frame_time)
        tracking_ms = (time.monotonic() - tracking_started_at) * 1000.0

        persistence_ms = self._persist_events(completed_events)

        queue_length = self._tracker.current_queue_length
        throughput = self._estimator.throughput_per_minute
        wait_seconds = self._estimator.estimate_wait_seconds(queue_length)
        level = self._estimator.busyness_level(queue_length)

        comfort_score, comfort_label = self._compute_comfort(wait_seconds)

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
        status = QueueStatusResponse(
            timestamp=frame_time,
            queue_length=queue_length,
            estimated_wait_seconds=wait_seconds,
            estimated_wait_human=humanize_wait(wait_seconds),
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
        self._state.update(status)
        self._preview.maybe_encode(
            state=self._state,
            frame=frame,
            input_color_space=camera.color_space,
            persons=persons,
            in_zone_persons=in_zone_persons,
            frame_time=frame_time,
            status=status,
        )

        status = self._maybe_write_snapshot(status, loop_started_at)
        self._log_level_transition(level)
        self._update_display(level, queue_length)
        self._sleep_to_target_fps(loop_started_at)

    def _read_sensors(self) -> None:
        if not hasattr(self._display, "read_sensors"):
            return
        try:
            raw_temp, humidity_pct, pressure_hpa = self._display.read_sensors()
            sensor = SensorReading(
                temperature_c=raw_temp + self._settings.temp_offset,
                humidity_pct=humidity_pct,
                pressure_hpa=pressure_hpa,
            )
            self._state.update_sensors(sensor)
        except Exception:
            logger.debug("Sensor read failed; skipping")

    def _persist_events(self, completed_events: list[PersonEvent]) -> float:
        if not completed_events:
            return 0.0
        started_at = time.monotonic()
        persist_person_events(completed_events)
        for event in completed_events:
            self._estimator.add_event(event)
        return (time.monotonic() - started_at) * 1000.0

    def _compute_comfort(self, wait_seconds: float) -> tuple[float, str]:
        sensors_now = self._state.get_sensors()
        return compute_comfort_score(
            wait_seconds=wait_seconds,
            temperature_c=sensors_now.temperature_c if sensors_now else None,
            humidity_pct=sensors_now.humidity_pct if sensors_now else None,
            pressure_hpa=sensors_now.pressure_hpa if sensors_now else None,
        )

    def _maybe_write_snapshot(
        self,
        status: QueueStatusResponse,
        loop_started_at: float,
    ) -> QueueStatusResponse:
        if (time.monotonic() - self._last_snapshot_time) < self._snapshot_interval_seconds:
            return status

        snapshot = QueueSnapshot(
            timestamp=status.timestamp,
            queue_length=status.queue_length,
            estimated_wait_seconds=status.estimated_wait_seconds,
            throughput_per_minute=status.throughput_per_minute,
            busyness_level=status.busyness_level,
        )
        snapshot_write_started_at = time.monotonic()
        persist_snapshot(snapshot)
        persistence_ms = status.persistence_ms + (
            (time.monotonic() - snapshot_write_started_at) * 1000.0
        )
        end_to_end_latency_ms = (time.monotonic() - loop_started_at) * 1000.0
        effective_fps = 1000.0 / max(end_to_end_latency_ms, 0.001)
        updated_status = status.model_copy(
            update={
                "persistence_ms": persistence_ms,
                "end_to_end_latency_ms": end_to_end_latency_ms,
                "effective_fps": effective_fps,
            }
        )
        self._state.update(updated_status)
        logger.info(
            (
                "Snapshot written | queue_length={} wait_seconds={:.2f} throughput={:.2f} "
                "inference_ms={:.2f} tracking_ms={:.2f} persistence_ms={:.2f} "
                "latency_ms={:.2f} fps={:.2f}"
            ),
            updated_status.queue_length,
            updated_status.estimated_wait_seconds,
            updated_status.throughput_per_minute,
            updated_status.inference_ms,
            updated_status.tracking_ms,
            updated_status.persistence_ms,
            updated_status.end_to_end_latency_ms,
            updated_status.effective_fps,
        )
        self._last_snapshot_time = time.monotonic()
        return updated_status

    def _log_level_transition(self, level: str) -> None:
        if level == self._last_level:
            return
        logger.info("Busyness level transition: {} -> {}", self._last_level, level)
        self._last_level = level

    def _update_display(self, level: str, queue_length: int) -> None:
        peers = self._peer_cache.get_all()
        local_snapshot = SiteDisplay(
            busyness_level=level,
            queue_length=queue_length,
            stale=False,
        )
        peer_snapshots = [
            SiteDisplay(
                busyness_level=peer.busyness_level,
                queue_length=peer.queue_length,
                stale=peer.stale,
            )
            for peer in sorted(peers, key=lambda item: item.site_id)
            if peer.site_id != self._settings.site_id
        ]
        self._display.show_sites([local_snapshot] + peer_snapshots)

    def _sleep_to_target_fps(self, loop_started_at: float) -> None:
        elapsed = time.monotonic() - loop_started_at
        target = 1.0 / max(self._settings.camera_fps, 1)
        time.sleep(max(0.0, target - elapsed))


def camera_loop(settings: Settings, state: SharedState, peer_cache: PeerCache) -> None:
    """Compatibility wrapper around the camera loop runner."""

    CameraLoopRunner(settings, state, peer_cache).run()
