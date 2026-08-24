"""Minimal LLM training demo (yamlgraph FR-876).

Trains on the public, redacted prompts/corpus.jsonl ONLY — never on
raw signed.log. All generated output passes training/boundary.py
before persistence (judgement R-2).
"""
