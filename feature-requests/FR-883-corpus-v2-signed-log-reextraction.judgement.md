# Judgement: FR-883 Corpus v2 - re-extract signed.log with prompt dialect and generation metadata

**Verdict:** APPROVED WITH REVISIONS - the boundary re-extraction is sound, but authority activates only after the FR cites committed/sanitized raw evidence, reuses the existing extractor surface, and tightens the unknown-id and ledger migration checks.

**Reviewed against:** `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-883-corpus-v2-signed-log-reextraction.md`; `/Users/sheikki/Documents/src/deviant-daily/.github/skills/judge-fr/doctrine.md`; `/Users/sheikki/Documents/src/yamlgraph/.github/skills/judge-fr/doctrine.md`; `/Users/sheikki/Documents/src/yamlgraph/.github/skills/judge-fr/judgement.template.md`; `/Users/sheikki/Documents/src/deviant-daily/README.md`; `/Users/sheikki/Documents/src/deviant-daily/AGENTS.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/TEMPLATE.md`; `/Users/sheikki/Documents/src/deviant-daily/scripts/extract_corpus.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/corpus.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/ledger.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/steps.py`; `/Users/sheikki/Documents/src/deviant-daily/tests/test_roster_corpus_post.py`; `/Users/sheikki/Documents/src/deviant-daily/tests/test_external_constraints.py`; `/Users/sheikki/Documents/src/deviant-daily/tests/test_ledger.py`; `/Users/sheikki/Documents/src/deviant-daily/capabilities/README.md`; `/Users/sheikki/Documents/src/deviant-daily/capabilities/CAP-03-external-constraint-mirroring.yaml`; `/Users/sheikki/Documents/src/deviant-daily/capabilities/CAP-06-idempotency-ledger.yaml`; `/Users/sheikki/Documents/src/deviant-daily/capabilities/CAP-09-roster-corpus-and-post-rendering.yaml`; `/Users/sheikki/Documents/src/deviant-daily/pyproject.toml`; `/Users/sheikki/Documents/src/deviant-daily/prompts/corpus.jsonl`; `/Users/sheikki/Documents/src/deviant-daily/state/published.jsonl`; `git -C /Users/sheikki/Documents/src/deviant-daily show --stat --oneline eac6d5a`. Cited but not consumable under input closure: `FR-826` (not present in this repo), `.github/copilot-instructions.md` (doctrine path cited by local judge doctrine but absent), and the 2026-08-24 session/raw `signed.log` evidence (not a committed artifact).

## What is sound

The first consumer is concrete: the FR names the `tools/corpus.py` draw step and the first scheduled run after merge (FR-883 lines 8-12), while the README confirms the pipeline draws from `prompts/corpus.jsonl` before generation (README lines 3-7). The cited recraft addition is also real evidence of a prose-native roster pressure point: the roster documents recraft as active (README lines 48-55), and the cited commit `eac6d5a` adds `recraft-ai/recraft-v4`.

The scope is mostly minimal and single-responsibility. The FR confines this change to corpus re-extraction and metadata preservation, explicitly deferring dialect-aware draw/restyle policy (FR-883 lines 76-78) and rejecting LLM enrichment because dialect is mechanically derivable and lacks a present consumer (FR-883 lines 101-108). That matches the repo doctrine to inspect raw artifacts before building measurement or policy layers (AGENTS.md lines 219-225) and avoids a downstream fix: the current `row_id()` hash branch exists only to compensate for `source_file: "unknown"` rows (tools/corpus.py lines 18-30).

Feasibility is high if implemented on the existing extractor. The current parser already reads ImageMagick-style `==== File:` entries, `parameters:`, prompt continuations, and `Steps:` boundaries (scripts/extract_corpus.py lines 1-7 and 66-91), and existing tests exercise those parser seams (tests/test_roster_corpus_post.py lines 124-153). Extra JSON fields are compatible with the draw path because `draw_prompt()` returns the selected row with additional keys preserved while still normalizing the published `source_file` through `row_id()` (tools/corpus.py lines 63-67).

