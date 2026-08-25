# Judgement: FR-890 Corpus Content Fingerprint + Genre Classification (Haiku Enrichment)

**Verdict:** APPROVED WITH REVISIONS - the carved-out corpus-enrichment direction is sound, but authority activates only after the FR commits its taxonomy evidence, normalizes the row schema/failure semantics, and makes extraction pass-through and spend controls mechanically enforceable.

**Reviewed against:** `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-890-corpus-haiku-fingerprint-enrichment.md`; `/Users/sheikki/Documents/src/deviant-daily/.github/skills/judge-fr/doctrine.md`; `/Users/sheikki/Documents/src/deviant-daily/.github/skills/judge-fr/judgement.template.md`; `/Users/sheikki/Documents/src/deviant-daily/AGENTS.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/TEMPLATE.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-886-corpus-fingerprint-and-deterministic-draw-routing.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-885-replicate-model-tolerance-fingerprinting.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-885-replicate-model-tolerance-fingerprinting.judgement.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-887-structured-generation-failure-logging.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-888-generate-all-selected-providers.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-889-user-given-prompt-option.md`; `/Users/sheikki/Documents/src/deviant-daily/prompts/corpus.jsonl`; `/Users/sheikki/Documents/src/deviant-daily/scripts/extract_corpus.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/corpus.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/gate.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/vision.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/steps.py`; `/Users/sheikki/Documents/src/deviant-daily/prompts/describe_post.yaml`; `/Users/sheikki/Documents/src/deviant-daily/graph.yaml`; `/Users/sheikki/Documents/src/deviant-daily/.github/workflows/_pipeline.yml`; `/Users/sheikki/Documents/src/deviant-daily/pyproject.toml`; `/Users/sheikki/Documents/src/deviant-daily/capabilities/README.md`; `/Users/sheikki/Documents/src/deviant-daily/capabilities/CAP-09-roster-corpus-and-post-rendering.yaml`. The local doctrine path named by judge doctrine, `.github/copilot-instructions.md`, is absent; `AGENTS.md` is the available repo-doctrine artifact.

## What is sound

The problem is real and has named consumers. FR-890 identifies FR-886's deterministic draw router as the first consumer and corpus analytics/rotation as the second consumer (FR-890 lines 9-12), while FR-886 has already moved corpus fingerprint production out of the router and made the router depend on FR-890's taxonomy (FR-886 lines 8-9, 60-66). That separation prevents a paid batch enrichment from being bundled into draw-time routing.

The corpus evidence supports the need for additive enrichment: the current rows contain only `prompt`, `source_file`, `local_model`, `dialect`, `seed`, `size`, and `created` (FR-890 lines 45-47; `prompts/corpus.jsonl` lines 1-5), and `scripts/extract_corpus.py` currently writes exactly those fields when regenerating rows (`scripts/extract_corpus.py` lines 241-249). The FR's additive-only constraint and row-count invariant are the right safety rails for a corpus rewrite (FR-890 lines 101-102, 112-114).

The proposal is feasible in this repository's shape if revised. The repo already runs YAMLGraph from a committed graph (`graph.yaml` lines 14-39; `.github/workflows/_pipeline.yml` lines 32-37), has structured-output validation precedent (`tools/vision.py` lines 14-16, 57-80, 160-182), and registers Pydantic/pytest patterns in source and project config (`tools/gate.py` lines 19, 32-43; `pyproject.toml` lines 31-34). Strategic classification: contrib/example-equivalent repo capability, not a framework primitive; it has two named consumers, and existing abstractions need a new corpus-enrichment surface rather than a new platform layer.

## Required revisions

### R-1: Commit the taxonomy evidence before granting classification authority

Add a committed evidence section or artifact that contains the claimed 2026-08-25 keyword scan and 40-prompt raw read. FR-890 currently says the taxonomy is grounded in a keyword scan and `read_raw_output_first` sample (FR-890 lines 55-56), but no cited committed scan/sample artifact exists under the reviewed tree. Local judge doctrine requires measurement/metric-tooling FRs to evidence `read_raw_output_first` before authority and to disposition prior art (judge doctrine lines 112-117); repo doctrine says raw artifacts must be read before measuring them (AGENTS.md lines 219-225), and the FR template requires paths plus concrete observed details for raw samples (feature-requests/TEMPLATE.md lines 25-37). Fold in: the exact scan command or script, counts per proposed class, sampling seed or selected row ids, and at least one concrete observed detail for each of the 40 raw prompt samples.

