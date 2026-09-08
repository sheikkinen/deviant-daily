# Feature Request: Refusal is a routing event — re-route on refusal, honour the operator's pin

**Priority:** HIGH
**Type:** Bug
**Status:** Approved with revisions (folded 2026-09-08)
**Effort:** 1 day
**Requested:** 2026-09-08
**Judgement:** `FR-891-refusal-reroute-and-honored-pin.judgement.md`
**First consumer / first event:** the scheduled `daily-publish` run at
06:00 UTC on the next day a provider refuses a drawn prompt — today it
fails red and every re-run repeats the same refused call; after this FR
it tries the next eligible roster model and publishes.

## Summary

A provider content refusal currently poisons the day's slot. The refused
prompt stays committed at status `drawn` with its model binding, so every
subsequent run — scheduled or manual — resumes the identical prompt
against the identical model and receives the identical refusal. Eight
consecutive CI failures on 2026-09-07/08 are this one defect. Operator
model selection does not escape it, because the resume path returns
before the dispatch input is read.

## Value Statement

A day whose first draw is refused still publishes, because the pipeline
consults the roster it already has instead of re-submitting a call the
provider has already deterministically declined.

## Problem

### Witnessed failures

All eight failing runs die at the same node with the same provider error:

```
❌ Error: tool_call node 'generate': tool 'generate_step' failed:
   ModelError: The input or output was flagged as sensitive. (E005)
```

| run | date | model | workflow |
|---|---|---|---|
| 34125302840 | 2026-09-07 | flux-2-flex | daily-publish |
| 34136757774 | 2026-09-07 | flux-2-flex | publish-now |
| 34194720806 | 2026-09-08 | grok | publish-now |
| 34195010358 | 2026-09-08 | grok | publish-now |
| 34195469199 | 2026-09-08 | grok | publish-now |
| 34195509979 | 2026-09-08 | grok | publish-now |
| 34196933025 | 2026-09-08 | grok | publish-now |
| 34222520565 | 2026-09-08 | grok | daily-publish |

`state/failures.jsonl` holds five rows for `prompt_sha 45661289…`, all
`error_class: refusal`, all `model: grok`. The evidence FR-886 needs was
recorded five times and consumed zero times.

### Defect 1 — a refusal leaves the slot poisoned

1. `draw_step` binds a model and commits the `drawn` row (FR-886,
   REQ-DD-113/114): generation consumes the committed binding and never
   re-selects.
2. `generate_step` catches the refusal, appends the `FailureRecord`
   (FR-887), and **re-raises**. The ledger row stays at `drawn`.
3. `TERMINAL = ("published", "skipped")` — `drawn` is not terminal.
4. The next run reaches `if existing and existing["status"] not in
   TERMINAL` and returns `_resumed(existing, …)`, which carries
   `existing["prompt"]` **and** `existing["model"]` forward unchanged.

The refusal is deterministic, so step 4 guarantees step 2. The FR-886
router — which exists precisely to exclude a model with a witnessed
refusal for a content tuple — only runs on a fresh draw, and a fresh
draw is exactly what the poisoned row prevents. Each component honours
its own contract; the loop lives in the policy connecting them
(`composition_bug`).

### Defect 2 — the operator's pin is silently discarded on resume

`publish-now` documents its `model` input as a capability: *"`model` and
`date` are capabilities, not guards."* In `draw_step`, the resume return
sits **above** `pinned = parse_model(model)`. On a poisoned slot the
dispatch input is never read; `_resumed` re-emits the committed binding.
This is field-witnessed: the five 2026-09-08 `publish-now` runs all ran
`grok` regardless of the model chosen at dispatch. The one manual lever
that could have escaped the loop was wired to nothing.

Both defects are the same boundary: **the resume path discards live
inputs** — the accumulated refusal evidence and the operator's
instruction.

## Ideal Result

No run ever repeats a call a provider has already deterministically
refused. A refusal is a routing event: the pipeline moves to the next
model the evidence still permits and publishes the day. When no model
remains for that content, the slot becomes terminal so the next run
draws something else, and the run ends red because the day produced no
post. An operator's explicit model choice is never silently discarded.

