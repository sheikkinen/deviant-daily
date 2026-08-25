#!/usr/bin/env python3
"""FR-890 taxonomy evidence generator: keyword scan + seed-42 raw sample.

Reproduces the 2026-08-25 corpus survey cited by FR-890. Annotations
(genre/sexual/gore) are human labels from the raw read, zipped by order.
"""

import json
import random
import re
import sys

CORPUS = "prompts/corpus.jsonl"

KEYWORDS = {
    "furry": r"anthro|furry|fox girl|wolf_girl|bunny_girl|satyr|feline|owl",
    "gothic": r"vampire|gothic|goth |satanic|demon|succubus",
    "scifi": r"cyborg|android|cyberpunk|biomechanical|robot|hologram|futuristic",
    "fantasy": r"sorceress|knight|angel|elf|dragon|medieval|wizard|fae|fairy",
    "mythological": r"goddess|kali|venus|deity|mytholog|valkyrie",
    "gore terms": r"gore|blood|severed|rotted|skeletal|corpse|zombie|decay",
    "fetish": r"bdsm|bondage|bound|rope|shibari|spanking|submissive|dominatrix",
    "nude/erotica terms": r"nude|erotica|erotic|naked|topless|nippl",
    "pinup": r"pin-up|pinup|boudoir|lingerie|seductive",
    "fanart": r"marvel|dc_comics|batman|disney|daisy duck|chel |likeness|carpenter",
    "booru tags": r"score_9|1girl|rating_explicit",
    "photo style": r"photograph|photography|photorealistic",
    "painting style": r"painting|painterly|charcoal|ink|watercolor|oil ",
    "anime/cartoon": r"anime|cartoon|chibi|manga|toriyama",
}

# Human raw-read labels for the seed-42 sample, in sample order:
# (genre, sexual, gore, observed detail)
ANNOTATIONS = [
    (
        "surreal",
        "safe",
        "safe",
        "ethereal spectral figure, art nouveau mystical landscape",
    ),
    (
        "mythological",
        "safe",
        "mature",
        "Kali dancing amidst a whirlwind of severed heads",
    ),
    (
        "furry",
        "safe",
        "safe",
        "curvaceous anthro owl on gnarled branch, blood-red moon",
    ),
    (
        "scifi",
        "safe",
        "safe",
        "forbidden love between a human and an android, dystopian",
    ),
    (
        "pinup",
        "mature",
        "safe",
        "reclining nude Titian's Venus on psychiatrist's couch",
    ),
    (
        "gothic",
        "mature",
        "safe",
        "gothic vampiress, booru tags incl. explicit anatomy terms",
    ),
    (
        "gothic",
        "mature",
        "safe",
        "souls of the dead, dark fog, rating_explicit tag present",
    ),
    (
        "fanart",
        "mature",
        "safe",
        "Chel from El Dorado, sexualized framing of named IP character",
    ),
    (
        "fanart",
        "safe",
        "safe",
        "Daisy Duck glamorous makeover, gown accentuating curves",
    ),
    (
        "fetish",
        "mature",
        "safe",
        "floating_bondage, elegant_lingerie, surreal dreamscape framing",
    ),
    (
        "surreal",
        "safe",
        "safe",
        "Beksinski-style elongated figure, skeletal architecture",
    ),
    ("gothic", "safe", "safe", "Legba reference, beautiful female vampire kneeling"),
    ("fantasy", "safe", "safe", "green-skinned muscular orc female, steampunk setting"),
    ("furry", "safe", "safe", "wolf_girl snowball fight, mock frown, flushed cheeks"),
    (
        "gothic",
        "mature",
        "safe",
        "chibi female vampire, explicit 'erotica' style directive",
    ),
    ("portrait", "safe", "safe", "charcoal masterpiece, two intertwined silhouettes"),
    (
        "gothic",
        "safe",
        "safe",
        "goth woman telegram sticker, satanic horror cartoon style",
    ),
    ("fantasy", "safe", "safe", "female medieval angel, chainmail armor, epic fantasy"),
    ("pinup", "mature", "safe", "nude in sunlit meadow, 'classical_eroticism' tag"),
    (
        "furry",
        "mature",
        "safe",
        "furry female satyr, 'dynamic action erotica' directive",
    ),
    (
        "fanart",
        "safe",
        "safe",
        "seductive female demon WITH Batman — IP precedence over gothic",
    ),
    (
        "scifi",
        "safe",
        "safe",
        "feline companion in metallic city, warp/distortion techniques",
    ),
    (
        "portrait",
        "safe",
        "safe",
        "young poet's face, tears of creative agony, eyes rolled back",
    ),
    ("pinup", "mature", "safe", "Helmut Newton style, provocative silhouette study"),
    ("furry", "safe", "safe", "baroque anthro fox girl in golden wheat field"),
    (
        "scifi",
        "safe",
        "safe",
        "female android repaired in futuristic workshop, sketch style",
    ),
    ("fetish", "mature", "safe", "bdsm, consensual spanking session, vintage decor"),
    ("pinup", "mature", "safe", "elegant sensual woman, Milo Manara style reference"),
    (
        "fetish",
        "mature",
        "safe",
        "demon girl bound by organic vines — fetish precedence over gothic/scifi",
    ),
    ("fanart", "safe", "mature", "DC_Comics gritty style, cradling dying soldier"),
    (
        "furry",
        "mature",
        "safe",
        "bunny_girl stocking_tug garter_snap, flirtatious dialogue",
    ),
    (
        "fetish",
        "mature",
        "safe",
        "satyr woman bound with silk ropes — fetish precedence over furry",
    ),
    (
        "fantasy",
        "safe",
        "safe",
        "enchanting sorceress atop cliff, Renaissance-inspired",
    ),
    (
        "pinup",
        "mature",
        "safe",
        "1920s pin-up, silk sheets, Art Deco boudoir, 'wearing only'",
    ),
    (
        "fantasy",
        "safe",
        "mature",
        "female knight in blood-soaked battlefield, crimson-stained armor",
    ),
    (
        "portrait",
        "safe",
        "safe",
        "Finnish woman removing jewelry by twilight lake, melancholic",
    ),
    (
        "fanart",
        "safe",
        "safe",
        "Charisma Carpenter likeness, cleaning of assault rifle",
    ),
    ("fetish", "mature", "safe", "bdsm sign streetlamp, submissive pose, choker"),
    (
        "furry",
        "safe",
        "safe",
        "fiery-furred anthro fox girl, bare shoulders, morning light",
    ),
    (
        "gothic",
        "mature",
        "safe",
        "kneeling female vampire, 'erotica' directive, Manara/Toriyama",
    ),
]


