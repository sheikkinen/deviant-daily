# Judgement: FR-891 Refusal is a routing event - re-route on refusal, honour the operator's pin

**Verdict:** APPROVED WITH REVISIONS - the defect is real and the fix direction is aligned with the existing routing/failure-ledger architecture, but authority activates only after the FR freezes resume-status safety, failure-ledger commit semantics, retry selection, and replay acceptance mechanically.

**Reviewed against:** `feature-requests/FR-891-refusal-reroute-and-honored-pin.md`; `.github/skills/judge-fr/doctrine.md`; `.github/skills/judge-fr/judgement.template.md`; `AGENTS.md`; `feature-requests/FR-886-corpus-fingerprint-and-deterministic-draw-routing.md`; `feature-requests/FR-886-corpus-fingerprint-and-deterministic-draw-routing.judgement.md`; `feature-requests/FR-887-structured-generation-failure-logging.md`; `feature-requests/FR-887-structured-generation-failure-logging.judgement.md`; `feature-requests/FR-888-generate-all-selected-providers.md`; `feature-requests/FR-888-generate-all-selected-providers.judgement.md`; `feature-requests/FR-890-corpus-haiku-fingerprint-enrichment.md`; `feature-requests/FR-890-corpus-haiku-fingerprint-enrichment.judgement.md`; `feature-requests/FR-890-evidence.md`; `state/published.jsonl`; `state/failures.jsonl`; `tools/steps.py`; `tools/route.py`; `tools/ledger.py`; `tools/failures.py`; `tools/fanout.py`; `tools/inputs.py`; `tools/roster.py`; `graph.yaml`; `.github/workflows/_pipeline.yml`; `.github/workflows/daily.yml`; `.github/workflows/publish-now.yml`; `tests/test_route.py`; `tests/test_steps.py`; `capabilities/CAP-18-draw-routing.yaml`; `scripts/req_coverage.py`; `pyproject.toml`. Cited but absent under input closure: `.github/copilot-instructions.md` and `capabilities/CAP-19-refusal-reroute.yaml`.

## What is sound

The problem is real and witnessed in committed artifacts. FR-891 names a first consumer and event: the next scheduled `daily-publish` run after a provider refusal should try another eligible model instead of repeating the same refused call (`feature-requests/FR-891-refusal-reroute-and-honored-pin.md` lines 8-11). The failure ledger contains five 2026-09-08 refusal rows for prompt SHA `45661289770...`, all on `model: grok` (`state/failures.jsonl` lines 5-9), while the publish ledger still has the 2026-09-08 slot at `status: "drawn"` with the same prompt/source and `model: "grok"` (`state/published.jsonl` line 120). That substantiates the loop described by the FR, not just a hypothetical routing concern.

The diagnosis matches the code. `draw_step()` resumes any non-terminal slot before it parses the live `model` input (`tools/steps.py` lines 105-117), and `_resumed()` returns the committed prompt and model unchanged (`tools/steps.py` lines 62-72). `generate_step()` logs a `FailureRecord` on exception and then re-raises (`tools/steps.py` lines 159-182), while `TERMINAL` is only `("published", "skipped")` (`tools/ledger.py` lines 21-22). Those lines directly support FR-891's claim that a refused `drawn` row is neither terminal nor re-routed on the next run (`feature-requests/FR-891-refusal-reroute-and-honored-pin.md` lines 55-72).

The proposed direction reuses the right primitives. FR-886 already established refusal-only routing evidence and draw-bound model binding (`feature-requests/FR-886-corpus-fingerprint-and-deterministic-draw-routing.md` lines 25-27, 91-96, 130-135), and the implementation exposes pure `refusal_evidence`, `eligible_models`, and `route` functions (`tools/route.py` lines 81-120). FR-887 already defines the generation failure row, `error_class`, redacted provider excerpt, and record-then-reraise semantics (`feature-requests/FR-887-structured-generation-failure-logging.md` lines 50-78; `tools/failures.py` lines 35-68). Extending `generate_step()` to treat a committed refusal as a routing event is therefore an architecture-aligned bug fix, not a new framework.

