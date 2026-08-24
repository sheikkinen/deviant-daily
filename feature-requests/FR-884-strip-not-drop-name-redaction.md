# Feature Request: Strip-Not-Drop Name Redaction — Recover Blocklist-Excluded Prompts (2,020 candidates)

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Judged — approved with revisions (R-1..R-4 folded)
**Effort:** 0.5 days
**Requested:** 2026-08-24
**First consumer / first event:** the daily draw step, on the first run
after corpus regeneration — its selection pool grows from 5,893 to
~7,900 rows (+34%), the single largest corpus recovery available.

## Summary

Change the personal-name blocklist in `scripts/extract_corpus.py` from
whole-row exclusion to mechanical segment stripping. The redaction goal
(no personal names in the committed corpus) is preserved by a mechanical
zero-leak invariant; the prompts themselves are recovered.

## Value Statement

The draw step gets up to 2,020 additional unique prompts (25% of all
usable material — the name-contaminated **candidate pool**; final
recovery is whatever survives the post-strip short/dedup/term/scan
gates) at zero LLM cost, with the redaction guarantee mechanically
intact.

## Problem

Measured 2026-08-24 against `signed.log` (9,038 parsed entries):

| Drop reason | Count | Unique? |
|---|---|---|
| `name_excluded` (blocklist: katja, tuija, nina) | 2,020 | all unique |
| `duplicates` | 1,054 | — |
| `term_excluded` | 69 | — |
| `empty` | 2 | — |

The NAME_BLOCKLIST exists so personal names never appear in a committed
file (operator-approved redaction policy, 2026-08-19). Whole-row
exclusion over-serves that goal: a 60-token prompt dies because one
token matches. 25% of the unique corpus is collateral.

**Operator ratification (2026-08-24):** "names out, names mechanically
out" — strip-and-keep is approved; stripping is mechanical (regex),
not LLM rewrite.

## Ideal Result

The corpus contains every unique usable prompt from `signed.log`, and a
mechanical scan of the emitted file finds **zero** blocklist matches.
No prompt is discarded for a redactable token; no name survives
redaction.

## Proposed Solution

In `scripts/extract_corpus.py`:

1. Replace the name-exclusion branch with **segment stripping**: split
   the sanitized prompt on commas; drop every comma-delimited segment
   containing a NAME_BLOCKLIST match (same substring-IGNORECASE
   semantics as today — catches `nina1`, `katja_x`, `Tuija's`,
   `nina_heikkinen`). Rejoin, collapse whitespace.
   - Segment-level (not token-level) stripping is deliberate: it
     removes adjacent identity residue in the same clause
     ("Nina Heikkinen, red hair" → the surname dies with the segment).
     Over-removal is accepted; under-removal is not.
   - Prose prompts without commas: strip at sentence boundaries
     (`.` / `;`) by the same rule; if the whole prompt is one
     name-bearing sentence, the empty/short gate below drops it.
2. Stripped prompts then pass the **existing** gates unchanged:
   `len < 10` → empty, lowercase dedup → duplicates, SCAN_PATTERNS →
   scan_hits.
3. **Zero-leak invariant (hard gate, atomic — R-1):** scan the
   serialized rows with `name_blocklist_re` BEFORE finalizing
   `out_path` (write to a temp file, atomically replace only after the
   scan passes). On a seeded leak: raise, and the destination is absent
   or byte-for-byte unchanged — no unsafe final artifact, ever. Same
   no-unsafe-output property as the existing SCAN_PATTERNS gate.
4. Stats (R-2): `name_candidates` (rows containing a blocklist match),
   `name_stripped_segments` (segments removed),
   `name_recovered_rows` (rows kept that exclusion would have dropped),
   plus post-strip drops by reason. Canonical regeneration must satisfy
   `kept == 5893 + name_recovered_rows`; final counts recorded here.
5. Doc drift (R-3): update README corpus provenance and the extractor
   docstring from "names excluded" to "name-bearing segments stripped,
   zero-leak scan enforced".
6. Traceability (R-4): CAP-09 gains requirement text for strip-not-drop
   redaction and the zero-leak invariant; every new test carries
   `@pytest.mark.req(...)`.
7. Regenerate `prompts/corpus.jsonl` (v2.1); back up v2 to /tmp first.

Out of scope (explicit): TERM_BLOCKLIST stays whole-row exclusion —
that is content policy, not identity redaction. LLM rewriting of
identity residue in non-adjacent descriptors ("34yo finnish woman")
is out of scope per operator ratification of the mechanical tier.

## Acceptance Criteria (revised per judgement)

- [ ] AC-01: Requirement-marked RED tests cover `nina1`, `katja_x`,
      `Tuija's`, `Nina Heikkinen` (adjacent surname, same segment),
      comma-free prose sentence stripping, and a name-only prompt
      dropping through the existing short/empty gate
- [ ] AC-02: Name-bearing comma/sentence-delimited segments stripped
      mechanically with existing substring/IGNORECASE semantics;
      TERM_BLOCKLIST stays whole-row exclusion
- [ ] AC-03: Zero-leak scan runs before finalizing `out_path`; seeded
      leak raises and leaves no new partial/unsafe destination artifact
- [ ] AC-04: Stats distinguish `name_candidates`,
      `name_stripped_segments`, `name_recovered_rows`, post-strip drops
      by reason; canonical run satisfies `kept == 5893 +
      name_recovered_rows` with counts recorded in this FR
- [ ] AC-05: Recovered rows use the same v2 metadata path (dialect,
      seed, size, created) — no special-case schema
- [ ] AC-06: FR-883 preservation tests stay green (v1 prompts present,
      ledger source ids resolve, Signed blocks excluded,
      REQ-DD-080..082 intact)
- [ ] AC-07: Corpus v2.1 regenerated and committed; mechanical scan of
      committed JSONL finds zero NAME_BLOCKLIST matches
- [ ] AC-08: README corpus provenance, extractor docstring, CAP-09, and
      this FR's implementation record state the new contract and final
      counts

## Alternatives Considered

- **Token-only stripping**: leaves adjacent surnames ("Heikkinen")
  in place — under-removal violates the redaction goal. Rejected.
- **LLM (haiku) rewrite**: gracefully removes identity residue beyond
  the segment, but operator ratified mechanical-only; LLM enrichment
  remains available as a later, separate FR if residue proves to leak
  identity in practice. Deferred.
- **Keep exclusion (status quo)**: forfeits 25% of the corpus for a
  goal achievable by strip + mechanical invariant. Rejected.

## Related

- FR-883 (corpus v2 re-extraction — established extractor, stats,
  scan-gate pattern)
- Redaction policy: operator-approved 2026-08-19; strip-and-keep
  ratified 2026-08-24
- `scripts/extract_corpus.py`, `tests/test_extract_corpus.py`,
  `capabilities/CAP-09`
