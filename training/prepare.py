"""Dataset preparation (FR-876 AC-03).

corpus.jsonl -> train.txt / val.txt: one prompt per document, register
prefix (<tag>/<prose>), <|end|> separators, seeded deterministic 95/5
split. Trains ONLY on the redacted committed corpus.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

END_TOKEN = "\n<|end|>\n"
VAL_FRACTION = 0.05


def classify_register(prompt: str) -> str:
    """Mechanical register classifier (FR-876: >=8 commas AND '_')."""
    return "<tag>" if prompt.count(",") >= 8 and "_" in prompt else "<prose>"


def prepare(corpus_path: Path, out_dir: Path, seed: int = 7) -> dict:
    rows = [
        json.loads(line)
        for line in Path(corpus_path).read_text().splitlines()
        if line.strip()
    ]
    docs = [f"{classify_register(r['prompt'])}{r['prompt']}" for r in rows]
    rng = random.Random(seed)
    rng.shuffle(docs)
    n_val = max(1, int(len(docs) * VAL_FRACTION))
    val, train = docs[:n_val], docs[n_val:]

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "train.txt").write_text(END_TOKEN.join(train) + END_TOKEN)
    (out_dir / "val.txt").write_text(END_TOKEN.join(val) + END_TOKEN)
    stats = {"seed": seed, "train_docs": len(train), "val_docs": len(val)}
    (out_dir / "meta.json").write_text(json.dumps(stats, indent=2))
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    print(json.dumps(prepare(args.corpus, args.out_dir, args.seed)))


if __name__ == "__main__":
    main()
