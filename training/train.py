"""Training loop (FR-876 AC-05; judgement R-4 reproducible witness).

Logs seed, device, params, hyperparameters, split counts, initial/final
loss, wall clock, and git SHA. Periodic samples pass the generation
boundary before printing (R-2) — rejected raw text is never persisted.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import torch

from training.boundary import Boundary
from training.model import CharTokenizer, TinyGPT


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def _load_split(data_dir: Path, tokenizer: CharTokenizer, name: str) -> torch.Tensor:
    text = (data_dir / f"{name}.txt").read_text()
    return torch.tensor(tokenizer.encode(text), dtype=torch.long)


def _batch(
    data: torch.Tensor, block: int, batch: int, device: str, g: torch.Generator
) -> tuple[torch.Tensor, torch.Tensor]:
    ix = torch.randint(0, len(data) - block - 1, (batch,), generator=g)
    x = torch.stack([data[i : i + block] for i in ix])
    y = torch.stack([data[i + 1 : i + block + 1] for i in ix])
    return x.to(device), y.to(device)


@torch.no_grad()
def _eval_loss(model, data, block, batch, device, g, iters: int = 20) -> float:
    model.eval()
    losses = []
    for _ in range(iters):
        x, y = _batch(data, block, batch, device, g)
        _, loss = model(x, y)
        losses.append(loss.item())
    model.train()
    return sum(losses) / len(losses)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("training/data"))
    ap.add_argument("--out", type=Path, default=Path("training/ckpt"))
    ap.add_argument("--corpus", type=Path, default=Path("prompts/corpus.jsonl"))
    ap.add_argument("--steps", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--block", type=int, default=256)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--embd", type=int, default=256)
    ap.add_argument("--eval-interval", type=int, default=250)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    g = torch.Generator().manual_seed(args.seed)

    train_text = (args.data / "train.txt").read_text()
    val_text = (args.data / "val.txt").read_text()
    tokenizer = CharTokenizer.fit([train_text, val_text])
    train_data = _load_split(args.data, tokenizer, "train")
    val_data = _load_split(args.data, tokenizer, "val")

    corpus_prompts = [
        json.loads(line)["prompt"]
        for line in args.corpus.read_text().splitlines()
        if line.strip()
    ]
    boundary = Boundary(corpus_prompts)

    model = TinyGPT(
        tokenizer.vocab_size, args.layers, args.heads, args.embd, args.block
    ).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)

    header = {
        "git_sha": _git_sha(),
        "seed": args.seed,
        "device": device,
        "n_params": n_params,
        "vocab_size": tokenizer.vocab_size,
        "block": args.block,
        "batch": args.batch,
        "steps": args.steps,
        "lr": args.lr,
        "layers": args.layers,
        "heads": args.heads,
        "embd": args.embd,
        "train_chars": len(train_text),
        "val_chars": len(val_text),
    }
    print(json.dumps({"config": header}))

    t0 = time.time()
    initial_val = _eval_loss(model, val_data, args.block, args.batch, device, g)
    print(json.dumps({"step": 0, "val_loss": round(initial_val, 4)}))

    for step in range(1, args.steps + 1):
        x, y = _batch(train_data, args.block, args.batch, device, g)
        _, loss = model(x, y)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % args.eval_interval == 0 or step == args.steps:
            val_loss = _eval_loss(model, val_data, args.block, args.batch, device, g)
            print(
                json.dumps(
                    {
                        "step": step,
                        "train_loss": round(loss.item(), 4),
                        "val_loss": round(val_loss, 4),
                        "elapsed_s": round(time.time() - t0, 1),
                    }
                ),
                flush=True,
            )
            text, ended = model.sample(tokenizer, "<prose>", temperature=0.8)
            res = boundary.check(text, ended=ended)
            if res.verdict == "pass":
                print(json.dumps({"sample": res.text}), flush=True)
            else:
                print(
                    json.dumps({"sample_rejected": f"{res.verdict}:{res.reason}"}),
                    flush=True,
                )

    final_val = _eval_loss(model, val_data, args.block, args.batch, device, g)
    wall = time.time() - t0
    args.out.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"model": model.state_dict(), "chars": tokenizer.chars, "config": header},
        args.out / "model.pt",
    )
    print(
        json.dumps(
            {
                "final": {
                    "initial_val_loss": round(initial_val, 4),
                    "final_val_loss": round(final_val, 4),
                    "wall_clock_s": round(wall, 1),
                    "ckpt": str(args.out / "model.pt"),
                }
            }
        )
    )


if __name__ == "__main__":
    main()
