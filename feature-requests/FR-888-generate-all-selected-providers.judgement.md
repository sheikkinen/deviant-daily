# Judgement: FR-888 Generate With All Selected Providers (Fan-Out)

**Verdict:** APPROVED WITH REVISIONS — the fan-out comparison primitive is real, bounded, and aligned with FR-887, but authority activates only after the FR fixes the entry-point dependency, date/output naming contract, failure-ledger semantics, and publish-ledger wording.

**Reviewed against:** `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-888-generate-all-selected-providers.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/.github/skills/judge-fr/doctrine.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/.github/skills/judge-fr/judgement.template.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/AGENTS.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/README.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-887-structured-generation-failure-logging.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-887-structured-generation-failure-logging.judgement.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-889-user-given-prompt-option.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-885-replicate-model-tolerance-fingerprinting.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-885-replicate-model-tolerance-fingerprinting.judgement.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/generate.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/steps.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/failures.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/ledger.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/roster.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/inputs.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/da_api.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/graph.yaml`; `/Users/sami.j.p.heikkinen/src/deviant-daily/pyproject.toml`. Cited but absent under input closure: `/Users/sami.j.p.heikkinen/src/deviant-daily/.github/copilot-instructions.md`.

## What is sound

The problem is real and has a named first consumer/event: the operator needs one comparison run that sends the same prompt to every active model and preserves both successful images and refusal rows (FR-888 lines 9-18). The current generation boundary is one-model only: `generate_step()` chooses one roster model and writes one `/tmp/deviant-daily-{date}.png` image (tools/steps.py lines 101-133), while `generate_image()` runs exactly one Replicate prediction for one model config (tools/generate.py lines 18-37). That matches the FR's problem statement that comparing five models currently means manual repeated runs (FR-888 lines 22-34).

The direction is strategically sound. FR-885 has been explicitly superseded by the trio of structured failure logging, fan-out, and user-given prompts (FR-885 lines 13-25), so this FR is not duplicating the rejected synthetic paid-probe harness. FR-887 is already enforced and includes `run_source="probe"` for non-corpus fan-out consumers without implementing fan-out itself (FR-887 lines 104-116; README.md lines 56-73; tools/failures.py lines 35-45). Strategic classification: target-repo operational comparison primitive, not a framework primitive.

The scope is mostly single-responsibility and feasible. The roster is centralized in `ACTIVE_MODELS` and unknown pinned model names already fail with a valid-list error through `parse_model()` / `choose_model()` (tools/roster.py lines 26-97; tools/inputs.py lines 40-48). Reusing `generate_image()` for a sequential loop is compatible with the repo's existing Python side-effect style, and the FR correctly forbids publish coupling, slot consumption, and parallelism (FR-888 lines 38-47 and 61-72).

## Required revisions

### R-1: Declare the operator entry point dependency mechanically

Amend the FR so implementation authority is not ambiguous about the CLI surface. FR-888 says to add `--all-models` / `--models a,b,c` on "the operator entry point" and says FR-889's `--prompt` composes with it (FR-888 lines 43-44), but FR-889 is still Draft and is the FR that creates the operator-supplied prompt entry point (FR-889 lines 36-47). Add FR-889 as an explicit dependency for any operator CLI acceptance, or state that this FR may only implement a callable fan-out primitive and tests until an existing/enforced operator prompt entry point exists. Do not implement `--prompt` or `--prompt-file` under FR-888.

### R-2: Add `date` to the fan-out contract and freeze output path identity

Amend `generate_all(prompt, models, out_dir)` to include the date or another explicit run identifier, because the proposed output naming requires `<out_dir>/<date>-<model_name>.png` (FR-888 lines 38-42) but the proposed function signature does not receive `date`. Define the output path as a pure function of `(out_dir, date, model_name)` and require parent directory creation, model-name validation before path construction, and no clobbering within one run. The current one-model path omits the model name and would be overwritten if reused for fan-out (tools/steps.py lines 113-116).

### R-3: Validate the full model selection before the first generation

Amend the FR to state that model selection is resolved up front from the active roster: `--all-models` means every usable active roster entry, `--models a,b,c` means exactly that explicit subset in deterministic order, duplicate names are rejected or de-duplicated by a stated rule, and any unknown name fails fast with the valid active list before any provider call or output file write. AC-2 names unknown-name failure (FR-888 lines 54-55), but the Proposed Solution does not specify preflight ordering. This is required so one bad name cannot leave a half-comparison artifact.

### R-4: Preserve FR-887 control flow without hiding failure-ledger failures

Amend the per-model failure semantics. The FR says one model's failure never aborts the others (FR-888 lines 38-41), while FR-887's enforced contract is record-then-reraise, with failure-ledger write/commit failure remaining visibly red and not success-shaped (FR-887 lines 72-77 and 120-129; tools/steps.py lines 116-132). For fan-out, provider failures may be caught after their `FailureRecord` is successfully appended and represented as `failed(FailureRecord)` so later models continue. If appending or committing the failure row itself fails, the fan-out run must abort red with both the provider failure and ledger failure inspectable; it must not continue as if the model merely refused.

### R-5: Replace "no ledger rows" with "no publish-ledger rows"

Amend AC-3 and constraints to say fan-out writes no `state/published.jsonl` rows and calls no DeviantArt API. The current text says "writes no ledger rows" (FR-888 line 56), which contradicts the central purpose of recording FR-887 failure rows during fan-out (FR-888 lines 15-18 and 45-46). The publish ledger is the DA idempotency ledger only (README.md lines 48-54; tools/ledger.py lines 1-11), while `state/failures.jsonl` is the separate failure ledger consumed by FR-888/FR-889 (README.md lines 56-73; tools/failures.py lines 1-9).

