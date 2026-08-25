# Judgement: FR-887 Structured Generation-Failure Logging

**Verdict:** APPROVED WITH REVISIONS — the failure ledger is a real and minimal supply-side evidence source, but authority activates only after the FR fixes the boundary/context mismatch, defines commit-failure semantics, and makes the failure schema and tests mechanically complete.

**Reviewed against:** `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-887-structured-generation-failure-logging.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/.github/skills/judge-fr/doctrine.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/.github/skills/judge-fr/judgement.template.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/AGENTS.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/README.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/graph.yaml`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/generate.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/steps.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/ledger.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tools/roster.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tests/test_ledger.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tests/test_steps.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/tests/test_provider_type_lie.py`; `/Users/sami.j.p.heikkinen/src/deviant-daily/capabilities/README.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/capabilities/CAP-06-idempotency-ledger.yaml`; `/Users/sami.j.p.heikkinen/src/deviant-daily/capabilities/CAP-09-roster-corpus-and-post-rendering.yaml`; `/Users/sami.j.p.heikkinen/src/deviant-daily/pyproject.toml`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-885-replicate-model-tolerance-fingerprinting.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-885-replicate-model-tolerance-fingerprinting.judgement.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-886-corpus-fingerprint-and-deterministic-draw-routing.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-888-generate-all-selected-providers.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-889-user-given-prompt-option.md`; `/Users/sami.j.p.heikkinen/src/deviant-daily/feature-requests/FR-890-corpus-haiku-fingerprint-enrichment.md`. Cited but absent under input closure: `/Users/sami.j.p.heikkinen/src/deviant-daily/.github/copilot-instructions.md`.

## What is sound

The problem is real and the first consumer is concrete. The current pipeline draws and commits the prompt before generation (tools/steps.py lines 63-96), then `generate_step()` calls `generate_image()` and returns only on success (tools/steps.py lines 99-102). `generate_image()` can raise `GenerationError` for missing token or unexpected provider output, and httpx/Replicate exceptions also propagate without a structured artifact (tools/generate.py lines 18-37 and 54-62). Because the graph marks the generate node `on_error: fail` (graph.yaml lines 50-58), a refused generation can kill the run after the draw ledger row without preserving the provider refusal as typed data, matching FR-887's problem statement (FR-887 lines 31-38).

The scope is appropriately small and single-responsibility. FR-887 limits itself to record-then-reraise failure capture and explicitly defers retries, routing, and model selection to FR-886 (FR-887 lines 50-53 and 73-77). That matches the repo's existing side-effect discipline: committed ledgers preserve knowledge before the next external effect (README.md lines 48-54; tools/ledger.py lines 1-11), and the router FR names FR-887/FR-888/FR-889 outcome evidence as its supply-side dependency (FR-886 lines 8-18). Strategic classification: target-repo operational evidence primitive for generation failures, not a cross-repo framework primitive.

The proposed privacy shape is sound. Recording `prompt_sha` plus `source_file` rather than full prompt text (FR-887 lines 42-45 and 67-69) respects the corpus provenance boundary that raw unsanitized corpus stays local (README.md lines 23-46) while still allowing lookup against committed corpus rows. Keeping the raw provider excerpt beside a tolerant classification also follows repo doctrine: boundary output classification is a claim, not a silent fallback (FR-887 lines 46-49; AGENTS.md lines 73-80 and 219-220).

## Required revisions

### R-1: Move the logging boundary to the caller or pass the missing context explicitly

