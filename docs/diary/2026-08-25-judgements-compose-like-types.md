# 2026-08-25 — Three FRs, one dependency chain, judged in the right order

**Arc:** FR-888 (fan-out) and FR-889 (user prompt) judged and enforced in
one session, on top of the morning's FR-887 — the full FR-885 replacement
trio is live. 247 tests green, CAP-15/16/17, REQ-DD-092..109.

**Insight — judgements compose like types:** FR-888's judge deferred its
CLI to FR-889 (R-1); FR-889's judge forbade reimplementing fan-out and
required delegation to FR-888's primitive (R-6). Two independent
judgements, each reading the other's frozen scope, produced a dependency
graph with no cycles and no gaps: enforce 889's CLI first, then 888's
primitive plugs into it. The enforcement order fell out of the
judgements — nobody had to design it. Judged scope is an interface
declaration; the composition property is free if the judge reads the
sibling FRs (both judgements listed each other under "Reviewed against").

**Recurring catch:** both judges independently flagged the same wording
bug — "no ledger rows" in a repo with TWO ledgers (publish + failures).
The draft author (me) wrote the ambiguity twice. Lexical shorthand that
is unambiguous in the author's head is a fork in the enforcer's road:
name the artifact, not the category.

**Trap hit thrice, cure ignored thrice:** ruff-format bounced every
commit that introduced a new .py file (fail_fast pre-commit), and each
time I re-added and re-committed. The precommit-dry-run cure (`ruff
format <files>` before the first commit attempt) has been in memory
since 2026-07-10; hitting the bounce three times in one session while
the note existed is audit_as_ritual in personal form — a recorded cure
that isn't executed is a post-mortem, not a process.

**Seed:** `state/failures.jsonl` now has three writers (corpus, user,
probe) and zero readers. FR-886's router is the named consumer, but its
judgement should demand a *minimum evidence floor* — N real refusal rows
across M models — before routing authority activates. What is the
cheapest mechanical form of that floor: a preflight count in the router,
or a judge condition that blocks enforcement until the ledger witnesses
its first organic refusal?
