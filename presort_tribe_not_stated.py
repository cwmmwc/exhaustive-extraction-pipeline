#!/usr/bin/env python3
"""
Pre-sort the 36 "tribe not stated" CAT_3 records by likely tribe.

For each of the 36 records, this script:
  1. Reads the surname and PO address
  2. Searches the rest of the corpus for OTHER records sharing that
     surname that DO have a tribe assigned
  3. Reports the likely tribe based on surname-match evidence + PO

This lets the patents-database lookup proceed grouped by tribe,
and flags records where corpus-internal evidence already strongly
suggests the tribe.

Output: a grouped worksheet at shawnee... no — at
validation_samples/task5_campaign/tribe_not_stated_presort.txt
"""
import json
import re
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
MANIFEST = (
    PROJECT_ROOT / "validation_samples" / "task5_campaign"
    / "candidates_post_20260504_v4.tsv"
)
OUTPUT = (
    PROJECT_ROOT / "validation_samples" / "task5_campaign"
    / "tribe_not_stated_presort.txt"
)


def get_surname(name):
    if not name:
        return ""
    name = re.sub(r"\([^)]*\)", "", name).strip()
    name = re.sub(r"^(Mrs?\.|Mr\.|Miss|Rev\.|Dr\.)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(deceased|Dec'd|widow of|formerly).*", "", name, flags=re.IGNORECASE).strip()
    # Drop trailing Jr./Sr.
    name = re.sub(r",?\s+(Jr\.?|Sr\.?)\s*$", "", name).strip()
    parts = name.split()
    return parts[-1].lower() if parts else ""


def get_record(path):
    try:
        d = json.load(open(path))
    except (json.JSONDecodeError, OSError):
        return None
    e = d.get("extraction", {})
    if isinstance(e, list):
        e = e[0] if e else {}
    return {
        "stem": path.stem,
        "name": (e.get("Name") or "").strip(),
        "tribe": (e.get("Tribe/Reservation") or "").strip(),
        "po": (e.get("Post Office Address") or "").strip(),
    }


def main():
    # 1. Read the 36 tribe-not-stated records from the v4 manifest
    target_stems = []
    if MANIFEST.exists():
        with open(MANIFEST) as f:
            header = f.readline()
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 5:
                    continue
                category, filename, name, allotment, tribe = parts[:5]
                if category == "CAT_3" and tribe in ("(blank)", "", "not stated"):
                    target_stems.append(filename.replace(".json", ""))
    else:
        print(f"Manifest not found: {MANIFEST}")
        return

    print(f"Tribe-not-stated CAT_3 records to pre-sort: {len(target_stems)}")
    print()

    # 2. Index the whole corpus by surname -> [tribes]
    surname_tribes = {}  # surname -> Counter of tribes
    for path in sorted(EXTRACTIONS.glob("*.json")):
        rec = get_record(path)
        if not rec or not rec["name"]:
            continue
        tribe = rec["tribe"]
        if tribe in ("", "not stated", "(blank)"):
            continue
        # Skip the non-tribe labels we know are bad
        if tribe.lower() in ("sioux",) or "county" in tribe.lower():
            continue
        surname = get_surname(rec["name"])
        if not surname:
            continue
        surname_tribes.setdefault(surname, Counter())[tribe] += 1

    # 3. For each target record, find surname-based tribe evidence
    lines = []
    lines.append("=" * 74)
    lines.append("TRIBE-NOT-STATED CAT_3 PRE-SORT — 36 records")
    lines.append("=" * 74)
    lines.append("")
    lines.append("For each record: likely tribe based on other corpus records")
    lines.append("sharing the same surname. 'STRONG' = surname appears with one")
    lines.append("tribe on 3+ other records. 'WEAK' = 1-2 supporting records.")
    lines.append("'NONE' = surname not found elsewhere with a tribe.")
    lines.append("")
    lines.append("Fill in allotment and confirm tribe for each.")
    lines.append("")

    rows = []
    for stem in sorted(target_stems):
        path = EXTRACTIONS / f"{stem}.json"
        rec = get_record(path)
        if not rec:
            continue
        surname = get_surname(rec["name"])
        tribe_counter = surname_tribes.get(surname, Counter())

        if tribe_counter:
            top_tribe, top_count = tribe_counter.most_common(1)[0]
            total = sum(tribe_counter.values())
            if top_count >= 3:
                strength = "STRONG"
            else:
                strength = "WEAK"
            distinct = len(tribe_counter)
            if distinct > 1:
                breakdown = ", ".join(
                    f"{t}:{c}" for t, c in tribe_counter.most_common()
                )
                evidence = f"{strength} -> {top_tribe} (corpus surname matches: {breakdown})"
            else:
                evidence = f"{strength} -> {top_tribe} ({top_count} corpus surname matches)"
        else:
            top_tribe = ""
            evidence = "NONE (surname not found elsewhere with a tribe)"

        rows.append({
            "stem": stem,
            "name": rec["name"],
            "po": rec["po"],
            "likely_tribe": top_tribe,
            "evidence": evidence,
        })

    # Group output by likely tribe
    by_tribe = {}
    for r in rows:
        key = r["likely_tribe"] or "(no surname evidence)"
        by_tribe.setdefault(key, []).append(r)

    for tribe_key in sorted(by_tribe.keys()):
        group = by_tribe[tribe_key]
        lines.append("-" * 74)
        lines.append(f"LIKELY TRIBE: {tribe_key}  ({len(group)} records)")
        lines.append("-" * 74)
        for r in group:
            lines.append(f"  {r['name']}")
            lines.append(f"    record: {r['stem']}")
            po = r["po"] if r["po"] not in ("not stated", "") else "(PO not stated)"
            lines.append(f"    PO: {po}")
            lines.append(f"    evidence: {r['evidence']}")
            lines.append(f"    -> allotment: __________   tribe: __________")
            lines.append("")
        lines.append("")

    text = "\n".join(lines)
    with open(OUTPUT, "w") as f:
        f.write(text)

    print(text)
    print(f"Worksheet written: {OUTPUT}")


if __name__ == "__main__":
    main()
