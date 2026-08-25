# Feature Request: Generate With All Selected Providers (Fan-Out)

**Priority:** HIGH
**Type:** Feature
**Status:** Draft
**Effort:** 0.5–1 day
**Requested:** 2026-08-25
**Depends on:** FR-887 (failure rows are the point of the exercise)
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

- `tools/generate.py`: `generate_all(prompt, models, out_dir) ->
  list[GenerationOutcome]` — sequential loop over the selected roster
  entries; per-model outcome `ok(path) | failed(FailureRecord)`; one
  model's failure never aborts the others.
- Output naming: `<out_dir>/<date>-<model_name>.png`.
- CLI surface: `--all-models` / `--models a,b,c` on the operator entry
  point (FR-889's `--prompt` composes with it).
- Fan-out runs are `run_source="probe"` in failure rows (extends the
  FR-887 enum) and DO NOT touch the publish ledger — generation only,
  no publish, no slot consumption.

## Acceptance Criteria

- [ ] AC-1: Mocked fan-out over 3 models where model 2 refuses:
  models 1 and 3 still produce outputs; exactly one FailureRecord row;
  outcome list carries all three (test).
- [ ] AC-2: `--models` subset selection honored; unknown name fails
  fast with the valid list (test).
- [ ] AC-3: Fan-out writes no ledger rows and calls no DA API (test).
- [ ] AC-4: Distinct output path per model, no clobbering (test).
- [ ] AC-5: New REQ-DD ids; tests req-marked; README documents the
  comparison workflow.

## Constraints

- C-1: Sequential execution (rate limits, spend visibility); no
  parallelism until a measured need exists.
- C-2: Publish pipeline untouched — fan-out is a generation-only path.
- C-3: Failure handling delegates to FR-887; no duplicate mechanism.

## Out of Scope

- Publishing fan-out outputs (operator picks manually if desired).
- Cost caps/budget tracking (spend is operator-visible per run).
- Parallel execution.
