"""Dispatch input normalization.

Workflow and CLI variables arrive as strings; they are parsed here,
before any ledger write, Replicate call, LLM call, or DA call.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from datetime import date as date_cls

from tools.roster import ACTIVE_MODELS, RosterError

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RANDOM = ("", "random")


def parse_date(raw: str) -> str:
    """Empty means today (UTC); anything else must be strict ISO."""
    if not raw:
        return datetime.now(UTC).date().isoformat()
    if not ISO_DATE.match(raw):
        raise ValueError(f"expected YYYY-MM-DD, got {raw!r}")
    date_cls.fromisoformat(raw)  # rejects 2026-13-40
    return raw


def parse_slot(raw: str | int) -> int:
    if raw == "":
        return 0
    if isinstance(raw, bool) or not isinstance(raw, (str, int)):
        raise TypeError(f"slot must be str or int, got {type(raw).__name__}")
    value = int(raw) if isinstance(raw, int) else int(raw, 10)
    if value < 0:
        raise ValueError(f"slot must be non-negative, got {value}")
    return value


def parse_model(raw: str) -> str:
    """Empty or 'random' means unpinned; any other name must be active."""
    if raw.lower() in RANDOM:
        return ""
    if raw not in ACTIVE_MODELS:
        raise RosterError(
            f"unknown model {raw!r}: not in roster {sorted(ACTIVE_MODELS)}"
        )
    return raw
