"""Sequential provider fan-out (FR-888).

One prompt through all (or a subset of) active roster models: per-model
outcome is an image path or a committed run_source="probe" failure row
(FR-887). Selection is validated up front — one bad name cannot leave a
half-comparison artifact. Generation only: no publish ledger, no DA
API, no slot. Sequential by judgement gate C-3 (rate limits, spend
visibility).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, model_validator

from tools.failures import (
    FailureRecord,
    append_failure_record,
    build_failure_record,
)
from tools.generate import generate_image
from tools.roster import RosterError, validate_roster

REPO_DIR = Path(__file__).parent.parent
FAILURES = REPO_DIR / "state" / "failures.jsonl"


class GenerationOutcome(BaseModel):
    model: str
    slug: str
    status: Literal["ok", "failed"]
    path: str | None = None
    failure: FailureRecord | None = None

    @model_validator(mode="after")
    def _exactly_one(self):
        if (self.path is None) == (self.failure is None):
            raise ValueError("exactly one of path or failure required")
        return self


def resolve_models(models: list[str] | None) -> list[str]:
    """Preflight (R-3): full selection validated before any side effect."""
    usable = validate_roster()
    if models is None:
        return sorted(usable)
    duplicates = sorted({m for m in models if models.count(m) > 1})
    if duplicates:
        raise ValueError(f"duplicate model names: {duplicates}")
    unknown = [m for m in models if m not in usable]
    if unknown:
        raise RosterError(f"model(s) {unknown} not in roster {sorted(usable)}")
    return list(models)


def resolve_configs(models: list[str] | None) -> dict[str, dict]:
    usable = validate_roster()
    return {name: usable[name] for name in resolve_models(models)}


def generate_all(
    prompt: str,
    date: str,
    models: list[str] | None,
    out_dir: str | Path,
    runner=subprocess.run,
) -> list[GenerationOutcome]:
    """Sequential fan-out; a refusal becomes a failed outcome only after
    its probe row is committed (R-4) — a ledger failure aborts red."""
    configs = resolve_configs(models)
    outcomes: list[GenerationOutcome] = []
    for name, config in configs.items():
        target = Path(out_dir) / f"{date}-{name}.png"
        try:
            path = generate_image(prompt, config, target)
        except Exception as exc:
            record = build_failure_record(
                exc=exc,
                date=date,
                slot=None,
                model=name,
                slug=config["slug"],
                prompt=prompt,
                source_file=None,
                run_source="probe",
            )
            try:
                append_failure_record(REPO_DIR, FAILURES, record, runner=runner)
            except Exception as ledger_exc:
                exc.add_note(f"failure-ledger write also failed: {ledger_exc}")
                raise exc from ledger_exc
            outcomes.append(
                GenerationOutcome(
                    model=name, slug=config["slug"], status="failed", failure=record
                )
            )
            continue
        outcomes.append(
            GenerationOutcome(
                model=name, slug=config["slug"], status="ok", path=str(path)
            )
        )
    return outcomes
