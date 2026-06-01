#!/usr/bin/env python3
"""
Patch 6 Pine Ridge CAT_3 records.

Allotments from Christian's research (2026-05-04). Tribe label set to
'Oglala Lakota' per his stated preference for Pine Ridge records.

CAT_3 = Sonnet captured the Name but not the Allotment. This batch
backfills the allotment.

  part3_affidavit_011          Nora Tway Sandery -> 4839
    Database name variants: 'Nora Tway' and 'Nora Sanders'. The corpus
    extraction's 'Nora Tway Sandery' appears to conflate her two
    recorded surnames. Name field left as extracted; variants noted.
  pine_ridge_vol1_affidavit_006  Charles Janis -> 70
  pine_ridge_vol1_affidavit_114  Mollie Janis -> 1783
  pine_ridge_vol1_affidavit_121  Margaret White Deer -> 1868
  pine_ridge_vol3_affidavit_062  Susie Green -> 5453
  pine_ridge_vol3_affidavit_068  George Bartlett -> 5563

NOT in this batch:
  part3_affidavit_010 (Tay Sander) — Christian is 99% certain this is
  the same person as Nora (part3_affidavit_011). Pending source-page
  review to confirm before patching.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

TRIBE = "Oglala Lakota"

PATCHES = [
    {
        "stem": "part3_affidavit_011",
        "name": "Nora Tway Sandery",
        "allotment": "4839",
        "name_variant_note": (
            "Federal-register-app patents database records her under two "
            "names: 'Nora Tway' and 'Nora Sanders'. The corpus extraction "
            "'Nora Tway Sandery' appears to conflate the two surnames "
            "(Tway and Sanders/Sandery). Name field left as extracted; "
            "variants documented here for cross-reference."
        ),
    },
    {
        "stem": "pine_ridge_vol1_affidavit_006",
        "name": "Charles Janis",
        "allotment": "70",
        "name_variant_note": "",
    },
    {
        "stem": "pine_ridge_vol1_affidavit_114",
        "name": "Mollie Janis",
        "allotment": "1783",
        "name_variant_note": "",
    },
    {
        "stem": "pine_ridge_vol1_affidavit_121",
        "name": "Margaret White Deer",
        "allotment": "1868",
        "name_variant_note": "",
    },
    {
        "stem": "pine_ridge_vol3_affidavit_062",
        "name": "Susie Green",
        "allotment": "5453",
        "name_variant_note": "",
    },
    {
        "stem": "pine_ridge_vol3_affidavit_068",
        "name": "George Bartlett",
        "allotment": "5563",
        "name_variant_note": "",
    },
]


def patch_one(spec):
    path = EXTRACTIONS / f"{spec['stem']}.json"
    if not path.exists():
        return False, "NOT FOUND"

    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        return False, "list-shaped extraction"

    previous = {
        "Name": e.get("Name", ""),
        "Allotment number": e.get("Allotment number", ""),
        "Tribe/Reservation": e.get("Tribe/Reservation", ""),
    }

    e["Allotment number"] = spec["allotment"]
    e["Tribe/Reservation"] = TRIBE

    tribe_norm_note = ""
    if previous["Tribe/Reservation"] not in (TRIBE, ""):
        tribe_norm_note = (
            f" TRIBE NORMALIZATION: previous label "
            f"'{previous['Tribe/Reservation']}' normalized to '{TRIBE}'."
        )

    variant_note = ""
    if spec["name_variant_note"]:
        variant_note = f" NAME VARIANT: {spec['name_variant_note']}"

    note_addition = (
        f" | TASK 5 CAT_3 BACKFILL 2026-05-04 (patents database): "
        f"Allotment {spec['allotment']} sourced from federal-register-app "
        f"patents database (Christian's research, 2026-05-04). CAT_3 "
        f"record — Sonnet text extraction captured the allottee Name but "
        f"not the Allotment number; this patch backfills the allotment. "
        f"Tribe set to {TRIBE} (Pine Ridge / Oglala).{tribe_norm_note}"
        f"{variant_note}"
    )
    e["NOTES"] = (e.get("NOTES") or "") + note_addition

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat3_backfill_patents_database",
        "method": "user_research_federal_register_app_patents_database",
        "source_url": "https://federal-register-app-996830241007.us-east1.run.app/patents",
        "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
        "previous_values": previous,
        "corrected_values": {
            "Allotment number": spec["allotment"],
            "Tribe/Reservation": TRIBE,
        },
        "name_variant_note": spec["name_variant_note"],
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"{spec['name']}, allot={spec['allotment']}, {TRIBE}"


def main():
    print("=" * 70)
    print(f"Pine Ridge CAT_3 backfill: {len(PATCHES)} records")
    print("=" * 70)

    ok = 0
    for spec in PATCHES:
        success, msg = patch_one(spec)
        marker = "  " if success else "  ! "
        print(f"{marker}{spec['stem']:38s} {msg}")
        if success:
            ok += 1

    print()
    print(f"Patched: {ok}/{len(PATCHES)}")
    print()
    print("Pending:")
    print("  part3_affidavit_010  Tay Sander — source review to confirm")
    print("    whether same person as Nora (part3_affidavit_011)")


if __name__ == "__main__":
    main()
