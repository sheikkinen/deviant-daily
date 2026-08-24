# Feature Request: Replicate Image Model Tolerance Fingerprinting

**Priority:** MEDIUM
**Type:** Feature
**Status:** Proposed
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
**No rung above `mature` exists** — no explicit-tier probes.

### Runner

`scripts/probe_tolerance.py`, reusing `tools/generate.py` (Replicate
wrapper) and `tools/vision.py` (judge):

1. For each (model, class): walk rungs in order, **one attempt per
   rung, early-stop at first refusal** — sequential by design; no
   hammering, minimal spend.
2. Outcome taxonomy per cell: `ok` (rendered faithfully) |
   `sanitized` (image produced, vision judge scores the class
   attribute absent/weakened) | `refused` (API/NSFW error) |
   `error` (unrelated failure, cell void).
3. Vision judge: existing anthropic vision path, prompt asks one
   closed question — "is <class attribute at rung R> present in this
   image?" — a closed-set judgement, cheap and small-model-safe.
4. Artifact: `state/tolerance/<date>-matrix.json` with model slug +
   **version pin**, probe file SHA, per-cell outcome + image hash,
   run timestamp. Images themselves are NOT committed.

### Compliance framing (binding constraints)

This is capability discovery for compliance routing — knowing limits
so mature content is *never sent* to models that prohibit it — not
filter evasion:

- One attempt per rung, early-stop per (model, class) at first refusal.
- Before probing a candidate model, check its Replicate page/ToS; if
  NSFW is explicitly prohibited, record `refused-by-policy` for
  mature rungs **without generating**.
- No retry, no prompt mutation to slip past a refusal.

### Cost

Worst case: 8 models (5 roster + ≤3 candidates) × 3 classes × 3 rungs
= 72 generations; early-stop and policy short-circuits reduce this.
Estimate $5–8 total.

## Acceptance Criteria

- [ ] Probe set committed with 9 minimal-pair probes, no rung above
      `mature`
- [ ] Runner walks ladders sequentially with witnessed early-stop
      (test: mock refusal at rung 2 ⇒ rung 3 never attempted)
- [ ] `sanitized` outcome witnessed by vision-judge disagreement
      (test with mocked judge; live run witnesses at least one real
      cell of each reachable outcome type)
- [ ] Matrix artifact validates against a Pydantic schema (model
      version pin, probe SHA, timestamp mandatory)
- [ ] `refused-by-policy` path records cells without generating
- [ ] One live run committed under `state/tolerance/`; findings
      summarized in the FR Implementation Record
- [ ] Roster docstring/README points to the matrix as the routing
      knowledge source

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
