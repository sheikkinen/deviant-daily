"""Vision describe step (FR-826 step 3; FR-769/FR-781 precedent).

Sends the generated image + the original corpus prompt through an
anthropic vision model with structured output. The instruction text
lives in prompts/describe_post.yaml (committed style artifact); the
result is re-validated deterministically by tools.gate.

The payload is normalized at this boundary twice over:

- size: providers cap the base64 image and 2K/2MP PNGs from the roster
  exceed it (run 32623570851 died at 10,896,644 > 10,485,760 bytes).
  Only the copy sent to the model is shrunk — DeviantArt still receives
  the full-size artwork.
- shape: structured output is a request, not a guarantee. Run
  32688775537 returned `paragraphs` as a JSON-encoded string. Capture
  permissively, repair narrowly, then validate strictly (FR-873).
"""

from __future__ import annotations

import base64
import io
import json
import logging
from pathlib import Path

import yaml
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from yamlgraph.utils.llm_factory import create_llm

from tools.gate import MatureClassification, PostDescription

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "describe_post.yaml"

# Anthropic downscales anything longer than this server-side anyway.
MAX_EDGE = 1568
# Provider ceiling is 10 MB of base64; leave headroom for the text parts.
MAX_B64_BYTES = 9 * 1024 * 1024
JPEG_QUALITIES = (85, 70, 55)

# The only fields a provider is permitted to mis-serialize as a JSON string.
REPAIRABLE_FIELDS = ("paragraphs", "tags", "mature_classification")


class InvalidDescription(Exception):
    """Schema-shaped, unrecoverable description — never a transport error."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(reason)
        self.field = field
        self.reason = reason


class CaptureDescription(BaseModel):
    """Permissive on exactly the axis providers lie about; strict elsewhere."""

    title: str
    paragraphs: list[str] | str
    quote: str | None = None
    tags: list[str] | str
    confidence: str
    mature: bool
    mature_level: str | None = None
    mature_classification: list[MatureClassification] | str = Field(
        default_factory=list
    )


class DescribeResult(BaseModel):
    """Typed outcome the gate consumes; `valid=False` becomes a skip."""

    valid: bool
    reason: str | None = None
    field: str | None = None
    payload: dict | None = None


def _repair_list_field(field: str, value):
    """Providers sometimes serialize a list as a JSON string (run 32688775537)."""
    if not isinstance(value, str):
        return value
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as e:
        raise InvalidDescription(
            field=field, reason=f"schema: {field} is not valid JSON"
        ) from e
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise InvalidDescription(
            field=field, reason=f"schema: {field} is not a list of strings"
        )
    logger.info("vision: repaired %s from JSON string", field)
    return parsed


def repair_payload(raw: dict) -> dict:
    """Repair only the authorized fields; every other value is untouched."""
    return {
        k: (_repair_list_field(k, v) if k in REPAIRABLE_FIELDS else v)
        for k, v in raw.items()
    }


def detect_media_type(data: bytes) -> str:
    """Media type from magic bytes — providers lie about extensions
    (flux-ultra returns JPEG regardless of requested output name)."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError(f"unsupported image magic: {data[:8]!r}")


def load_instruction() -> str:
    return yaml.safe_load(PROMPT_FILE.read_text())["template"]


def _fits(data: bytes) -> bool:
    return len(base64.b64encode(data)) <= MAX_B64_BYTES


def prepare_for_vision(data: bytes) -> tuple[bytes, str]:
    """Downscale every image to the edge cap and re-encode as JPEG.

    Unconditional by design: Anthropic bills by pixel, so a full-size
    passthrough is money burned. There is no 'small enough to skip'
    branch — the only variable is JPEG quality, stepped down until the
    payload fits the byte ceiling. Magic bytes still gate the input
    (FR-826): an undecodable payload raises here rather than reaching
    the provider.
    """
    from PIL import Image

    detect_media_type(data)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    for quality in JPEG_QUALITIES:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        shrunk = buf.getvalue()
        if _fits(shrunk):
            logger.info(
                "vision: %d -> %d bytes (%dx%d, q%d)",
                len(data),
                len(shrunk),
                *img.size,
                quality,
            )
            return shrunk, "image/jpeg"
    raise ValueError(
        f"image still exceeds the vision ceiling after downscaling: {len(shrunk)}"
    )


def describe_image(image_path: str | Path, prompt_text: str, llm=None) -> dict:
    """Capture permissively, repair narrowly, validate strictly (FR-873).

    Raises InvalidDescription for schema-shaped failures; every other
    error (missing key, network, undecodable image) propagates untouched.
    """
    img_bytes, media_type = prepare_for_vision(Path(image_path).read_bytes())
    img_b64 = base64.b64encode(img_bytes).decode()
    instruction = load_instruction().replace("{original_prompt}", prompt_text)
    message = HumanMessage(
        content=[
            {"type": "text", "text": instruction},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{img_b64}"},
            },
        ]
    )
    model = llm or create_llm(provider="anthropic")
    structured = model.with_structured_output(CaptureDescription)
    captured = structured.invoke([message])
    raw = captured if isinstance(captured, dict) else captured.model_dump()
    return PostDescription.model_validate(repair_payload(raw)).model_dump()
