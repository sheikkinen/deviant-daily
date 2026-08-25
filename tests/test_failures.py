"""Tests: FR-887 structured generation-failure logging — record at the
generate_step boundary, commit to state/failures.jsonl, then re-raise.
Two-error semantics (AC-06): the provider failure stays primary; a
ledger commit failure is attached, never swallowed."""

import hashlib
import json
from types import SimpleNamespace

import httpx
import pytest

from tools import steps
from tools.failures import (
    EXCERPT_CAP,
    FailureRecord,
    classify_failure,
    redact_excerpt,
)
from tools.generate import GenerationError
from tools.ledger import LedgerCommitError

PROMPT = "a serene mountain lake at dawn"


class GitRecorder:
    """Records git commands; optionally fails a given subcommand."""

    def __init__(self, fail_on=None):
        self.cmds = []
        self.fail_on = fail_on

    def __call__(self, cmd, **kwargs):
        self.cmds.append(cmd)
        if self.fail_on and self.fail_on in cmd:
            return SimpleNamespace(returncode=1, stderr="boom", stdout="")
        return SimpleNamespace(returncode=0, stderr="", stdout="")


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("REPLICATE_API_TOKEN", "x")
    monkeypatch.setattr(steps, "REPO_DIR", tmp_path)
    monkeypatch.setattr(steps, "FAILURES", tmp_path / "state" / "failures.jsonl")
    return tmp_path


def _fail_generate(monkeypatch, exc):
    def boom(prompt, config, output_path):
        raise exc

    monkeypatch.setattr(steps, "generate_image", boom)


def _rows(tmp_path):
    p = tmp_path / "state" / "failures.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


@pytest.mark.req("REQ-DD-092")
def test_refusal_commits_row_then_reraises(env, monkeypatch):
    """AC-01: refusal appends+commits exactly one row AND the run stays red."""
    _fail_generate(monkeypatch, GenerationError("prediction flagged as NSFW"))
    runner = GitRecorder()
    with pytest.raises(GenerationError):
        steps.generate_step(
            PROMPT,
            "2026-08-25",
            model="z-image",
            source_file="prompts/corpus.jsonl#42",
            slot=0,
            runner=runner,
        )
    rows = _rows(env)
    assert len(rows) == 1
    assert [c[:2] for c in runner.cmds] == [
        ["git", "add"],
        ["git", "commit"],
        ["git", "pull"],
        ["git", "push"],
    ]


@pytest.mark.req("REQ-DD-094")
def test_corpus_row_fields_and_privacy(env, monkeypatch):
    """AC-02 + AC-07: full context recorded; prompt only as sha256."""
    _fail_generate(monkeypatch, GenerationError("blocked by safety filter"))
    with pytest.raises(GenerationError):
        steps.generate_step(
            PROMPT,
            "2026-08-25",
            model="z-image",
            source_file="prompts/corpus.jsonl#42",
            slot=3,
            runner=GitRecorder(),
        )
    (row,) = _rows(env)
    assert row["date"] == "2026-08-25"
    assert row["slot"] == 3
    assert row["model"] == "z-image"
    assert row["slug"]
    assert row["source_file"] == "prompts/corpus.jsonl#42"
    assert row["error_class"] == "refusal"
    assert row["run_source"] == "corpus"
    assert row["prompt_sha"] == hashlib.sha256(PROMPT.encode("utf-8")).hexdigest()
    assert PROMPT not in json.dumps(row)


@pytest.mark.req("REQ-DD-093")
@pytest.mark.parametrize(
    "exc,expected",
    [
        (GenerationError("output flagged NSFW by provider"), "refusal"),
        (httpx.ConnectError("connection refused"), "transport"),
        (httpx.ReadTimeout("read timed out"), "timeout"),
        (RuntimeError("some novel explosion"), "unknown"),
    ],
)
def test_error_classes_witnessed_with_excerpt(env, monkeypatch, exc, expected):
    """AC-03: all four classes; raw excerpt preserved in every row."""
    _fail_generate(monkeypatch, exc)
    with pytest.raises(type(exc)):
        steps.generate_step(PROMPT, "2026-08-25", model="z-image", runner=GitRecorder())
    (row,) = _rows(env)
    assert row["error_class"] == expected
    assert str(exc)[:40] in row["provider_message"]


