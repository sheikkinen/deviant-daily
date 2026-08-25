"""Tests: FR-889 user-given prompt CLI — verbatim pass-through,
preflight before side effects, generation-only boundary, FR-887
run_source="user" rows."""

import json
import sys
from types import SimpleNamespace

import pytest

from tools import steps, user_generate
from tools.generate import GenerationError

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


class FakeStream:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_bytes(self):
        yield PNG


class GitRecorder:
    def __init__(self):
        self.cmds = []

    def __call__(self, cmd, **kwargs):
        self.cmds.append(cmd)
        return SimpleNamespace(returncode=0, stderr="", stdout="")


@pytest.fixture
def provider(monkeypatch, tmp_path):
    """Deep fake: records replicate.run inputs, fakes the download."""
    calls = []

    def fake_run(slug, input):
        calls.append((slug, input))
        return "https://replicate.delivery/img"

    monkeypatch.setitem(sys.modules, "replicate", SimpleNamespace(run=fake_run))
    monkeypatch.setattr("tools.generate.httpx.stream", lambda *a, **k: FakeStream())
    monkeypatch.setenv("REPLICATE_API_TOKEN", "x")
    monkeypatch.setattr(steps, "REPO_DIR", tmp_path)
    monkeypatch.setattr(steps, "FAILURES", tmp_path / "state" / "failures.jsonl")
    return calls


def _argv(tmp_path, *extra):
    return [
        "--model",
        "z-image",
        "--date",
        "2026-08-25",
        "--out-dir",
        str(tmp_path / "out"),
        *extra,
    ]


@pytest.mark.req("REQ-DD-098")
def test_prompt_verbatim_to_replicate(provider, tmp_path):
    """AC-01: byte-identical argv prompt reaches replicate.run."""
    text = 'kärpänen "quoted" — trailing spaces  '
    user_generate.main(_argv(tmp_path, "--prompt", text), runner=GitRecorder())
    (call,) = provider
    assert call[1]["prompt"] == text


@pytest.mark.req("REQ-DD-098")
def test_prompt_file_verbatim_with_trailing_newline(provider, tmp_path):
    """AC-02: UTF-8 file contents pass verbatim, newlines preserved."""
    text = "line one\nlinja kaksi — ääkköset\n\n"
    pf = tmp_path / "prompt.txt"
    pf.write_text(text, encoding="utf-8")
    user_generate.main(_argv(tmp_path, "--prompt-file", str(pf)), runner=GitRecorder())
    (call,) = provider
    assert call[1]["prompt"] == text


@pytest.mark.req("REQ-DD-099")
def test_invalid_utf8_fails_before_provider(provider, tmp_path):
    """AC-02: invalid UTF-8 fails before any provider call or write."""
    pf = tmp_path / "bad.txt"
    pf.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(UnicodeDecodeError):
        user_generate.main(
            _argv(tmp_path, "--prompt-file", str(pf)), runner=GitRecorder()
        )
    assert provider == []
    assert not (tmp_path / "out").exists()


@pytest.mark.req("REQ-DD-099")
def test_prompt_flags_mutually_exclusive_and_required(provider, tmp_path):
    """AC-03: --prompt XOR --prompt-file, exactly one required."""
    pf = tmp_path / "p.txt"
    pf.write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit):
        user_generate.main(_argv(tmp_path, "--prompt", "a", "--prompt-file", str(pf)))
    with pytest.raises(SystemExit):
        user_generate.main(_argv(tmp_path))
    assert provider == []


@pytest.mark.req("REQ-DD-099")
def test_unknown_model_fails_before_side_effects(provider, tmp_path):
    """AC-06: roster validation fires before provider call or write."""
    with pytest.raises(Exception, match="z-image"):
        user_generate.main(
            [
                "--model",
                "no-such-model",
                "--date",
                "2026-08-25",
                "--out-dir",
                str(tmp_path / "out"),
                "--prompt",
                "x",
            ],
            runner=GitRecorder(),
        )
    assert provider == []
    assert not (tmp_path / "out").exists()


@pytest.mark.req("REQ-DD-100")
def test_refusal_writes_user_row_and_stays_red(provider, tmp_path, monkeypatch):
    """AC-04: refusal -> committed run_source=user row, null slot/source, red."""

    def boom(prompt, config, output_path):
        raise GenerationError("flagged as NSFW")

    monkeypatch.setattr(steps, "generate_image", boom)
    runner = GitRecorder()
    with pytest.raises(GenerationError):
        user_generate.main(_argv(tmp_path, "--prompt", "secret prompt"), runner=runner)
    rows = [
        json.loads(line)
        for line in (tmp_path / "state" / "failures.jsonl").read_text().splitlines()
    ]
    (row,) = rows
    assert row["run_source"] == "user"
    assert row["slot"] is None
    assert row["source_file"] is None
    assert "secret prompt" not in json.dumps(row)
    assert runner.cmds  # row committed


@pytest.mark.req("REQ-DD-101")
def test_success_is_generation_only(provider, tmp_path, monkeypatch):
    """AC-05: image only — no publish ledger, no DA, no failure row."""
    from tools import da_api

    for name in ("submit_stash", "publish_stash"):
        if hasattr(da_api, name):
            monkeypatch.setattr(
                da_api, name, lambda *a, **k: pytest.fail("DA API touched")
            )
    path = user_generate.main(
        _argv(tmp_path, "--prompt", "hello"), runner=GitRecorder()
    )
    assert (tmp_path / "out").exists()
    assert not (tmp_path / "state" / "published.jsonl").exists()
    assert not (tmp_path / "state" / "failures.jsonl").exists()
    assert path.endswith(".png")


@pytest.mark.req("REQ-DD-102")
def test_output_path_identity(provider, tmp_path):
    """AC-07: deterministic <out_dir>/<date>-user-<model>.png."""
    path = user_generate.main(
        _argv(tmp_path, "--prompt", "hello"), runner=GitRecorder()
    )
    assert path == str(tmp_path / "out" / "2026-08-25-user-z-image.png")
    assert (tmp_path / "out" / "2026-08-25-user-z-image.png").read_bytes()[:8] == PNG[
        :8
    ]
