# Judgement: FR-889 User-Given Prompt Option

**Verdict:** APPROVED WITH REVISIONS — the operator-prompt path is a real, narrow generation-only capability, but authority activates only after the FR freezes the CLI surface, output identity, prompt-file byte semantics, and publish-ledger boundary.

**Reviewed against:** `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-889-user-given-prompt-option.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/.github/skills/judge-fr/doctrine.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/.github/skills/judge-fr/judgement.template.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/AGENTS.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/README.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/graph.yaml`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/generate.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/steps.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/failures.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/inputs.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/roster.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tests/test_dispatch.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tests/test_failures.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/pyproject.toml`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-887-structured-generation-failure-logging.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-887-structured-generation-failure-logging.judgement.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-888-generate-all-selected-providers.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-888-generate-all-selected-providers.judgement.md`. Cited but absent under input closure: `/Users/sami.j.p.heikkinen/src/deviant-daily/.github/copilot-instructions.md`.

## What is sound

The problem is real and the first consumer/event is concrete. FR-889 names the operator at the first ad-hoc command-line generation as the consumer and event (FR-889 lines 8-10). The current committed pipeline draws from the corpus before generation: `draw_step()` validates the roster, reads `state/published.jsonl`, draws from `prompts/corpus.jsonl`, and commits a `drawn` row (tools/steps.py lines 65-98), while `graph.yaml` wires `draw` directly into `generate` with the drawn prompt (graph.yaml lines 42-60). There is no operator-facing prompt input in README workflow inputs, only `model` and `date` (README.md lines 95-117). The FR therefore addresses an actual missing surface rather than duplicating an existing one.

The requested core behavior aligns with the existing architecture if kept as a generation-only entry point. `generate_step(prompt, date, model, source_file, slot, run_source, runner)` already accepts a prompt and has the full FR-887 failure logging boundary, including `run_source="user"` and null `slot`/`source_file` support for non-corpus runs (tools/steps.py lines 101-133; tests/test_failures.py lines 175-191). `generate_image()` passes the prompt to `replicate.run()` as the `input["prompt"]` value (tools/generate.py lines 18-26), so an exact pass-through test is feasible. FR-887 is enforced and documents `run_source="user"` as a supported failure-row source for FR-889 (FR-887 lines 50-58 and 104-116; README.md lines 56-73).

The scope is mostly single-responsibility. `--prompt` and `--prompt-file` are two input forms for the same operator-owned prompt capability, and the FR explicitly excludes prompt history, templating, publishing user-prompt outputs, and publish coupling (FR-889 lines 14-17, 46-47, and 67-71). Strategic classification: target-repo operational entry point/contrib capability, not a framework primitive; it serves one immediate operator use case by exposing existing generation machinery safely outside the publishing pipeline.

## Required revisions

### R-1: Freeze the operator entry point and keep it outside the publish graph

Amend the Proposed Solution to name the exact executable surface and its call contract. The current wording allows either a new `scripts/generate.py` or an "existing dispatch" extension (FR-889 lines 38-41), but the existing workflow/graph path publishes by design after draw/generate/describe/gate/publish (graph.yaml lines 42-118), and README states "Running it publishes" with no dry-run or force flag (README.md lines 100-108). Freeze a separate generation-only CLI, e.g. `scripts/generate.py --prompt ... [--model ...] [--date ...] [--out-dir ...]`, or explicitly name the non-publish dispatch extension and prove it cannot enter `draw_step`, `describe_step`, `gate_step`, `publish_step`, `state/published.jsonl`, or DeviantArt APIs. Do not authorize changes to `.github/workflows/*` or the daily publish graph under this FR.

### R-2: Define output identity so ad-hoc runs cannot silently clobber each other

Amend the FR to specify where successful user-prompt images are written and how paths are derived. The current `generate_step()` writes a single `/tmp/deviant-daily-{date}.png` path (tools/steps.py lines 113-116), which is acceptable for one publish pipeline run but can clobber repeated same-date ad-hoc generations and conflicts with FR-888's distinct per-model path contract (FR-888 lines 43-53 and 91-93). Require a deterministic output path for the user-prompt CLI, such as `<out_dir>/<date>-user-<model>.png` for single-model runs and FR-888's `<out_dir>/<date>-<model_name>.png` when fan-out is used, with parent directories created and no clobbering within one invocation.