The FR is mostly measurable. AC-1 through AC-6 map to direct unit tests around mocked provider failures, failure rows, model binding commits, and resume behavior (`feature-requests/FR-891-refusal-reroute-and-honored-pin.md` lines 153-173). The current test suite already has req-marked routing witnesses for no-ledger skip, draw-bound generation, graph binding, and pinned draw bypass (`tests/test_route.py` lines 137-204), and the repo has an explicit requirement coverage gate (`scripts/req_coverage.py` lines 4-11, 91-108; `pyproject.toml` lines 32-34).

Strategic classification: target-repo operational bugfix / policy refinement. This is not a framework primitive; it has one production failure mode, one operator escape hatch, and existing repo abstractions are sufficient.

## Required revisions

### R-1: Constrain pin override to safe resume statuses

Amend the pin-on-resume section so a differing operator pin may rebind only an existing `drawn` slot before generation. If the latest non-terminal row is `submitted` or any future status after an external side effect, the implementation must fail red with an explicit message or defer to a separate FR; it must not silently ignore the pin and must not mutate the model binding after a side-effect-guarding transition. Current resume covers every non-terminal status (`tools/steps.py` lines 105-113), while the ledger doctrine says transitions guard external calls and reruns resume incomplete records rather than drawing fresh (`tools/ledger.py` lines 3-10). FR-891's current wording says "a pin on resume overrides the committed binding" without this status boundary (`feature-requests/FR-891-refusal-reroute-and-honored-pin.md` lines 144-151).

### R-2: Preserve FR-887 two-error semantics before any reroute

State that `generate_step()` may reroute only after the refusal `FailureRecord` is successfully appended and committed. If appending or committing `state/failures.jsonl` fails, the original provider exception remains the primary failure with the failure-ledger error attached, and no retry is attempted. FR-887 explicitly owns that two-error behavior (`feature-requests/FR-887-structured-generation-failure-logging.md` lines 72-78), and current `generate_step()` implements it by adding a note and raising the provider exception from the ledger exception (`tools/steps.py` lines 166-182). FR-891 currently specifies commit-before-call for retry bindings, but not failure-ledger write failure before reroute (`feature-requests/FR-891-refusal-reroute-and-honored-pin.md` lines 158-163).

### R-3: Define the current-prompt evidence lookup and retry selection rule

Fold a concrete algorithm into the FR: compute the current prompt's content tuple from the committed corpus row matched by `prompt_sha` and/or `source_file`; load refusal evidence after the just-recorded refusal is committed; subtract every model attempted in this `generate_step()` invocation; then choose the next model by a named deterministic rule. If the rule reuses `route()`, the RNG/seed must be an explicit test input; otherwise use `sorted(eligible_models(...))` and pick the first remaining model. The existing evidence join is by prompt SHA (`tools/route.py` lines 81-96), eligibility is sorted and pure (`tools/route.py` lines 100-104), and `route()` is only deterministic when its RNG is controlled (`tools/route.py` lines 107-120). FR-891 currently says "next eligible roster model" and "minus the models already attempted" but does not freeze "next" or the lookup path (`feature-requests/FR-891-refusal-reroute-and-honored-pin.md` lines 112-116).

### R-4: Define commit-failure behavior for reroute and exhaustion transitions

Specify that each retry `drawn` transition and exhaustion `skipped` transition must include the same `date`, `slot`, `prompt`, and `source_file` as the existing slot plus the new `model` or `reason`; if `record_transition()` fails, the provider call must not happen and the run must exit red with the transition failure inspectable. `record_transition()` raises before returning when the git add/commit/pull/push sequence fails (`tools/ledger.py` lines 80-122), and FR-891 correctly requires retry binding commits before provider calls (`feature-requests/FR-891-refusal-reroute-and-honored-pin.md` lines 122-129), but AC-5 does not say what happens when the terminal `skipped` commit fails (`feature-requests/FR-891-refusal-reroute-and-honored-pin.md` lines 167-169).

