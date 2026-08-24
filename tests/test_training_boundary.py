"""Witness tests for training/boundary.py (FR-876 AC-07..AC-09, yamlgraph).

One rejection witness per category; rejected raw text must never
appear in rendered artifacts (judgement R-2 / AC-08).
"""

from training.boundary import BoundaryResult, check_sample

CORPUS = [
    "a dark forest of glass trees under a violet sky where shadows sing softly",
    "neon city streets with rain slick chrome reflections in every window pane",
]

PAD = " atmospheric painterly detailed lighting " * 3


def _ok_sample() -> str:
    return ("luminous koi drifting through a paper lantern sky," + PAD).strip()


def test_pass():
    res = check_sample(_ok_sample(), CORPUS)
    assert res.verdict == "pass"


def test_name_blocklist_rejects():
    res = check_sample("a portrait of katja in moonlight" + PAD, CORPUS)
    assert res.verdict == "redaction"


def test_term_blocklist_rejects():
    res = check_sample("a scene depicting rape in oil paint" + PAD, CORPUS)
    assert res.verdict == "redaction"


def test_scan_pattern_rejects():
    res = check_sample("saved to /Users/someone/art dark scene" + PAD, CORPUS)
    assert res.verdict == "redaction"


def test_verbatim_row_rejects():
    res = check_sample(CORPUS[0], CORPUS)
    assert res.verdict == "novelty"


def test_shared_8gram_rejects():
    sample = (
        "brand new opening but a dark forest of glass trees under a violet sky ends it"
        + PAD
    )
    res = check_sample(sample, CORPUS)
    assert res.verdict == "novelty"


def test_seven_gram_overlap_passes_novelty():
    sample = "forest of glass trees under a violet moon," + PAD
    res = check_sample(sample, CORPUS)
    assert res.verdict != "novelty"


def test_empty_rejects():
    assert check_sample("", CORPUS).verdict == "shape"


def test_too_short_rejects():
    assert check_sample("tiny prompt", CORPUS).verdict == "shape"


def test_too_long_rejects():
    assert check_sample("word " * 300, CORPUS).verdict == "shape"


def test_midword_truncation_rejects():
    sample = (_ok_sample()[:-40] + " truncated midwor").strip()
    res = check_sample(sample, CORPUS)
    assert res.verdict == "shape"


def test_rejected_text_not_in_result_repr():
    """R-2: the result object never carries rejected raw text."""
    bad = "a portrait of katja in moonlight" + PAD
    res = check_sample(bad, CORPUS)
    assert res.verdict != "pass"
    assert "katja" not in repr(res)
    assert res.text is None


def test_passing_text_is_carried():
    res = check_sample(_ok_sample(), CORPUS)
    assert isinstance(res, BoundaryResult)
    assert res.text == _ok_sample()


def test_regexes_imported_not_duplicated():
    """AC-07: boundary reuses extract_corpus.py patterns."""
    import training.boundary as tb

    import scripts.extract_corpus as ec

    assert tb.NAME_RE.pattern == ec.name_blocklist_re(ec.NAME_BLOCKLIST).pattern
    assert tb.SCAN_PATTERNS is ec.SCAN_PATTERNS
