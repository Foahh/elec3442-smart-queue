from __future__ import annotations

"""Main entrypoint for the queue estimator runtime."""

import sys

from loguru import logger

from config import Settings, get_settings
from runtime.app import QueueEstimatorApplication


def _configure_logging(settings: Settings) -> None:
    """Configure Loguru stderr output."""

    logger.remove()
    logger.add(
        sink=sys.stderr,
        level=settings.log_level.upper(),
        backtrace=True,
        diagnose=True,
    )


def main() -> None:
    """Run the queue estimator runtime."""

    settings = get_settings()
    _configure_logging(settings)
    QueueEstimatorApplication(settings).run()


if __name__ == "__main__":
    main()
