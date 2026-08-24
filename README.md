# deviant-daily

Autonomous daily art publisher. Every morning a GitHub Actions run:

1. **draws** a random prompt from the operator's own generation history
   ([prompts/corpus.jsonl](prompts/corpus.jsonl))
2. **generates** an image on Replicate (frozen model roster)
3. **describes** it in the sheikkinen mythic voice
   ([STYLE-CONTRACT.md](STYLE-CONTRACT.md), vision LLM)
4. **gates** the result through a deterministic typed schema — only
   `confidence: low` blocks; `medium` publishes escalated to mature
   (the model hedges on mature content, and a hedge is not a reason to
   throw the day away)
5. **publishes** to [DeviantArt](https://www.deviantart.com/sheikkinen)
   via the OAuth2 API (`is_ai_generated=true`, `noai=true`)
6. **commits** the post record back to this repo

The pipeline is a [YAMLGraph](https://github.com/sheikkinen/yamlgraph)
graph ([graph.yaml](graph.yaml)) — yamlgraph runs unattended; Python
exists only for side effects ([tools/](tools/)). Governed by yamlgraph
FR-826.

## Corpus provenance (FR-826 R-2; v2 metadata FR-883)

- **Source:** operator's local `signed.log` generation history
  (9,038 parsed entries; 13,682 raw log records)
- **Kept:** 7,392 prompts after sanitization, strip-not-drop recovery,
  and dedup (2,020 rows keep `source_file: unknown` — their raw
  basenames carry no generation id)
- **v2 fields (FR-883):** `prompt, source_file, local_model, dialect,
  seed, size, created`; `dialect ∈ {prose, tags}` derived mechanically
  (Pony/SDXL-family model or `score_`-family negative prompt ⇒ tags) —
  split: 4,659 prose / 2,733 tags. `==== Signed:` duplicate blocks are
  excluded at parse time.
- **Approval:** operator approved publication 2026-08-19
- **Redaction policy** (blocklists live in
  [scripts/extract_corpus.py](scripts/extract_corpus.py)):
  - LoRA/weight syntax stripped from kept prompts
  - name-bearing comma/sentence segments stripped, rows kept
    (strip-not-drop, FR-884: 1,499 rows recovered); serialized output
    is scanned for name leaks before the file is finalized — a leak
    raises and leaves no artifact
  - prompts containing non-consent/violence terms excluded (88)
  - mechanical scan: no absolute paths, token-like strings, or emails
  - `source_file` reduced to the numeric generation id
- The raw unsanitized corpus never leaves the operator's machine.

## State machine (FR-826 R-3)

`state/published.jsonl` statuses: `drawn → submitted → published | skipped`.
Every transition guarding an external call is committed-and-pushed
before the next side effect. Reruns resume; a terminal same-day record
exits idempotently. A post-publish commit failure fails the run as
`RECOVERY_REQUIRED` with the deviation id in the log.

## Model roster (FR-826 R-4, frozen)

| Model | Slug | Status |
|---|---|---|
| z-image | `prunaai/z-image-turbo` | active |
| flux-2-flex | `black-forest-labs/flux-2-flex` | active — 16:9, 2 MP, png |
| nano-banana-2 | `google/nano-banana-2` | active — 16:9, 2K, png |
| grok | `xai/grok-imagine-image-2` | active — 16:9, 2k, quality medium |
| recraft | `recraft-ai/recraft-v4` | active — 1344×768 (16:9), webp→png at boundary |
| flux-ultra | `black-forest-labs/flux-1.1-pro-ultra` | retired 2026-08-23 (superseded) |

## Workflows (FR-862)

Both workflows call one reusable body, `.github/workflows/_pipeline.yml`,
and share the concurrency group `daily-publish`. That sharing is
load-bearing, not cosmetic: overlapping runs each refresh the DA token,
which **rotates on every use**, so the second run would authenticate
with a token the first already invalidated while the secret write races.
`tests/test_workflows.py` fails if the two callers drift.

| Workflow | Trigger | Passes |
|---|---|---|
| `daily-publish` | cron `0 7 * * *` + dispatch | nothing — today's UTC date only |
| `publish-now` | dispatch only | `model`, `date` |

```bash
gh workflow run publish-now.yml                          # publishes now
gh workflow run publish-now.yml -f model=nano-banana-2   # pin the model
```

**Running it publishes.** There is no dry-run flag and no force flag:
invoking the workflow *is* the intent, and a button that does nothing
by default is not a safety feature. Every run takes the next slot for
the day and publishes it.

### Inputs

- **`model`** (default `random`) — pin one roster entry. An unknown
  name raises `RosterError` rather than silently falling back.
- **`date`** (default empty = today UTC) — strict `YYYY-MM-DD`.

Both arrive as strings and are parsed in [tools/inputs.py](tools/inputs.py)
before any side effect.

### Slots

Run identity is `(date, slot)`. The day's first run takes slot 0 and
writes `posts/<date>.md`; each further run that day takes the next slot
and writes `posts/<date>-<slot>.md`.

The **one** thing that diverts a run: an in-flight slot (`drawn` or
`submitted`) is resumed rather than duplicated, because its committed
ledger row may already guard a DeviantArt call in flight (FR-826 R-3).
That is crash recovery, not a guard against the operator.

Ledger rows written before slots existed have no `slot` field and
normalize to 0 when read. Corpus no-repeat is global across dates and
slots, so no post can reuse a published prompt.

## Secrets

`REPLICATE_API_TOKEN`, `ANTHROPIC_API_KEY`, `DA_CLIENT_ID`,
`DA_CLIENT_SECRET`, `DA_REFRESH_TOKEN` (rotates every run —
persisted back via `GH_PAT` BEFORE publishing), `GH_PAT`
(fine-grained, this repo only, secrets:write).

## Tests

```bash
pip install -e ".[dev]" && pytest
```
