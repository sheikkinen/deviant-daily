"""Critic scorer CLI (FR-879 D-2, yamlgraph): per-char NLL + per-register
band + boundary verdict per prompt.

Band semantics are STYLE ONLY (FR-879 R-1 obs 1): a verbatim corpus row
scores in_band at this model size, so `too_likely` is advisory and the
8-gram Boundary remains the sole novelty defense.

Contract: prompt JSONL ({"prompt": ...} per line) on stdin -> one JSON
object per prompt on stdout with provenance stamps. Calibration mode
(--calibrate) parses training/data/val.txt (a <|end|>-separated stream,
NOT JSONL) and persists per-register p10/p90 with full provenance.
Run from the repo root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

from training.boundary import Boundary
from training.generate import load_checkpoint
from training.model import CharTokenizer, TinyGPT
from training.prepare import END_TOKEN, classify_register

CKPT_DIR = Path("training/ckpt")
CALIBRATION_PATH = CKPT_DIR / "calibration.json"
REGISTERS = ("<tag>", "<prose>")


def nll_per_char(model: TinyGPT, tok: CharTokenizer, text: str) -> tuple[float, bool]:
    """Per-char NLL of text (register prefix included), truncated to block."""
    ids = [tok.stoi[c] for c in text if c in tok.stoi]
    truncated = len(ids) > model.block_size
    ids = ids[: model.block_size]
    x = torch.tensor([ids[:-1]])
    y = torch.tensor([ids[1:]])
    with torch.no_grad():
        logits, _ = model(x)
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
    return loss.item(), truncated


def parse_val_docs(val_path: Path) -> list[str]:
    return [d.strip() for d in val_path.read_text().split(END_TOKEN) if d.strip()]


def band_for(nll: float, register: str, calibration: dict) -> str:
    ref = calibration[register]
    if nll < ref["p10"]:
        return "too_likely"
    if nll > ref["p90"]:
        return "too_unlikely"
    return "in_band"


def parse_prompt_lines(lines: list[str]) -> list[str]:
    prompts = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"line {i + 1}: not JSON: {e}") from e
        if "prompt" not in row or not isinstance(row["prompt"], str):
            raise ValueError(f"line {i + 1}: missing string 'prompt' key")
        prompts.append(row["prompt"])
    return prompts


def score_rows(
    model: TinyGPT,
    tok: CharTokenizer,
    prompts: list[str],
    corpus_prompts: list[str],
    calibration: dict,
    provenance: dict,
) -> list[dict]:
    boundary = Boundary(corpus_prompts)
    rows = []
    for prompt in prompts:
        register = classify_register(prompt)
        nll, truncated = nll_per_char(model, tok, f"{register}{prompt}")
        band = band_for(nll, register, calibration)
        bres = boundary.check(prompt, ended=True)
        verdict = (
            "pass"
            if (band == "in_band" and bres.verdict == "pass")
            else (bres.verdict if bres.verdict != "pass" else f"band:{band}")
        )
        rows.append(
            {
                "prompt_sha": hashlib.sha1(prompt.encode()).hexdigest()[:12],
                "register": register,
                "nll_per_char": round(nll, 4),
                "truncated": truncated,
                "band": band,
                "boundary": bres.verdict if bres.verdict != "pass" else "pass",
                "boundary_reason": bres.reason,
                "verdict": verdict,
                **provenance,
            }
        )
    return rows


def _provenance() -> dict:
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    return {
        "ckpt_sha": hashlib.sha256((CKPT_DIR / "model.pt").read_bytes()).hexdigest()[
            :12
        ],
        "corpus_sha": hashlib.sha256(
            Path("prompts/corpus.jsonl").read_bytes()
        ).hexdigest()[:12],
        "git_sha": git_sha,
    }


def calibrate(model: TinyGPT, tok: CharTokenizer, val_path: Path) -> dict:
    docs = parse_val_docs(val_path)
    by_register: dict[str, list[float]] = {r: [] for r in REGISTERS}
    for doc in docs:
        register = next((r for r in REGISTERS if doc.startswith(r)), None)
        if register is None:
            raise ValueError(f"val doc lacks register prefix: {doc[:40]!r}")
        nll, _ = nll_per_char(model, tok, doc)
        by_register[register].append(nll)
    calibration: dict = {}
    for register, scores in by_register.items():
        if not scores:
            raise ValueError(f"no val docs for register {register}")
        s = sorted(scores)
        calibration[register] = {
            "p10": round(s[int(0.1 * len(s))], 4),
            "p90": round(s[int(0.9 * len(s))], 4),
            "n_docs": len(s),
        }
    calibration["provenance"] = {
        **_provenance(),
        "val_path": str(val_path),
        "block_size": model.block_size,
        "command": " ".join(sys.argv),
    }
    return calibration


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, default=CKPT_DIR)
    ap.add_argument("--corpus", type=Path, default=Path("prompts/corpus.jsonl"))
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--val", type=Path, default=Path("training/data/val.txt"))
    args = ap.parse_args()

    model, tok = load_checkpoint(args.ckpt)
    model = model.to("cpu")

    if args.calibrate:
        calibration = calibrate(model, tok, args.val)
        CALIBRATION_PATH.write_text(json.dumps(calibration, indent=2))
        print(json.dumps(calibration))
        return

    if not CALIBRATION_PATH.exists():
        raise SystemExit(
            "calibration.json missing — run: python -m training.score --calibrate"
        )
    calibration = json.loads(CALIBRATION_PATH.read_text())
    prompts = parse_prompt_lines(sys.stdin.readlines())
    corpus_prompts = [
        json.loads(line)["prompt"]
        for line in args.corpus.read_text().splitlines()
        if line.strip()
    ]
    provenance = {
        k: v for k, v in calibration["provenance"].items() if k.endswith("_sha")
    }
    for row in score_rows(model, tok, prompts, corpus_prompts, calibration, provenance):
        print(json.dumps(row))


if __name__ == "__main__":
    main()
