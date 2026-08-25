"""Corpus fingerprint enrichment boundary (FR-890).

Taxonomy loading, classifier-output validation (the LLM verdict is a
CLAIM — closed-set checked here, never coerced), batch I/O tools for
graphs/corpus_fingerprint.yaml, and the additive row merge.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

TAXONOMY_PATH = Path("data/corpus_fingerprint_taxonomy.yaml")
CONTENT_VALUES = ("safe", "mature")


class FingerprintError(RuntimeError):
    pass


def load_taxonomy(path: str | Path = TAXONOMY_PATH) -> dict:
    tax = yaml.safe_load(Path(path).read_text())
    for key in ("taxonomy", "content", "genres"):
        if key not in tax:
            raise FingerprintError(f"taxonomy missing key: {key}")
    return tax


def genre_names(tax: dict) -> list[str]:
    """Genre names in precedence order."""
    genres = sorted(tax["genres"], key=lambda g: g["precedence"])
    return [g["name"] for g in genres]


def taxonomy_rules_text(tax: dict) -> str:
    """Render taxonomy rules for the classifier prompt (single source)."""
    lines = []
    for axis in ("sexual", "gore"):
        spec = tax["content"][axis]
        lines.append(f"{axis}: mature iff {spec['mature_iff'].strip()}")
        lines.append(f"  safe note: {spec['safe_note'].strip()}")
    lines.append("")
    lines.append("Genres (precedence order — on overlap the earliest wins;")
    lines.append("choose the most specific non-other label):")
    for g in sorted(tax["genres"], key=lambda x: x["precedence"]):
        lines.append(f"- {g['name']}: {g['include'].strip()}")
        if g.get("exclude"):
            lines.append(f"  NOT: {g['exclude'].strip()}")
    return "\n".join(lines)


def validate_verdict(verdict: dict, batch_refs: set[int], tax: dict) -> str | None:
    """Return a rejection reason, or None when the verdict is in-set."""
    ref = verdict.get("ref")
    if not isinstance(ref, int) or ref not in batch_refs:
        return "bad-ref"
    if verdict.get("sexual") not in CONTENT_VALUES:
        return "bad-sexual"
    if verdict.get("gore") not in CONTENT_VALUES:
        return "bad-gore"
    if verdict.get("genre") not in genre_names(tax):
        return "bad-genre"
    return None


def merge_fingerprints(
    rows: list[dict],
    verdicts: list[dict],
    tax: dict,
    model: str,
    date: str,
) -> tuple[list[dict], dict[str, int]]:
    """Additive merge: classified rows gain content+fingerprint keys.

    Row order, count, and prompt bytes are invariant. Duplicate refs and
    out-of-set verdicts are counted rejections — never coerced (AC-03).
    Returns (rows, rejection_counts).
    """
    refs = set(range(len(rows)))
    rejections: dict[str, int] = {}
    seen: set[int] = set()
    for verdict in verdicts:
        reason = validate_verdict(verdict, refs, tax)
        if reason is None and verdict["ref"] in seen:
            reason = "duplicate-ref"
        if reason:
            rejections[reason] = rejections.get(reason, 0) + 1
            continue
        ref = verdict["ref"]
        seen.add(ref)
        rows[ref] = {
            **rows[ref],
            "content": {"sexual": verdict["sexual"], "gore": verdict["gore"]},
            "fingerprint": {
                "genre": verdict["genre"],
                "date": date,
                "model": model,
                "taxonomy": tax["taxonomy"],
            },
        }
    return rows, rejections


def is_classified(row: dict, tax: dict, model: str) -> bool:
    """Resume contract (AC-06): same taxonomy version and model id."""
    fp = row.get("fingerprint")
    return (
        isinstance(fp, dict)
        and "content" in row
        and fp.get("taxonomy") == tax["taxonomy"]
        and fp.get("model") == model
    )


# ── Graph tools (graphs/corpus_fingerprint.yaml) ──────────────────────


def load_batch(batch_file: str) -> dict:
    """Read the batch file and expose items + taxonomy rules to the graph."""
    payload = json.loads(Path(batch_file).read_text())
    tax = load_taxonomy(payload.get("taxonomy_path", TAXONOMY_PATH))
    return {
        "items": payload["items"],
        "taxonomy_rules": taxonomy_rules_text(tax),
        "genre_list": ", ".join(genre_names(tax)),
    }


def save_results(results_file: str, verdicts: list) -> dict:
    """Persist raw map verdicts; validation happens in the enrich script."""
    out = []
    for v in verdicts or []:
        if hasattr(v, "model_dump"):
            v = v.model_dump()
        out.append(v)
    Path(results_file).write_text(json.dumps(out, ensure_ascii=False))
    return {"saved": len(out)}
