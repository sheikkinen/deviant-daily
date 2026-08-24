"""Graph node step functions (FR-826 R-1: yamlgraph orchestrates, these
are the side-effect tools it calls).

Ordering contracts enforced here:
- ledger transition committed BEFORE the next side effect (R-3)
- rotated refresh token persisted BEFORE any DA submit/publish (AC-08)
- post-publish commit failure -> RecoveryRequired, visibly red (R-3)
"""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from tools import da_api
from tools.corpus import draw_prompt
from tools.gate import PostDescription, evaluate_gate
from tools.generate import generate_image
from tools.ledger import (
    TERMINAL,
    LedgerCommitError,
    RecoveryRequired,
    read_ledger,
    record_transition,
)
from tools.post import render_artist_comments, render_post_md
from tools.roster import choose_model, validate_roster
from tools.vision import describe_image

logger = logging.getLogger(__name__)

REPO_DIR = Path(__file__).parent.parent
LEDGER = REPO_DIR / "state" / "published.jsonl"
CORPUS = REPO_DIR / "prompts" / "corpus.jsonl"
DA_REPO = "sheikkinen/deviant-daily"


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def draw_step(date: str = "", runner=subprocess.run) -> dict:
    """Roster check first (R-4: fail before any draw), then draw + commit."""
    validate_roster()
    date = date or _today()
    entries = read_ledger(LEDGER)
    drawn = draw_prompt(CORPUS, entries, date)
    if drawn["resumed"]:
        if drawn["status"] in TERMINAL:
            logger.info("draw: %s already %s — idempotent exit", date, drawn["status"])
            return {**drawn, "date": date, "done": True}
        logger.info("draw: resuming %s from status=%s", date, drawn["status"])
        return {**drawn, "date": date, "done": False}
    record_transition(
        REPO_DIR,
        LEDGER,
        {
            "date": date,
            "status": "drawn",
            "prompt": drawn["prompt"],
            "source_file": drawn["source_file"],
        },
        runner=runner,
    )
    return {**drawn, "date": date, "done": False}


def generate_step(prompt: str, date: str) -> dict:
    model_name, config = choose_model()
    image_path = generate_image(prompt, config, f"/tmp/deviant-daily-{date}.png")
    return {"model_name": model_name, "image_path": image_path}


def describe_step(image_path: str, prompt: str) -> dict:
    return describe_image(image_path, prompt)


def gate_step(
    description: dict, date: str, prompt: str, source_file: str, runner=subprocess.run
) -> dict:
    """Deterministic gate; a skip is committed BEFORE the green exit (R-5)."""
    result = evaluate_gate(description)
    if not result.publish:
        record_transition(
            REPO_DIR,
            LEDGER,
            {
                "date": date,
                "status": "skipped",
                "reason": result.reason,
                "prompt": prompt,
                "source_file": source_file,
            },
            runner=runner,
        )
        logger.info("gate: SKIP (%s) — recorded and committed", result.reason)
        return {"publish": False, "reason": result.reason}
    return {"publish": True, "post": result.post.model_dump()}


def publish_step(
    post: dict,
    image_path: str,
    date: str,
    prompt: str,
    source_file: str,
    model_name: str,
    runner=subprocess.run,
    session=None,
) -> dict:
    """FR-822 flow with rotation-persist-first and committed transitions."""
    import requests

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
        env["DA_CLIENT_ID"],
        env["DA_CLIENT_SECRET"],
        env["DA_REFRESH_TOKEN"],
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
        {
            "date": date,
            "status": "submitted",
            "prompt": prompt,
            "source_file": source_file,
        },
        runner=runner,
    )
    itemid = da_api.stash_submit(
        access,
        image_path,
        post["title"],
        render_artist_comments(PostDescription.model_validate(post)),
        post["tags"],
        session=session,
    )
    result = da_api.stash_publish(
        access,
        itemid,
        post["mature"],
        post.get("mature_level"),
        post.get("mature_classification"),
        session=session,
    )
    url = result.get("url")

    # 4. post MD + 'published' in one commit; failure here = RECOVERY_REQUIRED
    post_path = REPO_DIR / "posts" / f"{date}.md"
    post_path.parent.mkdir(exist_ok=True)
    post_path.write_text(
        render_post_md(
            PostDescription.model_validate(post), prompt, model_name, url, date
        )
    )
    try:
        record_transition(
            REPO_DIR,
            LEDGER,
            {
                "date": date,
                "status": "published",
                "prompt": prompt,
                "source_file": source_file,
                "itemid": itemid,
                "url": url,
            },
            runner=runner,
            extra_paths=[f"posts/{date}.md"],
        )
    except LedgerCommitError as e:
        raise RecoveryRequired(
            f"RECOVERY_REQUIRED: published itemid={itemid} url={url} "
            f"but ledger commit failed — repair state/published.jsonl before rerun. {e}"
        ) from e
    return {"url": url, "itemid": itemid}
