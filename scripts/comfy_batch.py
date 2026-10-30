"""Render every deviant-daily corpus prompt through local ComfyUI, one at a time.

Resumable: each job is journaled (submitted -> success|failed|skipped) in
STATE. On restart, finished rows are skipped and an in-flight prompt_id is
re-polled instead of resubmitted.

    nohup .venv/bin/python scripts/comfy_batch.py >> tmp/comfy_batch.log 2>&1 &
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CORPUS = ROOT / "prompts/corpus.jsonl"
TEMPLATE = HERE / "zimage_reazit_api.json"
STATE = ROOT / "tmp/comfy_batch_state.jsonl"
BASE = "http://127.0.0.1:8188"
POLL_S = 5
JOB_TIMEOUT_S = 45 * 60
TERMINAL = {"success", "failed", "skipped"}


def row_id(row: dict) -> str:
    """Same key as deviant-daily tools/corpus.py, so ids line up with the ledger."""
    source = row.get("source_file") or "unknown"
    if source != "unknown":
        return source
    return "unknown-" + hashlib.sha1(row["prompt"].encode("utf-8")).hexdigest()[:12]


def api(path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def load_state() -> dict[str, dict]:
    last: dict[str, dict] = {}
    if STATE.exists():
        for line in STATE.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                last[rec["id"]] = rec
    return last


def journal(rec: dict) -> None:
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with STATE.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def build_graph(template: dict, row: dict, rid: str) -> dict:
    g = copy.deepcopy(template)
    w, h = (int(x) for x in (row.get("size") or "1024x1024").split("x"))
    g["57:27"]["inputs"]["text"] = row["prompt"]
    g["57:3"]["inputs"]["seed"] = int(row.get("seed") or 0)
    g["57:13"]["inputs"].update(width=w - w % 16, height=h - h % 16)
    g["9"]["inputs"]["filename_prefix"] = f"deviant-daily/corpus/{rid}"
    g.pop("62", None)  # PreviewImage only fills the temp dir
    return g


def wait_for(prompt_id: str) -> tuple[str, list[str], str]:
    start = time.time()
    while time.time() - start < JOB_TIMEOUT_S:
        hist = api(f"/history/{prompt_id}")
        if prompt_id in hist:
            entry = hist[prompt_id]
            st = entry.get("status", {})
            files = [
                f"{im['subfolder']}/{im['filename']}"
                for out in entry.get("outputs", {}).values()
                for im in out.get("images", [])
                if im.get("type") == "output"
            ]
            ok = st.get("status_str") == "success" and files
            err = "" if ok else json.dumps(st.get("messages", [])[-1:])[:500]
            return ("success" if ok else "failed"), files, err
        time.sleep(POLL_S)
    return "failed", [], f"timeout after {JOB_TIMEOUT_S}s"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="stop after N renders this session")
    args = ap.parse_args()

    template = json.loads(TEMPLATE.read_text())
    rows = [
        json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()
    ]
    state = load_state()
    done = sum(1 for r in state.values() if r["status"] in TERMINAL)
    print(f"corpus={len(rows)} already_done={done} state={STATE}", flush=True)

    rendered, seen = 0, set()
    try:
        for i, row in enumerate(rows):
            rid = row_id(row)
            if rid in seen:
                continue
            seen.add(rid)
            prev = state.get(rid)
            if prev and prev["status"] in TERMINAL:
                continue

            if args.limit is not None and rendered >= args.limit:
                break

            if prev and prev["status"] == "submitted":
                prompt_id = prev["prompt_id"]
                print(f"[{i}] {rid} resuming in-flight {prompt_id}", flush=True)
            else:
                resp = api(
                    "/prompt",
                    {
                        "prompt": build_graph(template, row, rid),
                        "client_id": str(uuid.uuid4()),
                    },
                )
                if resp.get("node_errors"):
                    journal(
                        {
                            "id": rid,
                            "index": i,
                            "status": "failed",
                            "error": json.dumps(resp["node_errors"])[:500],
                        }
                    )
                    continue
                prompt_id = resp["prompt_id"]
                journal(
                    {
                        "id": rid,
                        "index": i,
                        "status": "submitted",
                        "prompt_id": prompt_id,
                    }
                )

            t0 = time.time()
            status, files, err = wait_for(prompt_id)
            secs = round(time.time() - t0)
            journal(
                {
                    "id": rid,
                    "index": i,
                    "status": status,
                    "prompt_id": prompt_id,
                    "files": files,
                    "seconds": secs,
                    **({"error": err} if err else {}),
                }
            )
            rendered += 1
            print(
                f"[{i}/{len(rows)}] {rid} {status} {secs}s {files or err}", flush=True
            )
    except KeyboardInterrupt:
        print(
            "interrupted; rerun to resume (in-flight job keeps rendering)", flush=True
        )
        return 130
    except (urllib.error.URLError, ConnectionError) as e:
        print(f"ComfyUI unreachable: {e}; rerun to resume", flush=True)
        return 2
    print(f"session done: rendered={rendered}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
