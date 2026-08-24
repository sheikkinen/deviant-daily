"""Corpus extraction from signed.log (FR-826 R-2, AC-04; v2 metadata FR-883).

Parses ImageMagick-identify style log entries (``==== File: <name> ====``),
pulls the free text of each ``parameters:`` field (the generation prompt,
ending before ``Steps:`` / ``Negative prompt:``), sanitizes it per the
operator-approved redaction policy (2026-08-19), dedups, and writes
``prompts/corpus.jsonl`` v2 rows: ``{prompt, source_file, local_model,
dialect, seed, size, created}``. ``==== Signed:`` duplicate blocks are
excluded and reset parser state (FR-883 AC-04).

Redaction policy (public by design — the raw corpus never is):
- LoRA/weight syntax STRIPPED from kept prompts
- prompts containing personal names EXCLUDED (NAME_BLOCKLIST)
- prompts containing non-consent/violence terms EXCLUDED (TERM_BLOCKLIST)

Usage:
    python scripts/extract_corpus.py <signed.log> <out.jsonl> [--sample N]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

# Operator-approved blocklists (FR-826 C-4, 2026-08-19). Extensible.
NAME_BLOCKLIST = ["katja", "tuija", "nina"]
TERM_BLOCKLIST = ["rape"]

ENTRY_RE = re.compile(r"^==== File: (.+?) ====$")
HEADER_RE = re.compile(r"^==== ")
PARAMS_RE = re.compile(r"^\s{4}parameters: (.*)$")
NEG_RE = re.compile(r"^Negative prompt: (.*)$")
STEPS_RE = re.compile(r"^Steps: ")
DATE_RE = re.compile(r"^\s{4}date:create: (\S+)")
LORA_RE = re.compile(r"<(?:lora|lyco):[^>]*>", re.IGNORECASE)
WEIGHT_RE = re.compile(r":\d+(?:\.\d+)?\)")
# v2 metadata (FR-883): pulled from the Steps line and Properties block.
MODEL_RE = re.compile(r"(?:^|, )Model: ([^,]+)")
SEED_RE = re.compile(r"\bSeed: (\d+)")
SIZE_RE = re.compile(r"\bSize: (\d+x\d+)")
TAGS_MODEL_RE = re.compile(r"sdxl|pony|xl", re.IGNORECASE)
SCORE_NEG_RE = re.compile(r"score_\d")
# Mechanical scan patterns (AC-04: no paths, tokens, emails in output).
# Token pattern excludes underscores: booru-style tag prompts are long
# underscore_joined_words, not credentials.
SCAN_PATTERNS = {
    "absolute_path": re.compile(r"/Users/|/home/|[A-Z]:\\\\"),
    "token_like": re.compile(r"\b(?:[A-Za-z0-9+/=]{40,}|[0-9a-fA-F]{40,})\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}"),
}


def name_blocklist_re(words: list[str]) -> re.Pattern[str]:
    # Plain substring: catches nina_heikkinen, nina1, Nina's — misses cost
    # more than collateral exclusions.
    return re.compile("|".join(map(re.escape, words)), re.IGNORECASE)


def term_blocklist_re(words: list[str]) -> re.Pattern[str]:
    # Letter-lookbehind stem: catches raped/_raped, not drapery/grapes.
    return re.compile(
        r"(?<![a-zA-Z])(" + "|".join(map(re.escape, words)) + ")", re.IGNORECASE
    )


def sanitize(prompt: str) -> str:
    """Strip LoRA syntax and weight tags; collapse whitespace."""
    prompt = LORA_RE.sub("", prompt)
    prompt = WEIGHT_RE.sub(")", prompt)
    return re.sub(r"\s+", " ", prompt).strip()


def derive_dialect(local_model: str, negative: str) -> str:
    """Mechanical dialect rule (FR-883): Pony/SDXL family or score_-family
    negative prompt ⇒ booru-tag dialect; everything else is prose."""
    if local_model and TAGS_MODEL_RE.search(local_model):
        return "tags"
    if negative and SCORE_NEG_RE.search(negative):
        return "tags"
    return "prose"


def parse_entries(lines: list[str]) -> list[dict]:
    """Yield per-``==== File:`` entry dicts: source, prompt, negative,
    meta (Steps line), created. Any ``====`` header resets state, so
    ``==== Signed:`` blocks can never contribute or adopt a payload."""
    entries: list[dict] = []
    entry: dict | None = None
    buf: list[str] | None = None
    neg: list[str] | None = None

    def flush() -> None:
        nonlocal entry, buf, neg
        if entry is not None and buf is not None:
            entry["prompt"] = " ".join(buf).strip()
            entry["negative"] = " ".join(neg).strip() if neg else ""
            entries.append(entry)
        entry, buf, neg = None, None, None

    for line in lines:
        if HEADER_RE.match(line):
            flush()
            m = ENTRY_RE.match(line)
            if m:
                entry = {
                    "source": Path(m.group(1).strip()).name,
                    "created": "",
                    "meta": "",
                }
            continue
        if entry is None:
            continue
        dm = DATE_RE.match(line)
        if dm and not entry["created"]:
            entry["created"] = dm.group(1)
            continue
        pm = PARAMS_RE.match(line)
        if pm:
            buf = [pm.group(1)]
            continue
        if buf is None:
            continue
        nm = NEG_RE.match(line)
        if nm:
            neg = [nm.group(1)]
            continue
        if STEPS_RE.match(line):
            entry["meta"] = line
            flush()
            continue
        if line.startswith("    png:"):
            flush()
            continue
        if neg is not None:
            neg.append(line.strip())
        else:
            buf.append(line.strip())
    flush()
    return entries


def extract(log_path: Path, out_path: Path, sample_n: int = 0) -> dict:
    lines = log_path.read_text(errors="replace").splitlines()
    entries = parse_entries(lines)
    name_re = name_blocklist_re(NAME_BLOCKLIST)
    term_re = term_blocklist_re(TERM_BLOCKLIST)

    stats = {
        "entries": len(entries),
        "name_excluded": 0,
        "term_excluded": 0,
        "empty": 0,
        "duplicates": 0,
        "scan_hits": 0,
        "kept": 0,
        "unknown": 0,
    }
    seen: set[str] = set()
    rows: list[dict] = []
    for e in entries:
        source, raw = e["source"], e["prompt"]
        prompt = sanitize(raw)
        if not prompt or len(prompt) < 10:
            stats["empty"] += 1
            continue
        if name_re.search(prompt):
            stats["name_excluded"] += 1
            continue
        if term_re.search(prompt):
            stats["term_excluded"] += 1
            continue
        key = prompt.lower()
        if key in seen:
            stats["duplicates"] += 1
            continue
        seen.add(key)
        # Basenames embed raw prompt text (incl. LoRA names) — keep only
        # the NNNNN-SEED id as provenance; it leaks nothing.
        id_match = re.match(r"^(\d+-\d+)", source)
        source_id = id_match.group(1) if id_match else "unknown"
        meta = e["meta"]
        mm = MODEL_RE.search(meta)
        sm = SEED_RE.search(meta)
        zm = SIZE_RE.search(meta)
        local_model = mm.group(1).strip() if mm else ""
        row = {
            "prompt": prompt,
            "source_file": source_id,
            "local_model": local_model,
            "dialect": derive_dialect(local_model, e["negative"]),
            "seed": int(sm.group(1)) if sm else None,
            "size": zm.group(1) if zm else "",
            "created": e["created"],
        }
        hits = [n for n, p in SCAN_PATTERNS.items() if p.search(json.dumps(row))]
        if hits:
            stats["scan_hits"] += 1
            print(f"SCAN EXCLUDED ({hits}): {source}", file=sys.stderr)
            continue
        if source_id == "unknown":
            stats["unknown"] += 1
        rows.append(row)
    stats["kept"] = len(rows)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    if sample_n:
        sample = random.sample(rows, min(sample_n, len(rows)))
        sample_path = out_path.with_suffix(".sample.txt")
        sample_path.write_text(
            "\n\n".join(f"[{r['source_file']}]\n{r['prompt']}" for r in sample)
        )
        print(f"sample slice: {sample_path}", file=sys.stderr)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--sample", type=int, default=0)
    args = ap.parse_args()
    stats = extract(args.log, args.out, args.sample)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
