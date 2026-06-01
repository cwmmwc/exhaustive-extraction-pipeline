#!/usr/bin/env python3
"""
Systematic Sonnet vs. Kimi v5 cross-extraction disagreement scan.

For every Sonnet record in extractions/sonnet/part*.json (and pine_ridge_*),
look up the corresponding allottee in the matching Kimi v5 extraction
(v5/RG 75 1929 circular 2464 part N/Kimi K2.5.json) and compare:
  - Name
  - Allotment number
  - Tribe/Reservation

Produces a TSV report of disagreements for triage and source-page review.

Matching heuristic: extract the surname from the Sonnet record's Name
field, then search Kimi v5 entities for any 'person' with that surname
in their 'name' or 'context'. If multiple matches, prefer the one whose
context references an allotment number close to Sonnet's. If no match,
record as 'no kimi match'.

Limitations:
  - Surname matching is fuzzy and can produce false matches when surnames
    are common (Wallace, Henry, Johnson). Triage carefully.
  - Sonnet records that come from documents Kimi didn't fully process
    will appear as 'no kimi match' even when the data is fine.
  - Pine Ridge Volume 1/2/3 records won't have direct Kimi v5 cross-
    references because Kimi processed them as separate Pine Ridge
    extractions, not as parts in the v5/ directory tree.
"""
import csv
import json
import re
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
KIMI_V5_BASE = PROJECT_ROOT / "circular_2464_extractions" / "v5"
OUTPUT_TSV = PROJECT_ROOT / "sonnet_vs_kimi_v5_disagreements.tsv"

# Map part-N suffix to Kimi v5 directory (note part 11's "2564" typo)
PART_TO_KIMI_DIR = {
    "part1": "RG 75 1929 circular 2464 part 1",
    "part2": "RG 75 1929 circular 2464 part 2",
    "part3": "RG 75 1929 circular 2464 part 3",
    "part4": "RG 75 1929 circular 2464 part 4",
    "part6": "RG 75 1929 circular 2464 part 6",
    "part7": "RG 75 1929 circular 2464 part 7",
    "part8": "RG 75 1929 circular 2464 part 8",
    "part9": "RG 75 1929 circular 2464 part 9",
    "part10": "RG 75 1929 circular 2464 part 10",
    "part11": "RG 75 1929 circular 2564 part 11",
    "part12": "RG 75 1929 circular 2464 part 12",
    "part13": "RG 75 1929 circular 2464 part 13",
}


def load_kimi_v5(part_key):
    kimi_dir_name = PART_TO_KIMI_DIR.get(part_key)
    if not kimi_dir_name:
        return None
    path = KIMI_V5_BASE / kimi_dir_name / "Kimi K2.5.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def extract_surname(name):
    """Extract surname from a Name field. Handles 'Lastname (alt)', 'First M. Last',
    parenthetical aliases, deceased/heir notations."""
    if not name or name == "not stated":
        return ""
    # Strip parenthetical content
    cleaned = re.sub(r"\([^)]*\)", "", name)
    # Strip 'deceased', 'heirs', etc.
    cleaned = re.sub(
        r"\b(deceased|allottee|heirs?|husband|wife|son|daughter|filed by|for his|for her)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[;,].*$", "", cleaned).strip()
    parts = [p for p in cleaned.split() if len(p) > 2 and not p.endswith(".")]
    return parts[-1] if parts else ""


def extract_allotment_from_context(context):
    """Pull the allotment number from a Kimi context string like 'Allottee No. 1466'."""
    if not context:
        return ""
    m = re.search(r"[Aa]llott?ee\s*(?:No\.?)?\s*(\d{1,6})", context)
    if m:
        return m.group(1)
    m = re.search(r"[Aa]llotment\s*(?:No\.?)?\s*(\d{1,6})", context)
    return m.group(1) if m else ""


