# Feature Request: User-Given Prompt Option

**Priority:** HIGH
**Type:** Feature
**Status:** Judged — APPROVED WITH REVISIONS (2026-08-25); R-1..R-6 folded below
**Effort:** 0.5 day
**Requested:** 2026-08-25
**Depends on:** FR-887 (enforced 2026-08-25 — `run_source="user"` rows);
FR-888 composition optional, only by delegating to its enforced
fan-out primitive (R-6)
**First consumer / first event:** the operator, at the first ad-hoc
generation — a prompt typed at the command line generates immediately,
no corpus draw, no ledger ceremony.

## Summary

Accept an operator-supplied prompt (`--prompt "..."` or `--prompt-file
path`) as an alternative to drawing from the corpus. The user prompt
flows through the same generation boundary (and FR-887 failure
logging, and FR-888 fan-out when combined).

## Value Statement

The corpus is the scheduled pipeline's source; the operator is the
authority. Today there is no way to send an arbitrary prompt through
the pipeline's generation machinery — testing a hypothesis about a
model means writing throwaway Python. A prompt option makes the
operator's intent a first-class input: probe a model's limits, iterate
on phrasing, or generate a one-off, all through the audited boundary
with failures recorded.

## Problem

- `draw_step` is corpus-only; `generate_step` takes a prompt but has no
  operator-facing entry point.
- Ad-hoc generation happens outside the repo's boundaries — unlogged,
  unaudited, results discarded.

## Proposed Solution

*(Judge revisions R-1..R-6 folded.)*

- **Frozen entry point (R-1):** new generation-only CLI
  `scripts/generate.py --prompt "text" | --prompt-file path
  [--model name] [--date YYYY-MM-DD] [--out-dir dir]`. It is OUTSIDE
  the publish graph: it cannot enter `draw_step`, `describe_step`,
  `gate_step`, `publish_step`, `state/published.jsonl`, or DA APIs.
  No workflow changes under this FR.
- **Verbatim semantics (R-4):** the prompt is passed VERBATIM to the
  generation boundary — no rewriting, filtering, or augmentation.
  `--prompt-file` reads UTF-8 text preserving all contents including
  trailing newlines; invalid UTF-8 fails before any provider call or
  file write. Byte-identical string reaches `replicate.run()`.
- **Preflight (R-5):** `--prompt` XOR `--prompt-file`, exactly one
  required; invalid combinations rejected before any side effect.
  Model names validated via existing roster validation before any
  provider call or output write.
- **Output identity (R-2):** deterministic path
  `<out_dir>/<date>-user-<model>.png` for single-model runs (FR-888's
  `<out_dir>/<date>-<model_name>.png` when fan-out is used); parent
  dirs created; no clobbering within one invocation.
- **Ledger boundary (R-3):** success writes only the image artifact;
  a refusal appends/commits exactly one `state/failures.jsonl` row via
  FR-887 (`run_source="user"`, null slot/source_file) and stays red;
  neither path writes `state/published.jsonl` or consumes a slot.
- **FR-888 composition (R-6):** `--all-models`/`--models` wired ONLY by
  delegating to the enforced FR-888 fan-out primitive, preserving its
  preflight, sequential, output-path, and failure-ledger gates — never
  reimplemented here.

## Acceptance Criteria

*(Revised per judgement — supersedes the draft AC-1..AC-5.)*

- [ ] AC-01: `scripts/generate.py --prompt "text"` calls the generation
  boundary with exactly `text`; a mocked provider asserts
  byte-identical prompt delivery to `replicate.run()` input.
- [ ] AC-02: `--prompt-file path` reads UTF-8 text, preserves all file
  contents including trailing newlines, and passes exactly that string
  to `replicate.run()`; invalid UTF-8 fails before any provider call
  or output write.
- [ ] AC-03: `--prompt` and `--prompt-file` are mutually exclusive,
  exactly one is required, and any corpus draw/publish path
  combination is rejected before `draw_step()` or any ledger write.
- [ ] AC-04: A mocked user-prompt provider refusal appends and commits
  exactly one `state/failures.jsonl` row with `run_source="user"`,
  `slot=null`, `source_file=null`, and no full prompt text, then exits
  red per FR-887 two-error semantics.
- [ ] AC-05: A mocked successful user-prompt run writes an image to the
  defined output path and writes no `state/published.jsonl` row,
  consumes no slot, calls no `tools.da_api` function, and does not
  invoke `describe_step`, `gate_step`, or `publish_step`.
- [ ] AC-06: Unknown model names fail through the existing roster
  validation before any provider call or output file write; valid
  pinned models pass through to the generation boundary.
- [ ] AC-07: Repeated or multi-model invocations in one command cannot
  clobber outputs; tests assert the exact output path shape.
- [ ] AC-08: If `--all-models`/`--models` is implemented with this FR,
  it delegates to the enforced FR-888 fan-out primitive and satisfies
  FR-888's ordered preflight, sequential execution, distinct output
  path, failure-ledger, and no-publish gates.
- [ ] AC-09: New `REQ-DD` ids are added to a capability file, and every
  new/changed test carries `@pytest.mark.req(...)` linked to those ids.
- [ ] AC-10: README documents the user-prompt command, prompt-file
  encoding/newline behavior, output location, model/date options,
  failure logging with `run_source="user"`, no-publish/no-slot
  boundary, and FR-888 composition status.

## Constraints

- C-1: Verbatim pass-through after the defined CLI/file decoding
  boundary — no rewriting, softening, filtering, or safety pre-veto
  (gate C-4); provider responses are recorded, not anticipated.
- C-2: No publish-path coupling — no publish graph entry, no slot, no
  `state/published.jsonl`, no DA API (gate C-2).
- C-3: Prompt text goes only to the provider call path — never
  committed to `state/failures.jsonl` or publish/post artifacts
  (gate C-3).
- C-4: FR-887 semantics intact: user refusals stay red; ledger commit
  failures never success-shaped (gate C-5).
- C-5: No workflow/CI/hook/doctrine changes (gate C-7).

## Out of Scope

- Prompt templating/history.
- Publishing user-prompt outputs.
