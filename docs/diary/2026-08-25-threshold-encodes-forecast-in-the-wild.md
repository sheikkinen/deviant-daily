# Diary Entry — 2026-08-25 — The forecast was the defect, not the guard

## What happened

FR-890 end to end: carved from FR-885's wreckage, judged (APPROVED WITH
REVISIONS, R-1..R-7 folded), enforced TDD, and witnessed — 7,392/7,392
corpus rows fingerprinted by claude-haiku-4-5 with **zero boundary
rejections across 148 batches** and other-share 1.3% against a 10% gate.
The classifier was a yamlgraph map graph authored via the sole route;
the enrich runner batched global row indices, rewrote the corpus
atomically per batch (a free resume contract), and refused to start
past a spend ceiling.

Two surprises. First, the cost forecast was wrong twice in one FR: the
summary said ~$3 (stale haiku-3.5 prices), the real number was ~$7.4,
and the $5 ceiling — written to protect against overrun — would have
blocked a correct, in-budget-by-any-sane-measure run. The operator
raised the cap to $10 in four words; no code changed except two
constants. Second, the boundary machinery built to catch LLM
misbehavior (closed-set validation, duplicate-ref detection, counted
rejections) caught *nothing* — 7,372 structured-output calls at
temperature 0 produced 7,372 in-set verdicts.

## Trap

**threshold_encodes_forecast**, met in the wild: the $5 ceiling was not
a safety property, it was a price forecast wearing a guard costume.
When the forecast went stale (model generation changed the price list),
the "guard" pointed at the correct run, not at a defect. The Scripture
already names this for acceptance gates; it holds for spend gates too.

A near-trap avoided: the empty nohup log at minute 4 invited
instrumentation ("add flushing, add progress files"). The corpus diff —
the rawest artifact — already showed 820 rows changed.
`read_raw_output_first` applies to progress monitoring, not just
scores: the artifact under mutation IS the progress bar.

## Heuristic

Separate the *ceiling* (what the operator will pay — policy, one
constant, operator-owned) from the *estimate* (what the run will cost —
forecast, derived from prices that rot). The guard should compare the
two at start time and stop; it should never hardcode last quarter's
price list into the policy constant. Zero rejections is also evidence:
the boundary validation was cheap insurance, but its silence at temp 0
with structured output calibrates where the real risk lives — in the
forecast, not the verdict shape.

**Seed:** The run record now stamps model id + taxonomy version into
every row. When taxonomy v2 arrives, `is_classified` will mark all
7,392 rows stale at once — a full $7 re-run. Is there a cheaper
migration: re-classify only rows whose genre definitions changed
between taxonomy versions, keyed by a per-genre content hash?
