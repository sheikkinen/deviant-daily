"""Tests: gate schema, tags, mature combos (AC-10, AC-13, AC-18)."""

from tools.gate import PostDescription, evaluate_gate

VALID = {
    "title": "Veil and Vow",
    "paragraphs": ["First paragraph.", "Second paragraph."],
    "quote": "Be Art. Be Unique.",
    "tags": ["gothic", "aiart", "digitalart"],
    "confidence": "high",
    "mature": False,
}


def test_valid_post_publishes():
    r = evaluate_gate(VALID)
    assert r.publish is True
    assert isinstance(r.post, PostDescription)


def test_low_confidence_skips():
    r = evaluate_gate({**VALID, "confidence": "low"})
    assert r.publish is False
    assert "confidence" in r.reason


def test_medium_confidence_publishes_escalated():
    """Policy revised 2026-08-23: medium is a hedge, not an unreadable image."""
    r = evaluate_gate({**VALID, "confidence": "medium"})
    assert r.publish is True
    assert r.post.mature is True


def test_tags_normalized():
    r = evaluate_gate({**VALID, "tags": ["Dark Fantasy", "Ink-Punk"]})
    assert r.publish is True
    assert r.post.tags == ["dark_fantasy", "ink_punk"]


def test_invalid_tags_reject():
    r = evaluate_gate({**VALID, "tags": ["ok", "bäd tág!"]})
    assert r.publish is False
    assert "schema" in r.reason


def test_mature_true_requires_level_and_classification():
    r = evaluate_gate({**VALID, "mature": True})
    assert r.publish is False
    ok = evaluate_gate(
        {
            **VALID,
            "mature": True,
            "mature_level": "moderate",
            "mature_classification": ["nudity"],
        }
    )
    assert ok.publish is True


def test_mature_false_forbids_level():
    r = evaluate_gate({**VALID, "mature_level": "strict"})
    assert r.publish is False


def test_invalid_classification_rejects():
    r = evaluate_gate(
        {
            **VALID,
            "mature": True,
            "mature_level": "strict",
            "mature_classification": ["violence_extreme"],
        }
    )
    assert r.publish is False


def test_missing_fields_reject():
    r = evaluate_gate({"title": "x"})
    assert r.publish is False
    assert r.reason.startswith("schema")


def test_empty_paragraphs_reject():
    assert evaluate_gate({**VALID, "paragraphs": []}).publish is False