### R-3: Replace "no ledger row" with "no publish-ledger row"

Amend the generation-only path wording to say user-prompt success writes no `state/published.jsonl` row, consumes no slot, and calls no DeviantArt publish path. FR-889 simultaneously requires FR-887 failure logging for refusals with `run_source="user"` (FR-889 lines 16-17 and 56-57) and says "no ledger row" (FR-889 lines 46-47), which is ambiguous in a repo that has both `state/published.jsonl` and `state/failures.jsonl` (README.md lines 48-73). The intended boundary should be: success writes only the generated image artifact; failure appends/commits exactly one `state/failures.jsonl` row via FR-887; neither path writes `state/published.jsonl`.

### R-4: Make prompt-file verbatim semantics mechanically testable

Amend `--prompt-file` to define byte/encoding behavior: read the file as UTF-8 text, preserve all contents including trailing newlines, and pass exactly that string to `replicate.run()`; invalid UTF-8 should fail before any provider call or file write with a clear error. FR-889 requires verbatim file contents and byte-identical prompt delivery (FR-889 lines 51-54 and 62-64), but without an encoding/newline rule the enforcer can accidentally strip, normalize, or decode differently while still appearing to satisfy the option shape. This revision is required by the repo's `plausible_wrong_answer` doctrine: assert semantic identity beyond type validation (AGENTS.md lines 73-80).

### R-5: Define argument conflict and model-selection preflight before side effects

Amend AC-3 and the Proposed Solution to enumerate the complete invalid combinations and preflight order. `--prompt` and `--prompt-file` must be mutually exclusive and one of them must be required for this generation-only command; any corpus/draw option or publish workflow invocation must be rejected before `draw_step()` can commit a slot (FR-889 lines 31-34 and 53-55; tools/steps.py lines 65-98). Model names must reuse the existing active-roster validation behavior so unknown names fail before provider calls or output writes (tools/inputs.py lines 40-48; tools/roster.py lines 89-97). If FR-888 fan-out flags are present, model subset validation must follow FR-888's already judged preflight contract before the first provider call (FR-888 judgement lines 55-67 and 73-80).

### R-6: Separate direct FR-889 authority from optional FR-888 composition

Amend the FR so its required deliverable is the single-model user prompt entry point, with FR-888 composition authorized only when the FR-888 primitive is present/enforced. FR-889 says it "composes with FR-888 `--all-models`/`--models`" (FR-889 lines 38-41), while FR-888 itself deferred CLI activation to FR-889 and authorized a callable fan-out primitive first (FR-888 lines 65-68 and 102-105). This is not a split, but the dependency must be explicit: FR-889 may add the CLI hooks for FR-888 flags only by calling the already-enforced fan-out primitive and preserving FR-888's sequential, no-publish, failure-ledger gates. It must not reimplement fan-out inside the user-prompt command.

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | New generation-only operator CLI, preferably `scripts/generate.py`, with `--prompt` and `--prompt-file` plus existing `--model`/`--date` parsing where needed. |
| D-2 | `tools/steps.py` and/or a focused wrapper: reuse the existing `generate_step()`/FR-887 boundary with `run_source="user"`, null `slot`, and null `source_file` for user prompts. |
| D-3 | Prompt-file reader/parser tests proving UTF-8, newline-preserving, verbatim prompt delivery to `replicate.run()`. |
| D-4 | Output-path handling for user-prompt images, including parent directory creation and no same-invocation clobbering. |
| D-5 | Optional FR-888 CLI integration only by delegating to the enforced fan-out primitive and preserving its model-selection, sequential, output-path, and failure-ledger contracts. |
| D-6 | Tests for prompt argv pass-through, prompt-file pass-through, invalid argument combinations, unknown model preflight, FR-887 user failure row, no publish side effects, and optional FR-888 composition if implemented. |
| D-7 | Capability registry update with new `REQ-DD` ids and req-marked tests. |
| D-8 | `README.md`: document generation-only usage, output path, failure-row behavior, no-publish boundary, model/date options, prompt-file encoding, and FR-888 composition if active. |

