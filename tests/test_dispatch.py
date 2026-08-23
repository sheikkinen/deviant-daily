"""Tests: dispatch semantics (FR-862 AC-06, AC-07, AC-10, AC-13).

Force allocates only above a TERMINAL slot; dry_run performs no ledger
commit, no git commit, no DA call, and needs no DA secrets.
"""

import json

import pytest

from tools import steps

DRAWN_KEYS = ("prompt", "source_file", "slot", "done")


class Boom:
    """Any use is a failure — the strongest form of 'no side effects'."""

    def __call__(self, *a, **k):
        raise AssertionError(f"side effect attempted: {a!r}")

    post = get = run = __call__


@pytest.fixture
def ledger(monkeypatch, tmp_path):
    monkeypatch.setattr(steps, "REPO_DIR", tmp_path)
    monkeypatch.setattr(steps, "LEDGER", tmp_path / "state" / "published.jsonl")
    monkeypatch.setattr(steps, "CORPUS", tmp_path / "corpus.jsonl")
    (tmp_path / "state").mkdir()
    (tmp_path / "corpus.jsonl").write_text(
        "".join(json.dumps({"prompt": f"p{i}", "source_file": f"00{i}"}) + "\n" for i in range(1, 6))
    )

    def write(rows):
        (tmp_path / "state" / "published.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows)
        )
    return write


def _ok_runner(cmd, **kwargs):
    from types import SimpleNamespace
    return SimpleNamespace(returncode=0, stderr="", stdout="")


def test_terminal_slot_unforced_exits_idempotently(ledger):
    ledger([{"date": "2026-08-23", "status": "published", "source_file": "001", "prompt": "p1"}])
    out = steps.draw_step(date="2026-08-23", runner=Boom())
    assert out["done"] is True
    assert out["slot"] == 0


def test_terminal_slot_forced_allocates_next_slot(ledger):
    ledger([{"date": "2026-08-23", "status": "published", "source_file": "001", "prompt": "p1"}])
    out = steps.draw_step(date="2026-08-23", force="true", runner=_ok_runner)
    assert out["done"] is False
    assert out["slot"] == 1
    assert out["source_file"] != "001"


def test_forced_allocation_climbs_above_highest_slot(ledger):
    ledger([
        {"date": "2026-08-23", "status": "published", "source_file": "001", "prompt": "p1"},
        {"date": "2026-08-23", "status": "published", "slot": 1, "source_file": "002", "prompt": "p2"},
    ])
    out = steps.draw_step(date="2026-08-23", force="true", runner=_ok_runner)
    assert out["slot"] == 2


def test_force_resumes_an_in_flight_slot_instead_of_stranding_it(ledger):
    """AC-07: the in-flight row may already guard a DA submit."""
    ledger([{"date": "2026-08-23", "status": "drawn", "source_file": "001", "prompt": "p1"}])
    out = steps.draw_step(date="2026-08-23", force="true", runner=Boom())
    assert out["done"] is False
    assert out["slot"] == 0
    assert out["source_file"] == "001"


def test_force_false_string_does_not_force(ledger):
    """R-1 regression: "false" is truthy in Python."""
    ledger([{"date": "2026-08-23", "status": "published", "source_file": "001", "prompt": "p1"}])
    out = steps.draw_step(date="2026-08-23", force="false", runner=Boom())
    assert out["done"] is True


def test_draw_step_dry_run_commits_nothing(ledger):
    ledger([])
    out = steps.draw_step(date="2026-08-23", dry_run="true", runner=Boom())
    assert out["done"] is False
    assert not (steps.LEDGER).exists() or steps.LEDGER.read_text() == ""


def test_scheduled_path_regression_pin(ledger):
    """AC-13: no inputs -> slot 0, draws, commits normally."""
    ledger([])
    out = steps.draw_step(date="2026-08-23", runner=_ok_runner)
    assert all(k in out for k in DRAWN_KEYS)
    assert out["slot"] == 0 and out["done"] is False
    rows = [json.loads(x) for x in steps.LEDGER.read_text().splitlines()]
    assert rows[0]["status"] == "drawn" and rows[0]["slot"] == 0


def test_generate_step_honours_explicit_model(monkeypatch):
    monkeypatch.setattr(steps, "generate_image", lambda *a, **k: "/tmp/x.png")
    out = steps.generate_step("prompt", "2026-08-23", model="nano-banana-2")
    assert out["model_name"] == "nano-banana-2"


def test_generate_step_random_when_unpinned(monkeypatch):
    from tools.roster import ACTIVE_MODELS
    monkeypatch.setattr(steps, "generate_image", lambda *a, **k: "/tmp/x.png")
    out = steps.generate_step("prompt", "2026-08-23")
    assert out["model_name"] in ACTIVE_MODELS


def test_publish_step_dry_run_touches_nothing_and_needs_no_secrets(monkeypatch, ledger):
    for k in ("DA_CLIENT_ID", "DA_CLIENT_SECRET", "DA_REFRESH_TOKEN", "GH_PAT"):
        monkeypatch.delenv(k, raising=False)
    ledger([])
    out = steps.publish_step(
        post={"title": "T"}, image_path="/tmp/x.png", date="2026-08-23",
        prompt="p", source_file="001", model_name="z-image", slot=0,
        dry_run="true", runner=Boom(), session=Boom(),
    )
    assert out["dry_run"] is True
    assert "url" not in out


def test_gate_step_dry_run_does_not_commit_a_skip(ledger):
    ledger([])
    low = {"title": "T", "paragraphs": ["p"], "quote": None, "tags": ["x"],
           "confidence": "low", "mature": False, "mature_level": None,
           "mature_classification": []}
    out = steps.gate_step(description=low, date="2026-08-23", prompt="p",
                          source_file="001", slot=0, dry_run="true", runner=Boom())
    assert out["publish"] is False
