from __future__ import annotations

"""Comfortness score computation."""

from typing import Literal


ComfortLabel = Literal["comfortable", "moderate", "uncomfortable"]


def compute_comfort_score(
    wait_seconds: float,
    temperature_c: float | None = None,
    humidity_pct: float | None = None,
    pressure_hpa: float | None = None,
) -> tuple[float, ComfortLabel]:
    """Return (score 0-100, label).

    Comfort = clamp(100 - P_wait - P_env, 0, 100)

    P_wait: dominant penalty, 0 at 0 s → 100 at 900 s (15 min ceiling).
    P_env:  secondary penalty (max 25 pts) from DI and pressure deviation.
            Falls back to 0 when sensor data is unavailable.
    """

    p_wait = min(wait_seconds / 9.0, 100.0)

    p_env = 0.0
    if temperature_c is not None and humidity_pct is not None:
        di = temperature_c - (0.55 - 0.0055 * humidity_pct) * (temperature_c - 14.5)
        p_di = min(max(0.0, di - 21.0) * 1.43, 20.0)
        p_env += p_di

    if pressure_hpa is not None:
        p_pressure = min(0.05 * abs(pressure_hpa - 1013.0), 5.0)
        p_env += p_pressure

    score = max(0.0, min(100.0, 100.0 - p_wait - p_env))

    if score >= 70.0:
        label: ComfortLabel = "comfortable"
    elif score >= 40.0:
        label = "moderate"
    else:  # score < 40.0
        label = "uncomfortable"

    return score, label
