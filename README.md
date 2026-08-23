# deviant-daily

Autonomous daily art publisher. Every morning a GitHub Actions run:

1. **draws** a random prompt from the operator's own generation history
   ([prompts/corpus.jsonl](prompts/corpus.jsonl))
2. **generates** an image on Replicate (frozen model roster)
3. **describes** it in the sheikkinen mythic voice
   ([STYLE-CONTRACT.md](STYLE-CONTRACT.md), vision LLM)
4. **gates** the result through a deterministic typed schema
5. **publishes** to [DeviantArt](https://www.deviantart.com/sheikkinen)
   via the OAuth2 API (`is_ai_generated=true`, `noai=true`)
6. **commits** the post record back to this repo

The pipeline is a [YAMLGraph](https://github.com/sheikkinen/yamlgraph)
graph ([graph.yaml](graph.yaml)) — yamlgraph runs unattended; Python
exists only for side effects ([tools/](tools/)). Governed by yamlgraph
FR-826.

## Corpus provenance (FR-826 R-2)

- **Source:** operator's local `signed.log` generation history
  (9,038 parsed entries; 13,682 raw log records)
- **Kept:** 5,893 prompts after sanitization and dedup
- **Approval:** operator approved publication 2026-08-19
- **Redaction policy** (blocklists live in
  [scripts/extract_corpus.py](scripts/extract_corpus.py)):
  - LoRA/weight syntax stripped from kept prompts
  - prompts containing personal names excluded (2,020)
  - prompts containing non-consent/violence terms excluded (69)
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
| `publish-now` | dispatch only | `dry_run`, `model`, `force`, `date` |

```bash
gh workflow run publish-now.yml -f dry_run=true -f model=nano-banana-2
gh workflow run publish-now.yml -f dry_run=false -f force=true   # extra post today
```

### Inputs

- **`dry_run`** (default `true`) — runs draw → generate → describe →
  gate and stops. It is **no-publication, not no-cost**:

  | Guaranteed absent | Still spent |
  |---|---|
  | ledger commits, git commits, post files | Replicate generation |
  | all DeviantArt calls (OAuth, submit, publish) | Anthropic vision |
  | `gh secret set` token rotation | Actions minutes |

  A dry run needs no DeviantArt secrets at all. Output is a run
  artifact containing the image and the gate-passing post dict.

- **`model`** (default `random`) — pin one roster entry. An unknown
  name raises `RosterError` rather than silently falling back.

- **`force`** (default `false`) — publish an **extra** post on a date
  that already has one. Allocates the next slot, and only above a
  *terminal* slot: if the latest slot is still in flight, force resumes
  it instead, because its committed row may already guard a DA submit.

- **`date`** (default empty = today UTC) — strict `YYYY-MM-DD`.

All four arrive as strings and are parsed in [tools/inputs.py](tools/inputs.py)
before any side effect — `"false"` is truthy in Python, so an unparsed
boolean would invert `force`/`dry_run`.

### Slots

Run identity is `(date, slot)`. Slot 0 is the scheduled run and writes
`posts/<date>.md`; forced extras are slot 1, 2, … and write
`posts/<date>-<slot>.md`. Ledger rows written before FR-862 have no
`slot` field and normalize to 0 when read. Corpus no-repeat is global
across dates and slots, so a forced post can never reuse a published
prompt.

## Secrets

`REPLICATE_API_TOKEN`, `ANTHROPIC_API_KEY`, `DA_CLIENT_ID`,
`DA_CLIENT_SECRET`, `DA_REFRESH_TOKEN` (rotates every run —
persisted back via `GH_PAT` BEFORE publishing), `GH_PAT`
(fine-grained, this repo only, secrets:write).

## Tests

```bash
pip install -e ".[dev]" && pytest
```
