"""Graph node step functions (FR-826 R-1: yamlgraph orchestrates, these
are the side-effect tools it calls).

If the pipeline runs, it publishes. There is no dry-run and no force:
running it IS the intent. The one diversion is an in-flight slot, which
is resumed rather than duplicated — its committed row may already guard
a DA call in flight.

Ordering contracts enforced here:
- dispatch inputs normalized at entry
- ledger transition committed BEFORE the next side effect (R-3)
- rotated refresh token persisted BEFORE any DA submit/publish (AC-08)
- post-publish commit failure -> RecoveryRequired, visibly red (R-3)
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from tools import da_api
from tools.corpus import draw_prompt
from tools.gate import PostDescription, evaluate_gate
from tools.generate import generate_image
from tools.inputs import parse_date, parse_model, parse_slot
from tools.ledger import (
    TERMINAL,
    LedgerCommitError,
    RecoveryRequired,
    entry_for_slot,
    latest_slot,
    read_ledger,
    record_transition,
)
from tools.post import post_path, render_artist_comments, render_post_md
from tools.roster import choose_model, validate_roster
from tools.vision import describe_image

logger = logging.getLogger(__name__)

REPO_DIR = Path(__file__).parent.parent
LEDGER = REPO_DIR / "state" / "published.jsonl"
CORPUS = REPO_DIR / "prompts" / "corpus.jsonl"
DA_REPO = "sheikkinen/deviant-daily"


def _resumed(existing: dict, date: str, slot: int) -> dict:
    return {
        "prompt": existing.get("prompt", ""),
        "source_file": existing.get("source_file", ""),
        "resumed": True,
        "status": existing["status"],
        "date": date,
        "slot": slot,
        "done": False,
    }


def draw_step(date: str = "", runner=subprocess.run) -> dict:
    """Roster check first (R-4: fail before any draw), then take the next
    slot and draw. A terminal slot is not a stop sign — it just means the
    next run gets the next slot.
    """
    validate_roster()
    date = parse_date(date)

    entries = read_ledger(LEDGER)
    slot = latest_slot(entries, date)
    existing = entry_for_slot(entries, date, slot) if slot >= 0 else None

    if existing and existing["status"] not in TERMINAL:
        logger.info("draw: resuming %s#%d from status=%s", date, slot, existing["status"])
        return _resumed(existing, date, slot)

    slot = slot + 1 if existing else 0
    drawn = draw_prompt(CORPUS, entries, date, slot)
    logger.info("draw: %s#%d from %s", date, slot, drawn["source_file"])
    record_transition(
        REPO_DIR,
        LEDGER,
        {
            "date": date,
            "slot": slot,
            "status": "drawn",
            "prompt": drawn["prompt"],
            "source_file": drawn["source_file"],
        },
        runner=runner,
    )
    return {**drawn, "date": date, "slot": slot, "done": False}


def generate_step(prompt: str, date: str, model: str = "") -> dict:
    model_name, config = choose_model(name=parse_model(model))
    image_path = generate_image(prompt, config, f"/tmp/deviant-daily-{date}.png")
    return {"model_name": model_name, "image_path": image_path}


def describe_step(image_path: str, prompt: str) -> dict:
    return describe_image(image_path, prompt)


def gate_step(
    description: dict,
    date: str,
    prompt: str,
    source_file: str,
    slot: str | int = 0,
    runner=subprocess.run,
) -> dict:
    """Deterministic gate; a skip is committed BEFORE the green exit (R-5)."""
    slot = parse_slot(slot)
    result = evaluate_gate(description)
    if not result.publish:
        record_transition(
            REPO_DIR,
            LEDGER,
            {
                "date": date,
                "slot": slot,
                "status": "skipped",
                "reason": result.reason,
                "prompt": prompt,
                "source_file": source_file,
            },
            runner=runner,
        )
        logger.info("gate: SKIP (%s)", result.reason)
        return {"publish": False, "reason": result.reason}
    return {"publish": True, "post": result.post.model_dump()}


def publish_step(
    post: dict,
    image_path: str,
    date: str,
    prompt: str,
    source_file: str,
    model_name: str,
    slot: str | int = 0,
    runner=subprocess.run,
    session=None,
) -> dict:
    """FR-822 flow with rotation-persist-first and committed transitions."""
    import requests

    slot = parse_slot(slot)
    session = session or requests
    env = {
        k: os.environ.get(k, "")
        for k in ("DA_CLIENT_ID", "DA_CLIENT_SECRET", "DA_REFRESH_TOKEN", "GH_PAT")
    }
    missing = [k for k, v in env.items() if not v]
    if missing:
        raise RuntimeError(f"missing secrets: {missing}")

    # 1. refresh (rotates) → 2. persist NEW token BEFORE any publish effect
    tok = da_api.refresh_token(
        env["DA_CLIENT_ID"], env["DA_CLIENT_SECRET"], env["DA_REFRESH_TOKEN"],
        session=session,
    )
    da_api.persist_refresh_secret(
        tok["refresh_token"], DA_REPO, env["GH_PAT"], runner=runner
    )
    access = tok["access_token"]
    da_api.placebo(access, session=session)

    # 3. ledger 'submitted' committed BEFORE the submit side effect
    record_transition(
        REPO_DIR,
        LEDGER,
        {"date": date, "slot": slot, "status": "submitted", "prompt": prompt,
         "source_file": source_file},
        runner=runner,
    )
    itemid = da_api.stash_submit(
        access, image_path, post["title"],
        render_artist_comments(PostDescription.model_validate(post)),
        post["tags"], session=session,
    )
    result = da_api.stash_publish(
        access, itemid, post["mature"],
        post.get("mature_level"), post.get("mature_classification"),
        session=session,
    )
    url = result.get("url")

    # 4. post MD + 'published' in one commit; failure here = RECOVERY_REQUIRED
    rel_post = post_path(date, slot)
    target = REPO_DIR / rel_post
    target.parent.mkdir(exist_ok=True)
    target.write_text(
        render_post_md(
            PostDescription.model_validate(post), prompt, model_name, url, date, slot
        )
    )
    try:
        record_transition(
            REPO_DIR,
            LEDGER,
            {"date": date, "slot": slot, "status": "published", "prompt": prompt,
             "source_file": source_file, "itemid": itemid, "url": url},
            runner=runner,
            extra_paths=[rel_post],
        )
    except LedgerCommitError as e:
        raise RecoveryRequired(
            f"RECOVERY_REQUIRED: published itemid={itemid} url={url} "
            f"but ledger commit failed — repair state/published.jsonl before rerun. {e}"
        ) from e
    return {"url": url, "itemid": itemid}
