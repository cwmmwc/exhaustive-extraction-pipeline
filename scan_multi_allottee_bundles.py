#!/usr/bin/env python3
"""
Corpus-wide scan for multi-allottee bundle records.

Two detection methods:

1. PRIMARY — Records where the `extraction` field is a list rather than a
   dict. This is the structural signature of multi-allottee bundles like
   the Sarah Thompson + Hermos Merrivall case.

2. SECONDARY — Records where the `Name` field contains multiple-person
   patterns (semicolons, ' and ', ' & ', 'heirs are', 'children of').
   These are records where Sonnet captured multiple allottees as a
   compound name string rather than as a list.

Reports both kinds with enough detail to triage.

We've found 2 so far:
  - pine_ridge_vol1_affidavit_020 (Sarah Thompson + Hermos Merrivall — fixed)
  - part11_questionnaire_002 (Vanderbloom + Wallace — split into 002a/002b)
"""
import csv
import json
import re
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
OUTPUT_TSV = PROJECT_ROOT / "multi_allottee_bundle_scan.tsv"

# Patterns suggesting multi-person Name field
MULTI_NAME_PATTERNS = [
    (r";", "semicolon_separator"),
    (r"\b(?:and|And) [A-Z]", "conjunction_and"),
    (r" & [A-Z]", "ampersand_separator"),
    (r"heirs are", "heirs_pattern"),
    (r"children of", "children_pattern"),
    (r"\bdeceased\b.*\b(husband|wife|son|daughter|mother|father|brother|sister)\b",
     "deceased_with_relative"),
]


def has_multi_person_indicator(name):
    """Return list of (pattern_name, matched_text) findings."""
    if not name or name == "not stated":
        return []
    findings = []
    for pattern, label in MULTI_NAME_PATTERNS:
        m = re.search(pattern, name, flags=re.IGNORECASE)
        if m:
            findings.append((label, m.group()))
    return findings


def scan():
    list_shaped = []
    multi_name = []
    n_total = 0
    n_dict = 0

    for path in sorted(EXTRACTIONS.glob("*.json")):
        n_total += 1
        try:
            with open(path) as f:
                d = json.load(f)
        except json.JSONDecodeError:
            continue
        e = d.get("extraction")

        if isinstance(e, list):
            # List-shaped: confirmed multi-allottee structure
            n_in_list = len(e)
            names = []
            allots = []
            for item in e:
                if isinstance(item, dict):
                    names.append(item.get("Name", "?"))
                    allots.append(item.get("Allotment number", "?"))
            list_shaped.append({
                "filename": path.name,
                "n_items": n_in_list,
                "names": " | ".join(names),
                "allotments": " | ".join(allots),
            })
            continue

        if not isinstance(e, dict):
            continue
        n_dict += 1

        # Look for multi-person indicators in Name
        name = e.get("Name", "")
        findings = has_multi_person_indicator(name)
        if findings:
            multi_name.append({
                "filename": path.name,
                "name": name,
                "allotment": e.get("Allotment number", ""),
                "tribe": e.get("Tribe/Reservation", ""),
                "indicator_types": ", ".join(f[0] for f in findings),
                "matched_text": ", ".join(repr(f[1]) for f in findings),
            })

    # Write results
    with open(OUTPUT_TSV, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["category", "filename", "detail_1", "detail_2", "detail_3", "detail_4"])
        for r in list_shaped:
            w.writerow([
                "list_shaped_extraction",
                r["filename"],
                f"items={r['n_items']}",
                f"names={r['names']}",
                f"allotments={r['allotments']}",
                "",
            ])
        for r in multi_name:
            w.writerow([
                "multi_person_in_name",
                r["filename"],
                f"name={r['name']}",
                f"allot={r['allotment']}",
                f"tribe={r['tribe']}",
                f"indicators={r['indicator_types']}; matched={r['matched_text']}",
            ])

    print("=" * 70)
    print("Multi-allottee bundle scan results")
    print("=" * 70)
    print(f"Total records scanned:                  {n_total}")
    print(f"Dict-shaped (single-allottee form):     {n_dict}")
    print(f"LIST-SHAPED (multi-allottee bundles):   {len(list_shaped)}")
    print(f"Multi-person indicators in Name field:  {len(multi_name)}")
    print()
    print(f"Output TSV: {OUTPUT_TSV}")
    print()

    if list_shaped:
        print("=== LIST-SHAPED RECORDS (definite multi-allottee bundles) ===")
        for r in list_shaped[:20]:
            print(f"  {r['filename']:50s}  {r['n_items']} items")
            print(f"    names: {r['names']}")
            print(f"    allots: {r['allotments']}")
            print()

    if multi_name:
        print("=== MULTI-PERSON INDICATORS IN NAME FIELD (top 20) ===")
        for r in multi_name[:20]:
            print(f"  {r['filename']:50s}  ind={r['indicator_types']}")
            print(f"    name: {r['name']}")
            print()


if __name__ == "__main__":
    scan()