The migration risk is correctly identified. The committed ledger contains already-published source IDs, including raw `unknown` and hashed `unknown-*` forms (state/published.jsonl lines 15, 26, and 32), and `used_source_ids()` treats every non-empty `source_file` as a no-repeat key (tools/ledger.py lines 63-64). Preserving those IDs in the regenerated corpus is therefore a real gate, not bookkeeping.

## Required revisions

### R-1: Replace uncommitted raw evidence with committed sanitized evidence

Amend the FR's "Raw-record verification" and "Related" sections so every factual claim needed by the plan points to a committed, non-sensitive artifact. At minimum, add and cite a sanitized fixture or evidence note that shows: one `==== File:` block with `parameters:` containing prompt text plus `Negative prompt`, `Steps`, `Sampler`, `CFG`, `Seed`, `Size`, and `Model`; one `==== Signed:` block proving duplicate exclusion shape; one `flux-hyp16`/prose example; and one `autismmixSDXL_*` or `score_` negative-prompt example for tags. The FR currently cites a 2026-08-24 session log and local raw files (FR-883 lines 47-51 and 116-117), but the judge doctrine permits only committed artifacts and says missing essential context is an FR defect (judge doctrine lines 16-24). The fixture must not commit raw private corpus data; the README states the raw unsanitized corpus never leaves the operator's machine (README lines 23-36).

### R-2: Extend the existing extractor instead of creating a duplicate surface

Change the Proposed Solution from new `tools/extract_corpus.py` to extending `scripts/extract_corpus.py`, unless the FR explicitly authorizes a full migration that updates README references and all test imports. The existing repo surface is `scripts/extract_corpus.py` (README lines 29-30), its module docstring defines the corpus extraction contract (scripts/extract_corpus.py lines 1-16), and tests import that exact script path (tests/test_roster_corpus_post.py lines 20-24). A new `tools/extract_corpus.py` would duplicate the boundary parser and violate architecture alignment before the FR has justified a migration.

### R-3: Tighten the unknown-id acceptance criterion to the real invariant

Replace "unknown source_file count strictly below v1's 1,937" with a mechanical invariant: for every retained row whose raw source basename matches `^(\d+-\d+)`, `source_file` must equal that reduced ID; `source_file == "unknown"` is allowed only when the raw basename lacks that pattern; and the final residual unknown count must be recorded in the FR. This preserves the privacy boundary that raw basenames can embed prompt/LoRA material and must be reduced to IDs (scripts/extract_corpus.py lines 127-131; README lines 34-36). A "strictly below" threshold could pass after recovering only one of 1,937 rows, contradicting the FR's stated goal to recover generation IDs (FR-883 lines 20-21 and 41-45).

### R-4: Specify the migration verifier inputs and ledger comparison

Amend the acceptance criteria to name the old corpus source and live ledger path used by the migration check. The verifier must compare the pre-change `prompts/corpus.jsonl` prompt set against regenerated v2 rows, and must compare every non-empty `source_file` in committed `state/published.jsonl` against the v2 `source_file`/`row_id()` set. "Real ledger" is not enough: `tools/steps.py` defines the ledger path as `state/published.jsonl` and corpus path as `prompts/corpus.jsonl` (tools/steps.py lines 45-47), and the no-repeat contract is driven by `used_source_ids()` (tools/ledger.py lines 63-64).

### R-5: Bind new tests to the capability registry convention

Amend the FR's test criterion to require `@pytest.mark.req(...)` markers for new parser/migration tests and a capability registry update when the change introduces a new behavioral guarantee rather than merely extending `REQ-DD-049`. The repo's capability convention says every test function carries a requirement marker linked to the registry (capabilities/README.md lines 20-24), existing corpus extraction tests already use `REQ-DD-045` through `REQ-DD-049` (tests/test_roster_corpus_post.py lines 99-153), and `pyproject.toml` registers the `req` marker (pyproject.toml lines 31-34).

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | `scripts/extract_corpus.py`: extend the existing parser/extractor to emit corpus v2 metadata and stats. |
| D-2 | `prompts/corpus.jsonl`: regenerate from the operator-local `signed.log` into v2 JSONL rows. |
| D-3 | Sanitized signed-log fixture/evidence artifact cited by the FR; no raw private corpus committed. |
| D-4 | Parser, dialect, signed-duplicate exclusion, migration, and ledger-preservation tests, with requirement markers. |
| D-5 | Capability registry update only if the new tests need a new requirement rather than extending an existing one. |
| D-6 | README corpus provenance update and FR implementation notes, including final row count and residual unknown count. |

