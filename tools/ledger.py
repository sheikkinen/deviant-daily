"""Committed idempotency ledger (FR-826 R-3, AC-12).

`state/published.jsonl` is the only guard around DA side effects.
Statuses: drawn -> submitted -> published | skipped. Every transition
that guards an external call is committed-and-pushed BEFORE the next
side effect. A rerun that finds an incomplete same-day record resumes
from its status — it never draws a new prompt. An unrecoverable
post-publish commit failure raises RecoveryRequired with the
non-secret DA identifiers in the message.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

STATUSES = ("drawn", "submitted", "published", "skipped")
TERMINAL = ("published", "skipped")


class LedgerCommitError(RuntimeError):
    """Ledger transition could not be committed/pushed."""


class RecoveryRequired(RuntimeError):
    """Published on DA but ledger commit failed — manual repair needed."""


def read_ledger(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def entry_for_date(entries: list[dict], date: str) -> dict | None:
    """Latest ledger entry for the given ISO date, or None."""
    todays = [e for e in entries if e.get("date") == date]
    return todays[-1] if todays else None


def used_source_ids(entries: list[dict]) -> set[str]:
    return {e["source_file"] for e in entries if e.get("source_file")}


def append_entry(path: str | Path, entry: dict) -> dict:
    if entry.get("status") not in STATUSES:
        raise ValueError(f"invalid status: {entry.get('status')}")
    if not entry.get("date"):
        entry["date"] = datetime.now(UTC).date().isoformat()
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def commit_push(
    repo_dir: str | Path,
    paths: list[str],
    message: str,
    runner=subprocess.run,
) -> None:
    """git add/commit/pull --rebase/push; raises LedgerCommitError on failure.

    FR-819 concurrency pattern: rebase before push. `runner` is
    injectable so tests can simulate failure at each boundary.
    """
    cmds = [
        ["git", "add", *paths],
        ["git", "commit", "-m", message],
        ["git", "pull", "--rebase", "origin", "main"],
        ["git", "push", "origin", "main"],
    ]
    for cmd in cmds:
        result = runner(cmd, cwd=str(repo_dir), capture_output=True, text=True)
        if result.returncode != 0:
            raise LedgerCommitError(
                f"{' '.join(cmd)} failed: {result.stderr or result.stdout}"
            )


def record_transition(
    repo_dir: str | Path,
    ledger_path: str | Path,
    entry: dict,
    runner=subprocess.run,
    extra_paths: list[str] | None = None,
) -> dict:
    """Append + commit + push one transition. Raises before returning
    so the caller cannot proceed to the next side effect uncommitted."""
    written = append_entry(ledger_path, entry)
    rel = str(Path(ledger_path).resolve().relative_to(Path(repo_dir).resolve()))
    commit_push(
        repo_dir,
        [rel, *(extra_paths or [])],
        f"ledger: {entry['date']} -> {entry['status']}",
        runner=runner,
    )
    return written