### R-6: Define the `GenerationOutcome` shape and capability requirements

Amend scope to name the module and typed shape for `GenerationOutcome`: each model result must include the roster model name, slug, status `ok | failed`, and exactly one of output path or `FailureRecord`. Tests must assert the full list preserves one outcome per selected model in selection order. Keep the existing AC requiring new `REQ-DD` ids and req-marked tests (FR-888 lines 58-59), and add the capability file surface explicitly because this repo's pytest config has requirement markers and FR-887's enforcement record used a dedicated capability file for new behavior (pyproject.toml lines 31-34; FR-887 lines 140-150).

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | `tools/generate.py` or a new focused module under `tools/`: `GenerationOutcome` plus `generate_all(prompt, date, models, out_dir, runner/provider injection as needed)` implemented as a sequential fan-out over selected active roster models. |
| D-2 | `tools/roster.py` and/or `tools/inputs.py`: reusable model-list parsing/validation for all active models and explicit subsets, with unknown/duplicate behavior mechanically defined and tested. |
| D-3 | `tools/failures.py` / FR-887 boundary integration: fan-out failures are recorded with `run_source="probe"` and returned as failed outcomes only after the failure row is successfully written. |
| D-4 | Operator CLI surface only if an enforced prompt entry point exists or FR-889 is folded/enforced first; otherwise only the callable fan-out primitive and tests are authorized. |
| D-5 | Tests for sequential continuation after provider refusal, subset validation, no publish side effects, output path identity, failure-ledger write failure, and outcome ordering. |
| D-6 | Capability registry update with new `REQ-DD` ids and req-marked tests. |
| D-7 | `README.md`: comparison workflow documentation that accurately reflects whether the CLI is active now or awaits FR-889. |

Not authorized: implementing `--prompt` / `--prompt-file` semantics from FR-889, publishing fan-out outputs, touching DeviantArt API paths, writing `state/published.jsonl`, consuming publish slots, changing daily workflow behavior, adding parallel execution, changing the active roster, adding retries or prompt mutation, implementing FR-886 routing, reviving FR-885 synthetic probes, or modifying CI/hooks/judge/review doctrine.

## Revised acceptance criteria

- [ ] AC-01: A mocked fan-out over three valid active roster models where model 2 raises a provider refusal generates outputs for models 1 and 3, appends exactly one `state/failures.jsonl` row with `run_source="probe"`, and returns three ordered `GenerationOutcome` values.
- [ ] AC-02: `--all-models` or the callable equivalent resolves to every usable active roster model in deterministic order before generation begins.
- [ ] AC-03: `--models` or the callable equivalent honors an explicit subset in the specified deterministic order; any unknown model name fails before the first provider call or file write and reports the valid active list.
- [ ] AC-04: Duplicate model names in an explicit subset follow a stated tested rule: either fail fast before generation or collapse to one run before output paths are allocated.
- [ ] AC-05: Fan-out writes no rows to `state/published.jsonl`, calls no `tools.da_api` function, and consumes no slot; mocked tests fail if any DeviantArt publish path is touched.
- [ ] AC-06: Each successful selected model writes to a distinct output path derived from `(out_dir, date, model_name)`, and a test proves two successful models cannot clobber each other.
- [ ] AC-07: If failure-ledger append/commit fails for a model failure, the fan-out run exits red with the original provider failure and the ledger failure both inspectable; it does not continue and does not return a success-shaped outcome list.
- [ ] AC-08: `GenerationOutcome` is typed and includes model name, slug, status, and exactly one of output path or `FailureRecord`; tests assert one outcome per selected model when ledger writes succeed.
- [ ] AC-09: Operator CLI documentation and tests are present only when an enforced entry point exists; if FR-889 is not yet enforced, this FR documents the callable fan-out primitive and explicitly defers CLI activation.
- [ ] AC-10: New `REQ-DD` ids are added to a capability file, and every new/changed test carries `@pytest.mark.req(...)` linked to those ids.
- [ ] AC-11: README documents the comparison workflow, output directory/path shape, failure-row behavior, no-publish boundary, and the dependency relationship with FR-889.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | Authority is not active until R-1 through R-6 are folded into the FR. | GATE |
| C-2 | FR-888 enforcement must not implement FR-889's user prompt entry point unless FR-889 has separately granted and frozen that authority. | GATE |
| C-3 | Fan-out must be sequential; no parallel provider calls are authorized. | GATE |
| C-4 | Provider failures may be converted into failed outcomes only after the FR-887 failure row is successfully appended/committed. | GATE |
| C-5 | A failure-ledger write/commit failure must abort red; it must not be treated as an ordinary per-model refusal. | GATE |
| C-6 | `state/published.jsonl`, DA submit/publish APIs, publish workflows, and slot identity are out of scope. | GATE |
| C-7 | Model subset validation must complete before the first provider call or output write. | GATE |
| C-8 | All new behavior must be witnessed by req-marked tests linked to capability registry entries. | GATE |

Authority granted: after the revisions are folded, the enforcer may build only the sequential generation fan-out primitive, optional properly gated model-selection CLI flags, FR-887-backed probe failure rows, distinct per-model output files, tests, capability entries, and README comparison documentation described above.
