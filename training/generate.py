"""Sampling CLI (FR-876 AC-06; --json contract yamlgraph FR-881 R-3).

Every emitted sample passes the generation boundary first (R-2);
rejected raw text is never written to any stream or artifact. In
--json mode stdout carries ONLY JSON lines: one candidate record per
accepted prompt in generation order plus one final summary record,
stamped with checkpoint/corpus/git provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from collections.abc import Callable
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


def run_generation(
    sample_fn: Callable[[], tuple[str, bool]],
    boundary: Boundary,
    n: int,
    max_attempts_factor: int = 10,
) -> tuple[list[dict], dict]:
    """Boundary-gated accept loop; rejected raw text is dropped here."""
    candidates: list[dict] = []
    total: Counter[str] = Counter()
    window: Counter[str] = Counter()
    window_attempts = 0
    attempts = 0
    while len(candidates) < n and attempts < n * max_attempts_factor:
        attempts += 1
        window_attempts += 1
        text, ended = sample_fn()
        res = boundary.check(text, ended=ended)
        total[res.verdict] += 1
        window[res.verdict] += 1
        if res.verdict == "pass":
            candidates.append(
                {
                    "ordinal": len(candidates) + 1,
                    "prompt": res.text,
                    "attempts_for_candidate": window_attempts,
                    "verdict_counts": dict(window),
                }
            )
            window = Counter()
            window_attempts = 0
    return candidates, {"attempts": attempts, "verdict_counts": dict(total)}


def provenance(repo_root: Path) -> dict:
    def file_sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]

    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        cwd=repo_root,
    ).stdout.strip()
    return {
        "ckpt_sha": file_sha(repo_root / "training" / "ckpt" / "model.pt"),
        "corpus_sha": file_sha(repo_root / "prompts" / "corpus.jsonl"),
        "git_sha": git_sha,
    }


def format_jsonl(candidates: list[dict], summary: dict, meta: dict, prov: dict) -> str:
    lines = [
        json.dumps({"record": "candidate", **c, **meta, **prov}, ensure_ascii=False)
        for c in candidates
    ]
    lines.append(json.dumps({"record": "summary", **summary, **meta, **prov}))
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, default=Path("training/ckpt"))
    ap.add_argument("--corpus", type=Path, default=Path("prompts/corpus.jsonl"))
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--top-k", type=int, default=40)
    ap.add_argument("--cond", choices=["tag", "prose"], default="prose")
    ap.add_argument("--start", default="", help="seed text the model continues from")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=None, help="markdown sample sheet")
    ap.add_argument(
        "--json", action="store_true", help="JSONL on stdout (FR-881 contract)"
    )
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    model, tokenizer = load_checkpoint(args.ckpt)
    corpus_prompts = [
        json.loads(line)["prompt"]
        for line in args.corpus.read_text().splitlines()
        if line.strip()
    ]
    boundary = Boundary(corpus_prompts)

    unknown = sorted(set(args.start) - set(tokenizer.chars))
    if unknown:
        raise SystemExit(f"--start contains chars outside model vocab: {unknown}")
    prefix = f"<{args.cond}>{args.start}"

    def sample_fn() -> tuple[str, bool]:
        text, ended = model.sample(
            tokenizer, prefix, temperature=args.temp, top_k=args.top_k
        )
        return (f"{args.start}{text}" if args.start else text), ended

    candidates, summary = run_generation(sample_fn, boundary, args.n)

    if args.json:
        meta = {
            "seed": args.seed,
            "temp": args.temp,
            "top_k": args.top_k,
            "cond": args.cond,
            "start": args.start,
        }
        print(format_jsonl(candidates, summary, meta, provenance(Path.cwd())), end="")
    else:
        for c in candidates:
            print(f"--- [{c['ordinal']}] ---\n{c['prompt']}\n")
        print(
            json.dumps(
                {"attempts": summary["attempts"], "verdicts": summary["verdict_counts"]}
            )
        )
    if args.out:
        lines = [
            f"# Sample sheet — temp={args.temp} cond=<{args.cond}> seed={args.seed}",
            "",
            f"Verdicts over {summary['attempts']} attempts: `{summary['verdict_counts']}`",
            "(boundary-passing samples only — judgement R-2)",
            "",
        ]
        for c in candidates:
            lines.append(f"## Sample {c['ordinal']}\n\n{c['prompt']}\n")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
