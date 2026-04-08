from __future__ import annotations

import pytest
from queue_estimator.analyzer.comfort import compute_comfort_score


def test_zero_wait_ideal_env_gives_100() -> None:
    score, label = compute_comfort_score(
        wait_seconds=0.0, temperature_c=22.0, humidity_pct=50.0, pressure_hpa=1013.0
    )
    assert score == pytest.approx(100.0)
    assert label == "comfortable"


def test_zero_wait_no_sensors_gives_100() -> None:
    score, label = compute_comfort_score(wait_seconds=0.0)
    assert score == pytest.approx(100.0)
    assert label == "comfortable"


def test_15_min_wait_gives_zero() -> None:
    score, label = compute_comfort_score(
        wait_seconds=900.0, temperature_c=22.0, humidity_pct=50.0, pressure_hpa=1013.0
    )
    assert score == pytest.approx(0.0)
    assert label == "uncomfortable"


def test_moderate_wait() -> None:
    score, label = compute_comfort_score(
        wait_seconds=300.0, temperature_c=22.0, humidity_pct=50.0, pressure_hpa=1013.0
    )
    assert 40.0 <= score < 70.0
    assert label == "moderate"


def test_env_penalty_reduces_score() -> None:
    ideal = compute_comfort_score(
        wait_seconds=60.0, temperature_c=22.0, humidity_pct=50.0, pressure_hpa=1013.0
    )
    hot = compute_comfort_score(
        wait_seconds=60.0, temperature_c=35.0, humidity_pct=80.0, pressure_hpa=1013.0
    )
    assert hot[0] < ideal[0]


def test_score_clamped_to_zero() -> None:
    score, _ = compute_comfort_score(
        wait_seconds=1800.0, temperature_c=40.0, humidity_pct=90.0, pressure_hpa=1013.0
    )
    assert score == pytest.approx(0.0)
