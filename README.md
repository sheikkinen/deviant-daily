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
| flux-ultra | `black-forest-labs/flux-1.1-pro-ultra` | active |
| grok | xai/grok-imagine-image-2 | 16:9, 2k, quality medium |

## Secrets

`REPLICATE_API_TOKEN`, `ANTHROPIC_API_KEY`, `DA_CLIENT_ID`,
`DA_CLIENT_SECRET`, `DA_REFRESH_TOKEN` (rotates every run —
persisted back via `GH_PAT` BEFORE publishing), `GH_PAT`
(fine-grained, this repo only, secrets:write).

## Tests

```bash
pip install -e ".[dev]" && pytest
```
