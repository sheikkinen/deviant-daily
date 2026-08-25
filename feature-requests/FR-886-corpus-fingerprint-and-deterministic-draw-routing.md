# Feature Request: Corpus Content Fingerprinting and Deterministic Draw Routing

**Priority:** HIGH
**Type:** Feature
**Status:** Draft — blocked pending supply-side revision
**Effort:** 1–2 days
**Requested:** 2026-08-24
**Depends on:** FR-890 (corpus fingerprint enrichment — carved out
2026-08-25); FR-887/FR-888/FR-889 outcome evidence; FR-885 superseded
**First consumer / first event:** the daily draw step, at the first
scheduled run after merge — every drawn prompt is dispatched to a model
measured to tolerate it, instead of a blind roster pick.

**Revision required before judgement:** the demand side is now FR-890
(corpus fingerprint); the supply-side tolerance-matrix contract below
must still be replaced with the general outcome evidence produced by
FR-887/FR-888/FR-889. Do not judge or enforce this draft while the
stale matrix references remain.

## Summary

Replace the blind roster pick at draw time with a **deterministic
table join** over the FR-890 corpus fingerprint ({sexual, gore} ×
safe/mature): prompt fingerprint ≤ model tolerance on every axis →
eligible; pick among eligible. No LLM call at draw time.

## Value Statement

The corpus leans mature and models differ sharply in what they accept.
Today the draw picks a roster model with zero knowledge of either side,
so mature prompts routinely hit content-strict models: a refusal wastes
a paid generation, a silent sanitization burns the daily slot with a
dud. Gore and porn were already filtered out upstream — what remains is
the mid-spectrum (suggestive/mature) where per-model tolerance actually
varies, which is exactly the band a measured join resolves and guessing
does not.

## Ideal Result

Every prompt in the corpus carries a dated content fingerprint in the
FR-890 taxonomy. The draw step is a pure function
`route(prompt_fingerprint, tolerance_matrix, roster) -> model` — same
inputs, same output, testable without any network call. A prompt no
roster model tolerates is never drawn (excluded deterministically, with
a counted reason), never burned live.

## Problem

- `prompts/corpus.jsonl` (7,392 rows) has **no content-class fields**:
  `prompt, source_file, local_model, dialect, seed, size, created` only.
- Draw-time model selection is blind; mature-prompt × strict-model
  collisions are witnessed as wasted paid generations and sanitized
  duds.
- Upstream filtering removed the extremes (gore/porn dropped at
  extraction), but the surviving mid-spectrum is where model tolerance
  diverges — and it is unlabeled.

## Proposed Solution

### 1. Corpus fingerprinting (demand side) — FR-890

Carved out to **FR-890** (2026-08-25): a yamlgraph map graph classifies
all prompts into `content: {sexual: safe|mature, gore: safe|mature}` +
`genre` and commits them as additive corpus columns. This FR consumes
those columns; the taxonomy is owned by FR-890 (single source of
truth), not redeclared here. FR-885's {nudity, sexual, gore} × 3-rung
ladder is superseded.

### 2. Deterministic router

- `tools/route.py`: `eligible_models(fingerprint, matrix, roster) ->
  list[str]` — a model is eligible iff for every class, matrix outcome
  at the prompt's rung is `ok` (not sanitized / refused /
  refused-by-policy; `error` cells are void and count as unknown →
  policy decision below).
- `route(...)` picks among eligible with the existing draw's selection
  rule (preserve current rotation/randomness *within* the eligible
  set); raises a typed, counted exclusion when the eligible set is
  empty — the prompt is skipped, never burned.
- `error`/unknown cells: **conservative default** — treat as not
  tolerating (exclude), so a stale or partial matrix degrades toward
  fewer wasted generations, never more.

### 3. Draw integration

- The draw step consumes the router; prompts without a fingerprint are
  routed as if maximally mature (conservative) until enrichment
  completes.

## Acceptance Criteria

- [ ] AC-1: FR-890 enforced — corpus columns present (dependency
  witness, not re-implemented here).
- [ ] AC-2: Fingerprint rungs use the FR-890 taxonomy verbatim; a test
  fails if the taxonomies drift apart.
- [ ] AC-3: `eligible_models` is pure and fully unit-tested: tolerant
  model admitted, strict model excluded, sanitized excluded,
  error-cell excluded (conservative), empty-set raises typed exclusion.
- [ ] AC-4: Draw step routes via the join; a mocked end-to-end test
  witnesses a mature prompt bypassing a strict model and landing on a
  tolerant one.
- [ ] AC-5: Unfingerprinted prompts route as maximally mature (test).
- [ ] AC-6: No LLM call in the draw path (test: router works offline).
- [ ] AC-7: New REQ-DD ids in a capability file; all new tests
  req-marked.
- [ ] AC-8: README documents the routing contract and the enrichment
  re-run procedure.

## Constraints

- C-1: Draw-time routing is a pure function — no network, no LLM.
- C-2: (moved to FR-890 with the enrichment.)
- C-3: (moved to FR-890 with the enrichment.)
- C-4: No roster changes, no model admission/retirement.
- C-5: Taxonomy single-sourced from the FR-890 artifact.

## Out of Scope

- Corpus enrichment / fingerprint production (FR-890).
- Model roster changes (separate decision).
- Re-probing models (FR-887/FR-888/FR-889 territory).
- Prompt rewriting / softening to fit a model (routing only).
