# Judgement: FR-885 Replicate Image Model Tolerance Fingerprinting

**Verdict:** APPROVED WITH REVISIONS - the tolerance matrix is a real, bounded routing precursor, but authority activates only after the FR pins model/candidate identity, defines a dedicated closed-set vision judge, makes live-run acceptance measurable, and applies policy preflight to every model.

**Reviewed against:** `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-885-replicate-model-tolerance-fingerprinting.md`; `/Users/sheikki/Documents/src/deviant-daily/.github/skills/judge-fr/doctrine.md`; `/Users/sheikki/Documents/src/yamlgraph/.github/skills/judge-fr/doctrine.md`; `/Users/sheikki/Documents/src/yamlgraph/.github/skills/judge-fr/judgement.template.md`; `/Users/sheikki/Documents/src/deviant-daily/AGENTS.md`; `/Users/sheikki/Documents/src/deviant-daily/README.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-884-strip-not-drop-name-redaction.md`; `/Users/sheikki/Documents/src/deviant-daily/tools/roster.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/generate.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/vision.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/gate.py`; `/Users/sheikki/Documents/src/deviant-daily/tools/steps.py`; `/Users/sheikki/Documents/src/deviant-daily/graph.yaml`; `/Users/sheikki/Documents/src/deviant-daily/.github/workflows/_pipeline.yml`; `/Users/sheikki/Documents/src/deviant-daily/capabilities/README.md`; `/Users/sheikki/Documents/src/deviant-daily/capabilities/CAP-09-roster-corpus-and-post-rendering.yaml`; `/Users/sheikki/Documents/src/deviant-daily/pyproject.toml`. Cited but absent/new under input closure: `/Users/sheikki/Documents/src/deviant-daily/state/tolerance/`.

## What is sound

The problem is real and tied to an immediate consumer: the current roster has five active Replicate models (README.md lines 52-61; tools/roster.py lines 26-62), while the FR states the operator needs a roster decision at the next roster event rather than a speculative future feature (FR-885 lines 8-11). The value statement is also concrete: silent sanitization is not visible from API failures alone (FR-885 lines 29-38), and repo doctrine warns that semantically wrong model output can pass shape checks unless tested beyond structure (AGENTS.md lines 73-80).

The scope is mostly minimal and single-responsibility. It builds a dated measurement artifact, not draw-time routing; the FR explicitly defers the routing consumer (FR-885 lines 138-140). The 9-probe ladder is bounded to three visual mature classes from the existing DeviantArt enum (FR-885 lines 55-63; tools/gate.py lines 28-42), and the compliance constraints forbid retrying or prompt mutation after a refusal (FR-885 lines 84-95). Strategic classification: target-repo operational measurement artifact, not a framework primitive.

The implementation is feasible in this repository's shape. Image generation already goes through a Replicate wrapper (tools/generate.py lines 18-37), the roster is centralized (tools/roster.py lines 26-62), and the existing vision module already handles image normalization and Anthropic structured output at the boundary (tools/vision.py lines 127-182). The FR also correctly rejects a YAMLGraph map for the cost-critical sequential ladder, because early-stop per model/class is load-bearing (FR-885 lines 121-127).

## Required revisions

### R-1: Pin model identity and candidate selection mechanically

Amend the Proposed Solution and acceptance criteria so the runner records an immutable Replicate version identity for every roster and candidate model, and so candidate discovery is reproducible. The FR requires a version pin in the artifact (FR-885 lines 80-82) but the active roster currently stores only slugs/params (tools/roster.py lines 26-62), and `generate_image()` runs `replicate.run(model_config["slug"], ...)` without a version argument or captured version metadata (tools/generate.py lines 24-26). Define whether the runner calls an explicit version, resolves latest once then records the version id/digest, or records a Replicate API model-version field; the matrix must include the chosen method and value. Candidate selection must be frozen as a dated snapshot of at most three entries with slug, version, source URL/API payload hash, and exclusion reason for skipped candidates.

### R-2: Define a dedicated closed-set tolerance vision judge

Do not describe this as simply "reusing `tools/vision.py`" without naming the new surface. The existing module is a publish-description path whose prompt lives in `prompts/describe_post.yaml` and returns `PostDescription` for DeviantArt publishing (tools/vision.py lines 1-6 and 160-182). The FR instead needs a closed question - whether a specific class attribute at a specific rung is present (FR-885 lines 73-79). Amend scope to add a dedicated function, prompt, and Pydantic schema for tolerance judging, reusing only the image preparation/provider plumbing from `tools/vision.py`. Its output must be closed-set enough to distinguish `ok` from `sanitized` mechanically.

### R-3: Make live-run acceptance measurable instead of outcome-dependent

Replace the acceptance criterion requiring "at least one real cell of each reachable outcome type" (FR-885 lines 108-110). The live environment may legitimately produce no `sanitized`, no `refused`, or no `error` cells, so this criterion is not mechanically satisfiable by implementation alone. The judge doctrine requires acceptance criteria to be mechanically checkable (judge doctrine lines 43-44) and tests to be derivable without missing fixtures (judge doctrine lines 58-61). Require mocked/unit witnesses for every outcome taxonomy branch, and require the live run to commit whatever outcomes actually occurred with counts and representative cell references in the FR Implementation Record.

### R-4: Apply policy preflight to every model and freeze the probe safety envelope

