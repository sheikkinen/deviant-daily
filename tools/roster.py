"""Frozen model roster (FR-826 R-4, AC-09).

Three ACTIVE models. Grok enabled 2026-08-19: operator supplied the
slug https://replicate.com/xai/grok-imagine-image-2 (the earlier
"no Replicate grok" retirement was a search-API false negative —
GET /models/xai/grok-imagine-image-2 returns the schema).
2026-08-23: flux-ultra (flux-1.1-pro-ultra) retired as superseded;
flux-2-flex and nano-banana-2 added, both slugs verified by direct
GET /models/<owner>/<name> and their params taken from the returned
input schema enums.
2026-08-24: recraft (recraft-ai/recraft-v4) added the same way —
slug verified by direct GET, size enum from the input schema. Live
generation witnessed webp output (RIFF magic); generate._ensure_png
normalizes to PNG at the download boundary.
Zero active models is a hard failure BEFORE any corpus draw or DA
side effect — never a green skip.
"""

from __future__ import annotations

import logging
import random

logger = logging.getLogger(__name__)

ACTIVE_MODELS: dict[str, dict] = {
    "z-image": {
        "slug": "prunaai/z-image-turbo",
        "params": {
            "width": 1344,
            "height": 768,
            "guidance_scale": 0,
            "num_inference_steps": 8,
        },
    },
    "flux-2-flex": {
        "slug": "black-forest-labs/flux-2-flex",
        "params": {
            "aspect_ratio": "16:9",
            "resolution": "2 MP",
            "output_format": "png",
        },
    },
    "nano-banana-2": {
        "slug": "google/nano-banana-2",
        "params": {
            "aspect_ratio": "16:9",
            "resolution": "2K",
            "output_format": "png",
        },
    },
    "grok": {
        "slug": "xai/grok-imagine-image-2",
        "params": {"aspect_ratio": "16:9", "resolution": "2k", "quality": "medium"},
    },
    "recraft": {
        "slug": "recraft-ai/recraft-v4",
        # schema offers size enum only (no output_format/resolution);
        # 1344x768 matches z-image's 16:9 dims
        "params": {"size": "1344x768"},
    },
}

# name -> reason it is disabled (structured, logged, never silently used)
DISABLED_MODELS: dict[str, str] = {}


class RosterError(RuntimeError):
    """Zero usable models — must fire before any side effect."""


def validate_roster(unavailable: list[str] | None = None) -> dict[str, dict]:
    """Return usable models; hard-fail when none remain.

    `unavailable` drops optional models with a structured log line.
    """
    for name, reason in DISABLED_MODELS.items():
        logger.info("roster: model=%s disabled reason=%r", name, reason)
    usable = dict(ACTIVE_MODELS)
    for name in unavailable or []:
        if name in usable:
            logger.warning("roster: model=%s dropped reason=unavailable", name)
            usable.pop(name)
    if not usable:
        raise RosterError("roster empty: zero active models — refusing to run")
    return usable


def choose_model(rng: random.Random | None = None, name: str = "") -> tuple[str, dict]:
    """Random over the roster, or exactly `name` when pinned (FR-862)."""
    usable = validate_roster()
    if name:
        if name not in usable:
            raise RosterError(f"model {name!r} not in roster {sorted(usable)}")
        return name, usable[name]
    chosen = (rng or random).choice(sorted(usable))
    return chosen, usable[chosen]
