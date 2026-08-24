"""Tests: roster freeze (AC-09), corpus extraction sanitization (AC-04),
post MD rendering (AC-18)."""

import importlib.util
import random
from pathlib import Path

import pytest

from tools.gate import PostDescription
from tools.post import render_post_md
from tools.roster import (
    ACTIVE_MODELS,
    DISABLED_MODELS,
    RosterError,
    choose_model,
    validate_roster,
)

_spec = importlib.util.spec_from_file_location(
    "extract_corpus", Path(__file__).parent.parent / "scripts" / "extract_corpus.py"
)
extract_corpus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_spec and extract_corpus)


@pytest.mark.req("REQ-DD-041")
def test_roster_frozen_models():
    assert ACTIVE_MODELS["z-image"]["slug"] == "prunaai/z-image-turbo"
    assert (
        "grok" in ACTIVE_MODELS
    )  # enabled 2026-08-19, slug xai/grok-imagine-image-2 (R-4)
    assert ACTIVE_MODELS["grok"]["slug"] == "xai/grok-imagine-image-2"
    # flux-ultra retired 2026-08-23 (flux-1.1-pro-ultra superseded)
    assert "flux-ultra" not in ACTIVE_MODELS
    assert ACTIVE_MODELS["flux-2-flex"]["slug"] == "black-forest-labs/flux-2-flex"
    assert ACTIVE_MODELS["nano-banana-2"]["slug"] == "google/nano-banana-2"
    assert DISABLED_MODELS == {}


def test_roster_output_format_is_da_safe():
    """webp/jpg defaults are provider choices; DA submit needs png."""
    for name in ("flux-2-flex", "nano-banana-2"):
        assert ACTIVE_MODELS[name]["params"]["output_format"] == "png"


@pytest.mark.req("REQ-DD-042")
def test_roster_zero_active_hard_fails():
    with pytest.raises(RosterError):
        validate_roster(unavailable=list(ACTIVE_MODELS))


@pytest.mark.req("REQ-DD-043")
def test_roster_drop_logs_structured(caplog):
    import logging

    with caplog.at_level(logging.WARNING):
        usable = validate_roster(unavailable=["z-image"])
    assert "flux-2-flex" in usable
    assert any("model=z-image" in r.message for r in caplog.records)


@pytest.mark.req("REQ-DD-044")
def test_choose_model_deterministic_with_seed():
    name, config = choose_model(random.Random(1))
    assert name in ACTIVE_MODELS
    assert "slug" in config


@pytest.mark.req("REQ-DD-045")
def test_sanitize_strips_lora():
    s = extract_corpus.sanitize("a hero <lora:flux_lora_x:0.5> fighting (bold:1.2)")
    assert "<lora" not in s
    assert ":1.2" not in s
    assert "bold)" in s


@pytest.mark.req("REQ-DD-046")
def test_name_blocklist_catches_variants():
    r = extract_corpus.name_blocklist_re(extract_corpus.NAME_BLOCKLIST)
    for text in ("portrait of Nina", "nina_heikkinen_style", "NINA1 model", "katja"):
        assert r.search(text), text
    assert not r.search("feminine energy luminous")


@pytest.mark.req("REQ-DD-047")
def test_term_blocklist_stems_not_substrings():
    r = extract_corpus.term_blocklist_re(extract_corpus.TERM_BLOCKLIST)
    for text in ("raped by ogre", "(rape)", "girl_raped"):
        assert r.search(text), text
    for text in ("flowing drapery", "grapes on vine", "skyscrapers"):
        assert not r.search(text), text


@pytest.mark.req("REQ-DD-048")
def test_parse_entries_prompt_ends_at_steps():
    lines = [
        "==== File: 00001-123-foo.png ====",
        "Image:",
        "    parameters: a dark castle, moonlight",
        "wrapped continuation line",
        "Steps: 20, Sampler: Euler",
        "    png:IHDR.bit_depth: 8",
    ]
    entries = extract_corpus.parse_entries(lines)
    assert entries == [
        ("00001-123-foo.png", "a dark castle, moonlight wrapped continuation line")
    ]


@pytest.mark.req("REQ-DD-049")
def test_source_file_reduced_to_id(tmp_path):
    log = tmp_path / "signed.log"
    log.write_text(
        "==== File: 00314-268-A prompt with secret_lora_name.png ====\n"
        "    parameters: a castle on a hill at midnight glowing\n"
        "Steps: 20\n"
    )
    out = tmp_path / "corpus.jsonl"
    extract_corpus.extract(log, out)
    import json

    row = json.loads(out.read_text())
    assert row["source_file"] == "00314-268"


@pytest.mark.req("REQ-DD-050")
def test_render_post_md_shape():
    post = PostDescription(
        title="Veil",
        paragraphs=["One.", "Two."],
        quote="Be Art.",
        tags=["gothic"],
        confidence="high",
        mature=False,
    )
    md = render_post_md(post, "prompt text", "z-image", "https://da/x", "2026-08-19")
    assert md.startswith("# Veil\n\nOne.\n\nTwo.\n\n> Be Art.\n\n#gothic")
    assert "- deviation: https://da/x" in md
    assert "- model: z-image" in md


@pytest.mark.req("REQ-DD-051")
def test_render_artist_comments_style_contract():
    from tools.post import DESCRIPTION_FOOTER, render_artist_comments

    post = PostDescription(
        title="Veil",
        paragraphs=["One.", "Two."],
        quote="Vow.",
        tags=["gothic"],
        confidence="high",
        mature=False,
    )
    comments = render_artist_comments(post)
    # DA renders \n\n as an EMPTY <p> that collapses to zero height
    # (live witness 2026-08-19) — the separator line must carry a
    # non-breaking space so the blank line is visible.
    assert comments.startswith("One.\n\u00a0\nTwo.\n\u00a0\n\u201cVow.\u201d\n\u00a0\n")
    assert "\n\n" not in comments
    assert comments.endswith(DESCRIPTION_FOOTER)
    assert "deviantart.com/sheikkinen/gallery" in comments
