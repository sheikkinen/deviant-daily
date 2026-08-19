"""Frozen model roster (FR-826 R-4, AC-09).

Two ACTIVE models. Grok is RETIRED: verified 2026-08-19 that no grok
image model exists on Replicate (xai/x-ai/grok all 404, search empty);
grok imagegen is xAI-API-only, which this pipeline does not speak.
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
    "flux-ultra": {
        "slug": "black-forest-labs/flux-1.1-pro-ultra",
        "params": {"aspect_ratio": "16:9"},
    },
}

# name -> reason it is disabled (structured, logged, never silently used)
DISABLED_MODELS: dict[str, str] = {
    "grok": "retired — no grok image model on Replicate (verified 2026-08-19); xAI-API-only",
}


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


def choose_model(rng: random.Random | None = None) -> tuple[str, dict]:
    usable = validate_roster()
    name = (rng or random).choice(sorted(usable))
    return name, usable[name]
