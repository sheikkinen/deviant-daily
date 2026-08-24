"""Witness tests for training/score.py (FR-879 AC-02..AC-04, yamlgraph).

Uses a tiny injected model — no dependency on the real checkpoint.
"""

import pytest

torch = pytest.importorskip("torch")

# E402: importorskip must precede torch-dependent imports
from training.model import CharTokenizer, TinyGPT  # noqa: E402
from training.score import (  # noqa: E402
    band_for,
    nll_per_char,
    parse_val_docs,
    score_rows,
)

CAL = {
    "<tag>": {"p10": 1.0, "p90": 2.0},
    "<prose>": {"p10": 0.5, "p90": 1.5},
}


def _tiny():
    tok = CharTokenizer.fit(["<tag><prose>abcdefgh, _"])
    model = TinyGPT(tok.vocab_size, n_layer=1, n_head=2, n_embd=16, block_size=32)
    model.eval()
    return model, tok


def test_nll_deterministic():
    model, tok = _tiny()
    a, ta = nll_per_char(model, tok, "<prose>abc def gh")
    b, tb = nll_per_char(model, tok, "<prose>abc def gh")
    assert a == b and ta == tb is False


def test_truncation_flag():
    model, tok = _tiny()
    _, truncated = nll_per_char(model, tok, "<prose>" + "abcd " * 20)
    assert truncated is True


def test_parse_val_docs(tmp_path):
    f = tmp_path / "val.txt"
    f.write_text("<tag>a, b\n<|end|>\n<prose>hello there\n<|end|>\n")
    docs = parse_val_docs(f)
    assert docs == ["<tag>a, b", "<prose>hello there"]


def test_band_edges():
    assert band_for(0.4, "<prose>", CAL) == "too_likely"
    assert band_for(1.0, "<prose>", CAL) == "in_band"
    assert band_for(1.6, "<prose>", CAL) == "too_unlikely"
    assert band_for(1.6, "<tag>", CAL) == "in_band"


def test_score_rows_verdict_composition():
    model, tok = _tiny()
    corpus = ["a completely different training row about glass forests and moons"]
    # in-band + boundary pass -> pass; boundary reject wins otherwise
    ok = "abcd efgh " * 12  # >100 chars, vocab-safe
    rows = score_rows(
        model, tok, [ok], corpus, CAL, provenance={"ckpt_sha": "x", "corpus_sha": "y"}
    )
    row = rows[0]
    assert set(row) >= {
        "prompt_sha",
        "register",
        "nll_per_char",
        "truncated",
        "band",
        "boundary",
        "verdict",
        "ckpt_sha",
        "corpus_sha",
    }
    assert (
        row["verdict"] == "pass"
        if (row["band"] == "in_band" and row["boundary"] == "pass")
        else row["verdict"] != "pass"
    )


def test_score_rows_boundary_reject_never_pass():
    model, tok = _tiny()
    corpus = ["abcd efgh " * 12]
    rows = score_rows(
        model,
        tok,
        ["abcd efgh " * 12],
        corpus,
        CAL,
        provenance={"ckpt_sha": "x", "corpus_sha": "y"},
    )
    assert rows[0]["boundary"] != "pass"  # verbatim row -> novelty
    assert rows[0]["verdict"] != "pass"


def test_malformed_jsonl_rejected():
    from training.score import parse_prompt_lines

    with pytest.raises(ValueError):
        parse_prompt_lines(["not json at all"])
    with pytest.raises(ValueError):
        parse_prompt_lines(['{"no_prompt_key": 1}'])
