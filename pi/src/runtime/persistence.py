from __future__ import annotations

"""Persistence helpers for short-lived runtime writes."""

from collections.abc import Callable

from loguru import logger
from sqlmodel import Session

from database import get_session
from db_models import PersonEvent, QueueSnapshot


def _commit_with_retry(
    description: str,
    operation: Callable[[Session], None],
) -> None:
    """Run a database write operation and retry once on failure."""

    try:
        with get_session() as session:
            operation(session)
            session.commit()
    except Exception:
        logger.warning("{} write failed; retrying once", description)
        with get_session() as session:
            operation(session)
            session.commit()


def persist_person_events(events: list[PersonEvent]) -> None:
    """Persist completed person events."""

    if not events:
        return
    _commit_with_retry("Person event", lambda session: session.add_all(events))


def persist_snapshot(snapshot: QueueSnapshot) -> None:
    """Persist a queue snapshot."""

    _commit_with_retry("Snapshot", lambda session: session.add(snapshot))