### R-5: Reconcile generate-time exhaustion with FR-886 draw-time skip semantics

Amend the scope and acceptance criteria to preserve the distinction between draw-time unroutable candidates and an already-drawn slot exhausted during generation. FR-886/CAP-18 says draw routing skips unroutable candidates with zero ledger writes before a slot is burned (`capabilities/CAP-18-draw-routing.yaml` lines 4-9, 28-33), while FR-891 proposes committing `skipped` for an already committed slot after all retry candidates refuse (`feature-requests/FR-891-refusal-reroute-and-honored-pin.md` lines 131-142). Both can be correct, but the FR must say this `skipped` write is authorized only for the already-existing slot and must not change `_route_candidate()`'s no-ledger skip behavior (`tools/steps.py` lines 75-93).

### R-6: Correct the authorized surfaces and capability placement

Replace "Three changes, all inside `tools/steps.py`" with the actual frozen surfaces. The FR lists four solution sections and also requires tests and a capability file (`feature-requests/FR-891-refusal-reroute-and-honored-pin.md` lines 97-100, 177-179). Authorize `tools/steps.py` for control flow, `tools/route.py` only for a pure helper if needed by R-3, `tests/test_steps.py`/`tests/test_route.py`, and either a new `capabilities/CAP-19-refusal-reroute.yaml` or an explicit extension of `CAP-18` with REQ-DD-118..123. No graph or workflow changes are needed unless the folded FR adds a tested reason; current graph wiring already passes the operator model into draw and the draw-bound model into generate (`graph.yaml` lines 42-60), while `publish-now` already forwards the manual input (`.github/workflows/publish-now.yml` lines 37-43).

### R-7: Make the replay criterion offline and exact

Rewrite AC-7 as an offline fixture test, not an aspirational "publishes" claim. The fixture must load or reproduce the committed 2026-09-08 `drawn` row (`state/published.jsonl` line 120) and refusal rows (`state/failures.jsonl` lines 5-9), stub the provider so `grok` refuses and another eligible roster model succeeds, and assert the graph/node sequence reaches the post-generation path without a real Replicate or DeviantArt call. The daily workflow is scheduled (`.github/workflows/daily.yml` lines 3-8) and the generate node fails red on unhandled errors (`graph.yaml` lines 51-61), so replay must prove the reroute behavior at the Python boundary without relying on live CI, provider state, or DA publishing.

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | `tools/steps.py`: refusal-only reroute loop inside `generate_step()` after successful failure-row commit; retry `drawn` transition before each retry call; exhaustion `skipped` transition for the existing slot; `draw_step()` resume pin handling limited by R-1. |
| D-2 | `tools/route.py`: optional pure helper(s) only if needed to compute the current prompt content tuple or deterministic next eligible model; no network, LLM, ledger write, or roster mutation. |
| D-3 | `tests/test_steps.py` and `tests/test_route.py`: mocked provider/runner tests for refusal reroute, non-refusal no-reroute, attempted-model exclusion, retry commit failure, skipped commit failure, pin-on-drawn resume, unsafe-status pin behavior, and the 2026-09-08 replay fixture. |
| D-4 | Capability registry: `capabilities/CAP-19-refusal-reroute.yaml` or a justified extension of `capabilities/CAP-18-draw-routing.yaml` registering REQ-DD-118..123 and any added requirement IDs. |
| D-5 | Requirement coverage: req-mark every new/changed test and keep `python3 scripts/req_coverage.py --strict` green. |

Not authorized: new publish-ledger statuses; prompt rewriting, softening, filtering, or redraw; roster admission/retirement; broad retry on transport/timeout/unknown; parallel provider calls; FR-888 fan-out behavior; DA submit/publish policy changes; graph edge changes; workflow trigger/concurrency/permission changes; failure-row schema changes except reuse of existing fields; draw-time `_route_candidate()` ledger writes for skipped candidates; CI, hooks, judge/review doctrine, or skill/adapters.

