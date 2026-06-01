#!/usr/bin/env python3
"""
Final backfill for the Shawnee Indian Agency master list — RECREATED 2026-06-01.

Background: the original backfill_shawnee_final.py from 2026-05-04 was lost
when this morning's git filter-repo discarded uncommitted working-tree
patches. The script existed, was the record of the patents-database
lookup work, and got erased before being committed. The historian
re-supplied the 18 patents-database lookups on 2026-06-01; this script
applies them plus the 6 known-unresolved markings, matching what the
original script did per OPERATIONS lines 740-787.

Covers:
  * 18 patents-database confirmations (rows where the historian found
    the allottee in https://federal-register-app-996830241007.us-east1.run.app/patents).
    All confirmed allottees are Citizen Potawatomie. Documented database
    variants: Bourbonais→Bourbonnais (double-n), Joseph C.→Joseph H.
    Cummings (middle initial), Sophie→Sophia Johnson, Benis A.→Dennis A.
    Mars (B/D misread).
  * 6 known-unresolved rows (not in patents database, tribe undetermined).
    Convention: allotment="(not in patents database)",
    tribe="Shawnee Indian Agency (actual tribe unknown)".

Guards: the script refuses to overwrite a row whose Allotment number is
already populated with a real value (handles the case where shawnee_01
was patched earlier today as a one-off; that row will be skipped here).

FLAG: rows 8 (Raymond Haskell) and 13 (John T. Haskell) both have
allotment 1168 per the 2026-06-01 lookups. Could be same person under
two names (common 1928 pattern) or a typo. Captured as flagged in
recovery_notes for later historian review.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
PATENTS_URL = "https://federal-register-app-996830241007.us-east1.run.app/patents"

# 18 patents-database confirmations (Citizen Potawatomie tribe)
PATCHES = [
    {"row": "01", "name": "Lizzie Anderson",         "allot": "22",   "variant": None},
    {"row": "02", "name": "Mary C. Corder Barnett",  "allot": "1206", "variant": None},
    {"row": "05", "name": "Mary Bertrand",           "allot": "194",  "variant": None},
    {"row": "06", "name": "Ozetta Bourbonais",       "allot": "36",
     "variant": "Database spelling 'Bourbonnais' (double-n) vs master list 'Bourbonais'."},
    {"row": "08", "name": "Joseph C. Cummings",      "allot": "812",
     "variant": "Database middle initial 'Joseph H. Cummings' vs master list 'Joseph C. Cummings'."},
    {"row": "09", "name": "Andrew J. Cummings",      "allot": "811", "variant": None},
    {"row": "13", "name": "Nettie Hartman",          "allot": "768", "variant": None},
    {"row": "15", "name": "Raymond Haskell",         "allot": "1169", "variant": None},  # 1169 (corrected from initial 1168)
    {"row": "16", "name": "Charles Henry",           "allot": "33",  "variant": None},
    {"row": "17", "name": "Clarence Henry",          "allot": "32",  "variant": None},
    {"row": "20", "name": "Sophie Johnson",          "allot": "54",
     "variant": "Database spelling 'Sophia Johnson' vs master list 'Sophie Johnson'."},
    {"row": "21", "name": "Jacob Haskell",           "allot": "1170", "variant": None},
    {"row": "22", "name": "John T. Haskell",         "allot": "1168", "variant": None},
    {"row": "23", "name": "Allen Kennedy",           "allot": "1352", "variant": None},
    {"row": "24", "name": "James LeClair",           "allot": "1145", "variant": None},
    {"row": "25", "name": "Benis A. Mars",           "allot": "453",
     "variant": "Database spelling 'Dennis A. Mars' vs master list 'Benis A. Mars' (B/D OCR misread)."},
    {"row": "28", "name": "Theo. Abraham Pearce",    "allot": "265", "variant": None},
    {"row": "36", "name": "Mary A. Wallace",         "allot": "1158", "variant": None},
]

# 6 known-unresolved rows (per OPERATIONS lines 753-759)
NOT_IN_DB = [
    {"row": "04", "name": "Julia Bourasa Riley"},
    {"row": "07", "name": "Nellie Bourasa"},
    {"row": "10", "name": "R. DeGraff"},
    {"row": "11", "name": "Josephine DeGraff"},
    {"row": "26", "name": "Mrs. Jos. Nedeau"},
    {"row": "29", "name": "Julia C. Pierson"},
]

NOTE_TEMPLATE_CONFIRMED = (
    " | TASK 5 SHAWNEE FINAL BACKFILL 2026-06-01 (recreated after filter-repo loss): "
    "Allotment {allot}, tribe Citizen Potawatomie, sourced from "
    "federal-register-app patents database (Christian's research). "
    "Master list source page (part10 page 35) had only response-status "
    "annotations, no allotment numbers; allotments supplied from the "
    "patents database lookup. {variant_text}"
)

NOTE_TEMPLATE_NOT_IN_DB = (
    " | TASK 5 SHAWNEE FINAL BACKFILL 2026-06-01 (recreated after filter-repo loss): "
    "Not found in federal-register-app patents database. May indicate Circular "
    "2464 investigation began but no forced fee patent was consummated, or "
    "patent record exists under a different name not currently indexed. "
    "Marked as explicitly unresolved per OPERATIONS convention so it is "
    "distinguishable from unprocessed rows. Tribe also unknown — every "
    "resolvable row on the Shawnee Indian Agency master list turned out to "
    "be Citizen Potawatomie, but absent a confirmed database record this row "
    "cannot be assigned a definite tribe."
)


def patch_confirmed(spec):
    path = EXTRACTIONS / f"part10_shawnee_{spec['row']}.json"
    if not path.exists():
        return False, "FILE NOT FOUND"
    with open(path) as f:
        rec = json.load(f)
    e = rec["extraction"]
    if isinstance(e, list):
        return False, "List-shaped extraction (unexpected for master list row)"
    cur_allot = (e.get("Allotment number") or "").strip().lower()
    if cur_allot not in ("", "not stated", "not specified", "unknown"):
        return False, f"Allotment already set ('{e.get('Allotment number')}'); refusing to overwrite"

    prev = {"Allotment number": e.get("Allotment number"), "Tribe/Reservation": e.get("Tribe/Reservation")}
    e["Allotment number"] = spec["allot"]
    e["Tribe/Reservation"] = "Citizen Potawatomie"
    variant_text = spec["variant"] or ""
    e["NOTES"] = (e.get("NOTES") or "") + NOTE_TEMPLATE_CONFIRMED.format(
        allot=spec["allot"], variant_text=variant_text
    )

    rec.setdefault("recovery_notes", []).append({
        "date": "2026-06-01",
        "type": "task5_shawnee_final_backfill_recreated",
        "method": "user_research_federal_register_app_patents_database",
        "source_url": PATENTS_URL,
        "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
        "previous_values": prev,
        "corrected_values": {"Allotment number": spec["allot"], "Tribe/Reservation": "Citizen Potawatomie"},
        "database_name_variant": spec["variant"],
        "user_confirmed": True,
        "context": (
            "Recreation of lost 2026-05-04 backfill_shawnee_final.py work. "
            "Original script was wiped by this morning's git filter-repo. "
            "Historian re-supplied the 18 lookups on 2026-06-01; this script "
            "is the durable record so the work cannot be lost again."
        ),
    })

    with open(path, "w") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    return True, f"Allot 'not stated' → {spec['allot']}; tribe 'Shawnee' → Citizen Potawatomie"


def patch_not_in_db(spec):
    path = EXTRACTIONS / f"part10_shawnee_{spec['row']}.json"
    if not path.exists():
        return False, "FILE NOT FOUND"
    with open(path) as f:
        rec = json.load(f)
    e = rec["extraction"]
    if isinstance(e, list):
        return False, "List-shaped extraction (unexpected for master list row)"
    cur_allot = (e.get("Allotment number") or "").strip().lower()
    if cur_allot not in ("", "not stated", "not specified", "unknown"):
        return False, f"Allotment already set ('{e.get('Allotment number')}'); refusing to overwrite"

    prev = {"Allotment number": e.get("Allotment number"), "Tribe/Reservation": e.get("Tribe/Reservation")}
    e["Allotment number"] = "(not in patents database)"
    e["Tribe/Reservation"] = "Shawnee Indian Agency (actual tribe unknown)"
    e["NOTES"] = (e.get("NOTES") or "") + NOTE_TEMPLATE_NOT_IN_DB

    rec.setdefault("recovery_notes", []).append({
        "date": "2026-06-01",
        "type": "task5_shawnee_not_in_database_marker_recreated",
        "method": "user_research_federal_register_app_patents_database_no_match",
        "source_url": PATENTS_URL,
        "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
        "previous_values": prev,
        "corrected_values": {
            "Allotment number": "(not in patents database)",
            "Tribe/Reservation": "Shawnee Indian Agency (actual tribe unknown)",
        },
        "user_confirmed": True,
        "context": "Recreation of lost 2026-05-04 backfill_shawnee_final.py work.",
    })

    with open(path, "w") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    return True, "Marked as '(not in patents database)' / 'Shawnee Indian Agency (actual tribe unknown)'"


def main():
    print("=" * 70)
    print(f"Shawnee final backfill (recreated): {len(PATCHES)} confirmed + {len(NOT_IN_DB)} not-in-db")
    print("=" * 70)
    print()
    print("--- 18 patents-database confirmations ---")
    ok = skipped = 0
    for spec in PATCHES:
        success, msg = patch_confirmed(spec)
        marker = "  " if success else "  - "
        print(f"{marker}shawnee_{spec['row']}  {spec['name']:<30} {msg}")
        if success: ok += 1
        else: skipped += 1
    print()
    print("--- 6 known-unresolved (not in patents database) ---")
    nok = nskip = 0
    for spec in NOT_IN_DB:
        success, msg = patch_not_in_db(spec)
        marker = "  " if success else "  - "
        print(f"{marker}shawnee_{spec['row']}  {spec['name']:<30} {msg}")
        if success: nok += 1
        else: nskip += 1
    print()
    print(f"Confirmed:  {ok} applied, {skipped} skipped")
    print(f"Not-in-db:  {nok} applied, {nskip} skipped")


if __name__ == "__main__":
    main()