## Proposed Solution (revised per judgement, R-1…R-7)

Four changes across `tools/steps.py` (control flow) and, if needed,
`tools/route.py` (pure helper only). No graph edges change, no workflow
changes, no new ledger status (R-6).

### 1. Re-route inside `generate_step` on refusal only

```python
# tools/steps.py — generate_step, on exception
record = build_failure_record(exc=exc, ...)
append_failure_record(...)      # R-2: a ledger failure here aborts;
                                # FR-887 two-error semantics unchanged
if record.error_class != "refusal":
    raise                       # transport/timeout/unknown: slot stays drawn
# else: re-route (below)
```

Only `refusal` re-routes. A transport blip is not evidence about
content; leaving it at `drawn` so the next run resumes the same binding
is correct behaviour and stays. Attempts are sequential — the FR-888
judgement's C-3 rationale (rate limits, spend visibility) applies
unchanged.

**Re-routing is confined to the publish pipeline.** It requires
`run_source == "corpus"` and a non-null `slot` — i.e. a committed
`drawn` row exists to re-bind. The FR-889 user path (`run_source="user"`,
`slot=None`) keeps its contract untouched: the operator chose that model,
the provider's response is the only gate, and a refusal stays red with
one row. FR-888 fan-out is likewise untouched (C-7).

