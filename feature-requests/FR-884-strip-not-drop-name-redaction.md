# Feature Request: Strip-Not-Drop Name Redaction — Recover 2,020 Blocklist-Excluded Prompts

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Proposed
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

The draw step gets 2,020 additional unique prompts (25% of all usable
material) that are currently discarded for a one-token contamination,
at zero LLM cost and with the redaction guarantee mechanically intact.

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
3. **Zero-leak invariant (hard gate):** after writing the corpus, scan
   the emitted JSONL with `name_blocklist_re`; any match ⇒ raise, no
   partial output. This is the redaction policy, mechanized — same
   pattern as the existing AC-04 SCAN_PATTERNS gate.
4. Stats: replace `name_excluded` with `name_stripped` (segments
   removed) and `name_recovered` (rows kept that v2 would have
   dropped).
5. Regenerate `prompts/corpus.jsonl` (v2.1); back up v2 to /tmp first.

Out of scope (explicit): TERM_BLOCKLIST stays whole-row exclusion —
that is content policy, not identity redaction. LLM rewriting of
identity residue in non-adjacent descriptors ("34yo finnish woman")
is out of scope per operator ratification of the mechanical tier.

## Acceptance Criteria

- [ ] RED fixture covers the observed name forms: `nina1`, `katja_x`,
      `Tuija's`, `Nina Heikkinen` (adjacent surname, same segment),
      a comma-free prose sentence, and a prompt that is *only* a name
      (must drop via short gate)
- [ ] Zero-leak invariant: emitted corpus has 0 `name_blocklist_re`
      matches, enforced by raise (test witnesses the raise on a
      seeded leak)
- [ ] `kept` rises from 5,893; `name_recovered` reported in stats
- [ ] Recovered rows carry full v2 metadata (dialect, seed, size,
      created) — same code path, no special casing
- [ ] Existing FR-883 tests stay green (REQ-DD-080..082)
- [ ] Corpus v2.1 regenerated and committed; counts recorded in the FR

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
