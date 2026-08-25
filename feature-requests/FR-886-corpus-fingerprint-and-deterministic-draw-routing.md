# Feature Request: Corpus Content Fingerprinting and Deterministic Draw Routing

**Priority:** HIGH
**Type:** Feature
**Status:** Draft — supply-side rewritten 2026-08-25 around organic
refusal evidence; ready for judgement
**Effort:** 1–2 days
**Requested:** 2026-08-24
**Depends on:** FR-890 (corpus fingerprint enrichment — **DONE
2026-08-25**, 7392/7392 rows enriched); FR-887/FR-888/FR-889 **all
enforced 2026-08-25** — outcome evidence now accumulates in
`state/failures.jsonl`; FR-885 superseded
**First consumer / first event:** the daily draw step, at the first
scheduled run after merge — every drawn prompt is dispatched to a model
not yet witnessed refusing its content class, instead of a blind
roster pick.

## Decisions (operator, 2026-08-25)

- **Cold start:** a (model, content-tuple) cell with no refusal
  evidence is ELIGIBLE. Routing degrades gracefully from today's blind
  pick toward measured exclusion as refusals accumulate — no seeding
  run required.
- **Evidence floor:** ONE witnessed `error_class="refusal"` row
  excludes the cell. Transport/timeout/unknown rows never exclude.
- **Routing site:** `draw_step`, BEFORE the drawn row is committed — an
  unroutable prompt is skipped with a counted reason, never burns a
  slot. The drawn row records the model binding.
- **Operator pin:** an explicitly pinned `--model`/workflow `model`
  input bypasses routing — the operator is the authority; the refusal,
  if any, still lands in the failure ledger as evidence.

## Summary

Replace the blind roster pick at draw time with a **deterministic
evidence join**: the FR-890 corpus fingerprint ({sexual, gore} ×
safe/mature) on the demand side, accumulated `state/failures.jsonl`
refusal rows (FR-887/888/889) on the supply side. A model witnessed
refusing a content tuple is excluded for prompts carrying that tuple;
everything else stays eligible. No LLM call at draw time, no purchased
probe matrix — the evidence arrives free from real runs.

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
`route(prompt_fingerprint, refusal_evidence, roster) -> model` — same
inputs, same output, testable without any network call. A prompt every
roster model has refused is never drawn (excluded deterministically,
with a counted reason), never burned live. Each production refusal
makes the next draw smarter, automatically.

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

### 2. Refusal evidence join (supply side)

- Evidence source: `state/failures.jsonl` rows with
  `error_class="refusal"` ONLY — transport/timeout/unknown are
  operational noise, never tolerance signal.
- Attribution: a refusal is joined back to its corpus row via
  `prompt_sha` (FR-887 hashes the exact prompt bytes; the corpus is
  the lookup). The refusal witnesses the prompt's full content tuple
  `(sexual, gore)` — no per-axis attribution is invented: the evidence
  cell is `(model, content_tuple)`, four tuples total.
- Rows whose `prompt_sha` matches no corpus row (user/probe prompts of
  ad-hoc text) carry no fingerprint and are skipped by the join with a
  counted reason — never guessed.

### 3. Deterministic router

- `tools/route.py`:
  `refusal_evidence(failure_rows, corpus) -> dict[(model, tuple), int]`
  and `eligible_models(fingerprint, evidence, roster) -> list[str]` —
  a model is eligible iff its `(model, tuple)` cell has ZERO witnessed
  refusals (Decisions: floor = 1, unknown = eligible).
- `route(...)` picks among eligible with the existing draw's selection
  rule (preserve current rotation/randomness *within* the eligible
  set); raises a typed, counted exclusion when the eligible set is
  empty — the prompt is skipped, never burned.

### 4. Draw integration

- `draw_step` routes BEFORE committing the drawn row; the row records
  the bound model; `generate_step` consumes the binding.
- An operator-pinned model bypasses routing (Decisions).
- Prompts without a fingerprint are routed as maximally mature
  `(mature, mature)` — conservative — until enrichment covers them.

## Acceptance Criteria

- [ ] AC-1: FR-890 enforced — corpus columns present (dependency
  witness, not re-implemented here).
- [ ] AC-2: Evidence join uses `prompt_sha` and the FR-890 taxonomy
  verbatim; a test fails if the taxonomies drift apart; non-corpus
  `prompt_sha` rows are skipped with a counted reason.
- [ ] AC-3: `eligible_models` is pure and fully unit-tested: model with
  zero refusal evidence admitted (cold start), model with one witnessed
  refusal for the tuple excluded, transport/timeout/unknown rows never
  exclude, empty eligible set raises typed exclusion.
- [ ] AC-4: Draw step routes via the join BEFORE committing the drawn
  row; a mocked end-to-end test witnesses a mature prompt bypassing a
  refusal-witnessed model and landing on an unwitnessed one; the drawn
  row records the model binding.
- [ ] AC-5: Unfingerprinted prompts route as maximally mature (test);
  operator-pinned model bypasses routing (test).
- [ ] AC-6: No LLM call in the draw path (test: router works offline).
- [ ] AC-7: New REQ-DD ids in a capability file; all new tests
  req-marked.
- [ ] AC-8: README documents the routing contract, the evidence join,
  and the cold-start behavior.

## Constraints

- C-1: Draw-time routing is a pure function — no network, no LLM.
- C-2: Only `error_class="refusal"` rows are tolerance evidence;
  routing never writes to any ledger.
- C-3: Cold-start neutrality: with an empty failure ledger, routing
  behavior is identical to today's blind pick (witnessed by test).
- C-4: No roster changes, no model admission/retirement.
- C-5: Taxonomy single-sourced from the FR-890 artifact.

## Out of Scope

- Corpus enrichment / fingerprint production (FR-890).
- Model roster changes (separate decision).
- Re-probing models (FR-887/FR-888/FR-889 territory).
- Prompt rewriting / softening to fit a model (routing only).
