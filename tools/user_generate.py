"""Generation-only user-prompt CLI (FR-889).

The operator is the authority: the prompt passes VERBATIM to the
generation boundary — no rewriting, filtering, or augmentation. The
provider's own response is the only gate; a refusal becomes an FR-887
row (run_source="user"). This path never enters the publish graph:
no draw, no slot, no state/published.jsonl, no DeviantArt API.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from tools import steps
from tools.inputs import parse_date, parse_model
from tools.roster import choose_model


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="generate",
        description="Generate one image from an operator-supplied prompt "
        "(generation only — never publishes).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", help="prompt text, passed verbatim")
    group.add_argument("--prompt-file", help="UTF-8 file whose contents pass verbatim")
    parser.add_argument(
        "--model", default="", help="roster model name (default: random)"
    )
    parser.add_argument("--date", default="", help="YYYY-MM-DD (default: today)")
    parser.add_argument("--out-dir", default="outputs", help="output directory")
    return parser.parse_args(argv)


def read_prompt(args: argparse.Namespace) -> str:
    """Verbatim: strict UTF-8 decode fails before any side effect."""
    if args.prompt is not None:
        return args.prompt
    return Path(args.prompt_file).read_bytes().decode("utf-8")


def main(argv=None, runner=subprocess.run) -> str:
    args = parse_args(argv)
    prompt = read_prompt(args)
    date = parse_date(args.date)
    # Resolve the model up front so the output path names it (R-2).
    model_name, _ = choose_model(name=parse_model(args.model))
    out_path = Path(args.out_dir) / f"{date}-user-{model_name}.png"
    result = steps.generate_step(
        prompt,
        date,
        model=model_name,
        run_source="user",
        runner=runner,
        out_path=str(out_path),
    )
    print(result["image_path"])
    return result["image_path"]
