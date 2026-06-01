#!/usr/bin/env python3
"""
Triage script for the 36 Shawnee Indian Agency master list records.

Master list records (part10_shawnee_NN.json) currently have:
  - Name (captured)
  - Allotment number = 'not stated' (mostly)
  - Tribe/Reservation = 'Shawnee' (misclassified — Shawnee is the AGENCY,
    not the actual tribe; allottees are Citizen Potawatomie, Iowa,
    Sac & Fox, Eastern Shawnee, etc.)

For each row, this script searches the entire Sonnet corpus for
records whose Name matches the master list row's Name, then reports:
  1. Master list row ID and current values
  2. Matching corpus records (by name match)
  3. Allotment + actual tribe from those matches
  4. A 'verdict' for what to do next

Output is both stdout and a TSV file for easy review.

The matching uses:
  - Exact normalized-name match (lowercase, no spaces, no titles, no
    parens, alphanumeric only) — primary signal
  - Surname match (last word) — secondary signal, flagged for review
"""
import csv
import json
import re
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
OUTPUT_TSV = PROJECT_ROOT / "shawnee_master_list_triage.tsv"


def normalize_name(s):
    """Aggressive normalization for matching."""
    if not s:
        return ""
    s = re.sub(r"\([^)]*\)", "", s).strip()
    s = re.sub(r"^(Mrs?\.|Mr\.|Miss|Rev\.|Dr\.)\s+", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\bfor his deceased.*", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\bfor her deceased.*", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"[^a-zA-Z0-9 ]", "", s)
    return s.lower().replace(" ", "")


def get_surname(s):
    if not s:
        return ""
    s = re.sub(r"\([^)]*\)", "", s).strip()
    s = re.sub(r"^(Mrs?\.|Mr\.|Miss|Rev\.|Dr\.)\s+", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\bfor his deceased.*", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\bfor her deceased.*", "", s, flags=re.IGNORECASE).strip()
    parts = s.split()
    return parts[-1].lower() if parts else ""


def get_record_summary(path):
    """Read a corpus record and return Name/Allotment/Tribe/doc_type."""
    try:
        d = json.load(open(path))
    except (json.JSONDecodeError, FileNotFoundError):
        return None
    e = d.get("extraction", {})
    if isinstance(e, list):
        e = e[0] if e else {}
    return {
        "stem": path.stem,
        "name": e.get("Name", ""),
        "allotment": e.get("Allotment number", ""),
        "tribe": e.get("Tribe/Reservation", ""),
        "doc_type": e.get("Document type", ""),
    }


