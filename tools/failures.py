"""Committed generation-failure ledger (FR-887).

state/failures.jsonl accumulates every image-generation failure as a
typed row — the organic tolerance data FR-886's router consumes.
Classification is a claim bound to exception types at the boundary,
never a silent fallback: the raw (capped, redacted) provider excerpt
travels with it. Its own artifact with its own helper — the publish
ledger's status machine is untouched (judgement R-2).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel

from tools.ledger import commit_push

EXCERPT_CAP = 500
REFUSAL_KEYWORDS = ("nsfw", "flagged", "safety", "content policy", "sensitive")

_REDACT_KV = re.compile(
    r"(?i)\b(token|secret|key|authorization|bearer|password)\b(\s*[=:]\s*|\s+)\S+"
)
_REDACT_URL_CRED = re.compile(r"://[^/@\s]+@")


class FailureRecord(BaseModel):
    ts: str  # UTC ISO-8601
    date: str  # YYYY-MM-DD
    slot: int | None
    model: str  # roster name
    slug: str
    prompt_sha: str  # sha256 over exact prompt bytes; corpus is the lookup
    source_file: str | None
    error_class: Literal["refusal", "transport", "timeout", "unknown"]
    provider_message: str
    run_source: Literal["corpus", "user", "probe"]


def prompt_sha(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def classify_failure(exc: BaseException) -> str:
    """Closed contract (R-5): types first, refusal keywords second."""
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.HTTPError | ConnectionError):
        return "transport"
    message = str(exc).lower()
    if any(keyword in message for keyword in REFUSAL_KEYWORDS):
        return "refusal"
    return "unknown"


def redact_excerpt(message: str) -> str:
    """Cap + redact (R-4): provider text is adversarial input."""
    message = _REDACT_URL_CRED.sub("://[REDACTED]@", message)
    message = _REDACT_KV.sub(lambda m: f"{m.group(1)}=[REDACTED]", message)
    return message[:EXCERPT_CAP]


def build_failure_record(
    *,
    exc: BaseException,
    date: str,
    slot: int | None,
    model: str,
    slug: str,
    prompt: str,
    source_file: str | None,
    run_source: str,
) -> FailureRecord:
    return FailureRecord(
        ts=datetime.now(UTC).isoformat(),
        date=date,
        slot=slot,
        model=model,
        slug=slug,
        prompt_sha=prompt_sha(prompt),
        source_file=source_file,
        error_class=classify_failure(exc),
        provider_message=redact_excerpt(str(exc)),
        run_source=run_source,
    )


def append_failure_record(
    repo_dir: str | Path,
    path: str | Path,
    record: FailureRecord,
    runner=subprocess.run,
) -> None:
    """Append-only + commit_push discipline; raises LedgerCommitError."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")
    rel = str(p.resolve().relative_to(Path(repo_dir).resolve()))
    commit_push(
        repo_dir,
        [rel],
        f"failures: {record.date}#{record.slot} {record.model} {record.error_class}",
        runner=runner,
    )
