# Judgement: FR-886 Corpus Content Fingerprinting and Deterministic Draw Routing

**Verdict:** APPROVED WITH REVISIONS — the routing direction is sound and now properly depends on FR-890/887/888/889 evidence surfaces, but authority activates only after the FR removes stale pre-FR-890 claims and makes model binding, determinism, ledger absence, and skip semantics mechanically enforceable.

**Reviewed against:** `feature-requests/FR-886-corpus-fingerprint-and-deterministic-draw-routing.md`; `.github/skills/judge-fr/doctrine.md`; `.github/skills/judge-fr/judgement.template.md`; `AGENTS.md`; `feature-requests/FR-890-corpus-haiku-fingerprint-enrichment.md`; `feature-requests/FR-890-corpus-haiku-fingerprint-enrichment.judgement.md`; `feature-requests/FR-890-evidence.md`; `feature-requests/FR-887-structured-generation-failure-logging.md`; `feature-requests/FR-887-structured-generation-failure-logging.judgement.md`; `feature-requests/FR-888-generate-all-selected-providers.md`; `feature-requests/FR-889-user-given-prompt-option.md`; `prompts/corpus.jsonl`; `tools/corpus.py`; `tools/steps.py`; `tools/roster.py`; `tools/failures.py`; `graph.yaml`; `.github/workflows/_pipeline.yml`; `capabilities/README.md`; `capabilities/CAP-14-corpus-fingerprint-enrichment.yaml`; `capabilities/CAP-15-generation-failure-logging.yaml`; `capabilities/CAP-16-user-prompt-cli.yaml`; `capabilities/CAP-17-provider-fanout.yaml`; `pyproject.toml`. Cited but absent under input closure: `state/failures.jsonl`; the local doctrine path named by judge doctrine, `.github/copilot-instructions.md`, is also absent, so `AGENTS.md` is the available repo-doctrine artifact.

## What is sound

The problem and first consumer are concrete. FR-886 names the daily draw step at the first scheduled run after merge as the first consumer (FR-886 lines 13-16), and its draw-time join is specifically bounded to FR-890 corpus fingerprints plus FR-887/888/889 accumulated failure evidence (FR-886 lines 35-41). That matches FR-890's enforced implementation record: all 7,392 rows were classified with `content.sexual`, `content.gore`, and `fingerprint` metadata (FR-890 lines 231-245), and the current corpus rows visibly carry those fields (`prompts/corpus.jsonl` lines 1-5).

The architecture direction is aligned with existing side-effect boundaries. Today `draw_step()` validates the roster, reads the publish ledger, draws a row, and commits the drawn transition before generation (`tools/steps.py` lines 65-98); `generate_step()` later chooses or honors a model and records generation failures through FR-887 (`tools/steps.py` lines 101-135). Moving eligibility before the draw commit is the right call because the FR explicitly says an unroutable prompt must be skipped before it burns a slot (FR-886 lines 26-28, 114-115).

The supply-side evidence primitive already exists and is appropriately narrow. `FailureRecord` includes roster `model`, `prompt_sha`, `error_class`, and `run_source` (`tools/failures.py` lines 35-45), computes SHA-256 over the exact prompt bytes (`tools/failures.py` lines 48-49), and classifies only refusal/transport/timeout/unknown (`tools/failures.py` lines 52-61). FR-886's decision that only `error_class="refusal"` excludes a `(model, content_tuple)` cell (FR-886 lines 24-25, 88-90) preserves the distinction between tolerance signal and operational noise.

Strategic classification: repo-specific operational primitive, not a framework primitive. It has one immediate production consumer and one evidence source family, and the existing abstractions (`tools.corpus`, `tools.roster`, `tools.failures`, `tools.steps`) are sufficient if wired precisely.

## Required revisions

### R-1: Replace stale pre-FR-890 corpus claims with the current dependency state

Amend the Problem section so it no longer says `prompts/corpus.jsonl` has no content-class fields (FR-886 lines 66-67). That statement contradicts the FR's own dependency header saying FR-890 enriched 7,392/7,392 rows (FR-886 lines 9-10), FR-890's implementation record (FR-890 lines 236-245), and the current corpus rows (`prompts/corpus.jsonl` lines 1-5). Fold in the current problem instead: the corpus is fingerprinted, but the draw step does not yet consume those fingerprints for model eligibility.

### R-2: Move model binding authority to the draw boundary

