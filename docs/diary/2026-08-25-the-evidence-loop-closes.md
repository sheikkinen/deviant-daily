# 2026-08-25 — The evidence loop closes: four FRs, one organism

**Arc:** FR-886 judged (retry after a 600s judge timeout — first
timeout in four runs today; larger input surface, more cited FRs) and
enforced. With it the whole FR-885 replacement is live in one day:
FR-887 writes refusal evidence, FR-889/FR-888 multiply the writers,
FR-886 reads it back into the draw. The system now learns from its own
production failures with zero additional spend — the loop the purchased
probe matrix (FR-885, superseded) tried to buy.

**Insight — the operator's three answers replaced a design document:**
cold-start policy, evidence floor, and routing site were surfaced as
one structured question set before drafting. Each answer collapsed an
entire branch of the design space (the old draft's conservative
"unknown = excluded" would have required a paid seeding run; "1 refusal"
made the evidence floor a non-mechanism). Ten minutes of operator time
beat a judge round-trip over a speculative contract. The judgement then
found seven REAL revisions in what remained — none of them re-litigated
the answered questions. Ask-then-judge divides labor correctly:
decisions to the authority, mechanics to the judge.

**Trap — the FR contradicted its own header:** the Problem section
still said "no content-class fields" while the dependency line two
paragraphs up said 7,392/7,392 enriched. I wrote both, hours apart. A
rewritten FR inherits stale claims from its own earlier strata; R-1
existed because a document edited incrementally is a boundary too —
re-read the WHOLE artifact after a dependency lands, not just the
section being rewritten (intent_drift within one file).

**Mechanical note:** cold-start neutrality was testable only because
the judge forced randomness to become an explicit input (R-3):
`route(fp, {}, roster, rng=Random(7)) == choose_model(rng=Random(7))`.
"Preserve existing randomness" is untestable prose; "same injected RNG,
same pick" is a witness.

**Seed:** the evidence join recomputes over the full corpus + full
failure ledger on every draw. At 7,392 corpus rows that is milliseconds;
at 100k failure rows it is not. The join is also append-only-friendly —
when does incremental evidence (a committed materialized cell table,
updated by FR-887's writer) become the second consumer of the failure
ledger, and does its judgement demand the same absent-file semantics?
