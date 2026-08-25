"""Corpus fingerprint enrichment runner (FR-890).

Selects unclassified rows (resume contract keyed to taxonomy version +
model id), runs graphs/corpus_fingerprint.yaml in batches with GLOBAL
row indices as refs, merges verdicts additively, and rewrites the
corpus atomically after each batch — a killed run resumes for free.

Preflight cost estimate enforces the FR-890 spend ceiling ($10) before
any paid call. Emits a run record JSON (D-6) with the distribution
report; exits nonzero when other-share exceeds 10% (C-4 — result is
not committable).

Usage:
    python scripts/enrich_corpus.py [--corpus prompts/corpus.jsonl]
        [--batch-size 50] [--limit N] [--dry-run] [--ceiling 10.0]
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.fingerprint import (
    TAXONOMY_PATH,
    distribution_report,
    estimate_cost,
    is_classified,
    load_taxonomy,
    merge_fingerprints,
)

GRAPH_PATH = Path("graphs/corpus_fingerprint.yaml")
OTHER_SHARE_MAX = 0.10


def graph_model_id(graph_path: Path = GRAPH_PATH) -> str:
    """Single source of truth for the classifier model id."""
    m = re.search(r"^\s*model:\s*(\S+)", graph_path.read_text(), re.MULTILINE)
    if not m:
        raise SystemExit(f"no model id found in {graph_path}")
    return m.group(1)


def read_corpus(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_corpus_atomic(rows: list[dict], path: Path) -> None:
    payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(payload)
    tmp.replace(path)


def run_batch(refs: list[int], rows: list[dict], tmp_dir: Path) -> list[dict]:
    """One graph invocation; refs are global row indices."""
    batch_file = tmp_dir / "fingerprint_batch.json"
    results_file = tmp_dir / "fingerprint_results.json"
    results_file.unlink(missing_ok=True)
    batch_file.write_text(
        json.dumps(
            {
                "items": [{"ref": i, "prompt": rows[i]["prompt"]} for i in refs],
                "taxonomy_path": str(TAXONOMY_PATH),
            }
        )
    )
    proc = subprocess.run(
        [
            "yamlgraph",
            "graph",
            "run",
            str(GRAPH_PATH),
            "--var",
            f"batch_file={batch_file}",
            "--var",
            f"results_file={results_file}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not results_file.exists():
        raise SystemExit(
            f"graph run failed (rc={proc.returncode}):\n{proc.stderr[-2000:]}"
        )
    return json.loads(results_file.read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=Path("prompts/corpus.jsonl"))
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--limit", type=int, default=0, help="cap rows for a smoke run")
    ap.add_argument("--dry-run", action="store_true", help="preflight only")
    ap.add_argument("--ceiling", type=float, default=10.0)
    args = ap.parse_args()

    tax = load_taxonomy()
    model = graph_model_id()
    date = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    rows = read_corpus(args.corpus)

    pending = [i for i, r in enumerate(rows) if not is_classified(r, tax, model)]
    if args.limit:
        pending = pending[: args.limit]
    print(f"corpus rows: {len(rows)}, pending: {len(pending)}, model: {model}")

    est = estimate_cost([rows[i]["prompt"] for i in pending], ceiling=args.ceiling)
    print(f"preflight estimate: ${est:.2f} (ceiling ${args.ceiling:.2f})")
    if args.dry_run:
        return

    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)
    total_rejections: dict[str, int] = {}
    attempted = 0
    for start in range(0, len(pending), args.batch_size):
        batch_refs = pending[start : start + args.batch_size]
        # hard stop keyed to attempted calls, before the ceiling
        estimate_cost(
            [rows[i]["prompt"] for i in pending[: attempted + len(batch_refs)]],
            ceiling=args.ceiling,
        )
        attempted += len(batch_refs)
        verdicts = run_batch(batch_refs, rows, tmp_dir)
        rows, rejections = merge_fingerprints(rows, verdicts, tax, model, date)
        for k, v in rejections.items():
            total_rejections[k] = total_rejections.get(k, 0) + v
        write_corpus_atomic(rows, args.corpus)
        done = min(start + args.batch_size, len(pending))
        print(f"batch {start}-{done}/{len(pending)} merged, rejections={rejections}")

    report = distribution_report(rows)
    record = {
        "fr": "FR-890",
        "date": date,
        "model": model,
        "taxonomy": tax["taxonomy"],
        "attempted_calls": attempted,
        "estimate_usd": round(est, 2),
        "ceiling_usd": args.ceiling,
        "rejections": total_rejections,
        "report": report,
    }
    logs = Path("logs")
    logs.mkdir(exist_ok=True)
    record_path = logs / f"fingerprint_run_{date}.json"
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    print(json.dumps(record, indent=2, ensure_ascii=False))
    print(f"run record: {record_path}")

    if report["other_share"] > OTHER_SHARE_MAX:
        print(
            f"other-share {report['other_share']:.1%} > 10% — "
            "taxonomy audit required, result NOT committable (C-4)",
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
