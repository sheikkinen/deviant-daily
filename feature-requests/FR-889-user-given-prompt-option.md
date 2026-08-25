# Feature Request: User-Given Prompt Option

**Priority:** HIGH
**Type:** Feature
**Status:** Draft
**Effort:** 0.5 day
**Requested:** 2026-08-25
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

- Operator entry point (new `scripts/generate.py` or extend the
  existing dispatch): `--prompt "text"` | `--prompt-file path`,
  mutually exclusive with corpus draw; composes with FR-888
  `--all-models`/`--models`.
- The prompt is passed VERBATIM to the generation boundary — no
  rewriting, no filtering, no augmentation. The provider's own
  response is the only gate, and a refusal becomes an FR-887 row
  (`run_source="user"`).
- Generation-only path: no publish, no slot, no ledger row (same fence
  as FR-888 C-2).

## Acceptance Criteria

- [ ] AC-1: `--prompt` generates via mocked provider with the exact
  given text — byte-identical prompt reaches `replicate.run` (test).
- [ ] AC-2: `--prompt-file` reads and passes file contents verbatim
  (test).
- [ ] AC-3: Mutual exclusion with corpus draw enforced (test).
- [ ] AC-4: A mocked refusal of a user prompt produces an FR-887 row
  with `run_source="user"` (test).
- [ ] AC-5: New REQ-DD ids; tests req-marked; README documents usage.

## Constraints

- C-1: Verbatim pass-through — the tool does not alter, soften, or
  veto the operator's prompt; provider responses are recorded, not
  anticipated.
- C-2: No publish-path coupling.

## Out of Scope

- Prompt templating/history.
- Publishing user-prompt outputs.
