# Feature Request: Corpus v2 — re-extract signed.log with prompt dialect and generation metadata

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Proposed
**Effort:** 0.5 days
**Requested:** 2026-08-24
**First consumer / first event:** `tools/corpus.py` draw step, at the first
scheduled run after merge — a roster model receives a prompt whose dialect
(prose vs booru-tags) is known, instead of a blind draw that feeds
`score_5, score_4`-era tag strings to prose-native models (recraft,
nano-banana-2).

## Summary

Rebuild `prompts/corpus.jsonl` from the canonical source log
(`~/Documents/deviant-working/signed.log`, 13,635 unique image blocks,
9,041 with full A1111 `parameters:` payloads) keeping the metadata the v1
extraction dropped: local model name (→ prompt dialect), seed, size,
creation date. Recover generation ids for the 1,937 rows currently keyed
`unknown`.

## Value Statement

The daily pipeline stops feeding tag-dialect prompts to prose-native
roster models, and the corpus dedup contract becomes honest — both from
data we already own, no new generation cost.

## Problem

Two defects trace to the v1 extraction keeping only `{prompt, source_file}`:

1. **Dialect blindness.** signed.log records which local model each prompt
   was authored for: flux-hyp16 (5,831 blocks — natural-language prose
   dialect) vs autismmixSDXL_autismmixPony + SDXL variants (~3,200 blocks —
   booru-tag dialect; the `Negative prompt: score_5, score_4` fingerprint,
   3,117 occurrences). Roster models are prose-native; a tag-dialect draw
   is a silent quality tax on ~35% of the corpus, invisible in the ledger
   because generation still "succeeds."

2. **Dishonest dedup keys.** 1,937 of 5,893 corpus rows carry
   `source_file: "unknown"`; `corpus.row_id()` patches this with a content
   hash. The log carries the original filename (with generation id and
   seed) for every block — the ids are recoverable, the patch is
   downstream compensation for a boundary defect (`downstream_fix`).

Raw-record verification done 2026-08-24 (session log): block format is
`magick identify -verbose` dumps; `parameters:` payload carries prompt,
negative prompt, Steps/Sampler/CFG/Seed/Size/Model; and
`~/Documents/src/prompt-forge/signed.log` is a **strict subset** (0 unique
blocks via `comm -13` on sorted file ids) — exactly one source of truth.

## Ideal Result

`prompts/corpus.jsonl` rows carry everything the draw and future
per-model optimization need — `prompt, source_file, dialect, local_model,
seed, size, created` — extracted once at the boundary where the log
enters the repo; `row_id()`'s unknown-hash branch is nearly dead; the
draw can filter or restyle by dialect with a one-line change.

## Proposed Solution

One extractor script + one corpus regeneration, normalizing at the boundary:

**`tools/extract_corpus.py`** (new, ~120 lines):
- Parse signed.log blocks (`==== File:` delimiter; skip `==== Signed:`
  duplicates), pull `parameters:` payload per block.
- Emit corpus v2 rows: `prompt, source_file, local_model, dialect, seed,
  size, created`.
- `dialect` derived mechanically, no LLM: `tags` when local_model matches
  the Pony/SDXL family OR negative prompt matches the `score_\d` family;
  else `prose`. (LLM classification of subject/safety is out of scope —
  separate FR if a consumer appears.)
- Apply the same keep/drop filter v1 used, so v2 is auditable against v1.

**`tools/corpus.py`**: no draw-behavior change in this FR. `row_id()`
unchanged (hash branch remains for any residual unknowns). Dialect-aware
draw/restyle is the follow-up FR once engagement data justifies a policy.

**Migration invariant:** every v1 row's prompt appears in v2 (superset
check), and every previously-published ledger `source_file` id still
matches a v2 row — dedup history must survive regeneration.

## Acceptance Criteria

- [ ] `python tools/extract_corpus.py <signed.log>` regenerates
      `prompts/corpus.jsonl` with the 7-field schema.
- [ ] All 5,893 v1 prompts present in v2 (superset test on prompt text).
- [ ] All ledger `source_file` ids used to date resolve against v2 rows
      (no-repeat contract AC-12 unbroken; test with the real ledger).
- [ ] `unknown` source_file count strictly below v1's 1,937; final count
      recorded in this FR on completion.
- [ ] Every row has `dialect ∈ {prose, tags}`; spot-check test: a row with
      `Model: autismmixSDXL_*` is `tags`, a `flux-hyp16` row is `prose`.
- [ ] `==== Signed:` blocks excluded (no signed-duplicate rows).
- [ ] Tests added (parser on a fixture excerpt of signed.log, not the
      1.4M-line original); README corpus section updated.

## Alternatives Considered

- **LLM map-graph classification of all 5,893 prompts** (subject, DA-safety
  pre-score): deferred — dialect is derivable mechanically from metadata;
  LLM enrichment has no consumer until a draw policy exists.
- **Ingest prompt-forge/signed.log too:** rejected — proven strict subset.
- **Pixel statistics as engagement priors:** rejected — no consumer,
  `growth_as_default`.
- **Fix dialect at draw time with per-prompt heuristics:** rejected —
  `downstream_fix`; the model attribution exists at the source boundary.

## Related

- `tools/corpus.py` (UNKNOWN workaround this FR shrinks)
- FR-826 (pipeline + no-repeat contract AC-12)
- eac6d5a (recraft roster addition — first prose-native model whose draws
  this improves)
- Session raw-read evidence: 2026-08-24 yamlgraph session, signed.log
  block samples + subset proof

## Judgement (pending)
