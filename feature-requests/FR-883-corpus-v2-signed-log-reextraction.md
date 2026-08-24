# Feature Request: Corpus v2 — re-extract signed.log with prompt dialect and generation metadata

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Completed 2026-08-24 (enforced; see Implementation Record)
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

Raw-record verification (R-1): a committed sanitized fixture
`tests/fixtures/signed_log_excerpt.txt` (deliverable D-3) evidences the
block shapes this FR depends on — one `==== File:` block with a full
`parameters:` payload (prompt, Negative prompt, Steps, Sampler, CFG,
Seed, Size, Model), one `==== Signed:` duplicate block, one
`flux-hyp16` (prose) example, and one `autismmixSDXL_*` /
`score_\d`-negative (tags) example. Raw private corpus data is never
committed. Additionally verified on the operator-local raw log:
`~/Documents/src/prompt-forge/signed.log` is a **strict subset** of
`~/Documents/deviant-working/signed.log` (0 unique blocks via `comm -13`
on sorted file ids) — exactly one source of truth, stated here as an
operator-machine fact, not consumable evidence.

## Ideal Result

`prompts/corpus.jsonl` rows carry everything the draw and future
per-model optimization need — `prompt, source_file, dialect, local_model,
seed, size, created` — extracted once at the boundary where the log
enters the repo; `row_id()`'s unknown-hash branch is nearly dead; the
draw can filter or restyle by dialect with a one-line change.

## Proposed Solution

Extend the existing extractor (R-2 — no duplicate surface) + one corpus
regeneration, normalizing at the boundary:

**`scripts/extract_corpus.py`** (extend the existing parser):
- Keep the existing `==== File:` block parsing, sanitization, blocklist,
  dedup, and source-id reduction behavior; skip `==== Signed:` duplicate
  blocks.
- Emit corpus v2 rows: `prompt, source_file, local_model, dialect, seed,
  size, created`, and print stats (kept rows, residual unknown count).
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

## Acceptance Criteria (revised per judgement)

- [x] AC-01: The FR cites committed sanitized evidence
      (`tests/fixtures/signed_log_excerpt.txt`) for the signed-log block
      shape, metadata fields, `==== Signed:` duplicate shape, and both
      dialect fingerprints; no raw private corpus data is committed.
- [x] AC-02: `python scripts/extract_corpus.py <signed.log>
      prompts/corpus.jsonl` regenerates corpus v2 rows with keys `prompt`,
      `source_file`, `local_model`, `dialect`, `seed`, `size`, `created`,
      and prints stats including kept rows and residual unknown count.
- [x] AC-03: Every emitted row has `dialect ∈ {prose, tags}`; a
      `flux-hyp16` fixture row classifies as `prose`; an
      `autismmixSDXL_*` fixture row and/or a `score_\d`-negative row
      classifies as `tags`.
- [x] AC-04: `==== Signed:` blocks are excluded, with a fixture test
      proving they produce no duplicate rows.
- [x] AC-05: The extractor preserves the v1 sanitization, blocklist,
      dedup, and source-id reduction behavior already covered by
      `scripts/extract_corpus.py` tests.
- [x] AC-06: Every prompt from the pre-change v1 `prompts/corpus.jsonl`
      resolves in regenerated v2 by exact prompt text (verifier input:
      the pre-change `prompts/corpus.jsonl` at the commit before
      regeneration).
- [x] AC-07: Every non-empty `source_file` in committed
      `state/published.jsonl` resolves against regenerated v2 by direct
      `source_file` match or `row_id(row)` match.
- [x] AC-08: For every retained row whose raw basename matches
      `^(\d+-\d+)`, `source_file` equals that reduced ID; residual
      `unknown` rows allowed only when the raw basename lacks that
      pattern; final residual count recorded in this FR.
- [x] AC-09: `tools/corpus.py` draw behavior unchanged: no dialect
      filtering, no restyle policy, no change to `row_id()` semantics.
- [x] AC-10: README corpus provenance updated with corpus v2 fields and
      regenerated counts.
- [x] AC-11: Tests added for parser metadata extraction, dialect
      derivation, signed-block exclusion, v1 prompt preservation, and
      ledger source-id preservation; new tests carry
      `@pytest.mark.req(...)` markers and update the capability registry
      if a new requirement is introduced (R-5).

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
- `scripts/extract_corpus.py` (existing extractor this FR extends — R-2)
- `tests/fixtures/signed_log_excerpt.txt` (sanitized evidence fixture, D-3)

## Judgement (2026-08-24)

**Verdict:** APPROVED WITH REVISIONS — see
`FR-883-corpus-v2-signed-log-reextraction.judgement.md` (R-1..R-5 folded
above; scope frozen per its deliverables table; conditions C-1..C-5 are
GATEs). Authority granted for enforcement now that revisions are folded.

Key corrections accepted by the author:
- R-2 caught a precedent-search failure: `scripts/extract_corpus.py`
  already exists; the originally proposed `tools/extract_corpus.py` was a
  duplicate surface.
- R-3 replaced a gameable threshold ("strictly below 1,937") with the
  mechanical basename→ID invariant.
- R-1 replaced chat-session evidence with a committed sanitized fixture.

## Implementation Record (2026-08-24)

TDD trail: RED f459357 (fixture + 4 condemning tests,
`logs/fr883-red.log`) → GREEN (extractor v2, `logs/fr883-green.log`);
full suite green (`logs/fr883-full.log`).

- AC-01 ✅ fixture `tests/fixtures/signed_log_excerpt.txt` (both dialect
  fingerprints, Signed block, stale-source hazard block; invented prompts,
  no raw corpus data).
- AC-02 ✅ regenerated from operator-local
  `~/Documents/deviant-working/signed.log`; stats: entries 9,038, kept
  5,893 (deterministic match with v1), name_excluded 2,020,
  term_excluded 69, duplicates 1,054, scan_hits 0, **unknown 1,937**.
- AC-03 ✅ dialect split: prose 3,329 / tags 2,564; top models
  flux-hyp16-Q5_0 (3,357), autismmixSDXL_autismmixPony (1,391).
- AC-04 ✅ RED proved the stale-source bug live (a parameterless File
  block adopted the following Signed block's payload); GREEN resets state
  on every `====` header.
- AC-05 ✅ v1 sanitize/blocklist/dedup/id-reduction tests unchanged and
  green.
- AC-06 ✅ 0 of 5,893 v1 prompts lost (verifier input: v1 corpus at
  f90c14b, backed up pre-regeneration); permanent test pinned at f90c14b.
- AC-07 ✅ 0 of 17 published ledger source ids missing.
- AC-08 ✅ mechanical invariant holds; **residual unknown = 1,937,
  unchanged from v1** — the raw basenames genuinely lack the
  `^(\d+-\d+)` pattern, so there were never ids to recover. The FR's
  original "recover generation ids" premise was wrong; R-3's invariant
  framing exposed this honestly instead of letting a threshold hide it.
- AC-09 ✅ `tools/corpus.py` untouched.
- AC-10 ✅ README corpus provenance updated (v2 fields + counts).
- AC-11 ✅ REQ-DD-080/081/082 added to CAP-09; all new tests req-marked.
- Field coverage: created 5,893/5,893; seed missing on 1 row.

Deviation from plan: none beyond AC-08's finding above. Coverage: 1 row
lacks seed (its Steps line carries no Seed field) — left as `null` per
schema.
