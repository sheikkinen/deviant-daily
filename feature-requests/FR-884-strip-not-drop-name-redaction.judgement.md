# Judgement: FR-884 Strip-Not-Drop Name Redaction - Recover 2,020 Blocklist-Excluded Prompts

**Verdict:** APPROVED WITH REVISIONS - the boundary redaction change is sound, but authority activates only after the FR makes the zero-leak write atomic, reconciles candidate-vs-recovered counts, updates corpus doctrine, and binds the new behavior to requirement-marked tests.

**Reviewed against:** `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-884-strip-not-drop-name-redaction.md`; `/Users/sheikki/Documents/src/yamlgraph/.github/skills/judge-fr/doctrine.md`; `/Users/sheikki/Documents/src/yamlgraph/.github/skills/judge-fr/judgement.template.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-883-corpus-v2-signed-log-reextraction.md`; `/Users/sheikki/Documents/src/deviant-daily/feature-requests/FR-883-corpus-v2-signed-log-reextraction.judgement.md`; `/Users/sheikki/Documents/src/deviant-daily/AGENTS.md`; `/Users/sheikki/Documents/src/deviant-daily/README.md`; `/Users/sheikki/Documents/src/deviant-daily/STYLE-CONTRACT.md`; `/Users/sheikki/Documents/src/deviant-daily/scripts/extract_corpus.py`; `/Users/sheikki/Documents/src/deviant-daily/tests/test_roster_corpus_post.py`; `/Users/sheikki/Documents/src/deviant-daily/tests/fixtures/signed_log_excerpt.txt`; `/Users/sheikki/Documents/src/deviant-daily/tools/corpus.py`; `/Users/sheikki/Documents/src/deviant-daily/state/published.jsonl`; `/Users/sheikki/Documents/src/deviant-daily/capabilities/README.md`; `/Users/sheikki/Documents/src/deviant-daily/capabilities/CAP-09-roster-corpus-and-post-rendering.yaml`; `/Users/sheikki/Documents/src/deviant-daily/pyproject.toml`.

## What is sound

The first consumer is concrete and immediate: the daily draw step receives a larger pool on the first regeneration run (FR-884 lines 8-10), and the README confirms the pipeline draws from `prompts/corpus.jsonl` before generation (README lines 3-7). The proposal is correctly placed at the ingestion boundary: `scripts/extract_corpus.py` owns the operator-approved blocklists (scripts/extract_corpus.py lines 29-31) and currently drops name-bearing rows before dedup and output (scripts/extract_corpus.py lines 146-172).

The scope is mostly minimal and single-responsibility. It keeps TERM_BLOCKLIST as whole-row content policy and excludes LLM rewriting (FR-884 lines 80-83), so the change remains an identity-redaction extraction enhancement rather than a broader safety classifier or draw-policy change. Strategic classification: target-repo boundary enhancement, not a framework primitive.

The test direction is feasible. The existing tests already import the extractor directly from `scripts/extract_corpus.py` (tests/test_roster_corpus_post.py lines 20-24), cover current name regex variants (tests/test_roster_corpus_post.py lines 107-113), and witness the FR-883 metadata and signed-block parser guarantees that must stay green (tests/test_roster_corpus_post.py lines 151-234).

## Required revisions

### R-1: Make the zero-leak invariant atomic before finalizing output

Amend the Proposed Solution and acceptance criteria so the emitted rows are scanned before replacing `out_path`, or are written to a temporary file that is atomically replaced only after the name-blocklist scan passes. On a seeded leak, the destination file must be absent or byte-for-byte unchanged. The FR currently says to scan "after writing the corpus" while also promising "no partial output" (FR-884 lines 71-73), but the current extractor writes the destination directly (scripts/extract_corpus.py lines 209-212). The existing scan-gate pattern excludes rows before they enter output (scripts/extract_corpus.py lines 199-203); the name invariant must preserve that no-unsafe-final-artifact property.

### R-2: Reconcile the 2,020 headline with post-stripping recovery counts

Rewrite the title, Value Statement, stats, and acceptance criteria so `2,020` is treated as the name-contaminated candidate pool unless the final regeneration proves every candidate survives stripping. The FR claims "2,020 additional unique prompts" (FR-884 lines 21-23) and lists `name_excluded` as 2,020 unique rows (FR-884 lines 27-32), but its own flow sends stripped prompts through the existing short, dedup, term, and scan gates (FR-884 lines 68-70). Require stats that distinguish `name_candidates`, `name_stripped_segments`, `name_recovered_rows`, and post-strip drops by reason; require `kept == 5893 + name_recovered_rows` for the canonical regeneration; and record the final counts in the FR. If a minimum recovery floor is intended, state it as a mechanically checkable number rather than "kept rises from 5,893" (FR-884 line 94).

### R-3: Update the corpus redaction doctrine wherever the old contract is stated

