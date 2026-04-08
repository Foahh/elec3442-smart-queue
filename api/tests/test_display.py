from __future__ import annotations

import pytest
from queue_estimator.display.sensehat import band_rows


@pytest.mark.parametrize(
    "n, expected",
    [
        (1, [8]),
        (2, [4, 4]),
        (3, [3, 3, 2]),
        (4, [2, 2, 2, 2]),
        (5, [2, 2, 2, 1, 1]),
        (6, [2, 2, 1, 1, 1, 1]),
        (7, [2, 1, 1, 1, 1, 1, 1]),
        (8, [1, 1, 1, 1, 1, 1, 1, 1]),
    ],
)
def test_band_rows(n: int, expected: list[int]) -> None:
    assert band_rows(n) == expected
    assert sum(band_rows(n)) == 8