Define the exact data flow for the model selected by routing. Current `draw_step(date)` has no model argument (`tools/steps.py` lines 65-98), while the graph passes workflow `state.model` only to `generate_step()` (`graph.yaml` lines 50-59) and the workflow exposes `model` as a pipeline input (`.github/workflows/_pipeline.yml` lines 7-14, 32-40). The revised FR must require `draw_step` or its router wrapper to receive the operator-pinned model value, bypass routing when it is non-empty, and return/commit the bound model so `generate_step` consumes that binding rather than choosing independently. Without this, AC-4 and the operator-pin decision (FR-886 lines 29-31, 131-134) can pass unit tests while production still routes one model and generates with another.

### R-3: Resolve "deterministic router" versus current random roster selection

Specify the eligible-model selection rule as a pure, testable function. FR-886 calls the router deterministic and says the same inputs produce the same output (FR-886 lines 56-59), but also says to preserve the existing draw's rotation/randomness within the eligible set (FR-886 lines 107-109). The existing model picker uses `(rng or random).choice(sorted(usable))` (`tools/roster.py` lines 89-97), so the revised FR must either make randomness an explicit route input (`rng`/seed) or choose a deterministic rule over sorted eligible models. AC-3's cold-start neutrality (FR-886 lines 148-149) must define equality against today's blind pick in terms of the same injected RNG or same deterministic rule, not ambient global randomness.

### R-4: Define failure-evidence loading, absence, and join behavior mechanically

Add acceptance coverage for `state/failures.jsonl` not existing yet. The FR cites accumulated outcome evidence in that path (FR-886 lines 10-12, 37-38), but the file is absent under current input closure; FR-887's helper creates the parent/file only when the first failure is appended (`tools/failures.py` lines 96-107). The router must treat an absent failure ledger as an empty evidence set, must read only `error_class="refusal"` rows, must join by `prompt_sha` through the corpus lookup, and must count but ignore non-corpus prompt hashes exactly as the FR states (FR-886 lines 88-98). This is not optional because cold-start eligibility is an operator decision (FR-886 lines 20-23).

### R-5: Freeze the unroutable-prompt skip algorithm before the draw commit

Define how draw searches past an unroutable candidate without burning a slot or looping forever. Current `draw_prompt()` filters already-used rows and chooses one candidate (`tools/corpus.py` lines 46-67); `draw_step()` then immediately commits that row as `drawn` (`tools/steps.py` lines 83-98). FR-886 says an empty eligible set raises a typed, counted exclusion and the prompt is skipped before commit (FR-886 lines 107-110, 114-115), but it does not state whether draw retries the next candidate, how many candidates may be skipped in one run, what gets returned if every remaining prompt is unroutable, or where the counted reason lives given constraint C-2 says routing never writes to any ledger (FR-886 lines 145-147). Fold in a bounded algorithm and tests for one skipped prompt, all-candidates-unroutable, and no ledger transition for skipped candidates.

### R-6: Single-source FR-890 taxonomy and validate missing/invalid fingerprints at the boundary

Name `data/corpus_fingerprint_taxonomy.yaml` as the runtime source of truth and require the router to validate corpus `content.sexual`/`content.gore` values against it instead of redeclaring strings. FR-890 requires FR-886 to import the taxonomy artifact without redeclaration (FR-890 lines 88-98, 203-210), and CAP-14 records the exact artifact and closed content axes (CAP-14 lines 11-22). The FR already says unfingerprinted prompts route as maximally mature (FR-886 lines 117-118); extend that to invalid or partial fingerprint rows with a counted reason, because repo doctrine warns that shape-valid output can still be semantically wrong (AGENTS.md lines 73-80).

### R-7: Bind routing to capability requirements, tests, and README without broadening adjacent systems

Keep the REQ-DD/README acceptance shape (FR-886 lines 138-141), but make it concrete: add a routing capability entry or extend the narrowest existing capability with requirements for evidence loading, prompt-sha joins, eligible-model purity, pinned bypass, draw-before-commit binding, unroutable skip behavior, no draw-time network/LLM calls, and README routing contract. The repo convention requires every test to carry `@pytest.mark.req(...)` linked to a capability requirement (`capabilities/README.md` lines 20-26; `pyproject.toml` lines 31-34). Do not alter FR-887/888/889 semantics except by reading their already-defined artifacts.

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | `tools/route.py` or equivalent focused module for `refusal_evidence`, corpus prompt-sha lookup, `eligible_models`, typed unroutable exclusion, and route selection. |
| D-2 | `tools/corpus.py` changes limited to exposing enough candidate iteration/row identity for route-before-commit without changing corpus row contents. |
| D-3 | `tools/steps.py` draw integration: model input/pinned bypass, route-before-commit, committed drawn row includes bound model, skipped candidates are not committed. |
| D-4 | `graph.yaml` argument wiring so draw receives the workflow/operator model input and generate consumes the draw-bound model. |
| D-5 | Tests for cold start, refusal exclusion floor, transport/timeout/unknown non-exclusion, absent failure ledger, non-corpus prompt-sha skip count, taxonomy drift, unfingerprinted/invalid fingerprints as maximally mature, pinned bypass, no draw-time LLM/network, and unroutable skip behavior. |
| D-6 | Capability registry entry/requirements and README documentation for the routing contract and evidence join. |