def main():
    # 1. Load all master list records
    master_records = []
    for path in sorted(EXTRACTIONS.glob("part10_shawnee_*.json")):
        rec = get_record_summary(path)
        if rec:
            rec["normalized"] = normalize_name(rec["name"])
            rec["surname"] = get_surname(rec["name"])
            master_records.append(rec)

    print(f"Loaded {len(master_records)} master list records")

    # 2. Load all non-master corpus records into an index by normalized name
    print("Indexing corpus by normalized name...")
    name_index = {}  # normalized_name -> [record_summaries]
    surname_index = {}  # surname -> [record_summaries]
    n_indexed = 0
    for path in sorted(EXTRACTIONS.glob("*.json")):
        if path.stem.startswith("part10_shawnee_"):
            continue
        rec = get_record_summary(path)
        if not rec or not rec["name"]:
            continue
        norm = normalize_name(rec["name"])
        surname = get_surname(rec["name"])
        if norm:
            name_index.setdefault(norm, []).append(rec)
        if surname:
            surname_index.setdefault(surname, []).append(rec)
        n_indexed += 1
    print(f"Indexed {n_indexed} non-master corpus records")
    print()

    # 3. For each master record, find matches and assess
    print("=" * 80)
    print("SHAWNEE MASTER LIST TRIAGE")
    print("=" * 80)
    print()

    rows = []
    counts = {"resolved_full": 0, "resolved_partial": 0, "unresolved": 0, "name_collision": 0}

    for mr in master_records:
        # Exact match (normalized name)
        exact_matches = [
            r for r in name_index.get(mr["normalized"], [])
            if r["stem"] != mr["stem"]
        ]

        # Surname-only matches (excluding exact matches and the master list itself)
        surname_only_matches = []
        if mr["surname"]:
            for r in surname_index.get(mr["surname"], []):
                if r["stem"] == mr["stem"]:
                    continue
                if normalize_name(r["name"]) == mr["normalized"]:
                    continue  # already counted
                if r["stem"].startswith("part10_shawnee_"):
                    continue
                surname_only_matches.append(r)

        # Decision logic
        if exact_matches:
            # Pick first match that has both allotment and a non-Shawnee-agency tribe captured
            best = None
            for m in exact_matches:
                has_allot = m["allotment"] and m["allotment"] not in ("not stated", "")
                has_tribe = m["tribe"] and m["tribe"] not in ("not stated", "Shawnee", "")
                if has_allot and has_tribe:
                    best = m
                    break
            if best is None:
                # Fall back to first match with allotment, even if tribe is bad
                for m in exact_matches:
                    if m["allotment"] and m["allotment"] not in ("not stated", ""):
                        best = m
                        break
            if best is None:
                best = exact_matches[0]  # any match

            has_allot = best["allotment"] and best["allotment"] not in ("not stated", "")
            has_tribe = best["tribe"] and best["tribe"] not in ("not stated", "Shawnee", "")
            if has_allot and has_tribe:
                verdict = "resolved_full"
            elif has_allot:
                verdict = "resolved_partial"  # has allotment but tribe not normalized
            else:
                verdict = "unresolved"  # match exists but no useful data

            inferred_allot = best["allotment"] if has_allot else ""
            inferred_tribe = best["tribe"] if has_tribe else ""
            match_info = f"{best['stem']} ({best['doc_type']})"
            other_matches = "; ".join(m["stem"] for m in exact_matches if m["stem"] != best["stem"])
        elif surname_only_matches:
            verdict = "name_collision"  # surname matches but not full name
            inferred_allot = ""
            inferred_tribe = ""
            match_info = ""
            other_matches = "; ".join(m["stem"] + ":" + m["name"] for m in surname_only_matches[:3])
        else:
            verdict = "unresolved"
            inferred_allot = ""
            inferred_tribe = ""
            match_info = ""
            other_matches = ""

        counts[verdict] = counts.get(verdict, 0) + 1

        rows.append({
            "master_stem": mr["stem"],
            "master_name": mr["name"],
            "master_allot": mr["allotment"],
            "master_tribe": mr["tribe"],
            "verdict": verdict,
            "matched_record": match_info,
            "inferred_allot": inferred_allot,
            "inferred_tribe": inferred_tribe,
            "other_exact_matches": other_matches if exact_matches else "",
            "surname_collisions": other_matches if surname_only_matches and not exact_matches else "",
        })

        # Print row
        marker = {
            "resolved_full": "  ✓ ",
            "resolved_partial": "  ~ ",
            "unresolved": "  ? ",
            "name_collision": "  ⚠ ",
        }.get(verdict, "    ")
        print(f"{marker}{mr['stem']:24s}  {mr['name'][:32]:32s}  →  {verdict}")
        if match_info:
            print(f"      matched: {match_info}")
            if inferred_allot or inferred_tribe:
                print(f"      backfill candidate: allot={inferred_allot}, tribe={inferred_tribe}")
        if surname_only_matches and not exact_matches:
            print(f"      surname collisions: {other_matches[:120]}")
        if exact_matches and len(exact_matches) > 1:
            print(f"      multiple exact matches: also {other_matches[:120]}")
        print()

    # Write TSV
    with open(OUTPUT_TSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "master_stem", "master_name", "master_allot", "master_tribe",
            "verdict", "matched_record", "inferred_allot", "inferred_tribe",
            "other_exact_matches", "surname_collisions",
        ], delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  ✓ resolved_full     ({counts.get('resolved_full', 0):2d}): exact match in corpus has allotment + non-Shawnee-agency tribe")
    print(f"  ~ resolved_partial  ({counts.get('resolved_partial', 0):2d}): exact match has allotment but tribe not normalized (or = 'Shawnee')")
    print(f"  ? unresolved        ({counts.get('unresolved', 0):2d}): no useful data in any matching record")
    print(f"  ⚠ name_collision    ({counts.get('name_collision', 0):2d}): surname match only, full-name disagreement")
    print()
    print(f"TSV: {OUTPUT_TSV}")
    print()
    print(f"To see only the rows requiring action:")
    print(f"  awk -F'\\t' 'NR==1 || $5!=\"resolved_full\"' shawnee_master_list_triage.tsv | column -t -s $'\\t'")


if __name__ == "__main__":
    main()
