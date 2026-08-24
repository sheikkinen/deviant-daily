"""Witness tests for training/prepare.py and training/model.py
(FR-876 AC-03, AC-04, yamlgraph)."""

import json

import pytest

torch = pytest.importorskip("torch")

# E402: importorskip must precede torch-dependent imports
from training.model import CharTokenizer, TinyGPT  # noqa: E402
from training.prepare import END_TOKEN, classify_register, prepare  # noqa: E402

ROWS = [
    {"prompt": "a dark forest of glass trees under a violet sky, haunting"},
    {"prompt": "t1_a, t2_b, t3_c, t4_d, t5_e, t6_f, t7_g, t8_h, t9_i"},
    {"prompt": "neon city streets, rain slick, chrome reflections"},
    {"prompt": "misty harbor at dawn with copper bells ringing"},
] * 10


def test_classify_register():
    assert classify_register("t1_a, b, c, d, e, f, g, h, i_j") == "<tag>"
    assert classify_register("a long prose description, quite nice") == "<prose>"


def test_split_deterministic(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("\n".join(json.dumps(r) for r in ROWS))
    out1 = prepare(corpus, tmp_path / "d1", seed=7)
    out2 = prepare(corpus, tmp_path / "d2", seed=7)
    assert (tmp_path / "d1" / "train.txt").read_text() == (
        tmp_path / "d2" / "train.txt"
    ).read_text()
    assert out1["val_docs"] == out2["val_docs"] > 0


def test_separator_and_prefix(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("\n".join(json.dumps(r) for r in ROWS))
    prepare(corpus, tmp_path / "d", seed=7)
    text = (tmp_path / "d" / "train.txt").read_text()
    docs = [d for d in text.split(END_TOKEN) if d.strip()]
    assert all(
        d.strip().startswith(("<tag>", "<prose>")) for d in docs
    ), "every doc carries a register prefix"


def test_tokenizer_roundtrip():
    tok = CharTokenizer.fit(["abc def", "ghi"])
    s = "abc ghi"
    assert tok.decode(tok.encode(s)) == s


def test_model_forward_shape():
    tok = CharTokenizer.fit(["abcdefgh"])
    model = TinyGPT(
        vocab_size=tok.vocab_size, n_layer=1, n_head=2, n_embd=32, block_size=16
    )
    x = torch.randint(0, tok.vocab_size, (2, 16))
    logits, loss = model(x, x)
    assert logits.shape == (2, 16, tok.vocab_size)
    assert loss.item() > 0


def test_tiny_overfit_smoke():
    """One tiny CPU overfit run: loss must drop measurably."""
    text = "the quick brown fox jumps over the lazy dog. " * 8
    tok = CharTokenizer.fit([text])
    model = TinyGPT(
        vocab_size=tok.vocab_size, n_layer=1, n_head=2, n_embd=32, block_size=32
    )
    data = torch.tensor(tok.encode(text), dtype=torch.long)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    torch.manual_seed(0)

    def batch():
        ix = torch.randint(0, len(data) - 33, (8,))
        x = torch.stack([data[i : i + 32] for i in ix])
        y = torch.stack([data[i + 1 : i + 33] for i in ix])
        return x, y

    x, y = batch()
    _, first = model(x, y)
    for _ in range(60):
        x, y = batch()
        _, loss = model(x, y)
        opt.zero_grad()
        loss.backward()
        opt.step()
    assert loss.item() < first.item() * 0.6
