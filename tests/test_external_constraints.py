"""Tests: external-constraint mirroring (2026-08-23 production failures).

1. DeviantArt rejects long titles ("title has incorrect length", run
   32624528720). Our schema allowed 120 chars while DA caps at 50 — the
   constraint lives at the DA boundary and must be mirrored inward.
2. 1937 of 5893 corpus rows carry source_file "unknown". Publishing one
   would exclude every other one from future draws, silently killing a
   third of the corpus.
"""

import json

from tools.corpus import draw_prompt, row_id
from tools.gate import DA_TITLE_MAX, evaluate_gate

VALID = {
    "title": "T",
    "paragraphs": ["p"],
    "quote": None,
    "tags": ["aiart"],
    "confidence": "high",
    "mature": False,
    "mature_level": None,
    "mature_classification": [],
}


def test_short_title_is_untouched():
    r = evaluate_gate({**VALID, "title": "Starlight's Reckoning"})
    assert r.post.title == "Starlight's Reckoning"


def test_overlong_title_is_trimmed_to_the_da_ceiling():
    long = "Nocturnal Liturgy of the Cathedral and Its Dark Communion of Shadows"
    assert len(long) > DA_TITLE_MAX
    r = evaluate_gate({**VALID, "title": long})
    assert r.publish is True
    assert len(r.post.title) <= DA_TITLE_MAX


def test_trim_lands_on_a_word_boundary():
    long = "Descent Through Shadow and Flame and Everlasting Midnight Silence"
    r = evaluate_gate({**VALID, "title": long})
    assert not r.post.title.endswith(" ")
    assert long.startswith(r.post.title)
    assert r.post.title.split()[-1] in long.split()


def test_unknown_source_files_get_distinct_ids():
    a = {"prompt": "a vampire in a cathedral", "source_file": "unknown"}
    b = {"prompt": "a robot in a saloon", "source_file": "unknown"}
    assert row_id(a) != row_id(b)
    assert row_id(a) == row_id(dict(a)), "must be deterministic"


def test_real_source_file_is_its_own_id():
    assert row_id({"prompt": "p", "source_file": "00105-408526945"}) == "00105-408526945"


def test_publishing_one_unknown_row_does_not_exclude_the_others(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    rows = [
        {"prompt": "first unknown prompt", "source_file": "unknown"},
        {"prompt": "second unknown prompt", "source_file": "unknown"},
    ]
    corpus.write_text("".join(json.dumps(r) + "\n" for r in rows))
    used = [{"date": "2026-08-22", "slot": 0, "status": "published",
             "source_file": row_id(rows[0])}]
    drawn = draw_prompt(corpus, used, "2026-08-23", slot=0)
    assert drawn["prompt"] == "second unknown prompt"
    assert drawn["source_file"] == row_id(rows[1])
