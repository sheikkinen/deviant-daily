# Authoring brief: FR-890 corpus_fingerprint batch classification graph

**Governing FR:** deviant-daily FR-890 (judged APPROVED WITH REVISIONS,
authority active). **Target repo:** `/Users/sheikki/Documents/src/deviant-daily`
(all paths below relative to that root; author there, not in yamlgraph).

## Task

Repair ONE graph: `graphs/corpus_fingerprint.yaml` (already authored by
a prior adapter run — see `tmp/draft-authoring-report.md` in the target
repo). The prior run pinned a stale model id; the ONLY repair needed:
replace `model: claude-3-5-haiku-latest` with `model: claude-haiku-4-5`
(verified current, 404 witnessed in `logs/fr890-smoke.log`). Then
complete the validation below. Everything else already exists and must
be reused, not re-authored:

- Prompt template: `prompts/corpus_fingerprint.yaml` (exists — schema
  FingerprintVerdict {ref:int, sexual:str, gore:str, genre:str};
  variables: ref, prompt, taxonomy_rules, genre_list).
- Python tools: `tools/fingerprint.py` (exists) — `load_batch(batch_file)`
  returns `{items: [{ref:int, prompt:str}], taxonomy_rules: str,
  genre_list: str}`; `save_results(results_file, verdicts)` persists raw
  verdicts as JSON.
- Taxonomy artifact: `data/corpus_fingerprint_taxonomy.yaml` (exists;
  loaded inside load_batch — the graph never redeclares taxonomy).

## Graph contract

- `version: "1.0"`, `name: corpus_fingerprint`.
- Prompts resolved from the repo `prompts/` dir (the graph runs with
  cwd = deviant-daily root; use `prompts_dir: prompts`).
- state: `batch_file: str`, `results_file: str`, plus keys for the tool
  outputs and collected verdicts.
- tools: `load_batch` and `save_results` as `type: python` with
  `module: tools.fingerprint` (cwd import), descriptions included.
- nodes:
  1. `load` — tool_call load_batch with `batch_file: "{state.batch_file}"`.
  2. `classify` — `type: map` over the loaded items, `as: item`,
     `max_items: 100`, sub-node `type: llm`, `prompt: corpus_fingerprint`,
     `provider: anthropic`, `model: claude-haiku-4-5`,
     `temperature: 0.0`, variables ref/prompt from the item and
     taxonomy_rules/genre_list from the load output; collect verdicts.
     on_error stays `fail` (a silently dropped branch would undercount
     unfingerprinted rows — the calling script owns failure accounting).
  3. `save` — tool_call save_results with
     `results_file: "{state.results_file}"` and the collected verdicts.
- edges: START → load → classify → save → END.
- The graph must NOT: retry failed classifications, write to the
  corpus, compute costs, or validate the enum (closed-set validation
  lives at the script boundary, `scripts/enrich_corpus.py`).

## Validation

Run from the deviant-daily root (`cd /Users/sheikki/Documents/src/deviant-daily`):

1. `yamlgraph graph lint graphs/corpus_fingerprint.yaml`
2. Smoke (live haiku, 2 items, requires ANTHROPIC_API_KEY):
   write `tmp/fp_batch.json` containing
   `{"items": [{"ref": 0, "prompt": "A vintage 1920s pin-up photograph of a seductive blonde reclining on silk sheets in an Art Deco boudoir"}, {"ref": 1, "prompt": "Female android cyborg being repaired in a futuristic workshop, detailed sketch style"}]}`
   then
   `yamlgraph graph run graphs/corpus_fingerprint.yaml --var batch_file=tmp/fp_batch.json --var results_file=tmp/fp_results.json --full`
   and verify `tmp/fp_results.json` holds 2 verdicts with refs {0,1},
   sexual/gore in {safe, mature}, and genre strings (expected: pinup,
   scifi — record actuals honestly; a mismatch is reportable, not
   repairable by prompt edits in this brief's scope).
