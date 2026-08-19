"""Replicate image generation (FR-826 step 2; examples/shared precedent)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class GenerationError(RuntimeError):
    pass


def generate_image(prompt: str, model_config: dict, output_path: str | Path) -> str:
    """Run one Replicate prediction, download the image, return the path."""
    if not os.environ.get("REPLICATE_API_TOKEN"):
        raise GenerationError("REPLICATE_API_TOKEN not set")
    import replicate

    output = replicate.run(
        model_config["slug"], input={"prompt": prompt, **model_config["params"]}
    )
    url = _first_url(output)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=120, follow_redirects=True) as r:
        r.raise_for_status()
        with out.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    logger.info("generated %s (%d bytes)", out, out.stat().st_size)
    return str(out)


def _first_url(output) -> str:
    """Replicate returns FileOutput | list | str depending on model."""
    if isinstance(output, list):
        output = output[0]
    if isinstance(output, str):
        return output
    if hasattr(output, "url"):
        return output.url
    raise GenerationError(f"unexpected replicate output type: {type(output)}")