Not authorized: changing draw/restyle behavior; adding dialect filtering or prompt rewriting to the daily pipeline; adding LLM classification or subject/safety scoring; ingesting `prompt-forge/signed.log`; changing roster policy; rewriting ledger history; deleting or changing the `row_id()` hash branch; committing raw `signed.log`, raw basenames, or unsanitized private corpus material; adding a duplicate extractor under `tools/` while leaving the existing `scripts/` extractor in place.

## Revised acceptance criteria

- [ ] AC-01: The FR cites committed sanitized evidence for the signed-log block shape, metadata fields, `==== Signed:` duplicate shape, and both dialect fingerprints; no raw private corpus data is committed.
- [ ] AC-02: `python scripts/extract_corpus.py <signed.log> prompts/corpus.jsonl` regenerates corpus v2 rows with keys `prompt`, `source_file`, `local_model`, `dialect`, `seed`, `size`, and `created`, and prints stats including kept rows and residual unknown count.
- [ ] AC-03: Every emitted row has `dialect` in `{prose, tags}`; a `flux-hyp16` fixture row classifies as `prose`; an `autismmixSDXL_*` fixture row and/or a row with `score_\d` negative prompt classifies as `tags`.
- [ ] AC-04: `==== Signed:` blocks are excluded and have a fixture test proving they do not produce duplicate rows.
- [ ] AC-05: The extractor preserves the v1 sanitization, blocklist, dedup, and source-id reduction behavior already covered by `scripts/extract_corpus.py`.
- [ ] AC-06: Every prompt from the pre-change v1 `prompts/corpus.jsonl` resolves in regenerated v2 by exact prompt text, with the old-corpus source used by the verifier named in the FR.
- [ ] AC-07: Every non-empty `source_file` in committed `state/published.jsonl` resolves against regenerated v2 by either direct `source_file` match or `row_id(row)` match.
- [ ] AC-08: For every retained row whose raw basename matches `^(\d+-\d+)`, `source_file` equals that reduced ID; residual `unknown` rows are allowed only when the raw basename lacks that pattern, and the final residual count is recorded in the FR.
- [ ] AC-09: `tools/corpus.py` draw behavior is unchanged: no dialect filtering, no restyle policy, and no change to `row_id()` semantics.
- [ ] AC-10: README corpus provenance is updated to describe corpus v2 fields and the regenerated counts.
- [ ] AC-11: Tests are added for parser metadata extraction, dialect derivation, signed-block exclusion, v1 prompt preservation, and ledger source-id preservation; new tests carry requirement markers and update the capability registry if a new requirement is introduced.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | Do not consume the author's chat transcript or uncommitted session notes as implementation requirements; only the revised FR, committed evidence, and repo artifacts govern enforcement. | GATE |
| C-2 | Do not commit raw `signed.log`, raw source basenames that leak prompt material, absolute local paths, token-like strings, emails, or blocked private terms. | GATE |
| C-3 | Do not implement dialect-aware draw/restyle behavior in this FR; metadata extraction only. | GATE |
| C-4 | Do not add a second extractor surface under `tools/` unless the revised FR explicitly authorizes a full migration and updates README/tests accordingly. | GATE |
| C-5 | Do not rewrite `state/published.jsonl`; the ledger is an input to the preservation verifier, not a migration target. | GATE |

Authority granted: after R-1 through R-5 are folded into the FR, implementation may extend the existing corpus extractor, regenerate `prompts/corpus.jsonl` with v2 metadata, and add the tests/docs needed to prove the migration preserves prompt and ledger identity.
