"""Describe step pins its vision model (anthropic API 2026-10-21 outage).

Unpinned CI resolved anthropic 2.x (header 2026-10-21), which rejects
temperature; yamlgraph's default claude-haiku-4-5 still sent it -> 400.
claude-haiku-5-5 omits temperature under every API version.
"""

from pathlib import Path

from PIL import Image

import tools.vision as vision


def test_describe_uses_claude_haiku_5_5(tmp_path: Path, monkeypatch):
    img = tmp_path / "x.png"
    Image.new("RGB", (8, 8)).save(img)
    calls: list[dict] = []

    class Stop(Exception):
        pass

    def fake_create_llm(**kwargs):
        calls.append(kwargs)
        raise Stop

    monkeypatch.setattr(vision, "create_llm", fake_create_llm)
    try:
        vision.describe_image(img, "prompt")
    except Stop:
        pass
    assert calls == [{"provider": "anthropic", "model": "claude-haiku-5-5"}]
