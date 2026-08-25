"""Deterministic draw-time routing (FR-886).

Joins FR-890 corpus content fingerprints with FR-887 refusal evidence:
a model witnessed refusing a content tuple is excluded for prompts
carrying that tuple; everything else stays eligible (cold start =
today's blind pick). Pure functions — no LLM, no network. Routing
never writes to any ledger.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from tools.failures import prompt_sha

logger = logging.getLogger(__name__)

REPO_DIR = Path(__file__).parent.parent
TAXONOMY = REPO_DIR / "data" / "corpus_fingerprint_taxonomy.yaml"

AXES = ("sexual", "gore")
MAX_MATURE = ("mature", "mature")


class UnroutablePrompt(RuntimeError):
    """Every roster model has a witnessed refusal for this content tuple."""


class TaxonomyDrift(RuntimeError):
    """The taxonomy artifact no longer matches the router's contract."""


@dataclass
class EvidenceJoin:
    cells: dict[tuple[str, tuple[str, str]], int] = field(default_factory=dict)
    non_refusal: int = 0
    non_corpus: int = 0


def load_taxonomy(path: str | Path = TAXONOMY) -> dict[str, list[str]]:
    """Single source of truth (C-5); drift is rejected, never coerced."""
    data = yaml.safe_load(Path(path).read_text())
    content = data.get("content") or {}
    axes = {axis: spec.get("values") for axis, spec in content.items()}
    if set(axes) != set(AXES) or any(v != ["safe", "mature"] for v in axes.values()):
        raise TaxonomyDrift(f"taxonomy axes drifted from router contract: {axes}")
    return axes


def content_tuple(row: dict, axes: dict[str, list[str]]) -> tuple[str, str]:
    """Missing/partial/invalid fingerprints route as maximally mature."""
    content = row.get("content") or {}
    values = []
    for axis in AXES:
        value = content.get(axis)
        if value not in axes[axis]:
            logger.info(
                "route: invalid fingerprint axis=%s value=%r -> maximally mature",
                axis,
                value,
            )
            return MAX_MATURE
        values.append(value)
    return tuple(values)


def load_failure_rows(path: str | Path) -> list[dict]:
    """Absent ledger = empty evidence (R-4) — FR-887 creates it lazily."""
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def refusal_evidence(
    failure_rows: list[dict], corpus: list[dict], axes: dict[str, list[str]]
) -> EvidenceJoin:
    """Join refusal rows to corpus content tuples by prompt_sha (R-4)."""
    by_sha = {prompt_sha(row["prompt"]): row for row in corpus}
    join = EvidenceJoin()
    for row in failure_rows:
        if row.get("error_class") != "refusal":
            join.non_refusal += 1
            continue
        corpus_row = by_sha.get(row.get("prompt_sha"))
        if corpus_row is None:
            join.non_corpus += 1
            continue
        cell = (row["model"], content_tuple(corpus_row, axes))
        join.cells[cell] = join.cells.get(cell, 0) + 1
    return join


def eligible_models(
    fingerprint: tuple[str, str], evidence: EvidenceJoin, roster: dict
) -> list[str]:
    """Pure: one witnessed refusal for the exact tuple excludes (floor=1)."""
    return [m for m in sorted(roster) if not evidence.cells.get((m, fingerprint))]


def route(
    fingerprint: tuple[str, str],
    evidence: EvidenceJoin,
    roster: dict,
    rng: random.Random | None = None,
) -> str:
    """Same selection rule as choose_model over the eligible set (R-3)."""
    eligible = eligible_models(fingerprint, evidence, roster)
    if not eligible:
        raise UnroutablePrompt(
            f"no roster model tolerates content {fingerprint}; "
            f"refused by {sorted(m for m, fp in evidence.cells if fp == fingerprint)}"
        )
    return (rng or random).choice(eligible)
