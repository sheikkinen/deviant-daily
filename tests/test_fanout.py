"""Tests: FR-888 fan-out — one prompt through many models, sequential,
ordered outcomes, probe failure rows, generation-only boundary."""

import json
from types import SimpleNamespace

import pytest

from tools import fanout, user_generate
from tools.failures import FailureRecord
from tools.generate import GenerationError
from tools.ledger import LedgerCommitError
from tools.roster import RosterError

PROMPT = "the same prompt everywhere"
THREE = ["z-image", "grok", "recraft"]


class GitRecorder:
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
    monkeypatch.setattr(fanout, "REPO_DIR", tmp_path)
    monkeypatch.setattr(fanout, "FAILURES", tmp_path / "state" / "failures.jsonl")
    return tmp_path


def _fake_generate(monkeypatch, refuse_slugs=()):
    def fake(prompt, config, output_path):
        if config["slug"] in refuse_slugs:
            raise GenerationError("flagged as NSFW")
        from pathlib import Path

        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
        return str(p)

    monkeypatch.setattr(fanout, "generate_image", fake)


def _rows(tmp_path):
    p = tmp_path / "state" / "failures.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


@pytest.mark.req("REQ-DD-103")
def test_all_models_resolve_in_roster_order():
    """AC-02: all-models = every active model, deterministic order."""
    selected = fanout.resolve_models(None)
    assert selected == sorted(selected)
    assert len(selected) >= 3


@pytest.mark.req("REQ-DD-103")
def test_subset_order_unknown_and_duplicates():
    """AC-03 + AC-04: explicit order kept; unknown/duplicates fail fast."""
    assert fanout.resolve_models(["grok", "z-image"]) == ["grok", "z-image"]
    with pytest.raises(RosterError, match="z-image"):
        fanout.resolve_models(["no-such-model"])
    with pytest.raises(ValueError, match="duplicate"):
        fanout.resolve_models(["grok", "grok"])


@pytest.mark.req("REQ-DD-103")
def test_unknown_model_before_any_side_effect(env, monkeypatch):
    """AC-03: preflight fires before the first provider call or write."""
    calls = []
    monkeypatch.setattr(fanout, "generate_image", lambda *a: calls.append(a))
    with pytest.raises(RosterError):
        fanout.generate_all(
            PROMPT,
            "2026-08-25",
            ["z-image", "bogus"],
            env / "out",
            runner=GitRecorder(),
        )
    assert calls == []
    assert not (env / "out").exists()


@pytest.mark.req("REQ-DD-104")
def test_middle_refusal_does_not_abort_others(env, monkeypatch):
    """AC-01: model 2 refuses; 1 and 3 still generate; one probe row."""
    refused_slug = fanout.resolve_configs(["grok"])["grok"]["slug"]
    _fake_generate(monkeypatch, refuse_slugs={refused_slug})
    outcomes = fanout.generate_all(
        PROMPT,
        "2026-08-25",
        ["z-image", "grok", "recraft"],
        env / "out",
        runner=GitRecorder(),
    )
    assert [o.model for o in outcomes] == ["z-image", "grok", "recraft"]
    assert [o.status for o in outcomes] == ["ok", "failed", "ok"]
    (row,) = _rows(env)
    assert row["run_source"] == "probe"
    assert row["model"] == "grok"
    assert row["slot"] is None and row["source_file"] is None


@pytest.mark.req("REQ-DD-105")
def test_outcome_is_typed_and_exclusive(env, monkeypatch):
    """AC-08: model, slug, status, exactly one of path | failure."""
    refused_slug = fanout.resolve_configs(["grok"])["grok"]["slug"]
    _fake_generate(monkeypatch, refuse_slugs={refused_slug})
    ok, failed = fanout.generate_all(
        PROMPT, "2026-08-25", ["z-image", "grok"], env / "out", runner=GitRecorder()
    )
    assert ok.slug and ok.path and ok.failure is None
    assert failed.path is None and isinstance(failed.failure, FailureRecord)
    with pytest.raises(Exception):
        fanout.GenerationOutcome(
            model="m", slug="s", status="ok", path="p", failure=failed.failure
        )


@pytest.mark.req("REQ-DD-106")
def test_no_publish_side_effects(env, monkeypatch):
    """AC-05: no published.jsonl, git only for the failure row."""
    _fake_generate(monkeypatch)
    runner = GitRecorder()
    fanout.generate_all(PROMPT, "2026-08-25", THREE, env / "out", runner=runner)
    assert not (env / "state" / "published.jsonl").exists()
    assert runner.cmds == []  # all succeeded: no commits at all


@pytest.mark.req("REQ-DD-107")
def test_distinct_output_paths_no_clobber(env, monkeypatch):
    """AC-06: path = <out_dir>/<date>-<model>.png, one file per model."""
    _fake_generate(monkeypatch)
    outcomes = fanout.generate_all(
        PROMPT, "2026-08-25", ["z-image", "grok"], env / "out", runner=GitRecorder()
    )
    paths = [o.path for o in outcomes]
    assert paths == [
        str(env / "out" / "2026-08-25-z-image.png"),
        str(env / "out" / "2026-08-25-grok.png"),
    ]
    assert len(set(paths)) == 2


@pytest.mark.req("REQ-DD-108")
def test_ledger_commit_failure_aborts_red(env, monkeypatch):
    """AC-07: failure-row commit failure stops the run, both errors visible."""
    refused_slug = fanout.resolve_configs(["z-image"])["z-image"]["slug"]
    _fake_generate(monkeypatch, refuse_slugs={refused_slug})
    calls_after = []
    real = fanout.generate_image

    def counting(prompt, config, output_path):
        if config["slug"] != refused_slug:
            calls_after.append(config["slug"])
        return real(prompt, config, output_path)

    monkeypatch.setattr(fanout, "generate_image", counting)
    with pytest.raises(GenerationError) as excinfo:
        fanout.generate_all(
            PROMPT,
            "2026-08-25",
            ["z-image", "grok"],
            env / "out",
            runner=GitRecorder(fail_on="push"),
        )
    assert isinstance(excinfo.value.__cause__, LedgerCommitError)
    assert calls_after == []  # did not continue to later models


@pytest.mark.req("REQ-DD-109")
def test_cli_models_flag_delegates_to_fanout(env, monkeypatch, tmp_path):
    """FR-889 AC-08: --models delegates to the enforced primitive."""
    seen = {}

    def fake_all(prompt, date, models, out_dir, runner=None):
        seen.update(prompt=prompt, date=date, models=models)
        return []

    monkeypatch.setattr("tools.user_generate.generate_all", fake_all)
    user_generate.main(
        [
            "--prompt",
            "hello",
            "--date",
            "2026-08-25",
            "--models",
            "grok,z-image",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )
    assert seen["models"] == ["grok", "z-image"]
    assert seen["prompt"] == "hello"


@pytest.mark.req("REQ-DD-109")
def test_cli_model_and_models_mutually_exclusive(tmp_path):
    """--model (single) conflicts with --models/--all-models."""
    with pytest.raises(SystemExit):
        user_generate.main(
            [
                "--prompt",
                "x",
                "--model",
                "grok",
                "--models",
                "grok",
                "--out-dir",
                str(tmp_path),
            ]
        )
