"""Rejection-statistics evaluation (FR-876 AC-10).

The table IS the demonstration: what training buys is visible in the
pass/redaction/novelty/shape distribution per rung and temperature.
Only counts are persisted — never rejected raw text (R-2). Coherence
is deliberately NOT measured here (judgement R-5); human sample-read
notes are non-gating and live in the enforcement record.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

VERDICTS = ["pass", "redaction", "novelty", "shape"]


def render_table(stats: dict[tuple[str, float], dict], n_samples: int) -> str:
    lines = [
        f"# Rejection statistics ({n_samples} samples per cell)",
        "",
        "| rung | temp | pass | redaction | novelty | shape |",
        "|------|------|------|-----------|---------|-------|",
    ]
    for (rung, temp), counts in sorted(stats.items()):
        cells = " | ".join(str(counts.get(v, 0)) for v in VERDICTS)
        lines.append(f"| {rung} | {temp} | {cells} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    from training.boundary import Boundary
    from training.generate import load_checkpoint
    from training.markov import MarkovModel

    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, default=Path("training/ckpt"))
    ap.add_argument("--corpus", type=Path, default=Path("prompts/corpus.jsonl"))
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--temps", type=float, nargs="+", default=[0.5, 0.8, 1.2])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("training/rejection-stats.md"))
    args = ap.parse_args()

    corpus_prompts = [
        json.loads(line)["prompt"]
        for line in args.corpus.read_text().splitlines()
        if line.strip()
    ]
    boundary = Boundary(corpus_prompts)
    stats: dict[tuple[str, float], dict] = {}

    rng = random.Random(args.seed)
    markov = MarkovModel.fit(corpus_prompts)
    counts: Counter[str] = Counter()
    for _ in range(args.n):
        counts[boundary.check(markov.generate(rng)).verdict] += 1
    # Markov has no temperature; record once under 0.0
    stats[("markov", 0.0)] = dict(counts)
    print(json.dumps({"markov": dict(counts)}), flush=True)

    import torch

    model, tokenizer = load_checkpoint(args.ckpt)
    for temp in args.temps:
        torch.manual_seed(args.seed)
        counts = Counter()
        for i in range(args.n):
            cond = "tag" if i % 2 else "prose"
            text, ended = model.sample(tokenizer, f"<{cond}>", temperature=temp)
            counts[boundary.check(text, ended=ended).verdict] += 1
        stats[("transformer", temp)] = dict(counts)
        print(json.dumps({"transformer": {"temp": temp, **counts}}), flush=True)

    table = render_table(stats, args.n)
    args.out.write_text(table)
    print(table)


if __name__ == "__main__":
    main()
