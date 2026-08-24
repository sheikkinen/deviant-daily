"""Sampling CLI (FR-876 AC-06). Every emitted sample passes the
generation boundary first (R-2); rejected raw text is never written."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import torch

from training.boundary import Boundary
from training.model import CharTokenizer, TinyGPT


def load_checkpoint(ckpt_dir: Path) -> tuple[TinyGPT, CharTokenizer]:
    ckpt = torch.load(ckpt_dir / "model.pt", map_location="cpu", weights_only=True)
    tokenizer = CharTokenizer(ckpt["chars"])
    cfg = ckpt["config"]
    model = TinyGPT(
        cfg["vocab_size"], cfg["layers"], cfg["heads"], cfg["embd"], cfg["block"]
    )
    model.load_state_dict(ckpt["model"])
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    return model.to(device), tokenizer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, default=Path("training/ckpt"))
    ap.add_argument("--corpus", type=Path, default=Path("prompts/corpus.jsonl"))
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--top-k", type=int, default=40)
    ap.add_argument("--cond", choices=["tag", "prose"], default="prose")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=None, help="markdown sample sheet")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    model, tokenizer = load_checkpoint(args.ckpt)
    corpus_prompts = [
        json.loads(line)["prompt"]
        for line in args.corpus.read_text().splitlines()
        if line.strip()
    ]
    boundary = Boundary(corpus_prompts)

    passed: list[str] = []
    verdicts: Counter[str] = Counter()
    attempts = 0
    while len(passed) < args.n and attempts < args.n * 10:
        attempts += 1
        text, ended = model.sample(
            tokenizer, f"<{args.cond}>", temperature=args.temp, top_k=args.top_k
        )
        res = boundary.check(text, ended=ended)
        verdicts[res.verdict] += 1
        if res.verdict == "pass":
            passed.append(res.text)
            print(f"--- [{len(passed)}] ---\n{res.text}\n")
        else:
            print(f"[rejected: {res.verdict}:{res.reason}]")

    summary = dict(verdicts)
    print(json.dumps({"attempts": attempts, "verdicts": summary}))
    if args.out:
        lines = [
            f"# Sample sheet — temp={args.temp} cond=<{args.cond}> seed={args.seed}",
            "",
            f"Verdicts over {attempts} attempts: `{summary}`",
            "(boundary-passing samples only — judgement R-2)",
            "",
        ]
        for i, text in enumerate(passed, 1):
            lines.append(f"## Sample {i}\n\n{text}\n")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
