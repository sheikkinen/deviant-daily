"""Tests: FR-886 deterministic draw routing — refusal-evidence join,
pure eligibility, draw-boundary model binding, unroutable skip with
zero ledger writes."""

import json
import random
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import route, steps
from tools.failures import prompt_sha
from tools.roster import choose_model, validate_roster
from tools.route import (
    UnroutablePrompt,
    content_tuple,
    eligible_models,
    load_failure_rows,
    load_taxonomy,
    refusal_evidence,
)

SAFE = ("safe", "safe")
SPICY = ("mature", "safe")

CORPUS_ROWS = [
    {
        "prompt": "a calm forest",
        "source_file": "001",
        "content": {"sexual": "safe", "gore": "safe"},
    },
    {
        "prompt": "a spicy scene",
        "source_file": "002",
        "content": {"sexual": "mature", "gore": "safe"},
    },
]


def _ok_runner(cmd, **kwargs):
    return SimpleNamespace(returncode=0, stderr="", stdout="")


def _refusal(model, prompt):
    return {"model": model, "prompt_sha": prompt_sha(prompt), "error_class": "refusal"}


@pytest.fixture
def axes():
    return load_taxonomy()


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(steps, "REPO_DIR", tmp_path)
    monkeypatch.setattr(steps, "LEDGER", tmp_path / "state" / "published.jsonl")
    monkeypatch.setattr(steps, "FAILURES", tmp_path / "state" / "failures.jsonl")
    monkeypatch.setattr(steps, "CORPUS", tmp_path / "corpus.jsonl")
    (tmp_path / "state").mkdir()
    (tmp_path / "corpus.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in CORPUS_ROWS)
    )

    def write_failures(rows):
        (tmp_path / "state" / "failures.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows)
        )

    return tmp_path, write_failures


def _drawn_rows(tmp_path):
    p = tmp_path / "state" / "published.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


@pytest.mark.req("REQ-DD-110")
def test_refusal_evidence_join(axes):
    """AC-02: sha join, refusal-only, non-corpus counted, absent = empty."""
    rows = [
        _refusal("grok", "a spicy scene"),
        {
            "model": "grok",
            "prompt_sha": prompt_sha("a spicy scene"),
            "error_class": "transport",
        },
        _refusal("grok", "an ad-hoc user prompt not in corpus"),
    ]
    join = refusal_evidence(rows, CORPUS_ROWS, axes)
    assert join.cells == {("grok", SPICY): 1}
    assert join.non_refusal == 1
    assert join.non_corpus == 1
    assert load_failure_rows(Path("/nonexistent/failures.jsonl")) == []


@pytest.mark.req("REQ-DD-111")
def test_eligibility_pure_and_typed_exclusion(axes):
    """AC-03: cold start admits, exact-tuple refusal excludes, empty raises."""
    roster = validate_roster()
    empty = refusal_evidence([], CORPUS_ROWS, axes)
    assert eligible_models(SPICY, empty, roster) == sorted(roster)
    one = refusal_evidence([_refusal("grok", "a spicy scene")], CORPUS_ROWS, axes)
    assert "grok" not in eligible_models(SPICY, one, roster)
    assert "grok" in eligible_models(SAFE, one, roster)  # other tuple unaffected
    all_refused = refusal_evidence(
        [_refusal(m, "a spicy scene") for m in roster], CORPUS_ROWS, axes
    )
    with pytest.raises(UnroutablePrompt):
        route.route(SPICY, all_refused, roster)


@pytest.mark.req("REQ-DD-112")
def test_deterministic_and_cold_start_equals_blind_pick(axes):
    """AC-04: injected RNG; empty evidence == today's choose_model pick."""
    roster = validate_roster()
    empty = refusal_evidence([], CORPUS_ROWS, axes)
    picks = {route.route(SPICY, empty, roster, rng=random.Random(7)) for _ in range(3)}
    assert len(picks) == 1
    assert picks.pop() == choose_model(rng=random.Random(7))[0]


@pytest.mark.req("REQ-DD-113")
def test_draw_binds_model_and_commits_binding(env):
    """AC-05: routed binding recorded on the committed drawn row."""
    tmp_path, _ = env
    out = steps.draw_step(date="2026-08-25", runner=_ok_runner)
    assert out["model"] in validate_roster()
    (row,) = _drawn_rows(tmp_path)
    assert row["model"] == out["model"]
    assert row["status"] == "drawn"


