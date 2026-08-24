"""Tests: publish policy after the 2026-08-23 operator ruling.

Gate blocks `low` only. `high` publishes as declared; `medium` means the
model was unsure, so it publishes with mature escalated rather than
being skipped. Vision payloads are ALWAYS downscaled — Anthropic bills
by pixel, so full-size passthrough is money burned.
"""

import base64
import io

import pytest
from PIL import Image

from tools.gate import evaluate_gate
from tools.vision import MAX_B64_BYTES, MAX_EDGE, prepare_for_vision

BASE = {
    "title": "T",
    "paragraphs": ["p"],
    "quote": None,
    "tags": ["aiart"],
    "mature": False,
    "mature_level": None,
    "mature_classification": [],
}


def _png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (30, 40, 60)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.req("REQ-DD-033")
def test_low_confidence_is_the_only_block():
    result = evaluate_gate({**BASE, "confidence": "low"})
    assert result.publish is False
    assert result.reason == "confidence: low"


@pytest.mark.req("REQ-DD-033", "REQ-DD-034")
def test_high_confidence_publishes_as_declared():
    result = evaluate_gate({**BASE, "confidence": "high"})
    assert result.publish is True
    assert result.post.mature is False
    assert result.post.mature_level is None


@pytest.mark.req("REQ-DD-033", "REQ-DD-035")
def test_medium_confidence_publishes_escalated_to_mature():
    result = evaluate_gate({**BASE, "confidence": "medium"})
    assert result.publish is True
    assert result.post.mature is True
    assert result.post.mature_level == "moderate"


@pytest.mark.req("REQ-DD-036")
def test_medium_keeps_the_models_own_mature_classification():
    result = evaluate_gate(
        {
            **BASE,
            "confidence": "medium",
            "mature": True,
            "mature_level": "strict",
            "mature_classification": ["nudity"],
        }
    )
    assert result.publish is True
    assert result.post.mature_level == "strict"
    assert result.post.mature_classification == ["nudity"]


@pytest.mark.req("REQ-DD-037")
def test_schema_failure_still_blocks():
    result = evaluate_gate({**BASE, "confidence": "high", "tags": []})
    assert result.publish is False
    assert result.reason.startswith("schema:")


@pytest.mark.req("REQ-DD-038")
def test_every_image_goes_through_the_downscaler():
    """Anthropic bills by pixel — there is no 'small enough to skip' branch.
    Output format is always JPEG so the payload shape is deterministic."""
    data, media_type = prepare_for_vision(_png(900, 500))
    assert media_type == "image/jpeg"
    assert Image.open(io.BytesIO(data)).size == (900, 500)


@pytest.mark.req("REQ-DD-039")
def test_large_images_are_capped_at_the_edge():
    data, _ = prepare_for_vision(_png(4000, 2250))
    assert max(Image.open(io.BytesIO(data)).size) <= MAX_EDGE


@pytest.mark.req("REQ-DD-040")
def test_pixel_count_is_what_shrinks():
    original = _png(4000, 2250)
    data, _ = prepare_for_vision(original)
    before = Image.open(io.BytesIO(original)).size
    after = Image.open(io.BytesIO(data)).size
    assert after[0] * after[1] < before[0] * before[1] / 4
    assert len(base64.b64encode(data)) <= MAX_B64_BYTES