Amend the Proposed Solution so the failure row is recorded at `generate_step()` or at a new wrapper that receives the full draw/run context, not inside bare `generate_image()` unless its signature is explicitly expanded. FR-887 says to catch every failure at the `generate_image` boundary (FR-887 lines 16-18), but the row requires `date`, `slot`, roster `model`, `slug`, `source_file`, and `run_source` (FR-887 lines 42-45). The current `generate_image(prompt, model_config, output_path)` has no date, slot, source file, run source, or roster name (tools/generate.py lines 18-26), and the graph currently passes `source_file` and `slot` only to `gate_step()` and `publish_step()`, not to `generate_step()` (graph.yaml lines 50-58 and 69-91). Fold a concrete wiring change into the FR: either extend `generate_step(prompt, date, source_file, slot, model, run_source)` and the graph args, or introduce a separate generation-failure wrapper used by corpus/user/probe entry points.

### R-2: Define the failure-ledger write/commit primitive separately from publish statuses

Do not authorize reuse of `record_transition()` as-is for `state/failures.jsonl`. FR-887 requires appending `state/failures.jsonl` via the existing `record_transition` git pattern (FR-887 lines 50-52), but `record_transition()` calls `append_entry()`, and `append_entry()` rejects any status outside `drawn`, `submitted`, `published`, and `skipped` (tools/ledger.py lines 21-22, 67-77, and 105-122). Amend the FR to require a new failure-ledger helper that reuses `commit_push()` or the same add/commit/pull/push sequence without extending the publish ledger's status machine. The failure ledger must be its own artifact; `state/published.jsonl` remains the DA idempotency ledger only (README.md lines 48-54; CAP-06 lines 1-18).

### R-3: Specify commit-failure semantics without swallowing the generation exception

Amend the constraints and acceptance criteria to state what happens if writing or committing the failure row fails. "Record, then re-raise" is correct for provider failures (FR-887 lines 50-53 and 67-71), but the current commit helper raises `LedgerCommitError` on git failure before returning (tools/ledger.py lines 80-102; tests/test_ledger.py lines 81-90). The enforcer needs a testable rule for this two-error case: preserve the original generation exception as the primary failure and surface the logging/commit failure as explicit context, or raise a typed failure-ledger commit error that includes the original error class/message. Either choice is acceptable, but the FR must forbid a success-shaped exit and must not lose both the original provider message and the commit failure.

### R-4: Freeze the schema details that prevent accidental secret or prompt leakage

Amend `FailureRecord` to define exact field semantics: timestamp format, `date` format, nullable `slot` type, allowed `run_source`, prompt hash algorithm over the exact prompt bytes, `source_file` nullability for user/probe prompts, provider excerpt maximum length, and any redaction rule for secrets/tokens/URLs. The FR currently says the excerpt is capped and full prompt text is omitted (FR-887 lines 42-49 and 67-69), but it does not state the cap or redaction behavior. This must be mechanically testable because provider exceptions can contain arbitrary response text, and repo doctrine treats unprompted artifact changes and generated/system output as adversarial input (AGENTS.md lines 100-115 and 118-125).

### R-5: Bind failure classification to exception types and raw-message evidence

Replace "tolerant message matching" with a closed classification contract that names the checked exception families and keyword set. The repo already depends on `httpx` (pyproject.toml lines 6-13), and `generate_image()` uses `httpx.stream(... timeout=120)` and `raise_for_status()` (tools/generate.py lines 30-31), so `httpx.TimeoutException`, other `httpx.HTTPError`/transport failures, `GenerationError`, and provider exceptions can be unit-witnessed directly. The classifier may still use message keywords for provider refusals, but tests must assert that the raw excerpt is preserved and that unrecognized failures become `unknown` without being silently normalized away (FR-887 lines 46-49; judge doctrine lines 43-61).

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | `tools/generate.py`: generation exception taxonomy helpers only if they are provider-boundary concerns; no routing or retry behavior. |
| D-2 | `tools/steps.py` and `graph.yaml`: pass or preserve `date`, `slot`, `source_file`, roster model name, slug, and `run_source` at the generation-failure logging boundary. |
| D-3 | New or existing Python module for `FailureRecord`, `append_failure_record`, and committed failure-ledger write using the existing git commit/pull/push discipline without reusing publish statuses. |
| D-4 | `state/failures.jsonl`: append-only structured failure rows. |
| D-5 | Tests for refusal, transport, timeout, unknown, success-no-row, context wiring, prompt hashing/no prompt text, provider excerpt preservation/redaction, and failure-ledger commit failure behavior. |
| D-6 | Capability registry update with new `REQ-DD` ids covering generation-failure logging, and req-marked tests. |
| D-7 | `README.md`: document `state/failures.jsonl`, field meanings, and the consumer path into FR-886/FR-888/FR-889. |

