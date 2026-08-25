# 2026-08-25 — The judge moved the boundary the FR named

**Arc:** FR-887 structured generation-failure logging — judged (sole-route
graph, gpt-5.5), R-1..R-5 folded, RED (13 witnesses) → GREEN in one pass,
229 tests green, req_coverage strict clean.

**Insight:** The draft FR said "catch every failure at the `generate_image`
boundary" — plausible, and wrong: that function has none of the context
(`date`, `slot`, roster name, `source_file`, `run_source`) the row needs.
The judge caught it by reading the *signatures*, not the prose (R-1). This
is `normalize at the boundary` with a twist: the right boundary is not
where the exception is born but the innermost frame that already holds the
full context. Naming a boundary in an FR is a claim to verify against the
callsite, same as any provider type.

**Second catch (R-2):** "reuse the `record_transition` git pattern" would
have widened the publish ledger's closed status enum — `append_entry`
rejects anything outside `drawn/submitted/published/skipped`, and that
rejection is the idempotency guard. The cure was a sibling helper sharing
only `commit_push`. Pattern: *share the discipline, not the state machine.*

**Two-error semantics worked first try:** `raise exc from ledger_exc` +
`add_note` (3.11+) keeps the provider failure primary with the commit
failure inspectable — no green exit possible, no error lost.

**Trap dodged:** quick_confidence — the draft ACs looked complete (5 items);
the judgement expanded them to 10, and the extra five (nullability,
schema freeze, publish-ledger isolation, two-error, sha-privacy proof)
are where all the real design decisions lived.

**Seed:** `state/failures.jsonl` now accumulates organic tolerance data,
but nothing *reads* it yet — FR-886's router is the named consumer. When
does a ledger with zero readers become growth_as_default in reverse:
evidence rotting unconsumed? Should FR-886's judgement require a minimum
row count (real refusals witnessed) before routing authority activates,
so the router is calibrated on data instead of forecast?