Not authorized: prompt rewriting, prompt softening, prompt filtering/veto beyond provider response and explicit argument validation, corpus draw for user-prompt runs, writes to `state/published.jsonl`, slot allocation, DeviantArt submit/publish calls, changes to daily/publish workflow triggers, changes to the active roster, retries, routing/FR-886 implementation, prompt templating/history, publishing user-prompt outputs, reimplementing FR-888 fan-out instead of delegating to it, or modifying CI/hooks/judge/review doctrine.

## Revised acceptance criteria

- [ ] AC-01: `scripts/generate.py --prompt "text"` or the frozen equivalent calls the generation boundary with exactly `text`; a mocked provider asserts byte-identical prompt delivery to `replicate.run()` input.
- [ ] AC-02: `--prompt-file path` reads UTF-8 text, preserves all file contents including trailing newlines, and passes exactly that string to `replicate.run()`; invalid UTF-8 fails before any provider call or output write.
- [ ] AC-03: `--prompt` and `--prompt-file` are mutually exclusive, exactly one is required for the user-prompt command, and any corpus draw/publish path combination is rejected before `draw_step()` or any ledger write.
- [ ] AC-04: A mocked user-prompt provider refusal appends and commits exactly one `state/failures.jsonl` row with `run_source="user"`, `slot=null`, `source_file=null`, and no full prompt text, then exits red per FR-887 two-error semantics.
- [ ] AC-05: A mocked successful user-prompt run writes an image to the FR-defined output path and writes no `state/published.jsonl` row, consumes no slot, calls no `tools.da_api` function, and does not invoke `describe_step`, `gate_step`, or `publish_step`.
- [ ] AC-06: Unknown model names fail through the existing roster validation before any provider call or output file write; valid pinned models are passed through to the generation boundary.
- [ ] AC-07: Repeated or multi-model user-prompt invocations in one command cannot clobber outputs; tests assert the exact output path shape for single-model and, if implemented, FR-888 fan-out runs.
- [ ] AC-08: If `--all-models` or `--models` is implemented with this FR, it delegates to the enforced FR-888 fan-out primitive and satisfies FR-888's ordered preflight, sequential execution, distinct output path, failure-ledger, and no-publish gates.
- [ ] AC-09: New `REQ-DD` ids are added to a capability file, and every new/changed test carries `@pytest.mark.req(...)` linked to those ids.
- [ ] AC-10: README documents the user-prompt command, prompt-file encoding/newline behavior, output location, model/date options, failure logging with `run_source="user"`, no-publish/no-slot boundary, and FR-888 composition status.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | Authority is not active until R-1 through R-6 are folded into the FR. | GATE |
| C-2 | User-prompt runs must never enter the publish graph, allocate a corpus slot, write `state/published.jsonl`, or call DeviantArt APIs. | GATE |
| C-3 | Prompt text may be passed to the provider and written only to the operator-selected image-generation call path; it must not be committed to `state/failures.jsonl` or publish/post artifacts under this FR. | GATE |
| C-4 | Prompt input must be verbatim after the defined CLI/file decoding boundary; no rewriting, filtering, augmentation, or safety pre-veto is authorized by this FR. | GATE |
| C-5 | FR-887 failure logging semantics remain intact: user refusals write `run_source="user"` rows and stay red; failure-ledger write/commit failures must not become success-shaped. | GATE |
| C-6 | FR-888 flags may be wired only to an enforced fan-out primitive and must preserve FR-888 gates; no independent fan-out implementation is authorized here. | GATE |
| C-7 | Any change to workflows, CI, hooks, judge/review doctrine, or daily publish behavior requires separate human-reviewed authority. | GATE |
| C-8 | All new behavior must be witnessed by req-marked tests linked to capability registry entries. | GATE |

Authority granted: after the revisions are folded, the enforcer may implement only the generation-only user-prompt CLI, verbatim prompt/file input handling, FR-887-backed `run_source="user"` failure logging, safe output-path handling, optional delegation to enforced FR-888 fan-out, tests, capability entries, and README documentation described above.
