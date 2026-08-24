"""Tests: slot identity (FR-862 R-3, AC-08..AC-13).

`(date, slot)` is the run identity. Old slot-less rows normalize to
slot 0 at the read boundary. `force` may only allocate above a TERMINAL
slot — an in-flight slot is resumed, never stranded, because its
`submitted` row may already guard a DA call in flight.
"""

import json

import pytest

from tools.corpus import draw_prompt
from tools.ledger import entry_for_slot, latest_slot, read_ledger
from tools.post import post_path

CORPUS = [
    {"prompt": "p-one", "source_file": "001"},
    {"prompt": "p-two", "source_file": "002"},
    {"prompt": "p-three", "source_file": "003"},
]


def _write(tmp_path, rows):
    p = tmp_path / "published.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def _corpus(tmp_path):
    p = tmp_path / "corpus.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in CORPUS))
    return p


@pytest.mark.req("REQ-DD-052")
def test_read_ledger_normalizes_slotless_rows_to_zero(tmp_path):
    p = _write(
        tmp_path, [{"date": "2026-08-19", "status": "published", "source_file": "001"}]
    )
    assert read_ledger(p)[0]["slot"] == 0


@pytest.mark.req("REQ-DD-052")
def test_read_ledger_normalizes_the_live_committed_ledger():
    """AC-08 against the real file, not a fixture."""
    from pathlib import Path

    live = Path(__file__).parent.parent / "state" / "published.jsonl"
    entries = read_ledger(live)
    assert entries, "live ledger is empty"
    assert all(isinstance(e["slot"], int) and e["slot"] >= 0 for e in entries)


@pytest.mark.parametrize("bad", [-1, "0", 1.5, None])
@pytest.mark.req("REQ-DD-053")
def test_read_ledger_rejects_invalid_slot(tmp_path, bad):
    p = _write(tmp_path, [{"date": "2026-08-19", "status": "published", "slot": bad}])
    with pytest.raises(ValueError):
        read_ledger(p)


@pytest.mark.req("REQ-DD-054")
def test_entry_for_slot_isolates_slots(tmp_path):
    rows = [
        {"date": "2026-08-23", "status": "published", "source_file": "001"},
        {"date": "2026-08-23", "status": "drawn", "slot": 1, "source_file": "002"},
    ]
    entries = read_ledger(_write(tmp_path, rows))
    assert entry_for_slot(entries, "2026-08-23", 0)["status"] == "published"
    assert entry_for_slot(entries, "2026-08-23", 1)["status"] == "drawn"
    assert entry_for_slot(entries, "2026-08-23", 2) is None


@pytest.mark.req("REQ-DD-055")
def test_latest_slot(tmp_path):
    rows = [
        {"date": "2026-08-23", "status": "published", "source_file": "001"},
        {"date": "2026-08-23", "status": "published", "slot": 1, "source_file": "002"},
    ]
    entries = read_ledger(_write(tmp_path, rows))
    assert latest_slot(entries, "2026-08-23") == 1
    assert latest_slot(entries, "2026-08-24") == -1


@pytest.mark.req("REQ-DD-056")
def test_entry_for_date_is_gone():
    """A date-only lookup surviving beside a slot-aware one is the defect."""
    from tools import ledger

    assert not hasattr(ledger, "entry_for_date")


@pytest.mark.req("REQ-DD-057")
def test_draw_prompt_resumes_the_named_slot(tmp_path):
    rows = [
        {
            "date": "2026-08-23",
            "status": "published",
            "source_file": "001",
            "prompt": "p-one",
        },
        {
            "date": "2026-08-23",
            "status": "drawn",
            "slot": 1,
            "source_file": "002",
            "prompt": "p-two",
        },
    ]
    entries = read_ledger(_write(tmp_path, rows))
    drawn = draw_prompt(_corpus(tmp_path), entries, "2026-08-23", slot=1)
    assert drawn["resumed"] is True
    assert drawn["source_file"] == "002"


@pytest.mark.req("REQ-DD-058")
def test_draw_prompt_new_slot_never_reuses_published_source(tmp_path):
    """AC-12: no-repeat is global across dates AND slots."""
    rows = [
        {"date": "2026-08-23", "status": "published", "source_file": "001"},
        {"date": "2026-08-23", "status": "published", "slot": 1, "source_file": "002"},
    ]
    entries = read_ledger(_write(tmp_path, rows))
    drawn = draw_prompt(_corpus(tmp_path), entries, "2026-08-23", slot=2)
    assert drawn["resumed"] is False
    assert drawn["source_file"] == "003"


@pytest.mark.parametrize(
    "slot,expected",
    [
        (0, "posts/2026-08-23.md"),
        (1, "posts/2026-08-23-1.md"),
        (2, "posts/2026-08-23-2.md"),
    ],
)
@pytest.mark.req("REQ-DD-059")
def test_post_path_is_slot_aware(slot, expected):
    assert post_path("2026-08-23", slot) == expected
