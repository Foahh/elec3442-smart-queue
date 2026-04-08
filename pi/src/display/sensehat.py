from __future__ import annotations

"""Sense HAT display implementation."""

from importlib import import_module

from display.base import LEDDisplay, SiteDisplay


_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "low": ((0, 200, 0), (0, 20, 0)),
    "medium": ((220, 140, 0), (22, 14, 0)),
    "high": ((200, 0, 0), (20, 0, 0)),
    "stale": ((0, 0, 80), (0, 0, 80)),
}


def band_rows(n: int) -> list[int]:
    """Return row-count per site band for an 8x8 grid with n sites."""

    base, extra = divmod(8, n)
    return [base + 1] * extra + [base] * (n - extra)


class SenseHATDisplay(LEDDisplay):
    """Sense HAT LED matrix display."""

    def __init__(self, queue_max_display: int = 16) -> None:
        """Initialize Sense HAT instance."""

        try:
            sense_hat_module = import_module("sense_hat")
            sense_hat_cls = getattr(sense_hat_module, "SenseHat")
        except ImportError as exc:
            raise RuntimeError(
                "Sense HAT library not installed — on Raspberry Pi: pip install sense-hat"
            ) from exc
        self._sense = sense_hat_cls()
        self._queue_max = max(queue_max_display, 1)

    def read_sensors(self) -> tuple[float, float, float]:
        """Return (temperature_c, humidity_pct, pressure_hpa) from HAT sensors."""

        return (
            float(self._sense.get_temperature()),
            float(self._sense.get_humidity()),
            float(self._sense.get_pressure()),
        )

    def show_sites(self, sites: list[SiteDisplay]) -> None:
        """Render all sites as horizontal fill-bands on the 8×8 grid."""

        if not sites:
            self._sense.clear()
            return

        rows = band_rows(len(sites))
        pixels: list[tuple[int, int, int]] = []
        for site, row_count in zip(sites, rows):
            level_key = "stale" if site.stale else site.busyness_level
            lit, dim = _COLORS.get(level_key, _COLORS["stale"])
            filled = min(8, round(site.queue_length / self._queue_max * 8))
            row_pixels = [lit if col < filled else dim for col in range(8)]
            for _ in range(row_count):
                pixels.extend(row_pixels)

        self._sense.set_pixels(pixels)

    def clear(self) -> None:
        """Clear Sense HAT matrix."""

        self._sense.clear()