Not authorized: corpus enrichment or taxonomy changes under FR-890, changing FR-887 failure-row schema or classification semantics, fan-out/user-prompt behavior changes under FR-888/FR-889, synthetic model probing, prompt rewriting/softening/filtering, roster admission/retirement, DeviantArt gate/publish policy changes, workflow trigger changes, CI/hook changes, judge/review doctrine changes, or routing writes to `state/failures.jsonl`.

## Revised acceptance criteria

- [ ] AC-01: The FR text reflects the enforced FR-890 state: corpus rows already carry `content`/`fingerprint`, and this FR only consumes those fields for routing.
- [ ] AC-02: `refusal_evidence(failure_rows, corpus)` joins refusal rows to corpus rows by `prompt_sha`, uses the FR-890 `(sexual, gore)` tuple verbatim, ignores transport/timeout/unknown rows, treats an absent `state/failures.jsonl` as empty, and counts non-corpus prompt hashes without guessing.
- [ ] AC-03: `eligible_models(fingerprint, evidence, roster)` is pure and unit-tested: zero refusal evidence admits a model, one witnessed refusal for the exact tuple excludes it, other tuples do not exclude it, and an empty eligible set raises a typed unroutable exclusion.
- [ ] AC-04: Route selection is deterministic for declared inputs, either by deterministic sorted choice or by accepting an injected RNG/seed; cold-start routing with the same selection input is identical to today's blind roster pick.
- [ ] AC-05: `draw_step` routes before committing the drawn row, skips unroutable candidates without writing them to `state/published.jsonl` or `state/failures.jsonl`, records the bound model on the committed drawn row, and returns that binding for generation.
- [ ] AC-06: A mocked end-to-end draw test witnesses a mature prompt bypassing a refusal-witnessed model and binding to an eligible model before `generate_step`; `generate_step` uses the draw-bound model and does not re-select a different model.
- [ ] AC-07: Operator-pinned `--model`/workflow `model` bypasses routing at draw time, records the pinned binding, and still allows any later provider refusal to be logged by FR-887.
- [ ] AC-08: Missing, invalid, or partial corpus fingerprints route as maximally mature `(mature, mature)` with a counted reason; taxonomy drift from `data/corpus_fingerprint_taxonomy.yaml` fails a test.
- [ ] AC-09: No LLM call, provider call, or network call exists in the draw routing path; router tests run offline.
- [ ] AC-10: New REQ-DD ids in a capability file cover routing/evidence behavior, and every new or changed test carries `@pytest.mark.req(...)`.
- [ ] AC-11: README documents the routing contract, failure-evidence join, cold-start behavior, pinned-model bypass, unroutable skip behavior, and the fact that routing does not write the failure ledger.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | Authority is not active until R-1 through R-7 are folded into FR-886. | GATE |
| C-2 | Draw routing must happen before a drawn row is committed; skipped/unroutable candidates must not consume a slot or create publish-ledger rows. | GATE |
| C-3 | A model binding chosen or bypassed at draw time must be the model used by generation; production must not route and then independently call `choose_model()` again. | GATE |
| C-4 | An absent `state/failures.jsonl` is empty evidence, not an error and not permission to invent tolerance data. | GATE |
| C-5 | Only `error_class="refusal"` may exclude a model/content tuple; transport, timeout, unknown, user/probe non-corpus hashes, and unmatched hashes must not become tolerance evidence. | GATE |
| C-6 | The FR-890 taxonomy artifact is the single source of truth; the router must not redeclare or mutate the content taxonomy. | GATE |
| C-7 | Enforcement must not change corpus enrichment, failure logging schema, fan-out/user-prompt behavior, roster policy, publish/gate policy, workflow triggers, CI, hooks, or judge/review doctrine under this FR. | GATE |
| C-8 | All new behavior must be witnessed by req-marked tests linked to capability registry entries. | GATE |

Authority granted: after the required revisions are folded into FR-886, the enforcer may implement only deterministic refusal-evidence routing at draw time, including bound-model recording and unroutable skip handling, using the already-enforced FR-890 and FR-887/888/889 artifacts as inputs.