### R-2: Freeze the taxonomy as a single source of truth with testable definitions

Add an explicit taxonomy artifact path and make FR-886 import that artifact rather than prose. The FR says it owns the taxonomy and FR-886 must not redeclare it (FR-890 lines 115-116), but it only names a table in the FR (FR-890 lines 60-72), not a committed runtime artifact. Define the authorized surface, for example `data/corpus_fingerprint_taxonomy.yaml` or `prompts/corpus_fingerprint_taxonomy.yaml`, containing the closed genre enum, precedence order, inclusion/exclusion rules, and fixture examples for all 11 labels. The `other` label must be demote-last at the boundary, not merely audited after it has eaten rows: repo doctrine warns that junk-drawer labels are true-of-everything unless capped before the model vote (AGENTS.md lines 237-243), while FR-890 currently caps only after `other > 10%` (FR-890 lines 119-122).

### R-3: Define the content fingerprint semantics independently of DeviantArt image maturity

Specify exact prompt-classification rules for `content.sexual` and `content.gore`, including whether nudity is subsumed by `sexual`, whether language/ideology are intentionally out of scope, and whether classification is based on prompt text only. Existing publish policy uses image-derived `mature`, `mature_level`, and `mature_classification` values from DeviantArt's enum (`tools/gate.py` lines 28-42; `prompts/describe_post.yaml` lines 36-47), but FR-890 proposes prompt-row fields with only `sexual` and `gore` binary rungs (FR-890 lines 19-21, 98-100). Without these decision rules, acceptance tests can validate shape but not semantic correctness, violating judge doctrine's measurability/testability requirements (judge doctrine lines 43-44, 58-61) and repo doctrine's warning that plausible structured output can be semantically wrong (AGENTS.md lines 73-80).

### R-4: Normalize the row schema and failure representation

Resolve the internal inconsistency between "three additive columns per row" (FR-890 lines 16-23), dated/model-bearing fingerprints (FR-890 lines 37-40), proposed columns `content`, `genre`, `fingerprint_date`, and `classifier_model` (FR-890 lines 84-86), and failed rows being left unfingerprinted (FR-890 lines 80-83, 117-118). The revised FR must define the exact JSON keys for a classified row and for an unclassified failed row, including whether failure metadata is stored, whether `content` can be absent/null, and how FR-886 distinguishes "safe" from "unfingerprinted". Acceptance must not require "full corpus classified" if one-shot failures are allowed; instead require row count/order invariants plus exact counts of `classified` and `unfingerprinted` rows.

### R-5: Make re-extraction pass-through implementable from the current extractor

Amend the extractor acceptance criterion to name the merge key and CLI/API surface that preserves enrichment across regeneration. Today `scripts/extract_corpus.py` accepts only `<signed.log> <out.jsonl> [--sample N]` (`scripts/extract_corpus.py` lines 18-20), constructs fresh rows with only the v2 fields (`scripts/extract_corpus.py` lines 241-249), and writes them atomically (`scripts/extract_corpus.py` lines 102-114, 270). `tools.corpus.row_id()` supplies a stable fallback key for `unknown` source ids (`tools/corpus.py` lines 24-30). The revised FR must require a concrete pass-through mechanism, such as `--existing-corpus` merged by `source_file` plus prompt hash/`row_id`, and fixture tests proving the new fields survive re-extraction unchanged while dropped or changed source rows do not inherit stale fingerprints.

### R-6: Define the live-run controls for cost, resumability, and auditability

Turn the spend and resumability constraints into mechanical behavior. FR-890 estimates "~$3" and sets a $5 ceiling (FR-890 lines 23, 112), but the acceptance criteria do not require a call counter, pricing input, dry-run estimate, checkpoint file, or stop condition that can be tested. The revised FR must require deterministic batching over the 7,392-row corpus, resumable state keyed by row id, a preflight estimate using the selected classifier model id, a hard stop before the budget ceiling, and a witnessed run record containing model id, date, classified/unfingerprinted counts, distribution table, `other` audit status, and spend estimate.

### R-7: Bind the new behavior to capability requirements and targeted tests