Amend the compliance framing so the ToS/Replicate-page check happens before probing every roster and candidate model, not only candidates. The current text limits the policy precheck to "Before probing a candidate model" (FR-885 lines 90-93), but roster models can also prohibit mature or gore content. Also commit the exact probe file before any live run and state the hard exclusions: no rung above `mature`, no explicit sexual-act prompt, no minors, no non-consensual content, no real-person likeness, and no prompt mutation or retry after refusal. This keeps the proposal as compliance discovery rather than filter evasion, matching the FR's stated intent (FR-885 lines 84-95) and the judge doctrine requirement to surface safety/product decisions explicitly (judge doctrine lines 100-101).

### R-5: Bind the new tests to the capability registry

Add capability/requirement updates to scope and acceptance criteria. This repo requires every test function to carry `@pytest.mark.req(...)` linked to a capability requirement (capabilities/README.md lines 20-26; pyproject.toml lines 31-34). Existing CAP-09 covers roster, corpus, and post rendering (CAP-09 lines 1-51), but it does not cover tolerance probes, version-pinned model fingerprinting, policy short-circuiting, or matrix schema validation. Add a new capability or extend the appropriate existing one, then require all new tests to carry the new requirement ids.

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | `data/tolerance_probes.json`: exactly 9 minimal-pair probes, 3 classes x 3 rungs, with the safety envelope stated in R-4. |
| D-2 | `scripts/probe_tolerance.py`: sequential runner over roster plus at most three frozen candidates, with policy preflight, pinned version identity, early-stop, and JSON matrix output. |
| D-3 | `tools/vision.py` plus prompt/schema surface as needed: dedicated closed-set tolerance judge that reuses image preparation but does not reuse the publish-description contract as-is. |
| D-4 | Pydantic schema for `state/tolerance/<date>-matrix.json`, covering model slug, version identity, candidate/roster source, probe SHA, timestamp, per-cell outcome, refusal/policy/error reason, and image hash. |
| D-5 | `state/tolerance/<date>-matrix.json`: one live run artifact only; generated images are not committed. |
| D-6 | Tests for early-stop, policy short-circuit, version identity capture, schema validation, outcome taxonomy, sanitized detection, and no image commit path. |
| D-7 | Capability registry update for the new tested requirements. |
| D-8 | README or roster documentation pointer to the matrix as the source of routing knowledge. |
| D-9 | FR Implementation Record summarizing live-run counts, candidate snapshot, spend, and any void/error cells. |

Not authorized: draw-time routing, changing daily publish behavior, changing the active roster, admitting or retiring models, modifying corpus selection/redaction, adding workflow triggers, retrying or mutating refused prompts, committing generated images, or probing content outside the `safe`/`suggestive`/`mature` envelope.

## Revised acceptance criteria

- [ ] AC-01: `data/tolerance_probes.json` validates as exactly `classes={nudity, sexual, gore}` x `rungs={safe, suggestive, mature}`, with minimal-pair prompts and no explicit/prohibited safety-envelope violations.
- [ ] AC-02: Candidate discovery is frozen in the matrix as at most three dated Replicate image-generation candidates with slug, immutable version identity, source URL/API payload hash, and skipped-candidate reasons.
- [ ] AC-03: Every roster and candidate model receives a policy preflight before generation; prohibited mature/gore cells are recorded as `refused-by-policy` without calling Replicate.
- [ ] AC-04: The runner walks each `(model, class)` ladder sequentially, performs one attempt per rung, early-stops after `refused` or `refused-by-policy`, and never retries or mutates a prompt.
- [ ] AC-05: The runner records immutable version identity for every model cell, either by running an explicit Replicate version or by resolving and recording the exact version id before generation.
- [ ] AC-06: A dedicated tolerance vision judge returns a closed-set typed result sufficient to classify `ok` versus `sanitized`; publish-description schemas/prompts are not reused as the tolerance verdict contract.
- [ ] AC-07: Unit tests with mocked generation/judge paths witness `ok`, `sanitized`, `refused`, `refused-by-policy`, and `error`; `error` cells are void and do not lower the model's tolerance limit.
- [ ] AC-08: The matrix validates against a Pydantic schema requiring timestamp, probe file SHA, model slug, version identity, roster/candidate source, per-cell outcome, reason where applicable, and image hash.
- [ ] AC-09: Tests are requirement-marked and the capability registry contains the corresponding tolerance-fingerprinting requirements.
- [ ] AC-10: One live run artifact is committed under `state/tolerance/`; the FR Implementation Record summarizes observed counts, candidate snapshot, spend, and representative cells. The live run is not required to contain every possible outcome type.
- [ ] AC-11: No generated images, API tokens, raw Replicate payloads containing secrets, or mature prompt outputs beyond the committed probe text are committed.
- [ ] AC-12: README or roster documentation points future routing/model-retirement work to the latest tolerance matrix as dated evidence, without implementing routing in this FR.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | Authority is not active until R-1 through R-5 are folded into the FR. | GATE |
| C-2 | Live probing must not begin until the exact committed probe file and policy-preflight behavior are in the revised FR. | GATE |
| C-3 | Any model page/ToS prohibition records `refused-by-policy`; enforcement must not generate that cell. | GATE |
| C-4 | No prompt retries, prompt mutations, or escalation above `mature` are permitted after a refusal or policy block. | GATE |
| C-5 | Stop the live run before exceeding the FR's stated sub-$10 spend envelope. | GATE |
| C-6 | Generated images remain local/transient; only hashes and matrix rows may be committed. | GATE |
| C-7 | All new tests must be linked to capability requirements with `@pytest.mark.req(...)`. | GATE |

Authority granted: after the revisions are folded, the enforcer may build and run only the version-pinned tolerance fingerprinting probe/matrix workflow described above.