Not authorized: retries, prompt mutation, prompt filtering or softening, draw-time routing/model selection changes, fan-out implementation, user-prompt CLI implementation, synthetic tolerance probing, changes to DeviantArt publish behavior, rewriting `state/published.jsonl`, changing the roster, changing workflow triggers except the minimal graph argument wiring required for failure context, committing full prompt text to failure rows, or modifying judge/review doctrine or CI enforcement infrastructure.

## Revised acceptance criteria

- [ ] AC-01: A mocked provider refusal during corpus `generate_step` appends and commits exactly one `FailureRecord` row to `state/failures.jsonl`, then the run exits red by re-raising or surfacing the original generation failure according to the R-3 rule.
- [ ] AC-02: The logged corpus-row failure includes `date`, integer `slot`, roster `model` name, roster `slug`, `source_file`, `prompt_sha`, `error_class="refusal"`, capped/redacted `provider_message`, and `run_source="corpus"`; it does not include full prompt text.
- [ ] AC-03: Mocked tests witness `error_class` values `refusal`, `transport`, `timeout`, and `unknown`; every branch preserves a capped/redacted raw provider excerpt.
- [ ] AC-04: A mocked successful generation writes no row to `state/failures.jsonl`.
- [ ] AC-05: Failure-ledger writing is append-only and committed with git add, commit, pull --rebase, and push discipline equivalent to `commit_push()`; it does not add new statuses to `state/published.jsonl`.
- [ ] AC-06: A failure while writing or committing the failure row is tested and cannot produce a green/success-shaped exit; the original provider failure and the logging failure are both inspectable.
- [ ] AC-07: `prompt_sha` is computed from the exact prompt bytes passed to the provider, and tests prove the full prompt string is absent from the failure row.
- [ ] AC-08: `source_file` and `slot` nullability are tested for non-corpus runs, with `run_source="user"` and `run_source="probe"` available for FR-889 and FR-888 consumers without implementing those FRs here.
- [ ] AC-09: New `REQ-DD` ids are added to a capability file, and every new/changed test carries `@pytest.mark.req(...)` linked to those requirements.
- [ ] AC-10: README documents `state/failures.jsonl`, field meanings, failure classes, privacy boundary, and that FR-886/FR-888/FR-889 consume these rows without this FR implementing routing, fan-out, or user-prompt entry points.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | Authority is not active until R-1 through R-5 are folded into the FR. | GATE |
| C-2 | The implementation must never swallow a generation exception or convert it into a green run after writing a failure row. | GATE |
| C-3 | Full prompt text, secrets, tokens, and unredacted secret-bearing provider payloads must not be committed to `state/failures.jsonl`. | GATE |
| C-4 | `state/published.jsonl` remains the publish idempotency ledger; failure rows must not broaden its status enum or alter its resume semantics. | GATE |
| C-5 | Enforcement must not implement retries, routing, fan-out, user-prompt CLI, synthetic probing, or roster changes under this FR. | GATE |
| C-6 | Any change to workflow triggers, CI, hooks, or judge/review doctrine beyond minimal graph argument wiring requires separate human-reviewed authority. | GATE |
| C-7 | All new behavior must be witnessed by req-marked tests linked to capability registry entries. | GATE |

Authority granted: after the revisions are folded, the enforcer may implement only append-only structured logging of image-generation failures to `state/failures.jsonl`, with committed rows and unchanged failure control flow.