**R-2 — the failure row is a precondition, not a side note.** The
refusal `FailureRecord` must be appended *and* committed before any
retry. If `append_failure_record` raises, the original provider
exception stays primary with the ledger error attached as note and
cause (today's behaviour, `tools/steps.py`), and **no retry happens**.
A retry whose evidence was not durably recorded could be repeated by
the next run.

**R-3 — the selection rule, frozen.** After the refusal row is
committed:

1. Look up the corpus row by `prompt_sha(prompt)` (the same key
   `refusal_evidence` joins on). No corpus match → no re-route; re-raise.
2. `fingerprint = content_tuple(corpus_row, load_taxonomy())` — an
   invalid or missing fingerprint routes as `(mature, mature)`, as today.
3. `evidence = refusal_evidence(load_failure_rows(FAILURES), load_corpus(CORPUS), axes)`
   — loaded *after* the commit, so it contains the refusal just recorded.
4. `candidates = [m for m in eligible_models(fingerprint, evidence, validate_roster()) if m not in attempted]`
   where `attempted` is every model tried in this invocation.
5. Pick `candidates[0]`. `eligible_models` already returns
   `sorted(roster)`, so the choice is deterministic without an RNG.
   `route()` is **not** used here: its random pick would make the retry
   sequence untestable.

### 2. Every binding change is committed before it is used

`draw_step`'s invariant — the committed row records the model generation
consumes (REQ-DD-114) — must survive re-routing. Before each retry,
`generate_step` commits a new `drawn` transition carrying the new
binding. The ledger is append-only, so the sequence of attempted
bindings is auditable.

**R-4 — transition shape and commit failure.** Each retry transition
carries the existing slot's `date`, `slot`, `prompt`, and `source_file`
unchanged, with only `model` replaced. `record_transition` raises before
returning on any git failure; that exception propagates and **the retry
provider call does not happen**. The run exits red with the transition
failure inspectable — never a provider call behind an uncommitted
binding (R-3 of FR-826).

### 3. Exhaustion makes the slot terminal, then stays red

When no eligible unattempted model remains, `generate_step` commits

```json
{"status": "skipped", "reason": "unroutable: every roster model refused"}
```

for the slot — same `date`, `slot`, `prompt`, `source_file` — and
re-raises the last provider error. `skipped` is already in `TERMINAL`,
so the next run draws a fresh candidate instead of resuming. The run
stays red: the day produced no post and a human should see it — but the
re-run is no longer futile.

**R-4 — if the `skipped` commit fails**, the exception propagates and
the run exits red without claiming the slot is terminal. Both the
provider failure and the commit failure stay inspectable. A slot that
was not durably terminalized must not be reported as terminalized.

**R-5 — this is not draw-time skipping.** FR-886/CAP-18 skips
unroutable *candidates* at draw time with zero ledger writes, before a
slot is burned. This FR terminalizes an *already-committed* slot after
generation exhausted it. Both are correct and they do not meet:
`_route_candidate` keeps its zero-ledger-write behaviour and is not
touched. The `skipped` write authorized here applies only to the slot
that already has a committed `drawn` row.

### 4. A pin on resume re-binds a `drawn` slot

`draw_step` reads `parse_model(model)` **before** the resume return.

**R-1 — bounded by status.** The pin may re-bind only a resumed row at
status `drawn` — the pre-generation boundary, before any external side
effect. When a differing pin arrives on a resumed row at any other
non-terminal status (today: `submitted`, which guards a DA call already
in flight), `draw_step` raises with an explicit message naming the
status and both models. It never silently discards the pin, and it never
re-binds after a side-effect-guarding transition. Expanding the pin to
later states needs its own FR.

On a `drawn` resume with a differing pin, `draw_step` commits a new
`drawn` transition with the pinned model (fields otherwise unchanged) and
resumes with it. The pin already bypasses routing on a fresh draw
(REQ-DD-115); this makes resume agree. The prompt and slot are
untouched — the pin re-binds the model, never re-draws.

### Authorized surfaces (R-6)

| Surface | Authorized for |
|---|---|
| `tools/steps.py` | re-route control flow in `generate_step`; pin handling in `draw_step` |
| `tools/route.py` | pure helper(s) only, if needed for the R-3 lookup; no network, LLM, ledger write, or roster mutation |
| `tests/test_steps.py`, `tests/test_route.py` | req-marked offline witnesses |
| `capabilities/CAP-19-refusal-reroute.yaml` | REQ-DD-118…123 |

### Judgement fold record

| # | Required revision | Folded into |
|---|---|---|
| R-1 | Pin override bounded to safe resume statuses | Solution §4, AC-08/09, C-5 |
| R-2 | FR-887 two-error semantics precede any re-route | Solution §1, AC-02 |
| R-3 | Frozen evidence lookup + deterministic retry rule | Solution §1 (5-step rule), AC-03 |
| R-4 | Transition shape + commit-failure behaviour | Solution §2 and §3, AC-04/07 |
| R-5 | Generate-time exhaustion ≠ draw-time skip | Solution §3, C-6 |
| R-6 | Correct authorized surfaces | Authorized surfaces table |
| R-7 | Replay criterion offline and exact | AC-10 |

## Acceptance Criteria (revised per judgement, R-1…R-7)

- [ ] AC-01 A mocked refusal from the bound model appends and commits
      exactly one FR-887 failure row, then re-routes within the same
      `generate_step` invocation only when `error_class == "refusal"`;
      `transport`, `timeout`, and `unknown` append one failure row,
      re-raise, and leave the slot at `drawn` (REQ-DD-118, REQ-DD-121).
- [ ] AC-02 If the failure-ledger append/commit fails, no re-route is
      attempted; the provider failure and the ledger failure are both
      inspectable (FR-887 two-error semantics) (REQ-DD-119).
- [ ] AC-03 Re-routing computes the content tuple from the corpus row
      matched by `prompt_sha`, consults evidence loaded after the
      refusal row is committed, subtracts every model attempted in this
      invocation, and picks the first remaining model from
      `eligible_models` (sorted, no RNG) (REQ-DD-118).
- [ ] AC-04 Before each retry provider call, a new `drawn` transition is
      committed with the same `date`, `slot`, `prompt`, `source_file`
      and the new `model`; a failed commit aborts red before the call
      (REQ-DD-120).
- [ ] AC-05 On a successful retry, `generate_step` returns `model_name`
      for the model that actually produced `image_path`, and the graph
      continues through the existing generate→describe edge with no
      graph change (REQ-DD-118).
- [ ] AC-06 When no eligible unattempted model remains, `generate_step`
      commits `skipped` with reason `unroutable: every roster model
      refused` for that slot and re-raises the last provider error; a
      following `draw_step` treats the terminal slot as complete and
      draws the next candidate (REQ-DD-122).
- [ ] AC-07 If the exhaustion `skipped` transition fails to commit, the
      run exits red and does not claim the slot is terminal; both
      failures stay inspectable (REQ-DD-122).
- [ ] AC-08 A differing operator pin on a resumed `drawn` row is parsed
      before the resume return, commits a new `drawn` transition with
      the pinned model and unchanged `date`, `slot`, `prompt`,
      `source_file`, and generation uses that pinned model (REQ-DD-123).
- [ ] AC-09 A differing operator pin on a resumed non-`drawn`
      non-terminal row raises explicitly, naming the status and both
      models — never a silent discard, never a re-bind after a
      side-effect-guarding transition (REQ-DD-123).
- [ ] AC-10 An offline replay fixture built from the committed
      2026-09-08 `drawn` row and its five refusal rows stubs the
      provider so `grok` refuses and another eligible roster model
      succeeds, proving the run escapes the loop with no Replicate or
      DeviantArt call (REQ-DD-118).
- [ ] AC-11 REQ-DD-118…123 are registered in the capability registry,
      every new test carries `@pytest.mark.req(...)`, and
      `python3 scripts/req_coverage.py --strict` passes.
- [ ] AC-12 A refusal on the FR-889 user path (`run_source="user"`,
      `slot=None`) does not re-route: one failure row, re-raise, no
      ledger write (REQ-DD-121).

## Constraints (judgement gates C-1…C-8)

- **C-2** Only `error_class="refusal"` may trigger a re-route.
- **C-3** No retry provider call until both the refusal failure row and
  the new `drawn` binding transition are committed.
- **C-4** The invocation must not retry a model it already attempted,
  even if older evidence still admits it.
- **C-5** Pin override only at a `drawn` pre-generation resume boundary.
- **C-6** Generate-time exhaustion terminalizes only the already-existing
  slot; `_route_candidate`'s draw-time skips stay zero-ledger-write.
- **C-7** No graph edges, workflow triggers, roster policy, failure
  schema, DA publish policy, CI/hooks, or judge/review doctrine change.
- **C-8** All new behaviour witnessed by req-marked offline tests.

## Out of Scope

New publish-ledger statuses; prompt rewriting, softening, filtering, or
redraw; roster admission/retirement; retry on transport/timeout/unknown;
parallel provider calls; FR-888 fan-out behaviour; DA submit/publish
policy; graph edge changes; workflow changes; failure-row schema changes;
draw-time ledger writes for skipped candidates.

## Alternatives Considered

**A — terminal `refused` status, no retry.** On refusal, commit a new
terminal status and let the next run draw fresh. Frees the slot but
throws the day away and leaves the roster unused: a prompt one model
declines is often accepted by another, which is the entire premise of
FR-886's per-model evidence. Rejected as strictly weaker than B, though
B subsumes its ledger mechanics in change 3.

**C — drop the binding on resume when the slot has a witnessed
refusal.** Narrowest possible patch: `_resumed` re-routes instead of
re-emitting the model. Fixes the loop across runs but not within one, so
the day still fails once per refusal and the fix depends on the daily
schedule to make progress. It also leaves defect 2 untouched.

**Green END on exhaustion** instead of red. Symmetric with `gate_step`'s
skip, which ends green. Rejected: a gate skip means we generated and our
own quality gate declined; roster exhaustion means no provider will draw
this content at all, which is a corpus/roster signal a human should see.
It would also require a new conditional edge out of `generate`. Flagged
for the judge as the one place this FR chooses noise over silence.

**Broaden re-routing to any error class.** Rejected: transport and
timeout failures are not evidence about content, and retrying them
against a different model would burn spend on a blip. `classify_failure`
already draws this line.

## Related

- `tools/steps.py` — `draw_step`, `_resumed`, `generate_step`
- `tools/route.py` — `refusal_evidence`, `eligible_models`, `route`
- `tools/ledger.py` — `TERMINAL`, `record_transition`
- `tools/fanout.py` — FR-888 sequential fan-out (precedent for
  per-model outcome handling; not reused: fan-out is generation-only,
  writes `run_source="probe"` rows, and has no slot)
- FR-886 draw routing · FR-887 failure ledger · FR-888 fan-out ·
  FR-890 fingerprint enrichment
- Failing runs 34125302840, 34136757774, 34194720806, 34195010358,
  34195469199, 34195509979, 34196933025, 34222520565
