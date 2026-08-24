"""Tests: dispatch input normalization.

Workflow inputs arrive as strings and are parsed at the boundary, before
any side effect.
"""

import pytest

from tools.inputs import parse_date, parse_model, parse_slot
from tools.roster import ACTIVE_MODELS, RosterError


@pytest.mark.req("REQ-DD-019")
def test_parse_date_empty_is_today_utc():
    from datetime import UTC, datetime

    assert parse_date("") == datetime.now(UTC).date().isoformat()


@pytest.mark.req("REQ-DD-019")
def test_parse_date_accepts_iso():
    assert parse_date("2026-08-23") == "2026-08-23"


@pytest.mark.parametrize(
    "raw", ["23-08-2026", "2026-8-3", "2026-08-23-manual", "today"]
)
@pytest.mark.req("REQ-DD-019")
def test_parse_date_rejects_non_iso(raw):
    with pytest.raises(ValueError):
        parse_date(raw)


@pytest.mark.parametrize("raw,expected", [("", 0), ("0", 0), ("2", 2), (3, 3)])
@pytest.mark.req("REQ-DD-020")
def test_parse_slot_accepts_non_negative(raw, expected):
    assert parse_slot(raw) == expected


@pytest.mark.parametrize("raw", ["-1", -1, "1.5", "abc", None])
@pytest.mark.req("REQ-DD-020")
def test_parse_slot_rejects_invalid(raw):
    with pytest.raises((ValueError, TypeError)):
        parse_slot(raw)


@pytest.mark.parametrize("raw", ["", "random", "RANDOM"])
@pytest.mark.req("REQ-DD-021")
def test_parse_model_random_means_unpinned(raw):
    assert parse_model(raw) == ""


@pytest.mark.req("REQ-DD-021")
def test_parse_model_accepts_active_name():
    assert parse_model("nano-banana-2") == "nano-banana-2"


@pytest.mark.req("REQ-DD-021")
def test_parse_model_rejects_unknown():
    with pytest.raises(RosterError):
        parse_model("flux-ultra")  # retired 2026-08-23


@pytest.mark.req("REQ-DD-021")
def test_parse_model_covers_every_active_entry():
    for name in ACTIVE_MODELS:
        assert parse_model(name) == name
