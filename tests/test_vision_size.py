"""Tests: vision payload size ceiling (production failure 2026-08-23).

Run 32623570851 died at the describe step:
  "image exceeds 10 MB maximum: 10896644 bytes > 10485760 bytes"
The roster rotation to 2K/2MP PNG pushed base64 payloads past the
provider ceiling. The published artwork must stay full-size — only the
copy sent to the vision model is shrunk.
"""

import base64
import io

import pytest
from PIL import Image

from tools.vision import MAX_B64_BYTES, MAX_EDGE, prepare_for_vision


def _png(width: int, height: int, noisy: bool = False) -> bytes:
    img = Image.new("RGB", (width, height), (30, 40, 60))
    if noisy:  # defeat PNG compression so the fixture is genuinely large
        import random
        rnd = random.Random(0)
        img.putdata([(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256))
                     for _ in range(width * height)])
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_small_image_is_still_re_encoded():
    """No passthrough branch: every payload goes through the downscaler."""
    data, media_type = prepare_for_vision(_png(800, 450))
    assert media_type == "image/jpeg"
    assert data[:3] == b"\xff\xd8\xff"

def test_oversized_payload_is_shrunk_below_the_ceiling():
    original = _png(2000, 1500, noisy=True)
    assert len(base64.b64encode(original)) > MAX_B64_BYTES
    data, media_type = prepare_for_vision(original)
    assert len(base64.b64encode(data)) <= MAX_B64_BYTES
    assert media_type in ("image/png", "image/jpeg")


def test_shrinking_preserves_aspect_ratio_and_caps_the_long_edge():
    original = _png(2000, 1500, noisy=True)
    data, _ = prepare_for_vision(original)
    shrunk = Image.open(io.BytesIO(data))
    assert max(shrunk.size) <= MAX_EDGE
    assert shrunk.width / shrunk.height == pytest.approx(2000 / 1500, rel=0.02)


def test_oversized_dimensions_shrink_even_when_bytes_fit():
    """The edge cap is independent of the byte cap — a flat 4000px image
    compresses tiny, and passing it full-size wastes upload for nothing."""
    original = _png(4000, 2250)
    assert len(base64.b64encode(original)) <= MAX_B64_BYTES
    data, _ = prepare_for_vision(original)
    assert max(Image.open(io.BytesIO(data)).size) <= MAX_EDGE


def test_the_original_file_is_never_modified(tmp_path):
    """DA publishes the full-size artwork; only the vision copy shrinks."""
    path = tmp_path / "art.png"
    original = _png(2000, 1500, noisy=True)
    path.write_bytes(original)
    prepare_for_vision(path.read_bytes())
    assert path.read_bytes() == original
