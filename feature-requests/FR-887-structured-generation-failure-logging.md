# Feature Request: Structured Generation-Failure Logging

**Priority:** HIGH
**Type:** Feature
**Status:** Judged — APPROVED WITH REVISIONS (2026-08-25); R-1..R-5 folded below
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

*(Judge revisions R-1..R-5 folded.)*

- **Boundary (R-1):** the failure row is recorded at `generate_step()`
  (or a wrapper that receives full draw/run context), NOT inside bare
  `generate_image()`. Extend `generate_step(prompt, date, source_file,
  slot, model, run_source)` and the graph args so `date`, `slot`,
  roster `model` name, `slug`, `source_file`, and `run_source` are
  available at the logging boundary.
- **Schema (R-4):** Pydantic `FailureRecord` with frozen semantics:
  `ts` (UTC ISO-8601), `date` (`YYYY-MM-DD`), `slot` (`int | None` —
  None for non-corpus runs), `model` (roster name), `slug`,
  `prompt_sha` (SHA-256 over the exact prompt bytes passed to the
  provider) + `source_file` (`str | None` — None for user/probe),
  `error_class` (`refusal | transport | timeout | unknown`),
  `provider_message` (raw excerpt, capped at 500 chars, with
  secret/token/URL-credential redaction), `run_source`
  (`corpus | user | probe`). Full prompt text is never written.
- **Classification (R-5):** closed contract bound to exception types:
  `httpx.TimeoutException` → `timeout`; other `httpx.HTTPError` /
  transport failures → `transport`; provider refusal keyword set
  (NSFW/flagged/safety) on `GenerationError`/provider messages →
  `refusal`; anything else → `unknown`. A claim, never a silent
  fallback: the raw excerpt is always preserved alongside, and
  unrecognized failures stay `unknown`.
- **Ledger primitive (R-2):** a NEW failure-ledger helper
  (`append_failure_record`) appends to `state/failures.jsonl` and
  commits via `commit_push()` (same add/commit/pull --rebase/push
  discipline) — it does NOT reuse `record_transition()`/`append_entry()`
  and does NOT extend the publish ledger's status machine.
  `state/published.jsonl` remains the DA idempotency ledger only.
- **Two-error semantics (R-3):** record-then-reraise. If writing or
  committing the failure row itself fails, the original generation
  exception remains the primary failure and is re-raised with the
  logging/commit failure attached as explicit context (`raise ... from`
  / exception note). No success-shaped exit is possible; neither error
  is lost.
- Control flow unchanged: log-then-reraise. Retry/routing is FR-886.

## Acceptance Criteria

*(Revised per judgement — supersedes the draft AC-1..AC-5.)*

- [ ] AC-01: A mocked provider refusal during corpus `generate_step`
  appends and commits exactly one `FailureRecord` row to
  `state/failures.jsonl`, then the run exits red by re-raising the
  original generation failure per the R-3 rule.
- [ ] AC-02: The logged corpus-row failure includes `date`, integer
  `slot`, roster `model` name, roster `slug`, `source_file`,
  `prompt_sha`, `error_class="refusal"`, capped/redacted
  `provider_message`, and `run_source="corpus"`; no full prompt text.
- [ ] AC-03: Mocked tests witness `error_class` values `refusal`,
  `transport`, `timeout`, and `unknown`; every branch preserves a
  capped/redacted raw provider excerpt.
- [ ] AC-04: A mocked successful generation writes no row to
  `state/failures.jsonl`.
- [ ] AC-05: Failure-ledger writing is append-only and committed with
  git add/commit/pull --rebase/push discipline equivalent to
  `commit_push()`; it does not add new statuses to
  `state/published.jsonl`.
- [ ] AC-06: A failure while writing or committing the failure row is
  tested and cannot produce a green/success-shaped exit; the original
  provider failure and the logging failure are both inspectable.
- [ ] AC-07: `prompt_sha` is computed from the exact prompt bytes
  passed to the provider, and tests prove the full prompt string is
  absent from the failure row.
- [ ] AC-08: `source_file` and `slot` nullability are tested for
  non-corpus runs, with `run_source="user"` and `run_source="probe"`
  available for FR-889 and FR-888 consumers without implementing those
  FRs here.
- [ ] AC-09: New `REQ-DD` ids are added to a capability file, and every
  new/changed test carries `@pytest.mark.req(...)` linked to them.
- [ ] AC-10: README documents `state/failures.jsonl`, field meanings,
  failure classes, privacy boundary, and that FR-886/FR-888/FR-889
  consume these rows without this FR implementing routing, fan-out, or
  user-prompt entry points.

## Constraints

- C-1: Never swallow the exception — record, then re-raise (judgement
  gate C-2).
- C-2: Full prompt text, secrets, tokens, and unredacted secret-bearing
  provider payloads are never committed to `state/failures.jsonl`
  (gate C-3).
- C-3: Row write is atomic-append + commit, same git discipline as
  `state/published.jsonl` but via its own helper — the publish ledger's
  status enum and resume semantics are untouched (gate C-4).
- C-4: No retries, routing, fan-out, user-prompt CLI, synthetic
  probing, or roster changes under this FR (gate C-5).
- C-5: Workflow/graph changes limited to minimal argument wiring for
  failure context (gate C-6).

## Out of Scope

- Retries, routing, model selection changes (FR-886).
- Synthetic probing (FR-885 — proposed superseded by this + FR-888/889).
