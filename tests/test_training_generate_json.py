"""Witness tests for training/generate.py --json (yamlgraph FR-881
AC-02/AC-03): parseable JSONL, frozen schema, provenance stamping,
deterministic seeds, rejected raw text never emitted."""

import json
import subprocess
import sys
from pathlib import Path

from training.boundary import Boundary
from training.generate import format_jsonl, provenance, run_generation

REPO = Path(__file__).parent.parent
CKPT = REPO / "training" / "ckpt" / "model.pt"

CORPUS = [
    "a dark forest of glass trees under a violet sky where shadows sing softly",
    "neon city streets with rain slick chrome reflections in every window pane",
]
PAD = " atmospheric painterly detailed lighting " * 3


def _ok(i: int = 0) -> str:
    return f"luminous koi number {i} drifting through a paper lantern sky,{PAD}".strip()


def test_run_generation_schema_and_order():
    outputs = [
        ("a portrait of katja in moonlight" + PAD, True),
        (_ok(1), True),
        (_ok(2), True),
    ]
    it = iter(outputs)
    candidates, summary = run_generation(lambda: next(it), Boundary(CORPUS), n=2)
    assert [c["ordinal"] for c in candidates] == [1, 2]
    assert candidates[0]["attempts_for_candidate"] == 2  # one redaction first
    assert candidates[1]["attempts_for_candidate"] == 1
    assert summary["attempts"] == 3
    assert summary["verdict_counts"] == {"redaction": 1, "pass": 2}


def test_rejected_raw_text_never_in_jsonl():
    bad = "a portrait of katja in moonlight" + PAD
    it = iter([(bad, True), (_ok(), True)])
    candidates, summary = run_generation(lambda: next(it), Boundary(CORPUS), n=1)
    meta = {"seed": 1, "temp": 0.8, "top_k": 40, "cond": "prose", "start": ""}
    text = format_jsonl(
        candidates, summary, meta, {"ckpt_sha": "x", "corpus_sha": "y", "git_sha": "z"}
    )
    assert "katja" not in text


def test_format_jsonl_parseable_with_frozen_fields():
    it = iter([(_ok(), True)])
    candidates, summary = run_generation(lambda: next(it), Boundary(CORPUS), n=1)
    meta = {"seed": 7, "temp": 0.8, "top_k": 40, "cond": "prose", "start": "abc"}
    prov = {"ckpt_sha": "c" * 12, "corpus_sha": "d" * 12, "git_sha": "e" * 12}
    lines = format_jsonl(candidates, summary, meta, prov).strip().splitlines()
    records = [json.loads(line) for line in lines]
    assert records[-1]["record"] == "summary"
    cand = records[0]
    assert cand["record"] == "candidate"
    for field in (
        "ordinal",
        "prompt",
        "attempts_for_candidate",
        "verdict_counts",
        "seed",
        "temp",
        "top_k",
        "cond",
        "start",
        "ckpt_sha",
        "corpus_sha",
        "git_sha",
    ):
        assert field in cand, field
    assert records[-1]["attempts"] == summary["attempts"]


def test_provenance_stamps():
    prov = provenance(REPO)
    assert set(prov) == {"ckpt_sha", "corpus_sha", "git_sha"}
    assert all(len(v) >= 7 for v in prov.values())


def test_cli_json_deterministic_and_pure_stdout():
    if not CKPT.exists():
        import pytest

        pytest.skip("no trained checkpoint on this machine")
    cmd = [
        sys.executable,
        "-m",
        "training.generate",
        "--json",
        "--n",
        "2",
        "--temp",
        "0.8",
        "--seed",
        "11",
    ]
    a = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, check=True)
    b = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, check=True)
    assert a.stdout == b.stdout
    records = [json.loads(line) for line in a.stdout.strip().splitlines()]
    assert records[-1]["record"] == "summary"
    assert sum(1 for r in records if r["record"] == "candidate") == 2