def find_kimi_match(sonnet_name, sonnet_allot, kimi_data):
    """Find the best Kimi entity match for a Sonnet record."""
    if not kimi_data:
        return None
    surname = extract_surname(sonnet_name)
    if not surname:
        return None

    candidates = []
    for ent in kimi_data.get("entities", []):
        if ent.get("type") != "person":
            continue
        ent_name = ent.get("name", "")
        ent_context = ent.get("context", "")
        if surname.lower() in ent_name.lower() or surname.lower() in ent_context.lower():
            ent_allot = extract_allotment_from_context(ent_context)
            candidates.append({
                "name": ent_name,
                "context": ent_context,
                "allotment": ent_allot,
            })

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    # Multiple candidates — prefer one whose allotment matches Sonnet's
    if sonnet_allot and sonnet_allot != "not stated":
        sonnet_allot_clean = re.sub(r"[^0-9]", "", str(sonnet_allot))
        for c in candidates:
            if c["allotment"] and c["allotment"] == sonnet_allot_clean:
                return c
    # Otherwise prefer the candidate whose name field (not just context) contains the surname
    for c in candidates:
        if surname.lower() in c["name"].lower():
            return c
    return candidates[0]


def normalize_for_compare(value):
    if not value:
        return ""
    return str(value).strip().lower().replace("not stated", "")


def normalize_allot(value):
    if not value or value == "not stated":
        return ""
    return re.sub(r"[^0-9]", "", str(value))


def normalize_tribe(value):
    """Tribe normalization for comparison: 'Rosebud' and 'Rosebud Sioux' both
    map to 'rosebud'."""
    if not value:
        return ""
    v = value.strip().lower()
    if v in ("not stated", ""):
        return ""
    # Strip 'sioux' suffix
    v = re.sub(r"\s+sioux\s*$", "", v)
    return v


