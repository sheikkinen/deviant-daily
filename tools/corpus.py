"""Corpus draw (FR-826 pipeline step 1, AC-12 no-repeat).

Random prompt from prompts/corpus.jsonl never drawn before (ledger
source_file ids). Resume contract: an existing same-day record is
returned as-is — a rerun never draws a new prompt for the same date.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from tools.ledger import entry_for_date, used_source_ids


class CorpusExhausted(RuntimeError):
    pass


def load_corpus(path: str | Path) -> list[dict]:
    rows = [
        json.loads(line)
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]
    if not rows:
        raise CorpusExhausted("corpus is empty")
    return rows


def draw_prompt(
    corpus_path: str | Path,
    ledger_entries: list[dict],
    date: str,
    rng: random.Random | None = None,
) -> dict:
    """Return {prompt, source_file, resumed, status} for the date."""
    existing = entry_for_date(ledger_entries, date)
    if existing:
        return {
            "prompt": existing.get("prompt", ""),
            "source_file": existing.get("source_file", ""),
            "resumed": True,
            "status": existing["status"],
        }
    used = used_source_ids(ledger_entries)
    candidates = [r for r in load_corpus(corpus_path) if r["source_file"] not in used]
    if not candidates:
        raise CorpusExhausted("all corpus prompts have been published")
    row = (rng or random).choice(candidates)
    return {**row, "resumed": False, "status": None}