Keep AC-7 but make it specific: add or extend a capability file with new `REQ-DD` ids for taxonomy validation, content/genre boundary rejection, additive corpus writing, extraction pass-through, resumability, cost stop, and distribution reporting. The repo convention requires every test to carry `@pytest.mark.req(...)` linked to a capability requirement (capabilities/README.md lines 20-26; `pyproject.toml` lines 31-34), and existing CAP-09 covers corpus extraction/rendering but not LLM enrichment or taxonomy classification (CAP-09 lines 1-61).

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | FR-890 evidence section or committed supporting artifact with keyword scan output and 40 raw-sample observations. |
| D-2 | Single taxonomy artifact for `content.sexual`, `content.gore`, and the 11-label `genre` enum, with precedence and test fixtures. |
| D-3 | `graphs/corpus_fingerprint.yaml` or the repo-approved equivalent YAMLGraph surface, plus the committed prompt/schema used for haiku-class structured output. |
| D-4 | `scripts/enrich_corpus.py` for resumable, budget-capped enrichment and atomic additive writes to `prompts/corpus.jsonl`. |
| D-5 | `scripts/extract_corpus.py` changes limited to preserving existing fingerprint columns during re-extraction. |
| D-6 | One witnessed enrichment run record containing classifier model id, date, spend estimate, row counts, genre x content distribution, and `other` audit result. |
| D-7 | Targeted tests and capability registry entries for the new corpus-enrichment guarantees. |

Not authorized: draw routing or eligibility joins, model tolerance probing, provider fan-out, user-prompt generation, prompt rewriting/filtering, changes to publish/gate policy, roster changes, CI/enforcement-doctrine changes, multi-label genre classification, new style/medium axes, retries after classifier failure, or committing unreviewed raw private corpus dumps beyond the scoped taxonomy evidence needed for judgement/enforcement.

## Revised acceptance criteria

- [ ] AC-01: A committed FR-890 evidence artifact records the keyword scan command/results and 40 raw prompt row ids with concrete observations supporting the taxonomy.
- [ ] AC-02: A single taxonomy artifact defines `content.sexual`, `content.gore`, and `genre` labels, precedence, inclusion/exclusion rules, and fixture examples; FR-886 imports or references this artifact without redeclaring the taxonomy.
- [ ] AC-03: The classifier boundary accepts only `safe|mature` for `content.sexual` and `content.gore` and only the frozen 11-label `genre` enum; out-of-set output leaves the row `unfingerprinted` with a counted reason and is never coerced.
- [ ] AC-04: `other` is demoted behind every concrete genre before acceptance; if the witnessed run reports `other > 10%`, the run record includes 20 raw `other` samples and the corpus columns are not committed until the taxonomy artifact is revised and rerun.
- [ ] AC-05: Enrichment preserves prompt text, row order, and row count exactly; tests compare before/after row ids and prompt bytes.
- [ ] AC-06: Re-running enrichment skips rows already classified with the same taxonomy version and classifier model id, resumes unclassified rows, and records classified/unfingerprinted counts.
- [ ] AC-07: The live run has a preflight cost estimate and a tested stop-before-$5 guard keyed to attempted calls; no classifier retry is attempted for a failed row.
- [ ] AC-08: `scripts/extract_corpus.py` preserves fingerprint fields from an existing corpus by the revised merge key during re-extraction, with fixture coverage for normal and `unknown` source ids.
- [ ] AC-09: The enrichment run emits a genre x sexual x gore distribution report and stores enough run metadata to reproduce the classifier model id, taxonomy version, date, row counts, and `other` audit status.
- [ ] AC-10: New capability requirements are added or extended, and every new test is marked with the corresponding `@pytest.mark.req(...)`.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | Authority is not active until R-1 through R-7 are folded into FR-890. | GATE |
| C-2 | The enforcer must not run the full paid classifier until the taxonomy evidence artifact, taxonomy file, preflight cost estimate, and stop-before-$5 guard exist. | GATE |
| C-3 | Classifier output is a claim; closed-set validation and semantic fixture tests must sit at the boundary before writing corpus rows. | GATE |
| C-4 | `other` must be demoted/capped and audited exactly as AC-04 specifies; a high-`other` run cannot be committed as finished corpus enrichment. | GATE |
| C-5 | Corpus mutation must be atomic and additive: no prompt byte changes, row drops, row reordering, or stale fingerprint inheritance across changed rows. | GATE |
| C-6 | Enforcement must stay inside corpus enrichment; FR-886 routing, FR-887/888/889 generation surfaces, roster policy, and publish gate behavior remain out of scope. | GATE |
| C-7 | Any change to CI, hooks, judge/review doctrine, or skill/adapters is adversarial infrastructure input and requires human review before landing. | GATE |

Authority granted: after the required revisions are folded into FR-890, the enforcer may build only the witnessed, budget-capped corpus fingerprint enrichment and extraction pass-through surfaces described above.
