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
    # recraft added 2026-08-24: collect generation data before per-model tuning
    assert ACTIVE_MODELS["recraft"]["slug"] == "recraft-ai/recraft-v4"
    assert DISABLED_MODELS == {}


def test_roster_output_format_is_da_safe():
    """webp/jpg defaults are provider choices; DA submit needs png."""
    for name in ("flux-2-flex", "nano-banana-2"):
        assert ACTIVE_MODELS[name]["params"]["output_format"] == "png"


def test_ensure_png_converts_webp(tmp_path):
    """recraft-v4 has no output_format param and returns webp (witnessed
    2026-08-24: RIFF magic on live generation); normalize at the download
    boundary, not downstream."""
    from PIL import Image

    from tools.generate import _ensure_png

    p = tmp_path / "img.png"
    Image.new("RGB", (4, 4), "red").save(p, format="WEBP")
    assert p.read_bytes()[:4] == b"RIFF"
    _ensure_png(p)
    assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_ensure_png_leaves_png_untouched(tmp_path):
    from PIL import Image

    from tools.generate import _ensure_png

    p = tmp_path / "img.png"
    Image.new("RGB", (4, 4), "blue").save(p, format="PNG")
    before = p.read_bytes()
    _ensure_png(p)
    assert p.read_bytes() == before


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
    assert len(entries) == 1
    assert entries[0]["source"] == "00001-123-foo.png"
    assert entries[0]["prompt"] == "a dark castle, moonlight wrapped continuation line"


FIXTURE_LOG = Path(__file__).parent / "fixtures" / "signed_log_excerpt.txt"


def _extract_fixture(tmp_path):
    out = tmp_path / "corpus.jsonl"
    extract_corpus.extract(FIXTURE_LOG, out)
    import json

    return [json.loads(line) for line in out.read_text().splitlines()]


@pytest.mark.req("REQ-DD-080")
def test_extract_v2_metadata_fields(tmp_path):
    rows = _extract_fixture(tmp_path)
    by_source = {r["source_file"]: r for r in rows}
    keeper = by_source["00101-111222333"]
    assert keeper["local_model"] == "flux-hyp16-Q5_0"
    assert keeper["seed"] == 111222333
    assert keeper["size"] == "1360x792"
    assert keeper["created"] == "2025-03-01T10:00:00+00:00"
    armor = by_source["00202-444555666"]
    assert armor["local_model"] == "autismmixSDXL_autismmixPony"
    assert armor["seed"] == 444555666
    unknown = by_source["unknown"]
    assert unknown["local_model"] == "albedobaseXL_v21"
    assert unknown["seed"] == 777888999


@pytest.mark.req("REQ-DD-080")
def test_dialect_derivation(tmp_path):
    rows = _extract_fixture(tmp_path)
    dialects = {r["source_file"]: r["dialect"] for r in rows}
    assert dialects["00101-111222333"] == "prose"  # flux family
    assert dialects["00202-444555666"] == "tags"  # Pony family + score_ negative
    assert dialects["unknown"] == "tags"  # XL family
    assert set(dialects.values()) <= {"prose", "tags"}
    # score_-family negative forces tags even for a prose-family model
    assert (
        extract_corpus.derive_dialect("flux-hyp16-Q5_0", "score_5, score_4") == "tags"
    )
    assert extract_corpus.derive_dialect("flux-hyp16-Q5_0", "") == "prose"


@pytest.mark.req("REQ-DD-081")
def test_signed_blocks_excluded(tmp_path):
    rows = _extract_fixture(tmp_path)
    prompts = " ".join(r["prompt"] for r in rows)
    assert len(rows) == 3
    assert "signed duplicate payload" not in prompts
    # stale-source hazard: a File block without parameters must not adopt
    # the following Signed block's payload
    assert "orphaned parameters payload" not in prompts


@pytest.mark.req("REQ-DD-082")
def test_ledger_source_ids_preserved():
    """AC-07: every published source_file resolves against the live corpus."""
    import json

    from tools.corpus import row_id
    from tools.ledger import read_ledger, used_source_ids

    root = Path(__file__).parent.parent
    rows = [
        json.loads(line)
        for line in (root / "prompts" / "corpus.jsonl").read_text().splitlines()
    ]
    known = {r["source_file"] for r in rows} | {row_id(r) for r in rows}
    used = used_source_ids(read_ledger(root / "state" / "published.jsonl"))
    missing = {s for s in used if s not in known}
    assert not missing, f"ledger ids missing from corpus: {sorted(missing)[:5]}"


@pytest.mark.req("REQ-DD-082")
def test_v1_prompts_preserved_in_v2():
    """AC-06: v1 corpus (pinned at f90c14b, pre-regeneration) is a subset of
    the live corpus by exact prompt text. Skipped on shallow clones."""
    import json
    import subprocess

    root = Path(__file__).parent.parent
    proc = subprocess.run(
        ["git", "-C", str(root), "show", "f90c14b:prompts/corpus.jsonl"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.skip("pinned v1 corpus commit unavailable (shallow clone)")
    v1 = {json.loads(line)["prompt"] for line in proc.stdout.splitlines() if line}
    v2 = {
        json.loads(line)["prompt"]
        for line in (root / "prompts" / "corpus.jsonl").read_text().splitlines()
    }
    missing = v1 - v2
    assert not missing, f"{len(missing)} v1 prompts lost; e.g. {sorted(missing)[:1]}"


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
