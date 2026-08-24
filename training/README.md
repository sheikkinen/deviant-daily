# training/ — Minimal LLM Training Demo (yamlgraph FR-876)

A from-scratch demonstration of LLM training mechanics using this
repo's public, redacted `prompts/corpus.jsonl` (5,893 image-generation
prompts, ~600 K tokens) as the training source.

**Honesty note:** 600 K tokens is far too small to train a *good*
language model. That asymmetry is the point — this is a *teaching
artifact* whose distinctive corpus style makes learning visible to the
naked eye within minutes, not a quality generator.

**Provenance rule:** train ONLY on the committed, redacted
`prompts/corpus.jsonl` — never on raw `signed.log` or any unsanitized
source. The trained model is exactly as public as its data.

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[training]"   # torch enters ONLY via this extra
```

The publish pipeline never imports torch — witnessed by
`tests/test_training_eval.py::test_publish_modules_import_without_torch`.

## The three commands

```bash
python -m training.prepare prompts/corpus.jsonl training/data --seed 7
python -m training.train --seed 42 --steps 5000 --out training/ckpt
python -m training.generate --ckpt training/ckpt --n 20 --temp 0.8
```

Run everything from the repo root (the boundary imports redaction
patterns from `scripts/extract_corpus.py`).

## What each piece teaches

| Module | Lesson |
|--------|--------|
| `markov.py` | Generation = next-token prediction (stdlib trigram baseline) |
| `prepare.py` | Dataset shaping: documents, separators, register conditioning (`<tag>`/`<prose>`), deterministic 95/5 split |
| `model.py` | Char tokenizer + tiny GPT (~5 M params): embeddings, causal attention, LM head, temperature/top-k sampling |
| `train.py` | The loop: batching, loss curve, reproducibility (seed/device/SHA logging) |
| `boundary.py` | Model output is a claim: redaction re-scan, 8-gram novelty floor, shape gates |
| `evaluate.py` | Rejection-statistics table — what training buys, measured |

## The generation boundary

Extraction-time redaction does not transfer to a trained model — it
can recombine tokens into excluded content. Every sample that reaches
stdout, a log, or a committed artifact passes `boundary.py` first:

1. **Redaction** — the same NAME/TERM blocklists and scan patterns as
   `scripts/extract_corpus.py`, imported (never copied).
2. **Novelty** — reject verbatim rows and any shared word-level 8-gram
   with the corpus (small models memorize small corpora; the
   regurgitation-rate-vs-temperature curve is itself a demo output).
3. **Shape** — 100–800 chars, non-empty, no truncation (the sampler
   reports whether `<|end|>` was emitted within the token budget).

Rejected raw text is never persisted — only its rejection reason.

## Evaluation

```bash
python -m training.evaluate --ckpt training/ckpt --n 200
```

Produces `training/rejection-stats.md`: pass/redaction/novelty/shape
counts for Markov vs transformer per temperature. Coherence is
deliberately not a mechanical claim (FR-876 judgement R-5); human
sample-read notes are non-gating.

## Artifact hygiene

- Checkpoints (`training/ckpt/`) and datasets (`training/data/`) are
  gitignored — regenerable from the corpus.
- Committed evidence: training run log, temperature sample sheets,
  rejection-stats table — all boundary-filtered (judgement C-4).

## What this is not

- Not a `draw_prompt()` fallback — corpus-exhaustion integration is
  deferred to a future FR (judgement AC-13/C-6).
- Not a fine-tuning demo — LoRA on an open model teaches adaptation,
  a different lesson, and is out of scope.

Governing FR: `yamlgraph:feature-requests/FR-876-minimal-llm-training-demo.md`
and its judgement.
