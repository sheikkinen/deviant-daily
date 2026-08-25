"""FR-890 corpus fingerprint enrichment tests (CAP-14).

Witnesses: taxonomy artifact validity, classifier-output boundary
rejection, additive merge invariants, resume contract, cost guard,
distribution report, and extractor pass-through.
"""

from __future__ import annotations

import json

import pytest

from tools.fingerprint import (
    CONTENT_VALUES,
    FingerprintError,
    distribution_report,
    estimate_cost,
    genre_names,
    is_classified,
    load_taxonomy,
    merge_fingerprints,
    validate_verdict,
)

TAX = load_taxonomy()
MODEL = "claude-haiku-4-5"
DATE = "2026-08-25"


def rows3() -> list[dict]:
    return [
        {"prompt": "a", "source_file": "f1.png"},
        {"prompt": "b", "source_file": "unknown"},
        {"prompt": "c", "source_file": "f3.png"},
    ]


def verdict(
    ref: int, genre: str = "gothic", sexual: str = "safe", gore: str = "safe"
) -> dict:
    return {"ref": ref, "sexual": sexual, "gore": gore, "genre": genre}


# ── Taxonomy artifact (AC-02) ────────────────────────────────────────


@pytest.mark.req("REQ-DD-085")
def test_taxonomy_artifact_valid():
    names = genre_names(TAX)
    assert len(names) == 11
    assert names[-1] == "other", "junk-drawer cap must be demote-last"
    assert len(set(names)) == 11
    precedences = sorted(g["precedence"] for g in TAX["genres"])
    assert precedences == list(range(1, 12))
    for axis in ("sexual", "gore"):
        assert TAX["content"][axis]["values"] == ["safe", "mature"]


@pytest.mark.req("REQ-DD-085")
def test_taxonomy_fixtures_semantic():
    """Every genre carries a fixture whose expected rungs are in-set."""
    for g in TAX["genres"]:
        fx = g["fixture"]
        assert fx["genre"] == g["name"]
        assert fx["sexual"] in CONTENT_VALUES
        assert fx["gore"] in CONTENT_VALUES
        assert fx["prompt"].strip()


# ── Boundary rejection (AC-03) ───────────────────────────────────────


@pytest.mark.req("REQ-DD-086")
def test_boundary_accepts_in_set():
    assert validate_verdict(verdict(0), {0, 1}, TAX) is None


@pytest.mark.req("REQ-DD-086")
@pytest.mark.parametrize(
    ("bad", "reason"),
    [
        (verdict(9), "bad-ref"),
        ({"ref": "0", "sexual": "safe", "gore": "safe", "genre": "gothic"}, "bad-ref"),
        (verdict(0, sexual="explicit"), "bad-sexual"),
        (verdict(0, gore="suggestive"), "bad-gore"),
        (verdict(0, genre="bdsm_fetish"), "bad-genre"),
        (verdict(0, genre="landscape"), "bad-genre"),
    ],
)
def test_boundary_rejects_out_of_set(bad, reason):
    assert validate_verdict(bad, {0, 1}, TAX) == reason


@pytest.mark.req("REQ-DD-086")
def test_boundary_rejects_duplicate_ref():
    rows = rows3()
    merged, rejections = merge_fingerprints(
        rows, [verdict(0), verdict(0, genre="pinup")], TAX, MODEL, DATE
    )
    assert rejections == {"duplicate-ref": 1}
    assert merged[0]["fingerprint"]["genre"] == "gothic"


# ── Additive merge invariants (AC-05) ────────────────────────────────


@pytest.mark.req("REQ-DD-087")
def test_merge_additive_invariants():
    rows = rows3()
    before = [json.dumps(r, sort_keys=True) for r in rows]
    merged, rejections = merge_fingerprints(
        rows, [verdict(1, genre="furry", sexual="mature")], TAX, MODEL, DATE
    )
    assert len(merged) == 3
    assert [r["prompt"] for r in merged] == ["a", "b", "c"]
    # untouched rows are byte-identical
    assert json.dumps(merged[0], sort_keys=True) == before[0]
    assert json.dumps(merged[2], sort_keys=True) == before[2]
    # classified row: additive keys only, prompt intact
    assert merged[1]["prompt"] == "b"
    assert merged[1]["content"] == {"sexual": "mature", "gore": "safe"}
    fp = merged[1]["fingerprint"]
    assert fp == {"genre": "furry", "date": DATE, "model": MODEL, "taxonomy": "v1"}
    assert rejections == {}