def scan():
    # Load all Kimi v5 extractions once
    kimi_by_part = {}
    for part_key in PART_TO_KIMI_DIR:
        data = load_kimi_v5(part_key)
        if data:
            kimi_by_part[part_key] = data

    print(f"Loaded Kimi v5 extractions for {len(kimi_by_part)} parts:")
    for k in sorted(kimi_by_part):
        n_ents = len(kimi_by_part[k].get("entities", []))
        print(f"  {k}: {n_ents} entities")
    print()

    rows = []
    n_total = 0
    n_pine_ridge = 0
    n_no_kimi_match = 0
    n_disagree = 0
    n_agree = 0

    for path in sorted(EXTRACTIONS.glob("part*.json")):
        n_total += 1
        # Determine part key
        m = re.match(r"^(part\d+)_", path.name)
        if not m:
            continue
        part_key = m.group(1)
        kimi_data = kimi_by_part.get(part_key)

        with open(path) as f:
            try:
                d = json.load(f)
            except json.JSONDecodeError:
                continue
        e = d.get("extraction", {})
        if isinstance(e, list):
            e = e[0] if e else {}
        if not isinstance(e, dict):
            continue

        sonnet_name = e.get("Name", "")
        sonnet_allot = e.get("Allotment number", "")
        sonnet_tribe = e.get("Tribe/Reservation", "")

        kimi_match = find_kimi_match(sonnet_name, sonnet_allot, kimi_data)
        if not kimi_match:
            n_no_kimi_match += 1
            rows.append({
                "filename": path.name,
                "sonnet_name": sonnet_name,
                "sonnet_allot": sonnet_allot,
                "sonnet_tribe": sonnet_tribe,
                "kimi_name": "",
                "kimi_allot": "",
                "kimi_tribe_context": "",
                "verdict": "no_kimi_match",
                "fields_disagree": "",
            })
            continue

        kimi_name = kimi_match["name"]
        kimi_allot = kimi_match["allotment"]
        kimi_context = kimi_match["context"]

        # Compare each field
        disagrees = []

        # Name comparison: surname must match (we already use surname for matching,
        # but full name might still differ — note as "name_variant" not disagreement)
        sonnet_surname = extract_surname(sonnet_name).lower()
        kimi_surname = extract_surname(kimi_name).lower()
        # Names differ but share surname -> not necessarily a disagreement
        # (e.g., 'Mary Julia Neiss' vs 'Mary Julia Neiss', or with maiden names)
        # We only flag a name disagreement if surnames don't match, which would be rare given the matching logic
        if sonnet_surname and kimi_surname and sonnet_surname != kimi_surname:
            disagrees.append("name")

        sonnet_allot_n = normalize_allot(sonnet_allot)
        kimi_allot_n = normalize_allot(kimi_allot)
        if sonnet_allot_n and kimi_allot_n and sonnet_allot_n != kimi_allot_n:
            disagrees.append("allotment")
        elif not sonnet_allot_n and kimi_allot_n:
            disagrees.append("allotment_sonnet_missing")

        # Tribe: Kimi may not have it as a structured field; check context for 'Rosebud', 'Sioux', 'Pine Ridge', etc.
        sonnet_tribe_n = normalize_tribe(sonnet_tribe)
        kimi_tribe_clue = ""
        for tribe_word in ["rosebud", "pine ridge", "sioux", "potawatomie", "potawatomi",
                           "kiowa", "comanche", "ute", "blackfeet", "fort berthold",
                           "shawnee", "pawnee", "ponca", "otoe", "wichita", "crow"]:
            if tribe_word in kimi_context.lower():
                kimi_tribe_clue = tribe_word
                break
        if sonnet_tribe_n and kimi_tribe_clue and kimi_tribe_clue not in sonnet_tribe_n:
            disagrees.append("tribe")
        elif not sonnet_tribe_n and kimi_tribe_clue:
            disagrees.append("tribe_sonnet_missing")

        if disagrees:
            n_disagree += 1
            verdict = "disagree"
        else:
            n_agree += 1
            verdict = "agree"

        rows.append({
            "filename": path.name,
            "sonnet_name": sonnet_name,
            "sonnet_allot": sonnet_allot,
            "sonnet_tribe": sonnet_tribe,
            "kimi_name": kimi_name,
            "kimi_allot": kimi_allot,
            "kimi_tribe_context": kimi_tribe_clue or "(none)",
            "verdict": verdict,
            "fields_disagree": ";".join(disagrees),
        })

    # Pine Ridge skipped from Kimi v5 cross-reference
    for path in sorted(EXTRACTIONS.glob("pine_ridge_*.json")):
        n_pine_ridge += 1
        rows.append({
            "filename": path.name,
            "sonnet_name": "(pine ridge - skipped)",
            "sonnet_allot": "",
            "sonnet_tribe": "",
            "kimi_name": "",
            "kimi_allot": "",
            "kimi_tribe_context": "",
            "verdict": "skipped_pine_ridge",
            "fields_disagree": "",
        })

    # Write TSV
    with open(OUTPUT_TSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "filename", "verdict", "fields_disagree",
            "sonnet_name", "kimi_name",
            "sonnet_allot", "kimi_allot",
            "sonnet_tribe", "kimi_tribe_context",
        ], delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print("=" * 70)
    print("Sonnet vs Kimi v5 disagreement scan: results")
    print("=" * 70)
    print(f"Total Sonnet records scanned (part*):         {n_total}")
    print(f"Pine Ridge records (skipped):                 {n_pine_ridge}")
    print(f"Records with no Kimi v5 match:                {n_no_kimi_match}")
    print(f"Records where Sonnet and Kimi v5 agree:       {n_agree}")
    print(f"Records where Sonnet and Kimi v5 DISAGREE:    {n_disagree}")
    print()
    print(f"Output TSV: {OUTPUT_TSV}")
    print()
    print("To see disagreements only:")
    print(f"  awk -F'\\t' 'NR==1 || $2==\"disagree\"' {OUTPUT_TSV.name} | head -50")


if __name__ == "__main__":
    scan()
