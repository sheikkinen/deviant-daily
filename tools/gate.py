"""Deterministic publish gate (FR-826 R-5, AC-10; policy revised 2026-08-23).

Typed Pydantic model over the describe step's output plus mechanical
validators. Only `confidence == "low"` blocks; invalid tags or
inconsistent mature fields reject — the caller records a ledger skip.

`confidence` conflates legibility with policy risk, so a `medium`
verdict does not mean 'unreadable' — it means the model hedged, most
often on mature content. Those publish, escalated to mature rather than
being thrown away (operator ruling 2026-08-23).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

TAG_RE = re.compile(r"^[a-z0-9_]+$")

# DA stash/publish mature_classification enum (FR-822 contract)
MatureClassification = Literal["nudity", "sexual", "gore", "language", "ideology"]


class PostDescription(BaseModel):
    """Validated describe output — the only shape allowed to publish."""

    title: str = Field(min_length=1, max_length=120)
    paragraphs: list[str] = Field(min_length=1)
    quote: str | None = None
    tags: list[str] = Field(min_length=1, max_length=10)
    confidence: Literal["high", "medium", "low"]
    mature: bool
    mature_level: Literal["strict", "moderate"] | None = None
    mature_classification: list[MatureClassification] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def tags_normalized(cls, v: list[str]) -> list[str]:
        normalized = [t.strip().lower().replace(" ", "_").replace("-", "_") for t in v]
        bad = [t for t in normalized if not TAG_RE.match(t)]
        if bad:
            raise ValueError(f"tags not normalizable to [a-z0-9_]+: {bad}")
        return normalized

    @model_validator(mode="after")
    def mature_consistency(self) -> PostDescription:
        if self.mature:
            if self.mature_level is None:
                raise ValueError("mature=true requires mature_level")
        elif self.mature_level is not None or self.mature_classification:
            raise ValueError("mature=false forbids level/classification")
        return self


@dataclass
class GateResult:
    publish: bool
    reason: str | None = None
    post: PostDescription | None = None


def _escalate_to_mature(post: PostDescription) -> PostDescription:
    """A hedged verdict publishes behind DA's mature gate, not into the void."""
    if post.mature:
        return post
    return post.model_copy(update={"mature": True, "mature_level": "moderate"})


def evaluate_gate(raw: dict) -> GateResult:
    """Mechanical gate: schema-validate, then confidence policy."""
    try:
        post = PostDescription.model_validate(raw)
    except ValidationError as e:
        return GateResult(publish=False, reason=f"schema: {e.errors()[0]['msg']}")
    if post.confidence == "low":
        return GateResult(publish=False, reason="confidence: low", post=post)
    if post.confidence == "medium":
        return GateResult(publish=True, post=_escalate_to_mature(post))
    return GateResult(publish=True, post=post)