@pytest.mark.req("REQ-DD-087")
def test_failed_row_gains_no_keys():
    rows = rows3()
    merged, rejections = merge_fingerprints(
        rows, [verdict(0), verdict(2, genre="nope")], TAX, MODEL, DATE
    )
    assert "content" not in merged[2] and "fingerprint" not in merged[2]
    assert rejections == {"bad-genre": 1}


# ── Resume contract (AC-06) ──────────────────────────────────────────


@pytest.mark.req("REQ-DD-088")
def test_resume_skips_same_taxonomy_and_model():
    rows = rows3()
    merged, _ = merge_fingerprints(rows, [verdict(0)], TAX, MODEL, DATE)
    assert is_classified(merged[0], TAX, MODEL)
    assert not is_classified(merged[1], TAX, MODEL)
    assert not is_classified(merged[0], TAX, "other-model")
    other_tax = {**TAX, "taxonomy": "v2"}
    assert not is_classified(merged[0], other_tax, MODEL)


# ── Cost guard (AC-07) ───────────────────────────────────────────────


@pytest.mark.req("REQ-DD-089")
def test_estimate_cost_and_ceiling():
    est = estimate_cost(["x" * 400] * 100)
    assert est > 0
    # full-corpus scale stays under the FR ceiling
    full = estimate_cost(["x" * 400] * 7392)
    assert full < 5.0
    with pytest.raises(FingerprintError, match="ceiling"):
        estimate_cost(["x" * 400] * 7392, ceiling=full / 2)


# ── Distribution report (AC-09) ──────────────────────────────────────


@pytest.mark.req("REQ-DD-090")
def test_distribution_report():
    rows = rows3()
    merged, _ = merge_fingerprints(
        rows,
        [verdict(0, genre="other"), verdict(1, genre="furry", sexual="mature")],
        TAX,
        MODEL,
        DATE,
    )
    report = distribution_report(merged)
    assert report["classified"] == 2
    assert report["unfingerprinted"] == 1
    assert report["genres"]["other"] == 1
    assert report["genres"]["furry"] == 1
    assert report["other_share"] == 0.5
    assert report["content"]["sexual"]["mature"] == 1


# ── Extractor pass-through (AC-08) ───────────────────────────────────


@pytest.mark.req("REQ-DD-091")
def test_extract_passthrough_inherits_by_row_id():
    from scripts.extract_corpus import merge_existing_fingerprints

    fp = {"genre": "gothic", "date": DATE, "model": MODEL, "taxonomy": "v1"}
    content = {"sexual": "safe", "gore": "safe"}
    old = [
        {"prompt": "a", "source_file": "f1.png", "content": content, "fingerprint": fp},
        {
            "prompt": "b",
            "source_file": "unknown",
            "content": content,
            "fingerprint": fp,
        },
        {
            "prompt": "gone",
            "source_file": "f9.png",
            "content": content,
            "fingerprint": fp,
        },
    ]
    new = [
        {"prompt": "a", "source_file": "f1.png"},  # unchanged → inherits
        {"prompt": "b", "source_file": "unknown"},  # unknown id, same prompt → inherits
        {"prompt": "fresh", "source_file": "f4.png"},  # new row → nothing
    ]
    merged = merge_existing_fingerprints(new, old)
    assert merged[0]["fingerprint"] == fp and merged[0]["content"] == content
    assert merged[1]["fingerprint"] == fp
    assert "fingerprint" not in merged[2]


@pytest.mark.req("REQ-DD-091")
def test_extract_passthrough_no_stale_inherit_on_changed_prompt():
    from scripts.extract_corpus import merge_existing_fingerprints

    fp = {"genre": "gothic", "date": DATE, "model": MODEL, "taxonomy": "v1"}
    old = [
        {
            "prompt": "original text",
            "source_file": "f1.png",
            "content": {"sexual": "safe", "gore": "safe"},
            "fingerprint": fp,
        }
    ]
    new = [{"prompt": "redacted text", "source_file": "f1.png"}]
    merged = merge_existing_fingerprints(new, old)
    assert (
        "fingerprint" not in merged[0]
    ), "changed prompt must not inherit stale fingerprint"
