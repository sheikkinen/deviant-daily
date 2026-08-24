"""Tests: FR-873 — the provider's type lie must not kill the run.

Run 32688775537 (workflow_dispatch / publish-now, 2026-08-24 04:07) drew
slot 2026-08-24#1 and died at describe: the vision model returned
`paragraphs` as a JSON-encoded string. The content was correct; the
container was wrong. Two contracts are proved here:

1. narrow repair at the vision boundary (json.loads -> list[str] only)
2. schema-shaped failures reach the gate as a typed value and become a
   committed `skipped` row — they never escape as an exception, and they
   never turn a transport error into a silent skip.
"""

import json

import pytest
from pydantic import ValidationError

from tools import steps
from tools.gate import evaluate_gate
from tools.vision import (
    CaptureDescription,
    DescribeResult,
    InvalidDescription,
    repair_payload,
)

GOOD = {
    "title": "Vigil in the Hollow World",
    "paragraphs": ["one", "two"],
    "quote": "q",
    "tags": ["aiart", "gothic"],
    "confidence": "high",
    "mature": False,
    "mature_level": None,
    "mature_classification": [],
}


# --- S-1: capture, repair, validate -----------------------------------


def test_capture_schema_accepts_the_lie():
    """The capture stage must not raise on the exact failing payload."""
    raw = {**GOOD, "paragraphs": json.dumps(["one", "two"])}
    captured = CaptureDescription.model_validate(raw)
    assert captured.paragraphs == '["one", "two"]'


def test_strict_schema_still_rejects_the_lie():
    """PostDescription stays authoritative — it is not loosened."""
    from tools.gate import PostDescription

    with pytest.raises(ValidationError):
        PostDescription.model_validate({**GOOD, "paragraphs": json.dumps(["a"])})


def test_repair_restores_paragraphs(caplog):
    raw = {**GOOD, "paragraphs": json.dumps(["A figure stands alone", "Be Art."])}
    with caplog.at_level("INFO"):
        repaired = repair_payload(raw)
    assert repaired["paragraphs"] == ["A figure stands alone", "Be Art."]
    assert any("paragraphs" in r.message for r in caplog.records)


@pytest.mark.parametrize(
    "field,value",
    [
        ("tags", ["aiart", "gothic"]),
        ("mature_classification", ["nudity"]),
    ],
)
def test_repair_covers_the_other_authorized_fields(field, value):
    raw = {**GOOD, "mature": True, "mature_level": "moderate", field: json.dumps(value)}
    assert repair_payload(raw)[field] == value


def test_repaired_mature_classification_still_hits_the_enum():
    raw = {
        **GOOD,
        "mature": True,
        "mature_level": "moderate",
        "mature_classification": json.dumps(["not_an_enum_member"]),
    }
    result = evaluate_gate(repair_payload(raw))
    assert result.publish is False
    assert result.reason.startswith("schema:")


def test_well_formed_payload_is_not_touched(caplog):
    with caplog.at_level("INFO"):
        assert repair_payload(dict(GOOD)) == GOOD
    assert not [r for r in caplog.records if "repaired" in r.message]


def test_non_string_values_pass_through_untouched():
    raw = {**GOOD, "paragraphs": ["already", "a", "list"]}
    assert repair_payload(raw)["paragraphs"] == ["already", "a", "list"]


@pytest.mark.parametrize("field", ["paragraphs", "tags", "mature_classification"])
def test_invalid_json_is_not_repaired(field):
    with pytest.raises(InvalidDescription) as e:
        repair_payload({**GOOD, field: "not json at all"})
    assert e.value.field == field
    assert e.value.reason.startswith("schema:")


@pytest.mark.parametrize(
    "payload", ['{"a": 1}', "[1, 2, 3]", '[["nested"]]', '"scalar"']
)
def test_valid_json_that_is_not_list_of_str_is_not_repaired(payload):
    with pytest.raises(InvalidDescription) as e:
        repair_payload({**GOOD, "paragraphs": payload})
    assert e.value.field == "paragraphs"


def test_unauthorized_string_field_is_never_parsed():
    """title is a str by contract; a JSON-looking title stays a string."""
    raw = {**GOOD, "title": '["not", "a", "list"]'}
    assert repair_payload(raw)["title"] == '["not", "a", "list"]'


# --- S-2: typed failure routed through the gate ------------------------


def test_gate_recognises_the_typed_invalid_value():
    result = evaluate_gate(
        DescribeResult(
            valid=False,
            reason="schema: paragraphs is not valid JSON",
            field="paragraphs",
        )
    )
    assert result.publish is False
    assert result.reason == "schema: paragraphs is not valid JSON"
    assert result.post is None


def test_describe_step_returns_typed_failure_not_an_exception(monkeypatch):
    def boom(*a, **k):
        raise InvalidDescription(
            field="paragraphs", reason="schema: paragraphs is not valid JSON"
        )

    monkeypatch.setattr(steps, "describe_image", boom)
    out = steps.describe_step("/tmp/x.png", "prompt")
    assert out["valid"] is False
    assert out["field"] == "paragraphs"


def test_describe_step_lets_transport_errors_stay_red(monkeypatch):
    """Missing key, network, undecodable image must not become skips."""

    def boom(*a, **k):
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    monkeypatch.setattr(steps, "describe_image", boom)
    with pytest.raises(RuntimeError):
        steps.describe_step("/tmp/x.png", "prompt")


def test_gate_step_commits_one_skipped_row_for_the_typed_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(steps, "REPO_DIR", tmp_path)
    monkeypatch.setattr(steps, "LEDGER", tmp_path / "state" / "published.jsonl")
    (tmp_path / "state").mkdir()

    def ok_runner(cmd, **kw):
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0, stderr="", stdout="")

    out = steps.gate_step(
        description={
            "valid": False,
            "reason": "schema: paragraphs is not valid JSON",
            "field": "paragraphs",
            "payload": None,
        },
        date="2026-08-24",
        prompt="p",
        source_file="001",
        slot=1,
        runner=ok_runner,
    )
    assert out["publish"] is False
    rows = [json.loads(x) for x in steps.LEDGER.read_text().splitlines() if x.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "skipped"
    assert rows[0]["slot"] == 1
    assert rows[0]["reason"].startswith("schema:")
    assert "paragraphs" in rows[0]["reason"]


def test_describe_step_makes_no_publish_decision_and_writes_no_ledger():
    """AC-13: the gate is the sole decider."""
    import inspect

    src = inspect.getsource(steps.describe_step)
    assert "record_transition" not in src
    assert "publish" not in src
