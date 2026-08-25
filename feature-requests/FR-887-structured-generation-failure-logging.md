# Feature Request: Structured Generation-Failure Logging

**Priority:** HIGH
**Type:** Feature
**Status:** Draft
**Effort:** 0.5 day
**Requested:** 2026-08-25
**First consumer / first event:** the operator, at the first refused
generation after merge — the refusal becomes a committed data row
instead of a vanished stack trace. Second consumer: FR-886's router,
which derives per-model tolerance from accumulated failure rows
instead of a purchased probe matrix.

## Summary

Catch every image-generation failure at the `generate_image` boundary
and record it as a typed, committed JSONL row: which model, which
prompt, what class of failure, what the provider said. Failures still
fail the run — nothing is swallowed — but the knowledge stops being
thrown away.

## Value Statement

Every refused generation today is a paid lesson the pipeline
immediately forgets: the exception kills the run and leaves no record
of which model refused which prompt. Accumulated failure rows are
exactly the per-model tolerance data FR-885 planned to buy with a
synthetic probe run — here they arrive free, from real prompts, as a
byproduct of normal and operator-driven runs.

## Problem

- `generate_step` → `generate_image` raises `GenerationError` or a
  provider exception; the run dies red with no structured record.
- Refusals (content-filter), transport errors, and timeouts are
  indistinguishable after the fact.
- No artifact accumulates tolerance knowledge; FR-886's router has no
  organic data source.

## Proposed Solution

- Pydantic `FailureRecord`: `ts`, `date`, `slot` (nullable), `model`
  (roster name), `slug`, `prompt_sha` + `source_file`, `error_class`
  (`refusal | transport | timeout | unknown`), `provider_message`
  (excerpt, capped), `run_source` (`corpus | user | probe`).
- `error_class` from tolerant message matching at the boundary
  (NSFW/flagged/safety keywords → `refusal`; httpx classes →
  `transport`/`timeout`; else `unknown`) — a claim, never a silent
  fallback: the raw excerpt is always preserved alongside.
- Append to `state/failures.jsonl` and commit via the existing
  `record_transition` git pattern BEFORE re-raising — the row survives
  the red run.
- Control flow unchanged: log-then-reraise. Retry/routing is FR-886.

## Acceptance Criteria

- [ ] AC-1: A mocked refusal in `generate_step` produces a committed
  `FailureRecord` row AND still raises (test witnesses both).
- [ ] AC-2: All four `error_class` values witnessed by mocked tests;
  raw provider excerpt preserved in every row.
- [ ] AC-3: Successful generations write nothing.
- [ ] AC-4: New REQ-DD ids; tests req-marked.
- [ ] AC-5: README documents the failure ledger and its consumer path.

## Constraints

- C-1: Never swallow the exception — record, then re-raise.
- C-2: Full prompt text is not written to the failure row (sha +
  source_file suffice; corpus is the lookup).
- C-3: Row write is atomic-append + commit, same discipline as
  `state/published.jsonl`.

## Out of Scope

- Retries, routing, model selection changes (FR-886).
- Synthetic probing (FR-885 — proposed superseded by this + FR-888/889).
