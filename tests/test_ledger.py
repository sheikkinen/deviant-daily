"""Tests: ledger state machine + commit-failure boundaries (AC-12, AC-16)."""

import json
from types import SimpleNamespace

import pytest

from tools.corpus import CorpusExhausted, draw_prompt
from tools.ledger import (
    LedgerCommitError,
    append_entry,
    entry_for_slot,
    read_ledger,
    record_transition,
)

OK = SimpleNamespace(returncode=0, stderr="", stdout="")
FAIL = SimpleNamespace(returncode=1, stderr="push rejected", stdout="")


def ok_runner(cmd, **kw):
    return OK


def make_failing_runner(fail_on: str):
    def runner(cmd, **kw):
        return FAIL if fail_on in " ".join(cmd) else OK

    return runner


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "state").mkdir()
    return tmp_path


def test_append_and_read(repo):
    ledger = repo / "state" / "published.jsonl"
    append_entry(
        ledger, {"date": "2026-08-19", "status": "drawn", "source_file": "1-2"}
    )
    entries = read_ledger(ledger)
    assert entries[0]["status"] == "drawn"


def test_invalid_status_rejected(repo):
    with pytest.raises(ValueError):
        append_entry(repo / "state" / "l.jsonl", {"date": "d", "status": "bogus"})


def test_entry_for_slot_latest_wins(repo):
    entries = [
        {"date": "2026-08-19", "status": "drawn", "slot": 0},
        {"date": "2026-08-19", "status": "submitted", "slot": 0},
        {"date": "2026-08-18", "status": "published", "slot": 0},
    ]
    assert entry_for_slot(entries, "2026-08-19")["status"] == "submitted"
    assert entry_for_slot(entries, "2026-08-20") is None


def test_record_transition_commits(repo):
    calls = []

    def runner(cmd, **kw):
        calls.append(cmd)
        return OK

    ledger = repo / "state" / "published.jsonl"
    record_transition(repo, ledger, {"date": "d1", "status": "drawn"}, runner=runner)
    joined = [" ".join(c) for c in calls]
    assert any("git add" in c for c in joined)
    assert any("git commit" in c for c in joined)
    assert any("pull --rebase" in c for c in joined)
    assert any("git push" in c for c in joined)


def test_commit_failure_raises_before_return(repo):
    ledger = repo / "state" / "published.jsonl"
    with pytest.raises(LedgerCommitError):
        record_transition(
            repo,
            ledger,
            {"date": "d1", "status": "drawn"},
            runner=make_failing_runner("push"),
        )


def test_draw_no_repeat(repo, tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    rows = [{"prompt": f"p{i}", "source_file": f"s{i}"} for i in range(3)]
    corpus.write_text("\n".join(json.dumps(r) for r in rows))
    entries = [{"date": "2026-08-18", "status": "published", "source_file": "s0"}]
    for _ in range(20):
        drawn = draw_prompt(corpus, entries, "2026-08-19")
        assert drawn["source_file"] != "s0"


def test_draw_resumes_same_day(repo, tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(json.dumps({"prompt": "p", "source_file": "s1"}))
    entries = [
        {
            "date": "2026-08-19",
            "status": "drawn",
            "prompt": "orig",
            "source_file": "sX",
            "slot": 0,
        }
    ]
    drawn = draw_prompt(corpus, entries, "2026-08-19")
    assert drawn["resumed"] is True
    assert drawn["prompt"] == "orig"
    assert drawn["source_file"] == "sX"


def test_draw_terminal_day_reports_status(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(json.dumps({"prompt": "p", "source_file": "s1"}))
    entries = [
        {"date": "2026-08-19", "status": "published", "source_file": "s1", "slot": 0}
    ]
    drawn = draw_prompt(corpus, entries, "2026-08-19")
    assert drawn["resumed"] is True
    assert drawn["status"] == "published"


def test_corpus_exhausted(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(json.dumps({"prompt": "p", "source_file": "s1"}))
    entries = [{"date": "2026-08-18", "status": "published", "source_file": "s1"}]
    with pytest.raises(CorpusExhausted):
        draw_prompt(corpus, entries, "2026-08-19")
