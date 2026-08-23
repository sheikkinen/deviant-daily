"""Tests: run semantics after the 2026-08-23 de-hedging.

No dry_run, no force. If the pipeline runs, it publishes. The only
thing that diverts a run is an in-flight slot, which is resumed rather
than duplicated — that is FR-826 R-3 protecting a DA call that may
already be in flight, not a guard against the operator.
"""

import inspect
import json

import pytest

from tools import steps


class Boom:
    """Any use is a failure."""

    def __call__(self, *a, **k):
        raise AssertionError(f"side effect attempted: {a!r}")

    post = get = run = __call__


def _ok_runner(cmd, **kwargs):
    from types import SimpleNamespace
    return SimpleNamespace(returncode=0, stderr="", stdout="")


@pytest.fixture
def ledger(monkeypatch, tmp_path):
    monkeypatch.setattr(steps, "REPO_DIR", tmp_path)
    monkeypatch.setattr(steps, "LEDGER", tmp_path / "state" / "published.jsonl")
    monkeypatch.setattr(steps, "CORPUS", tmp_path / "corpus.jsonl")
    (tmp_path / "state").mkdir()
    (tmp_path / "corpus.jsonl").write_text(
        "".join(json.dumps({"prompt": f"p{i}", "source_file": f"00{i}"}) + "\n"
                for i in range(1, 6))
    )

    def write(rows):
        (tmp_path / "state" / "published.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows)
        )
    return write


def test_first_run_of_the_day_takes_slot_zero(ledger):
    ledger([])
    out = steps.draw_step(date="2026-08-23", runner=_ok_runner)
    assert out["slot"] == 0
    assert out["done"] is False


def test_a_run_after_a_published_slot_publishes_again(ledger):
    """If it runs, it publishes — no idempotent no-op for the operator."""
    ledger([{"date": "2026-08-23", "slot": 0, "status": "published",
             "source_file": "001", "prompt": "p1"}])
    out = steps.draw_step(date="2026-08-23", runner=_ok_runner)
    assert out["done"] is False
    assert out["slot"] == 1
    assert out["source_file"] != "001"


def test_a_run_after_a_skipped_slot_publishes_again(ledger):
    ledger([{"date": "2026-08-23", "slot": 0, "status": "skipped",
             "source_file": "001", "prompt": "p1"}])
    assert steps.draw_step(date="2026-08-23", runner=_ok_runner)["slot"] == 1


def test_slots_keep_climbing(ledger):
    ledger([
        {"date": "2026-08-23", "slot": 0, "status": "published", "source_file": "001"},
        {"date": "2026-08-23", "slot": 1, "status": "published", "source_file": "002"},
    ])
    assert steps.draw_step(date="2026-08-23", runner=_ok_runner)["slot"] == 2


def test_an_in_flight_slot_is_resumed_not_duplicated(ledger):
    """The only diversion: its committed row may guard a live DA submit."""
    ledger([{"date": "2026-08-23", "slot": 0, "status": "submitted",
             "source_file": "001", "prompt": "p1"}])
    out = steps.draw_step(date="2026-08-23", runner=Boom())
    assert out["slot"] == 0
    assert out["source_file"] == "001"
    assert out["done"] is False


def test_draw_step_takes_no_flags():
    params = set(inspect.signature(steps.draw_step).parameters)
    assert "dry_run" not in params and "force" not in params


def test_publish_step_takes_no_dry_run():
    assert "dry_run" not in inspect.signature(steps.publish_step).parameters


def test_gate_step_takes_no_dry_run():
    assert "dry_run" not in inspect.signature(steps.gate_step).parameters


def test_generate_step_honours_explicit_model(monkeypatch):
    monkeypatch.setattr(steps, "generate_image", lambda *a, **k: "/tmp/x.png")
    out = steps.generate_step("p", "2026-08-23", model="nano-banana-2")
    assert out["model_name"] == "nano-banana-2"


def test_generate_step_random_when_unpinned(monkeypatch):
    from tools.roster import ACTIVE_MODELS
    monkeypatch.setattr(steps, "generate_image", lambda *a, **k: "/tmp/x.png")
    assert steps.generate_step("p", "2026-08-23")["model_name"] in ACTIVE_MODELS