## Revised acceptance criteria

- [ ] AC-01: A mocked refusal from the bound model appends and commits exactly one FR-887 failure row, then reroutes within the same `generate_step()` invocation only when `error_class == "refusal"`; `transport`, `timeout`, and `unknown` still append one failure row, re-raise, and leave the slot at `drawn`.
- [ ] AC-02: If the failure-ledger append/commit fails, no reroute is attempted; the original provider failure and the failure-ledger failure are both inspectable, preserving FR-887 two-error semantics.
- [ ] AC-03: Rerouting computes the current prompt content tuple from the committed corpus row matched to the prompt, consults evidence including the just-committed refusal row, subtracts all models already attempted in the current invocation, and chooses the next model by the deterministic rule folded under R-3.
- [ ] AC-04: Before each retry provider call, `generate_step()` commits a new `drawn` transition for the same `date`, `slot`, `prompt`, and `source_file` with the new bound `model`; a failed commit aborts red before the retry call.
- [ ] AC-05: On a successful retry, `generate_step()` returns `model_name` for the model that actually produced `image_path`, and the graph continues through the existing generate-to-describe edge without any graph edge change.
- [ ] AC-06: When no eligible unattempted model remains for the already-drawn slot, `generate_step()` commits `skipped` with reason `unroutable: every roster model refused` for that slot and re-raises the last provider error; a following `draw_step()` run treats the terminal slot as complete and draws the next candidate.
- [ ] AC-07: If the exhaustion `skipped` transition fails to commit, the run exits red and does not claim the slot is terminal; the provider failure and commit failure are inspectable.
- [ ] AC-08: A differing operator pin on a resumed `drawn` row is parsed before the resume return, commits a new `drawn` transition with the pinned model and unchanged `date`, `slot`, `prompt`, and `source_file`, and generation uses that pinned model.
- [ ] AC-09: A differing operator pin on a resumed non-`drawn` non-terminal row follows the folded R-1 rule: explicit red failure or separately authorized behavior, never silent discard and never unsafe rebinding after side-effect-guarding transitions.
- [ ] AC-10: An offline replay fixture for the committed 2026-09-08 slot (`state/published.jsonl` line 120 plus `state/failures.jsonl` lines 5-9) stubs providers so `grok` refuses and another eligible roster model succeeds, proving the run escapes the refusal loop without live Replicate or DeviantArt calls.
- [ ] AC-11: REQ-DD-118..123 are registered in the capability registry, every new/changed test is marked with the corresponding `@pytest.mark.req(...)`, and `python3 scripts/req_coverage.py --strict` passes.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | Authority is not active until R-1 through R-7 are folded into FR-891. | GATE |
| C-2 | Only `error_class="refusal"` may trigger reroute; transport, timeout, and unknown failures remain record-then-reraise with the existing drawn slot resumable. | GATE |
| C-3 | A retry provider call is forbidden until both the refusal failure row and the new `drawn` binding transition have been successfully committed. | GATE |
| C-4 | The current invocation must not retry a model it already attempted, even if that model remains eligible by older evidence. | GATE |
| C-5 | Operator pin override is authorized only at a safe pre-generation `drawn` resume boundary unless a separate human-reviewed FR expands the state machine. | GATE |
| C-6 | Generate-time exhaustion may terminalize only the already-existing slot; draw-time unroutable candidate skips must remain zero-ledger-write behavior. | GATE |
| C-7 | Enforcement must not change graph edges, workflow triggers, roster policy, failure schema, DA publish policy, CI/hooks, or judge/review doctrine under this FR. | GATE |
| C-8 | All new behavior must be witnessed by req-marked offline tests linked to capability requirements. | GATE |

Authority granted: after the required revisions are folded into FR-891, the enforcer may implement only refusal-triggered rerouting and safe operator-pin honoring for an already drawn slot, using the existing failure ledger, routing primitives, publish ledger transitions, tests, and capability registry surfaces named above.
