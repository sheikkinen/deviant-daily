# Feature Request: Replicate Image Model Tolerance Fingerprinting

**Priority:** MEDIUM
**Type:** Feature
**Status:** Judged — approved with revisions (R-1..R-5 folded)
**Effort:** 1 day
**Requested:** 2026-08-24
**First consumer / first event:** the operator, at the next roster
decision — which models to keep, add, or route mature-leaning prompts
away from. Second consumer (deferred, named): a draw-time routing FR
that joins this matrix with corpus-side mature priors.

## Summary

Probe each Replicate image model in the roster — plus a small set of
new & popular candidates — with a fixed severity ladder of content
probes, and record a **dated per-model tolerance matrix**: which model
refuses, silently sanitizes, or faithfully renders each content class
at each severity rung.

## Value Statement

The corpus leans mature; every mature prompt sent to a content-strict
model is a wasted paid generation (refusal) or worse, a silently
sanitized dud that burns a daily slot. Today the roster's content
limits are guesses ("recraft probably blocks NSFW" — unwitnessed).
The matrix converts guesses into measured, dated data.

## Problem

- 5 active models (`z-image`, `flux-2-flex`, `nano-banana-2`, `grok`,
  `recraft`) with **zero measured knowledge** of content tolerance.
- Failure modes are asymmetric and only one is visible: an API refusal
  is loggable, but **silent sanitization** (model renders a tame
  variant of a mature prompt) is invisible without comparing the image
  to prompt intent — exactly what burned slots look like.
- Provider filters drift over time; any tolerance knowledge must be a
  dated artifact, not a constant in code.
