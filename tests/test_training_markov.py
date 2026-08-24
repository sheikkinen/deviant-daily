"""Witness tests for training/markov.py (FR-876 AC-02, yamlgraph)."""

import random
import subprocess
import sys
from pathlib import Path

from training.markov import MarkovModel

ROWS = [
    {"prompt": "a dark forest of glass trees under a violet sky, haunting"},
    {"prompt": "a dark forest of iron trees under a golden sky, serene"},
    {"prompt": "neon city streets, rain slick, chrome reflections everywhere"},
]


def test_deterministic_under_seeded_rng():
    model = MarkovModel.fit([r["prompt"] for r in ROWS])
    a = model.generate(random.Random(42), max_words=30)
    b = model.generate(random.Random(42), max_words=30)
    assert a == b
    assert len(a.split()) >= 3


def test_different_seeds_can_differ():
    model = MarkovModel.fit([r["prompt"] for r in ROWS])
    outs = {model.generate(random.Random(s), max_words=30) for s in range(20)}
    assert len(outs) > 1


def test_no_torch_dependency():
    code = (
        "import sys; import training.markov; "
        "sys.exit(1 if 'torch' in sys.modules else 0)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=Path(__file__).parent.parent, check=False
    )
    assert proc.returncode == 0