def main() -> None:
    rows = [json.loads(line) for line in open(CORPUS)]
    n = len(rows)
    print("# FR-890 Taxonomy Evidence — corpus scan + raw sample (2026-08-25)\n")
    print(
        f"Corpus: `{CORPUS}`, {n} rows. Generated by "
        f"`python scripts/fr890_evidence.py > feature-requests/FR-890-evidence.md`.\n"
    )

    print("## Keyword scan (case-insensitive regex, share of rows)\n")
    print("| Signal | Pattern | Rows | Share |")
    print("|---|---|---|---|")
    lowered = [r["prompt"].lower() for r in rows]
    for name, pattern in KEYWORDS.items():
        c = sum(1 for p in lowered if re.search(pattern, p))
        print(f"| {name} | `{pattern}` | {c} | {100 * c / n:.0f}% |")

    print("\n## Raw sample read (`read_raw_output_first`), seed=42, k=40\n")
    print("Selection: `random.seed(42); random.sample(rows, 40)`. Labels are")
    print("human annotations from reading each prompt raw; the observed detail")
    print("column quotes the distinguishing signal.\n")
    print(
        "| # | Row | Genre | Sexual | Gore | Observed detail | Prompt (first 120 chars) |"
    )
    print("|---|---|---|---|---|---|---|")
    random.seed(42)
    sample_idx = random.sample(range(n), 40)
    if len(ANNOTATIONS) != 40:
        sys.exit("annotation count mismatch")
    for i, (idx, (genre, sexual, gore, detail)) in enumerate(
        zip(sample_idx, ANNOTATIONS), 1
    ):
        snippet = rows[idx]["prompt"][:120].replace("\n", " ").replace("|", "\\|")
        print(f"| {i} | {idx} | {genre} | {sexual} | {gore} | {detail} | {snippet} |")

    print("\n## Label distribution in the sample\n")
    from collections import Counter

    genres = Counter(a[0] for a in ANNOTATIONS)
    print("| Genre | Count |")
    print("|---|---|")
    for g, c in genres.most_common():
        print(f"| {g} | {c} |")
    sexual_mature = sum(1 for a in ANNOTATIONS if a[1] == "mature")
    gore_mature = sum(1 for a in ANNOTATIONS if a[2] == "mature")
    print(
        f"\nsexual=mature: {sexual_mature}/40; gore=mature: {gore_mature}/40; "
        f"`other` needed: 0/40 — every sampled prompt fit a concrete class."
    )


if __name__ == "__main__":
    main()