- New popular models (candidates chosen at enforcement time from
  Replicate's image-generation leaderboard, version-pinned) should be
  fingerprinted *before* roster admission, not after a week of
  production duds.

## Ideal Result

A committed, dated artifact `state/tolerance/<date>-matrix.json` that
answers, for every roster and candidate model: "up to which severity
rung does this model faithfully render nudity / sexual / gore
content?" — with each cell backed by a witnessed generation outcome,
model version pinned, at a probe cost under $10, repeatable whenever
filters are suspected to have drifted.

## Proposed Solution

### Probe set (committed, hand-written)

`data/tolerance_probes.json`: 3 content classes × 3 severity rungs =
9 probes. Classes reuse the DA `mature_classification` enum's visual
members — `nudity`, `sexual`, `gore` (`language`/`ideology` rarely
gate image generation; deferred). Rungs: `safe` → `suggestive` →
`mature`. Probes are minimal pairs: same subject/composition, only the
class attribute escalates, so the vision judge has one axis to score.

**Safety envelope (R-4, binding):** no rung above `mature` exists; no
explicit sexual-act prompts, no minors, no non-consensual content, no
real-person likeness; the exact probe file is committed BEFORE any
live run.

### Runner

`scripts/probe_tolerance.py`, reusing `tools/generate.py` (Replicate
wrapper) and the image-preparation plumbing of `tools/vision.py`:

1. **Version pinning (R-1):** the runner resolves and records an
   immutable Replicate version id for every roster and candidate model
   before generation (resolve-latest-once, record id in the matrix).
   Candidate discovery is frozen as a dated snapshot: ≤3 entries with
   slug, version id, source URL/payload hash, and exclusion reason for
   skipped candidates.
2. For each (model, class): walk rungs in order, **one attempt per
   rung, early-stop at first refusal or policy block** — sequential by
   design; no hammering, minimal spend.
3. Outcome taxonomy per cell: `ok` | `sanitized` (image produced,
   judge scores class attribute absent/weakened) | `refused` (API/NSFW
   error) | `refused-by-policy` (recorded without generating) |
   `error` (unrelated failure — cell void, does NOT lower the model's
   tolerance limit).
4. **Dedicated tolerance judge (R-2):** a new function + prompt +
   Pydantic schema asking the closed question "is <class attribute at
   rung R> present in this image?" — reuses vision.py's image
   preparation/provider plumbing only; the publish-description
   `PostDescription` contract is NOT the tolerance verdict.
5. Artifact: `state/tolerance/<date>-matrix.json` validating against a
   Pydantic schema — timestamp, probe file SHA, model slug, version
   id, roster/candidate source, per-cell outcome + reason + image
   hash. Images themselves are NOT committed.

### Compliance framing (binding constraints)

This is capability discovery for compliance routing — knowing limits
so mature content is *never sent* to models that prohibit it — not
filter evasion:

- One attempt per rung, early-stop per (model, class) at first refusal.
- **Policy preflight for EVERY model (R-4)** — roster and candidate
  alike: check the Replicate page/ToS before probing; if a class/rung
  is prohibited, record `refused-by-policy` **without generating**.
- No retry, no prompt mutation to slip past a refusal.
- Hard spend ceiling: stop the live run before exceeding $10.

### Cost

Worst case: 8 models (5 roster + ≤3 candidates) × 3 classes × 3 rungs
= 72 generations; early-stop and policy short-circuits reduce this.
Estimate $5–8 total.

## Acceptance Criteria (revised per judgement)

- [ ] AC-01: Probe file validates as exactly {nudity, sexual, gore} ×
      {safe, suggestive, mature}, minimal pairs, safety envelope
      respected
- [ ] AC-02: Candidate snapshot frozen in the matrix: ≤3 dated entries
      with slug, immutable version id, source hash, skip reasons
- [ ] AC-03: Policy preflight for every roster+candidate model;
      prohibited cells recorded `refused-by-policy` without generating
- [ ] AC-04: Sequential ladder walk, one attempt per rung, early-stop
      on `refused`/`refused-by-policy`, no retry or mutation (test:
      mocked refusal at rung 2 ⇒ rung 3 never attempted)
- [ ] AC-05: Immutable version identity recorded for every model cell
- [ ] AC-06: Dedicated closed-set tolerance judge (own prompt+schema)
      distinguishes `ok` vs `sanitized`; PostDescription not reused as
      the verdict contract
- [ ] AC-07: Mocked unit witnesses for all five outcomes; `error` cells
      are void and never lower a tolerance limit
- [ ] AC-08: Matrix validates against its Pydantic schema (timestamp,
      probe SHA, slug, version id, source, per-cell outcome/reason/
      image hash mandatory)
- [ ] AC-09: All new tests requirement-marked; capability registry
      gains tolerance-fingerprinting requirements
- [ ] AC-10: One live-run artifact committed under `state/tolerance/`;
      Implementation Record summarizes observed counts, candidate
      snapshot, spend — live run NOT required to contain every outcome
      type
- [ ] AC-11: No generated images, tokens, or secret-bearing payloads
      committed
- [ ] AC-12: README/roster docs point routing and model-retirement
      decisions at the latest matrix, without implementing routing

## Alternatives Considered

- **yamlgraph map graph** (first_person_tool_horizon check): the fan
  is models × classes, but the *ladder within each pair is
  sequential* — early-stop is the cost- and compliance-critical
  property, and map's parallel fan-out defeats it. The LLM component
  (vision judge) is one closed-set call per generated image, embedded
  in the sequential walk. Script is honest here; a graph adds fan-out
  we must then suppress.
- **Assume from ToS/docs alone**: docs are a lossy summary of the
  vendor's filter (does_the_platform_already_do_this inverse); silent
  sanitization is documented nowhere. ToS check is kept as a
  *pre-filter*, not the measurement.
- **Probe with real corpus prompts**: corpus rows carry LoRA residue
  and confounded axes; minimal pairs isolate the class attribute so a
  `sanitized` verdict is attributable. Rejected.

## Related

- FR-884 (strip-not-drop) — grows the corpus this matrix will route
- Deferred consumer: draw-time routing FR joining matrix × corpus
  mature priors (not commissioned; do not build routing here)
- `tools/roster.py` (ACTIVE_MODELS), `tools/generate.py`,
  `tools/vision.py`, `state/tolerance/`
