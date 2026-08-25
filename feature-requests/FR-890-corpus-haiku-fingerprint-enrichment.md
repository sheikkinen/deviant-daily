# Feature Request: Corpus Content Fingerprint + Genre Classification (Haiku Enrichment)

**Priority:** HIGH
**Type:** Feature
**Status:** Draft
**Effort:** 1 day
**Requested:** 2026-08-25
**Depends on:** none (carved out of FR-886; FR-886 now depends on this)
**First consumer / first event:** the FR-886 deterministic draw router,
at its first eligibility join after merge; second consumer: corpus
analytics/rotation (genre distribution report), at the first enrichment
run.

## Summary

A yamlgraph **map-node graph** fans all 7,392 corpus prompts across
haiku-class calls and commits three additive columns per row:

1. `content.sexual`: `safe | mature`
2. `content.gore`: `safe | mature`
3. `genre`: single-label closed-set image classification (list below)

One shot per prompt, structured output (Pydantic), resumable, ~$3.
This FR owns the taxonomy; FR-886's router consumes it (FR-885 is
superseded and is not referenced).

## Value Statement

For the draw router (FR-886): mature-prompt × strict-model collisions
waste paid generations; the join needs per-prompt content rungs to
exist at all. For the daily product: the corpus has no genre signal, so
draw variety and analytics are blind — a genre column enables rotation
policy and distribution reporting without any LLM call at draw time.

## Ideal Result

Every corpus row carries a dated fingerprint: two binary content rungs
and one genre label, produced by a witnessed enrichment run, committed
as additive columns with classifier model id. Re-extraction passes them
through untouched. A one-page distribution report shows the corpus
composition by genre × content.

## Problem

- `prompts/corpus.jsonl` (7,392 rows) has no content-class or genre
  fields: `prompt, source_file, local_model, dialect, seed, size,
  created` only.
- FR-886 bundled enrichment with the router and draw integration,
  coupling a ~$3 batch job to a blocked FR; the enrichment has
  independent value (analytics, rotation) and no dependency on the
  tolerance-matrix revision that blocks FR-886.

## Proposed Genre Taxonomy

Grounded in a 2026-08-25 corpus keyword scan (n=7,392) and a 40-prompt
random-sample read (`read_raw_output_first`). Single label, dominant
theme; overlaps resolved by the precedence order below (first match on
tie wins):

| # | Class | Corpus evidence (keyword scan) |
|---|-------|-------------------------------|
| 1 | `fetish` | bondage/rope/submissive/spanking — 16% |
| 2 | `gothic` | vampire/demon/satanic/succubus — 21%; gore/decay terms 9% |
| 3 | `furry` | fox girl/wolf_girl/satyr/anthro — 8% |
| 4 | `scifi` | android/cyborg/biomechanical/neon — 10% |
| 5 | `mythological` | goddess/Kali/Venus/valkyrie — 7% |
| 6 | `fantasy` | sorceress/knight/angel/medieval — 17% |
| 7 | `pinup` | pin-up/boudoir/lingerie/vintage glamour — 10% |
| 8 | `fanart` | recognizable IP/celebrity likeness (Marvel, Disney, named persons) — ~1%, kept despite size because it is policy-relevant for image models |
| 9 | `surreal` | dreamlike/floating/Beksiński-style abstraction |
| 10 | `portrait` | photographic/photoreal portrait without genre framing — photo terms 6% |
| 11 | `other` | junk-drawer cap, see constraint C-6 |

Precedence rationale: fetish and IP signals are routing/policy-relevant
and must not be absorbed by broader genre framing; `fantasy` is last
among the themed classes because it is the widest net.

## Proposed Solution

- **Graph:** `graphs/corpus_fingerprint.yaml` + prompt template — map
  node fans prompts to haiku; per prompt one structured call returning
  `{sexual: safe|mature, gore: safe|mature, genre: <enum>}`. No
  retries; a failed row is recorded as unfingerprinted, not guessed.
- **Enrichment script:** `scripts/enrich_corpus.py` owns writing the
  columns (`content`, `genre`, `fingerprint_date`, `classifier_model`)
  back into `prompts/corpus.jsonl`; batchable and resumable (skips
  already-fingerprinted rows).
- **Extractor pass-through:** `scripts/extract_corpus.py` treats the
  new columns as pass-through on re-extraction.
- **Distribution report:** enrichment run emits genre × content counts
  to stdout/log for the witnessed-run record.

## Acceptance Criteria

- [ ] AC-1: Graph + enrichment script exist; a witnessed run classifies
  the full corpus; columns committed with `fingerprint_date` and
  classifier model id.
- [ ] AC-2: Schema is closed-set: `sexual`/`gore` ∈ {safe, mature},
  `genre` ∈ the 11-class enum; out-of-set output is rejected at the
  boundary (row left unfingerprinted), never coerced.
- [ ] AC-3: Enrichment is additive-only: prompt text unmodified, row
  count invariant (7,392 before == after), verified by test.
- [ ] AC-4: Re-running enrichment skips fingerprinted rows (resumable).
- [ ] AC-5: `extract_corpus.py` passes the new columns through
  (test with a fingerprinted fixture row).
- [ ] AC-6: Distribution report produced; `other` share recorded.
- [ ] AC-7: New REQ-DD ids in a capability file; all new tests
  req-marked.

## Constraints

- C-1: Spend ceiling $5; stop before exceeding.
- C-2: Haiku-class model only; classifier model id recorded per row.
- C-3: Columns additive only; no row mutation or reordering.
- C-4: This FR owns the taxonomy artifact; FR-886 imports it — no
  redeclaration (single source of truth). No FR-885 references.
- C-5: One LLM call per prompt, no retries — a failure is a counted
  unfingerprinted row (FR-886 already routes those conservatively).
- C-6: Junk-drawer cap on `other`: if the witnessed run yields
  `other` > 10%, the run record must include 20 sampled `other`
  prompts read raw, and the taxonomy is revised before the columns
  are committed — `other` must not eat correct answers.

## Out of Scope

- Draw routing / eligibility join (FR-886).
- Model tolerance probing (FR-887/FR-888/FR-889 territory).
- Prompt rewriting or filtering — classification only.
- Multi-label genre or a style/medium axis (single dominant label
  suffices for the named consumers; revisit only with a named consumer
  for the second axis).
