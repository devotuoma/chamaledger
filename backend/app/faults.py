"""Deliberate failures for rehearsing incidents. Inert unless CHAOS_ENABLED=true."""

import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import NotFound
from app.models import RuntimeFlag, utcnow

WRITE_FAILURE = "contribution_write_failure"
WRITE_LATENCY = "contribution_write_latency"
KNOWN_FAULTS = (WRITE_FAILURE, WRITE_LATENCY)
INJECTED_DELAY_SECONDS = 1.5


class ContributionWriteFault(Exception):
    """Raised when the write-failure flag is on. It looks like any other server error."""


def enabled_faults(session: Session) -> set[str]:
    rows = session.scalars(select(RuntimeFlag.name).where(RuntimeFlag.enabled))
    return set(rows)


def list_flags(session: Session) -> dict[str, bool]:
    enabled = enabled_faults(session)
    return {name: name in enabled for name in KNOWN_FAULTS}


def set_flag(session: Session, name: str, enabled: bool) -> None:
    if name not in KNOWN_FAULTS:
        raise NotFound(f"Unknown flag {name}")
    flag = session.get(RuntimeFlag, name)
    if flag is None:
        session.add(RuntimeFlag(name=name, enabled=enabled))
    else:
        flag.enabled = enabled
        flag.updated_at = utcnow()
    session.commit()


def apply_contribution_faults(session: Session) -> None:
    if not get_settings().chaos_enabled:
        return
    active = enabled_faults(session)
    if WRITE_LATENCY in active:
        time.sleep(INJECTED_DELAY_SECONDS)
    if WRITE_FAILURE in active:
        raise ContributionWriteFault("Injected contribution write failure")
