# Feature Request: Corpus Content Fingerprinting and Deterministic Draw Routing

**Priority:** HIGH
**Type:** Feature
**Status:** Draft
**Effort:** 1–2 days
**Requested:** 2026-08-24
**Depends on:** FR-885 (tolerance matrix — the supply side of the join)
**First consumer / first event:** the daily draw step, at the first
scheduled run after merge — every drawn prompt is dispatched to a model
measured to tolerate it, instead of a blind roster pick.

## Summary

Classify every corpus prompt into the **same content taxonomy FR-885
probes models with** ({nudity, sexual, gore} × severity rung), commit
the classification as corpus columns, and replace the blind roster pick
at draw time with a **deterministic table join**: prompt fingerprint ≤
model tolerance on every axis → eligible; pick among eligible. No LLM
call at draw time.

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
FR-885 taxonomy. The draw step is a pure function
`route(prompt_fingerprint, tolerance_matrix, roster) -> model` — same
inputs, same output, testable without any network call. A prompt no
roster model tolerates is never drawn (excluded deterministically, with
a counted reason), never burned live.

## Problem

- `prompts/corpus.jsonl` (7,392 rows) has **no content-class fields**:
  `prompt, source_file, local_model, dialect, seed, size, created` only.
- Draw-time model selection is blind; mature-prompt × strict-model
  collisions are witnessed as wasted paid generations and sanitized
  duds (FR-885 Problem section).
- Upstream filtering removed the extremes (gore/porn dropped at
  extraction), but the surviving mid-spectrum is where model tolerance
  diverges — and it is unlabeled.

## Proposed Solution

### 1. Corpus fingerprinting (demand side) — yamlgraph map graph

- A yamlgraph graph with a **map node** fans the 7,392 prompts across
  haiku-class calls: per prompt, per class ({nudity, sexual, gore}),
  a rung on the **identical ladder FR-885 uses** (safe / suggestive /
  mature). Closed-set structured output (Pydantic), one shot, no
  retries.
- Estimated spend ≈ $3 (haiku, short prompts). Batchable/resumable.
- Output committed as new corpus columns:
  `content: {nudity: rung, sexual: rung, gore: rung}` +
  `fingerprint_date` + classifier model id. Extractor
  (`scripts/extract_corpus.py`) treats them as pass-through on future
  re-extractions; a separate enrichment script owns them.
- Taxonomy is imported from the FR-885 artifact (single source of
  truth), not redeclared.

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

- [ ] AC-1: Enrichment graph + script exist; a witnessed run classifies
  the full corpus; columns committed with date + classifier id.
- [ ] AC-2: Fingerprint rungs use the FR-885 ladder verbatim; a test
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
- C-2: Enrichment spend ceiling $5; stop before exceeding.
- C-3: Corpus prompt text is never modified by enrichment — columns
  are additive only; row count is invariant (7,392 before == after).
- C-4: No roster changes, no model admission/retirement (FR-885
  boundary honored).
- C-5: Taxonomy single-sourced from the FR-885 probe artifact.

## Out of Scope

- Model roster changes (separate decision, informed by FR-885 matrix).
- Re-probing models (FR-885 owns the matrix lifecycle).
- Prompt rewriting / softening to fit a model (routing only).
