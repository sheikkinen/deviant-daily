# Feature Request: Corpus Content Fingerprinting and Deterministic Draw Routing

**Priority:** HIGH
**Type:** Feature
**Status:** Judged — APPROVED WITH REVISIONS (2026-08-25); R-1..R-7 folded below
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

*(R-1: updated to the post-FR-890 state.)*

- `prompts/corpus.jsonl` (7,392 rows) is fully fingerprinted
  (`content.sexual`, `content.gore`, `fingerprint` — FR-890, enforced
  2026-08-25), but the draw step does not consume those fields: model
  selection is still blind.
- Mature-prompt × strict-model collisions are witnessed as wasted paid
  generations and sanitized duds; each refusal now lands in
  `state/failures.jsonl` (FR-887) but nothing reads it.
- Upstream filtering removed the extremes (gore/porn dropped at
  extraction); the surviving mid-spectrum is where model tolerance
  diverges — labeled now, still unrouted.

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
- **Absent ledger (R-4):** a missing `state/failures.jsonl` is an
  EMPTY evidence set — not an error, not permission to invent data
  (FR-887 creates the file only on first failure).
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
- **Determinism (R-3):** randomness is an explicit input — `route(...)`
  accepts an injected `rng: random.Random` and applies the existing
  selection rule `rng.choice(sorted(eligible))` (same shape as
  `choose_model`). Same inputs including the RNG → same output.
  Cold-start neutrality is defined against the same injected RNG:
  with empty evidence, `route(fp, {}, roster, rng)` equals
  `choose_model`'s pick with an equally-seeded RNG.
- `route(...)` raises a typed exclusion (`UnroutablePrompt`) when the
  eligible set is empty — the prompt is skipped, never burned.
- **Taxonomy boundary (R-6):** `data/corpus_fingerprint_taxonomy.yaml`
  is the runtime source of truth; the router validates corpus
  `content` values against it and never redeclares the axes. Missing,
  invalid, or partial fingerprints route as maximally mature
  `(mature, mature)` with a counted reason.

### 4. Draw integration

- **Model binding flow (R-2):** `draw_step` gains a `model` argument
  wired from the workflow input in `graph.yaml`. Non-empty pin →
  routing bypassed, pin recorded as the binding. Otherwise `draw_step`
  routes BEFORE committing the drawn row; the committed row records
  the bound model; `generate_step` consumes `drawn.model` and does NOT
  re-select — binding authority lives at the draw boundary.
- **Unroutable skip algorithm (R-5):** draw iterates candidates in the
  existing draw order; an unroutable candidate is skipped WITHOUT any
  ledger write (no drawn row, no failure row — counted reasons are
  returned/logged only, per C-2), bounded by the remaining unused
  corpus. If every remaining candidate is unroutable, `draw_step`
  raises the typed exclusion and the run exits red with zero ledger
  writes. Tests witness: one skipped candidate, all-unroutable, and
  no ledger transition for skipped candidates.

## Acceptance Criteria

*(Revised per judgement — supersedes the draft AC-1..AC-8.)*

- [ ] AC-01: The FR text reflects the enforced FR-890 state: corpus
  rows already carry `content`/`fingerprint`; this FR only consumes
  those fields for routing.
- [ ] AC-02: `refusal_evidence(failure_rows, corpus)` joins refusal
  rows to corpus rows by `prompt_sha`, uses the FR-890 `(sexual, gore)`
  tuple verbatim, ignores transport/timeout/unknown rows, treats an
  absent `state/failures.jsonl` as empty, and counts non-corpus prompt
  hashes without guessing.
- [ ] AC-03: `eligible_models(fingerprint, evidence, roster)` is pure
  and unit-tested: zero refusal evidence admits a model, one witnessed
  refusal for the exact tuple excludes it, other tuples do not exclude
  it, and an empty eligible set raises a typed unroutable exclusion.
- [ ] AC-04: Route selection is deterministic for declared inputs via
  an injected RNG/seed; cold-start routing with the same selection
  input is identical to today's blind roster pick.
- [ ] AC-05: `draw_step` routes before committing the drawn row, skips
  unroutable candidates without writing them to `state/published.jsonl`
  or `state/failures.jsonl`, records the bound model on the committed
  drawn row, and returns that binding for generation.
- [ ] AC-06: A mocked end-to-end draw test witnesses a mature prompt
  bypassing a refusal-witnessed model and binding to an eligible model
  before `generate_step`; `generate_step` uses the draw-bound model
  and does not re-select a different model.
- [ ] AC-07: Operator-pinned `--model`/workflow `model` bypasses
  routing at draw time, records the pinned binding, and still allows
  any later provider refusal to be logged by FR-887.
- [ ] AC-08: Missing, invalid, or partial corpus fingerprints route as
  maximally mature `(mature, mature)` with a counted reason; taxonomy
  drift from `data/corpus_fingerprint_taxonomy.yaml` fails a test.
- [ ] AC-09: No LLM call, provider call, or network call exists in the
  draw routing path; router tests run offline.
- [ ] AC-10: New REQ-DD ids in a capability file cover routing/evidence
  behavior, and every new or changed test carries `@pytest.mark.req`.
- [ ] AC-11: README documents the routing contract, failure-evidence
  join, cold-start behavior, pinned-model bypass, unroutable skip
  behavior, and that routing does not write the failure ledger.

## Constraints

- C-1: Draw-time routing is a pure function — no network, no LLM
  (gate: router tests run offline).
- C-2: Only `error_class="refusal"` rows are tolerance evidence;
  routing never writes to any ledger — skipped candidates leave zero
  ledger rows (gates C-4/C-5).
- C-3: Cold-start neutrality: with an empty failure ledger and the
  same injected RNG, routing behavior is identical to today's blind
  pick (witnessed by test).
- C-4: No roster changes, no model admission/retirement.
- C-5: Taxonomy single-sourced from
  `data/corpus_fingerprint_taxonomy.yaml` — never redeclared (gate C-6).
- C-6: The draw-bound model IS the generation model — production must
  not route and then independently `choose_model()` again (gate C-3).

## Out of Scope

- Corpus enrichment / fingerprint production (FR-890).
- Model roster changes (separate decision).
- Re-probing models (FR-887/FR-888/FR-889 territory).
- Prompt rewriting / softening to fit a model (routing only).
