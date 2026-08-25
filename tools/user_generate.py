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
from tools.fanout import generate_all
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
    models = parser.add_mutually_exclusive_group()
    models.add_argument(
        "--model", default="", help="roster model name (default: random)"
    )
    models.add_argument(
        "--models", help="comma-separated roster subset (FR-888 fan-out)"
    )
    models.add_argument(
        "--all-models", action="store_true", help="fan out over every active model"
    )
    parser.add_argument("--date", default="", help="YYYY-MM-DD (default: today)")
    parser.add_argument("--out-dir", default="outputs", help="output directory")
    return parser.parse_args(argv)


def read_prompt(args: argparse.Namespace) -> str:
    """Verbatim: strict UTF-8 decode fails before any side effect."""
    if args.prompt is not None:
        return args.prompt
    return Path(args.prompt_file).read_bytes().decode("utf-8")


def main(argv=None, runner=subprocess.run):
    args = parse_args(argv)
    prompt = read_prompt(args)
    date = parse_date(args.date)
    if args.all_models or args.models:
        # FR-888 composition: delegation only — the primitive owns
        # preflight, ordering, output identity, and failure semantics.
        selection = None if args.all_models else args.models.split(",")
        outcomes = generate_all(prompt, date, selection, args.out_dir, runner=runner)
        for outcome in outcomes:
            print(f"{outcome.model}: {outcome.status} {outcome.path or ''}")
        return outcomes
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
