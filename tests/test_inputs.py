"""Tests: dispatch input normalization (FR-862 R-1, AC-05).

Workflow inputs arrive as strings. `"false"` is truthy in Python, so an
unparsed boolean would invert `force`/`dry_run` — a live publish when a
dry run was asked for. Every value is parsed at the boundary and every
invalid value raises BEFORE any side effect.
"""

import pytest

from tools.inputs import parse_date, parse_flag, parse_model, parse_slot
from tools.roster import ACTIVE_MODELS, RosterError


@pytest.mark.parametrize("raw", ["false", "False", "FALSE"])
def test_parse_flag_string_false_is_false(raw):
    assert parse_flag(raw) is False


@pytest.mark.parametrize("raw", ["true", "True", "TRUE"])
def test_parse_flag_string_true_is_true(raw):
    assert parse_flag(raw) is True


def test_parse_flag_empty_uses_default():
    assert parse_flag("", default=False) is False
    assert parse_flag("", default=True) is True


def test_parse_flag_passes_through_real_bools():
    assert parse_flag(True) is True
    assert parse_flag(False) is False


@pytest.mark.parametrize("raw", ["yes", "1", "0", "no", "maybe", "  true"])
def test_parse_flag_rejects_anything_else(raw):
    with pytest.raises(ValueError):
        parse_flag(raw)


def test_parse_date_empty_is_today_utc():
    from datetime import UTC, datetime
    assert parse_date("") == datetime.now(UTC).date().isoformat()


def test_parse_date_accepts_iso():
    assert parse_date("2026-08-23") == "2026-08-23"


@pytest.mark.parametrize("raw", ["23-08-2026", "2026-8-3", "2026-08-23-manual", "today"])
def test_parse_date_rejects_non_iso(raw):
    with pytest.raises(ValueError):
        parse_date(raw)


@pytest.mark.parametrize("raw,expected", [("", 0), ("0", 0), ("2", 2), (3, 3)])
def test_parse_slot_accepts_non_negative(raw, expected):
    assert parse_slot(raw) == expected


@pytest.mark.parametrize("raw", ["-1", -1, "1.5", "abc", None])
def test_parse_slot_rejects_invalid(raw):
    with pytest.raises((ValueError, TypeError)):
        parse_slot(raw)


@pytest.mark.parametrize("raw", ["", "random", "RANDOM"])
def test_parse_model_random_means_unpinned(raw):
    assert parse_model(raw) == ""


def test_parse_model_accepts_active_name():
    assert parse_model("nano-banana-2") == "nano-banana-2"


def test_parse_model_rejects_unknown():
    with pytest.raises(RosterError):
        parse_model("flux-ultra")  # retired 2026-08-23


def test_parse_model_covers_every_active_entry():
    for name in ACTIVE_MODELS:
        assert parse_model(name) == name
