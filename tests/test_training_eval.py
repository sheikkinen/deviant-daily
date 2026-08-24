"""Witness tests for training/eval.py table rendering and the
base-install import boundary (FR-876 AC-10, AC-11, yamlgraph)."""

import subprocess
import sys
from pathlib import Path

from training.evaluate import render_table

REPO = Path(__file__).parent.parent

PUBLISH_MODULES = ["tools.corpus", "tools.ledger", "tools.roster", "tools.gate"]


def test_render_table_fixture():
    stats = {
        ("markov", 0.8): {"pass": 120, "redaction": 3, "novelty": 60, "shape": 17},
        ("transformer", 0.8): {"pass": 150, "redaction": 1, "novelty": 9, "shape": 40},
    }
    md = render_table(stats, n_samples=200)
    assert "| markov |" in md and "| transformer |" in md
    assert "60" in md and "150" in md
    assert md.count("|") > 10


def test_publish_modules_import_without_torch():
    """AC-11: base install never pulls torch into the publish path."""
    code = (
        "import sys\n"
        + "\n".join(f"import {m}" for m in PUBLISH_MODULES)
        + "\nsys.exit(1 if 'torch' in sys.modules else 0)"
    )
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO, check=False)
    assert proc.returncode == 0


def test_training_extra_declared():
    text = (REPO / "pyproject.toml").read_text()
    assert 'training = ["torch"]' in text
    base = text.split("[project.optional-dependencies]")[0]
    assert "torch" not in base