@pytest.mark.req("REQ-DD-113")
def test_unroutable_candidate_skipped_without_ledger_writes(env):
    """AC-05: spicy row unroutable for all -> safe row drawn, no extra rows."""
    tmp_path, write_failures = env
    roster = validate_roster()
    write_failures([_refusal(m, "a spicy scene") for m in roster])
    out = steps.draw_step(date="2026-08-25", runner=_ok_runner)
    assert out["source_file"] == "001"  # the safe candidate
    rows = _drawn_rows(tmp_path)
    assert len(rows) == 1 and rows[0]["source_file"] == "001"


@pytest.mark.req("REQ-DD-113")
def test_all_unroutable_raises_with_zero_ledger_writes(env, monkeypatch):
    """AC-05: every candidate unroutable -> typed exclusion, nothing burned."""
    tmp_path, write_failures = env
    (tmp_path / "corpus.jsonl").write_text(json.dumps(CORPUS_ROWS[1]) + "\n")
    roster = validate_roster()
    write_failures([_refusal(m, "a spicy scene") for m in roster])
    failures_before = (tmp_path / "state" / "failures.jsonl").read_text()
    with pytest.raises(UnroutablePrompt):
        steps.draw_step(date="2026-08-25", runner=_ok_runner)
    assert _drawn_rows(tmp_path) == []
    assert (tmp_path / "state" / "failures.jsonl").read_text() == failures_before


@pytest.mark.req("REQ-DD-114")
def test_generation_consumes_the_draw_binding(env, monkeypatch):
    """AC-06: mature prompt bypasses the refused model; generate uses it."""
    tmp_path, write_failures = env
    roster = validate_roster()
    only = sorted(roster)[0]
    (tmp_path / "corpus.jsonl").write_text(json.dumps(CORPUS_ROWS[1]) + "\n")
    write_failures([_refusal(m, "a spicy scene") for m in roster if m != only])
    out = steps.draw_step(date="2026-08-25", runner=_ok_runner)
    assert out["model"] == only  # every other model was bypassed
    seen = {}

    def fake(prompt, config, output_path):
        seen["slug"] = config["slug"]
        return "/tmp/x.png"

    monkeypatch.setattr(steps, "generate_image", fake)
    result = steps.generate_step(out["prompt"], out["date"], model=out["model"])
    assert result["model_name"] == only
    assert seen["slug"] == roster[only]["slug"]


@pytest.mark.req("REQ-DD-114")
def test_graph_wires_binding_from_draw_to_generate():
    """AC-06: mechanical wiring witness — no independent re-selection."""
    text = Path(steps.REPO_DIR / "graph.yaml").read_text()
    assert '"{state.drawn.result.model}"' in text
    generate_block = text.split("generate:")[1].split("describe:")[0]
    assert "{state.drawn.result.model}" in generate_block


@pytest.mark.req("REQ-DD-115")
def test_pinned_model_bypasses_routing(env):
    """AC-07: pin wins even when evidence excludes it; binding recorded."""
    tmp_path, write_failures = env
    write_failures(
        [_refusal("grok", "a spicy scene"), _refusal("grok", "a calm forest")]
    )
    out = steps.draw_step(date="2026-08-25", model="grok", runner=_ok_runner)
    assert out["model"] == "grok"
    (row,) = _drawn_rows(tmp_path)
    assert row["model"] == "grok"


@pytest.mark.req("REQ-DD-116")
def test_invalid_fingerprints_route_maximally_mature(axes):
    """AC-08: missing/partial/invalid content -> (mature, mature)."""
    assert content_tuple({"prompt": "x"}, axes) == ("mature", "mature")
    assert content_tuple({"content": {"sexual": "safe"}}, axes) == ("mature", "mature")
    assert content_tuple({"content": {"sexual": "spicy", "gore": "safe"}}, axes) == (
        "mature",
        "mature",
    )
    assert content_tuple(CORPUS_ROWS[0], axes) == SAFE


@pytest.mark.req("REQ-DD-116")
def test_taxonomy_drift_fails(tmp_path):
    """AC-08: a drifted taxonomy artifact is rejected, never coerced."""
    drifted = tmp_path / "taxonomy.yaml"
    drifted.write_text(
        "content:\n  sexual:\n    values: [safe, spicy]\n"
        "  gore:\n    values: [safe, mature]\n"
    )
    with pytest.raises(route.TaxonomyDrift):
        load_taxonomy(drifted)


@pytest.mark.req("REQ-DD-117")
def test_router_is_offline(env):
    """AC-09: no provider/network imports in the routing path."""
    source = Path(route.__file__).read_text()
    assert not re.search(r"\b(httpx|replicate|requests)\b", source)
    out = steps.draw_step(date="2026-08-25", runner=_ok_runner)
    assert out["model"]  # full draw path ran with zero network access
