from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import queue_estimator.api.app as app_module
from queue_estimator.api.app import create_app
from queue_estimator.api.dependencies import get_db_session
from queue_estimator.db_models import PersonEvent, QueueSnapshot
from queue_estimator.schemas import QueueStatusResponse, SensorReading
from queue_estimator.sync.hub_sync import PeerCache, SiteSnapshot


class StubSharedState:
    """Minimal shared state for API route tests."""

    def __init__(
        self,
        *,
        status: QueueStatusResponse | None = None,
        preview_jpeg: bytes | None = None,
        sensors: SensorReading | None = None,
    ) -> None:
        self._status = status
        self._preview_jpeg = preview_jpeg
        self._sensors = sensors

    def get(self) -> QueueStatusResponse | None:
        return self._status

    def get_preview_jpeg(self) -> bytes | None:
        return self._preview_jpeg

    def get_sensors(self) -> SensorReading | None:
        return self._sensors


@pytest.fixture
def api_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, Session, StubSharedState, PeerCache]:
    """Create a test app with an isolated in-memory database."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    shared_state = StubSharedState()
    peer_cache = PeerCache()

    def override_get_db_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(app_module, "create_db_and_tables", lambda: None)
    app = create_app(shared_state=shared_state, peer_cache=peer_cache)
    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as client:
        with Session(engine) as session:
            yield client, session, shared_state, peer_cache


def test_queue_status_returns_latest_shared_state(
    api_fixture: tuple[TestClient, Session, StubSharedState, PeerCache],
) -> None:
    client, _, shared_state, _ = api_fixture
    timestamp = datetime(2026, 4, 9, 12, 0, tzinfo=UTC)
    shared_state._status = QueueStatusResponse(
        timestamp=timestamp,
        queue_length=4,
        estimated_wait_seconds=120.0,
        estimated_wait_human="~2 min 0 sec",
        throughput_per_minute=1.5,
        busyness_level="medium",
        comfort_score=88.0,
        comfort_label="comfortable",
        inference_ms=22.0,
        tracking_ms=4.0,
        persistence_ms=3.0,
        end_to_end_latency_ms=40.0,
        effective_fps=25.0,
    )

    response = client.get("/api/v1/queue/status")

    assert response.status_code == 200
    assert response.json()["queue_length"] == 4
    assert response.json()["timestamp"] == timestamp.isoformat()


def test_queue_status_returns_503_while_uninitialized(
    api_fixture: tuple[TestClient, Session, StubSharedState, PeerCache],
) -> None:
    client, _, _, _ = api_fixture

    response = client.get("/api/v1/queue/status")

    assert response.status_code == 503
    assert response.json() == {"detail": "System initializing"}


def test_queue_history_filters_and_orders_snapshots(
    api_fixture: tuple[TestClient, Session, StubSharedState, PeerCache],
) -> None:
    client, session, _, _ = api_fixture
    now = datetime.now(UTC)
    recent = now - timedelta(minutes=10)
    older = now - timedelta(minutes=20)
    expired = now - timedelta(minutes=90)
    session.add_all(
        [
            QueueSnapshot(
                timestamp=older,
                queue_length=3,
                estimated_wait_seconds=90.0,
                throughput_per_minute=1.0,
                busyness_level="low",
            ),
            QueueSnapshot(
                timestamp=recent,
                queue_length=5,
                estimated_wait_seconds=150.0,
                throughput_per_minute=1.4,
                busyness_level="medium",
            ),
            QueueSnapshot(
                timestamp=expired,
                queue_length=9,
                estimated_wait_seconds=480.0,
                throughput_per_minute=0.7,
                busyness_level="high",
            ),
        ]
    )
    session.commit()

    response = client.get("/api/v1/queue/history", params={"minutes": 60, "limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert [row["queue_length"] for row in payload] == [5, 3]


def test_analytics_routes_share_aggregation_logic(
    api_fixture: tuple[TestClient, Session, StubSharedState, PeerCache],
) -> None:
    client, session, _, _ = api_fixture
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    current_hour = now - timedelta(minutes=15)
    current_hour_second = now - timedelta(minutes=5)
    previous_hour = now - timedelta(hours=1, minutes=10)

    session.add_all(
        [
            QueueSnapshot(
                timestamp=current_hour,
                queue_length=4,
                estimated_wait_seconds=120.0,
                throughput_per_minute=1.2,
                busyness_level="medium",
            ),
            QueueSnapshot(
                timestamp=current_hour_second,
                queue_length=6,
                estimated_wait_seconds=180.0,
                throughput_per_minute=1.6,
                busyness_level="medium",
            ),
            QueueSnapshot(
                timestamp=previous_hour,
                queue_length=2,
                estimated_wait_seconds=60.0,
                throughput_per_minute=1.0,
                busyness_level="low",
            ),
            PersonEvent(
                track_id=1,
                entry_time=previous_hour - timedelta(minutes=2),
                exit_time=previous_hour,
                dwell_seconds=120.0,
                date_hour=previous_hour.strftime("%Y-%m-%dT%H"),
            ),
            PersonEvent(
                track_id=2,
                entry_time=current_hour - timedelta(minutes=3),
                exit_time=current_hour,
                dwell_seconds=180.0,
                date_hour=current_hour.strftime("%Y-%m-%dT%H"),
            ),
            PersonEvent(
                track_id=3,
                entry_time=current_hour_second - timedelta(minutes=4),
                exit_time=current_hour_second,
                dwell_seconds=240.0,
                date_hour=current_hour_second.strftime("%Y-%m-%dT%H"),
            ),
        ]
    )
    session.commit()

    summary_response = client.get("/api/v1/analytics/summary", params={"hours": 6})
    peak_response = client.get("/api/v1/analytics/peak-hours")

    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["total_persons_served"] == 3
    assert summary["avg_service_time_seconds"] == pytest.approx(180.0)
    assert summary["peak_hour"] == current_hour.strftime("%Y-%m-%dT%H")
    assert summary["hourly_breakdown"][1]["avg_queue_length"] == pytest.approx(5.0)
    assert summary["hourly_breakdown"][1]["total_persons_served"] == 2

    assert peak_response.status_code == 200
    peak_hours = peak_response.json()
    assert peak_hours[0]["hour"] == current_hour.strftime("%Y-%m-%dT%H")
    assert peak_hours[0]["peak_queue_length"] == 6


def test_peers_route_returns_cached_sites(
    api_fixture: tuple[TestClient, Session, StubSharedState, PeerCache],
) -> None:
    client, _, _, peer_cache = api_fixture
    peer_cache.update(
        [
            SiteSnapshot(
                site_id="site-b",
                display_name="Site B",
                queue_length=7,
                estimated_wait_seconds=300.0,
                busyness_level="high",
                comfort_score=65.0,
                updated_at=1_744_198_400_000,
                stale=False,
                temperature_c=24.0,
                humidity_pct=55.0,
                pressure_hpa=1012.0,
                latitude=22.3,
                longitude=114.2,
            )
        ]
    )

    response = client.get("/api/v1/peers/")

    assert response.status_code == 200
    assert response.json()["sites"][0]["display_name"] == "Site B"
