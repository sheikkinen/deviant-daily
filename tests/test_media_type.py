"""Tests: media type detected from content, not filename (FR-826 fix:
flux-ultra returned JPEG regardless of output extension)."""

import io

import pytest
from PIL import Image

from tools.vision import detect_media_type

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16


def _real_jpeg(width: int = 640, height: int = 360) -> bytes:
    """A decodable JPEG — the describe path runs a real decoder."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (10, 20, 30)).save(buf, format="JPEG")
    return buf.getvalue()


def test_png_magic():
    assert detect_media_type(PNG) == "image/png"


def test_jpeg_magic():
    assert detect_media_type(JPEG) == "image/jpeg"


def test_unknown_raises():
    with pytest.raises(ValueError):
        detect_media_type(b"GIF89a not supported")


def test_describe_uses_content_type(tmp_path):
    """A .png-named file with JPEG content must be declared image/jpeg."""
    img = tmp_path / "lying-name.png"
    img.write_bytes(_real_jpeg())

    captured = {}

    class FakeStructured:
        def invoke(self, messages):
            captured["url"] = messages[0].content[1]["image_url"]["url"]
            from tools.gate import PostDescription

            return PostDescription(
                title="t",
                paragraphs=["p"],
                tags=["a"],
                confidence="high",
                mature=False,
            )

    class FakeLLM:
        def with_structured_output(self, schema):
            return FakeStructured()

    from tools.vision import describe_image

    describe_image(img, "prompt", llm=FakeLLM())
    assert captured["url"].startswith("data:image/jpeg;base64,")
