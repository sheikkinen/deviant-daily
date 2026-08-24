"""Rung 0: stdlib-only word-level trigram Markov baseline (FR-876 AC-02).

Demonstrates that prompt generation is next-token prediction; the
baseline the transformer rung is measured against.
"""

from __future__ import annotations

import random
from collections import defaultdict

START = ("<s>", "<s>")
END = "</s>"


class MarkovModel:
    def __init__(self, table: dict[tuple[str, str], list[str]]):
        self.table = table

    @classmethod
    def fit(cls, prompts: list[str]) -> MarkovModel:
        table: dict[tuple[str, str], list[str]] = defaultdict(list)
        for prompt in prompts:
            words = prompt.split()
            state = START
            for word in words:
                table[state].append(word)
                state = (state[1], word)
            table[state].append(END)
        return cls(dict(table))

    def generate(self, rng: random.Random, max_words: int = 80) -> str:
        state = START
        out: list[str] = []
        for _ in range(max_words):
            choices = self.table.get(state)
            if not choices:
                break
            word = rng.choice(choices)
            if word == END:
                break
            out.append(word)
            state = (state[1], word)
        return " ".join(out)
