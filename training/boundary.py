"""Generation boundary (FR-876 AC-07..AC-09; judgement R-2, C-4).

Model output is a CLAIM, not a prompt. Every sample destined for
stdout, logs, or committed artifacts passes here first. Rejected raw
text is never carried on the result object, so it cannot leak into
persisted artifacts.

Redaction patterns are imported from scripts/extract_corpus.py — one
source of truth, no copies (AC-07). Run from the repo root.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from scripts.extract_corpus import (
    NAME_BLOCKLIST,
    SCAN_PATTERNS,
    TERM_BLOCKLIST,
    name_blocklist_re,
    term_blocklist_re,
)

NAME_RE = name_blocklist_re(NAME_BLOCKLIST)
TERM_RE = term_blocklist_re(TERM_BLOCKLIST)

MIN_CHARS = 100
MAX_CHARS = 800
NGRAM_N = 8

_WORD_EDGE = re.compile(r"^\W+|\W+$")


def _norm_words(text: str) -> list[str]:
    words = (_WORD_EDGE.sub("", w).lower() for w in text.split())
    return [w for w in words if w]


def _ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


@dataclass(frozen=True)
class BoundaryResult:
    """`text` is None unless verdict == 'pass' (R-2: no raw leak)."""

    verdict: str  # pass | redaction | novelty | shape
    reason: str
    text: str | None = field(default=None, repr=False)


class Boundary:
    """Precomputes corpus n-grams once; reuse across many samples."""

    def __init__(self, corpus_prompts: list[str]):
        self._rows = {" ".join(_norm_words(p)) for p in corpus_prompts}
        self._ngrams: set[tuple[str, ...]] = set()
        for p in corpus_prompts:
            self._ngrams |= _ngrams(_norm_words(p), NGRAM_N)

    def check(self, text: str, ended: bool = True) -> BoundaryResult:
        if NAME_RE.search(text):
            return BoundaryResult("redaction", "name_blocklist")
        if TERM_RE.search(text):
            return BoundaryResult("redaction", "term_blocklist")
        for name, pattern in SCAN_PATTERNS.items():
            if pattern.search(text):
                return BoundaryResult("redaction", f"scan:{name}")
        words = _norm_words(text)
        if " ".join(words) in self._rows:
            return BoundaryResult("novelty", "verbatim_row")
        if self._ngrams & _ngrams(words, NGRAM_N):
            return BoundaryResult("novelty", f"shared_{NGRAM_N}gram")
        if not text.strip():
            return BoundaryResult("shape", "empty")
        if len(text) < MIN_CHARS:
            return BoundaryResult("shape", "too_short")
        if len(text) > MAX_CHARS:
            return BoundaryResult("shape", "too_long")
        if not ended:
            return BoundaryResult("shape", "truncated_mid_word")
        return BoundaryResult("pass", "ok", text=text)


def check_sample(
    text: str, corpus_prompts: list[str], ended: bool = True
) -> BoundaryResult:
    """One-shot convenience; use Boundary directly for bulk checks."""
    return Boundary(corpus_prompts).check(text, ended=ended)