Add README and extractor-docstring updates to the frozen scope. The committed repo doctrine currently says prompts containing personal names are excluded (README lines 35-39), and the extractor docstring states the same public redaction policy (scripts/extract_corpus.py lines 11-14). The FR modifies that policy but only names the script change, corpus regeneration, and FR count record (FR-884 lines 54-78 and 98). The delivered change must make the documented redaction contract say "strip name-bearing segments, then enforce zero name leaks" instead of leaving stale whole-row-exclusion doctrine behind.

### R-4: Bind the new behavior to the capability registry

Amend the test acceptance criterion to require `@pytest.mark.req(...)` on every new test and a CAP-09 requirement update for strip-not-drop redaction and the zero-leak corpus invariant. The repo convention requires every test function to carry a requirement marker linked to the registry (capabilities/README.md lines 20-24; pyproject.toml lines 31-34). Existing CAP-09 only guarantees that the name blocklist regex matches variants (CAP-09 lines 22-25); it does not cover row recovery, segment stripping, atomic zero-leak output, or regenerated-corpus name absence.

## Scope is frozen

| Deliverable | Surface |
|---|---|
| D-1 | `scripts/extract_corpus.py`: replace whole-row name exclusion with mechanical segment stripping, add recovery stats, and enforce atomic zero-leak output. |
| D-2 | `tests/test_roster_corpus_post.py` and/or committed sanitized fixtures: RED/GREEN coverage for name forms, segment boundaries, short-drop behavior, seeded leak failure, stats, and FR-883 preservation. |
| D-3 | `capabilities/CAP-09-roster-corpus-and-post-rendering.yaml`: requirement text for strip-not-drop redaction and zero-leak corpus output. |
| D-4 | `README.md` and extractor docstring: public corpus provenance/redaction policy updated from exclude-names to strip-segments-and-scan. |
| D-5 | `prompts/corpus.jsonl`: regenerated v2.1 corpus from the operator-local source log, with no raw private corpus committed. |
| D-6 | FR implementation record: final candidate, recovery, drop-by-reason, kept, and zero-leak counts. |

Not authorized: changing TERM_BLOCKLIST from whole-row exclusion; adding LLM rewriting or identity inference; changing draw, roster, ledger, or publish behavior; rewriting `state/published.jsonl`; changing the NAME_BLOCKLIST membership unless a separate FR authorizes it; committing raw `signed.log`, raw source basenames, local absolute paths, secrets, emails, or unsafe unsanitized corpus material.

## Revised acceptance criteria

- [ ] AC-01: Requirement-marked RED tests cover `nina1`, `katja_x`, `Tuija's`, `Nina Heikkinen` with adjacent surname in the same segment, comma-free prose sentence stripping, and a prompt that is only a name and drops through the existing short/empty gate.
- [ ] AC-02: Name-bearing comma-delimited or sentence-delimited segments are stripped mechanically with the existing substring/IGNORECASE blocklist semantics; TERM_BLOCKLIST remains whole-row exclusion.
- [ ] AC-03: The zero-leak invariant scans serialized output rows with `name_blocklist_re(NAME_BLOCKLIST)` before finalizing `out_path`; a seeded leak raises and leaves no new partial/unsafe destination artifact.
- [ ] AC-04: Extractor stats distinguish `name_candidates`, `name_stripped_segments`, `name_recovered_rows`, and post-strip drops by reason; canonical regeneration records final counts and satisfies `kept == 5893 + name_recovered_rows`.
- [ ] AC-05: Recovered rows use the same v2 metadata path as existing rows and include `dialect`, `seed`, `size`, and `created` where available, with no special-case schema.
- [ ] AC-06: Existing FR-883 preservation tests stay green: v1 prompts remain present, published ledger source ids resolve, signed blocks stay excluded, and v2 dialect/metadata guarantees remain intact.
- [ ] AC-07: `prompts/corpus.jsonl` v2.1 is regenerated and committed; a mechanical scan of the committed JSONL finds zero `NAME_BLOCKLIST` matches.
- [ ] AC-08: README corpus provenance, extractor docstring, CAP-09, and the FR implementation record are updated to state the new strip-not-drop redaction contract and final regeneration counts.

## Conditions for enforcement

| # | Condition | Severity |
|---|---|---|
| C-1 | The enforcer must use only the revised FR, committed evidence, and repo artifacts as authority; uncommitted chat/session notes are not implementation requirements. | GATE |
| C-2 | No raw private corpus data, raw source basenames, absolute local paths, token-like strings, emails, or blocked names may be committed. | GATE |
| C-3 | A name-blocklist leak in serialized corpus output is a hard failure and must not leave a new final output file behind. | GATE |
| C-4 | TERM_BLOCKLIST policy, LLM rewriting, draw behavior, roster policy, ledger history, and publish flow are out of scope. | GATE |
| C-5 | New tests must be requirement-marked and backed by CAP-09 requirement text before enforcement is complete. | GATE |

Authority granted: after R-1 through R-4 are folded into the FR, implementation may modify the existing extractor to strip name-bearing segments, regenerate the corpus, and update tests/docs/requirements needed to prove zero name leaks and measured prompt recovery.