@pytest.mark.req("REQ-DD-093")
def test_classifier_is_closed_contract():
    """AC-03: classification bound to exception types, unknown never coerced."""
    assert classify_failure(httpx.TimeoutException("t")) == "timeout"
    assert classify_failure(httpx.HTTPError("h")) == "transport"
    assert classify_failure(GenerationError("content policy violation")) == "refusal"
    assert classify_failure(ValueError("???")) == "unknown"


@pytest.mark.req("REQ-DD-095")
def test_success_writes_no_row(env, monkeypatch):
    """AC-04: a successful generation leaves no failure row."""
    monkeypatch.setattr(steps, "generate_image", lambda *a, **k: "/tmp/x.png")
    result = steps.generate_step(
        PROMPT, "2026-08-25", model="z-image", runner=GitRecorder()
    )
    assert result["image_path"] == "/tmp/x.png"
    assert _rows(env) == []


@pytest.mark.req("REQ-DD-095")
def test_publish_ledger_untouched(env, monkeypatch):
    """AC-05: failure ledger is its own artifact; published.jsonl untouched."""
    _fail_generate(monkeypatch, GenerationError("nsfw"))
    with pytest.raises(GenerationError):
        steps.generate_step(PROMPT, "2026-08-25", model="z-image", runner=GitRecorder())
    assert not (env / "state" / "published.jsonl").exists()
    (row,) = _rows(env)
    assert row["error_class"] not in ("drawn", "submitted", "published", "skipped")


@pytest.mark.req("REQ-DD-096")
def test_commit_failure_keeps_original_error_primary(env, monkeypatch):
    """AC-06: ledger commit failure cannot go green; both errors inspectable."""
    original = GenerationError("flagged NSFW")
    _fail_generate(monkeypatch, original)
    runner = GitRecorder(fail_on="push")
    with pytest.raises(GenerationError) as excinfo:
        steps.generate_step(PROMPT, "2026-08-25", model="z-image", runner=runner)
    assert excinfo.value is original
    assert isinstance(excinfo.value.__cause__, LedgerCommitError)
    assert any("failure-ledger" in n for n in getattr(excinfo.value, "__notes__", []))


@pytest.mark.req("REQ-DD-097")
def test_non_corpus_nullability_and_run_sources(env, monkeypatch):
    """AC-08: user/probe rows carry null slot/source_file."""
    for run_source in ("user", "probe"):
        _fail_generate(monkeypatch, GenerationError("nsfw"))
        with pytest.raises(GenerationError):
            steps.generate_step(
                PROMPT,
                "2026-08-25",
                model="z-image",
                run_source=run_source,
                runner=GitRecorder(),
            )
    rows = _rows(env)
    assert [r["run_source"] for r in rows] == ["user", "probe"]
    assert all(r["slot"] is None for r in rows)
    assert all(r["source_file"] is None for r in rows)


@pytest.mark.req("REQ-DD-094")
def test_excerpt_capped_and_redacted():
    """AC-02: cap enforced; secrets and URL credentials never committed."""
    long = "x" * (EXCERPT_CAP * 3)
    assert len(redact_excerpt(long)) <= EXCERPT_CAP
    redacted = redact_excerpt(
        "401 token=r8_abc123secret at https://u:pw@api.example.com/v1"
    )
    assert "r8_abc123secret" not in redacted
    assert "u:pw@" not in redacted


@pytest.mark.req("REQ-DD-094")
def test_failure_record_schema_frozen():
    """AC-02: schema semantics — ts ISO-8601 UTC, closed enums."""
    row = FailureRecord(
        ts="2026-08-25T06:00:00+00:00",
        date="2026-08-25",
        slot=None,
        model="z-image",
        slug="prunaai/z-image-turbo",
        prompt_sha="a" * 64,
        source_file=None,
        error_class="unknown",
        provider_message="m",
        run_source="probe",
    )
    assert row.slot is None
    with pytest.raises(Exception):
        FailureRecord(**{**row.model_dump(), "error_class": "oops"})
    with pytest.raises(Exception):
        FailureRecord(**{**row.model_dump(), "run_source": "cron"})
