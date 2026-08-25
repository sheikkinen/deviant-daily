# Feature Request: Generate With All Selected Providers (Fan-Out)

**Priority:** HIGH
**Type:** Feature
**Status:** Judged — APPROVED WITH REVISIONS (2026-08-25); R-1..R-6 folded below
**Effort:** 0.5–1 day
**Requested:** 2026-08-25
**Depends on:** FR-887 (failure rows are the point of the exercise —
enforced 2026-08-25); FR-889 for the operator CLI surface (R-1: until
FR-889 is enforced, only the callable fan-out primitive + tests are
authorized — CLI activation is deferred and documented as such)
**First consumer / first event:** the operator, at the first comparison
run — one prompt, every active model, side-by-side outputs plus a
failure row for every model that refused it.

## Summary

Add a fan-out mode: run one prompt through **all** roster models (or an
explicit subset) in a single invocation, saving each output to a
distinct path and recording each failure via FR-887. One prompt in →
N images and/or N failure rows out.

## Value Statement

Per-model tolerance and style differences are only observable by
sending the same prompt everywhere. Today `generate_step` picks exactly
one model; comparing five models means five manual runs with five
manual model overrides. Fan-out makes the comparison — and the failure
data it generates — a single command. Combined with FR-887 and FR-889
this is empirical tolerance probing with real corpus prompts at
roster prices, replacing FR-885's synthetic probe harness.

## Problem

- `generate_step(prompt, date, model)` is strictly one-model.
- No entry point exists to run a prompt across the roster; tolerance
  comparisons are manual and unrecorded.

## Proposed Solution

*(Judge revisions R-1..R-6 folded.)*

- **Fan-out primitive (R-2, R-6):** new focused module `tools/fanout.py`:
  `generate_all(prompt, date, models, out_dir, runner=...) ->
  list[GenerationOutcome]` — sequential loop over the selected roster
  entries. `GenerationOutcome` is typed: roster `model` name, `slug`,
  `status` (`ok | failed`), and exactly one of `path` or
  `failure: FailureRecord`. One outcome per selected model, in
  selection order.
- **Output identity (R-2):** path is a pure function of
  `(out_dir, date, model_name)` → `<out_dir>/<date>-<model_name>.png`;
  parent dirs created; model names validated before path construction;
  no clobbering within one run.
- **Preflight selection (R-3):** the full model list resolves up front
  from the active roster BEFORE any provider call or file write:
  all-models = every active roster entry in roster order; explicit
  subset = exactly those names in the given order; duplicate names
  fail fast; unknown names fail fast with the valid active list.
- **Failure semantics (R-4):** per-model provider failure is caught and
  becomes `failed(FailureRecord)` ONLY after the FR-887 row
  (`run_source="probe"`) is successfully appended+committed; later
  models continue. If the failure-ledger write/commit itself fails,
  the fan-out run aborts red with both errors inspectable — it is
  never treated as an ordinary refusal.
- **CLI surface (R-1):** deferred to FR-889's operator entry point.
  This FR ships the callable primitive and tests only; `--all-models` /
  `--models a,b,c` activate when FR-889's `--prompt` entry point is
  enforced. No `--prompt`/`--prompt-file` implementation here.
- **Publish boundary (R-5):** fan-out writes no `state/published.jsonl`
  rows, calls no DeviantArt API, consumes no slot — generation only.

## Acceptance Criteria

*(Revised per judgement — supersedes the draft AC-1..AC-5.)*

- [ ] AC-01: A mocked fan-out over three valid active roster models
  where model 2 raises a provider refusal generates outputs for models
  1 and 3, appends exactly one `state/failures.jsonl` row with
  `run_source="probe"`, and returns three ordered `GenerationOutcome`
  values.
- [ ] AC-02: All-models selection resolves to every usable active
  roster model in deterministic order before generation begins.
- [ ] AC-03: Explicit subset selection honors the specified
  deterministic order; any unknown model name fails before the first
  provider call or file write and reports the valid active list.
- [ ] AC-04: Duplicate model names in an explicit subset fail fast
  before generation.
- [ ] AC-05: Fan-out writes no rows to `state/published.jsonl`, calls
  no `tools.da_api` function, and consumes no slot; mocked tests fail
  if any DeviantArt publish path is touched.
- [ ] AC-06: Each successful selected model writes to a distinct output
  path derived from `(out_dir, date, model_name)`; a test proves two
  successful models cannot clobber each other.
- [ ] AC-07: If failure-ledger append/commit fails for a model failure,
  the fan-out run exits red with the original provider failure and the
  ledger failure both inspectable; it does not continue and does not
  return a success-shaped outcome list.
- [ ] AC-08: `GenerationOutcome` is typed and includes model name,
  slug, status, and exactly one of output path or `FailureRecord`;
  tests assert one outcome per selected model when ledger writes
  succeed.
- [ ] AC-09: Operator CLI documentation and tests are present only when
  an enforced entry point exists; FR-889 not yet enforced → this FR
  documents the callable fan-out primitive and explicitly defers CLI
  activation.
- [ ] AC-10: New `REQ-DD` ids are added to a capability file, and every
  new/changed test carries `@pytest.mark.req(...)` linked to those ids.
- [ ] AC-11: README documents the comparison workflow, output
  directory/path shape, failure-row behavior, no-publish boundary, and
  the dependency relationship with FR-889.

## Constraints

- C-1: Sequential execution (rate limits, spend visibility); no
  parallelism (gate C-3).
- C-2: Publish pipeline untouched — no `state/published.jsonl` rows,
  no DA API, no slot identity (gates C-5/C-6).
- C-3: Failure handling delegates to FR-887; no duplicate mechanism;
  failed outcomes only after the row is committed (gate C-4).
- C-4: No FR-889 entry-point implementation under this FR (gate C-2).
- C-5: Model subset validation completes before the first provider
  call or output write (gate C-7).

## Out of Scope

- Publishing fan-out outputs (operator picks manually if desired).
- Cost caps/budget tracking (spend is operator-visible per run).
- Parallel execution.
