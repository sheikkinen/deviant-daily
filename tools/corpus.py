"""Corpus draw (FR-826 pipeline step 1, AC-12 no-repeat).

Random prompt from prompts/corpus.jsonl never drawn before (ledger
source_file ids, global across dates AND slots). Resume contract: an
existing record for the selected (date, slot) is returned as-is — a
rerun never draws a new prompt for a run already in flight.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from tools.ledger import entry_for_slot, used_source_ids

# 1937 of 5893 corpus rows carry source_file "unknown" (extraction could
# not recover a generation id). Left as-is they share one dedup key, so
# publishing any one of them would exclude all the others forever.
UNKNOWN = "unknown"


def row_id(row: dict) -> str:
    """Stable per-row dedup key; content hash when the id is missing."""
    source = row.get("source_file") or UNKNOWN
    if source != UNKNOWN:
        return source
    digest = hashlib.sha1(row["prompt"].encode("utf-8")).hexdigest()[:12]
    return f"{UNKNOWN}-{digest}"


class CorpusExhausted(RuntimeError):
    pass


def load_corpus(path: str | Path) -> list[dict]:
    rows = [
        json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()
    ]
    if not rows:
        raise CorpusExhausted("corpus is empty")
    return rows


def draw_prompt(
    corpus_path: str | Path,
    ledger_entries: list[dict],
    date: str,
    slot: int = 0,
    rng: random.Random | None = None,
) -> dict:
    """Return {prompt, source_file, resumed, status} for the (date, slot) run."""
    existing = entry_for_slot(ledger_entries, date, slot)
    if existing:
        return {
            "prompt": existing.get("prompt", ""),
            "source_file": existing.get("source_file", ""),
            "resumed": True,
            "status": existing["status"],
        }
    used = used_source_ids(ledger_entries)
    candidates = [r for r in load_corpus(corpus_path) if row_id(r) not in used]
    if not candidates:
        raise CorpusExhausted("all corpus prompts have been published")
    row = (rng or random).choice(candidates)
    return {**row, "source_file": row_id(row), "resumed": False, "status": None}
