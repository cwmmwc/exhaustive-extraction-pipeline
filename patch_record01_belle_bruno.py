#!/usr/bin/env python3
"""
Patch part10_affidavit_003 — Belle Bruno (middle name unclear).

CAT_1 record. User source-page review (2026-05-04) using Sonnet vision +
direct source review:
  - Name: Belle Bruno (middle name illegible — could be Binia, Bridie,
    Birdie, or other; Sonnet vision read "Birdie", Shawnee master list
    has "Bino")
  - Allotment: not visible on this page; remains "not stated"
  - Tribe: Shawnee (per Shawnee master list row 3 cross-reference)
  - PO: not visible

Cross-reference: this allottee appears as row 3 on the Shawnee Indian
Agency master list (part10_shawnee_03) as "Belle Bino Bruno". Master
list row reads "Belle Bino Bruno — Report in detail attached" — this
affidavit is part of her detail submission.

Sonnet vision verdict: partial — got the first and last name right,
middle name is genuinely illegible on the source. User chose to leave
as "Belle Bruno" rather than commit to a possibly-wrong middle name.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
RECORD_PATH = (
    PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
    / "part10_affidavit_003.json"
)


def main():
    with open(RECORD_PATH) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        print("ERROR: list-shaped extraction")
        return

    previous = {
        "Name": e.get("Name", ""),
        "Allotment number": e.get("Allotment number", ""),
        "Tribe/Reservation": e.get("Tribe/Reservation", ""),
    }

    e["Name"] = "Belle Bruno"
    e["Tribe/Reservation"] = "Shawnee"
    # Allotment stays "not stated" — not visible on source page
    e["NOTES"] = (e.get("NOTES") or "") + (
        " | TASK 5 CAT_1 SONNET-ONLY ARBITRATION 2026-05-04: User source-"
        "page review with Sonnet vision recovery. NAME: Belle Bruno (first "
        "and last names legible; middle name illegible — could be Binia, "
        "Bridie, Birdie, or other. Sonnet vision read 'Birdie'; Shawnee "
        "master list row 3 has 'Bino'). Middle name left out of corpus "
        "Name field rather than commit to an uncertain reading. ALLOTMENT: "
        "not visible on source page; remains 'not stated'. TRIBE: Shawnee "
        "(per Shawnee master list row 3 cross-reference, part10_shawnee_03 "
        "= 'Belle Bino Bruno'). This affidavit is part of her detail "
        "submission for the Shawnee master list entry."
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat1_sonnet_only_arbitration",
        "method": "user_source_page_review_with_sonnet_vision",
        "fields_corrected": ["Name", "Tribe/Reservation", "NOTES"],
        "previous_values": previous,
        "corrected_values": {
            "Name": "Belle Bruno",
            "Allotment number": "not stated (not visible on source)",
            "Tribe/Reservation": "Shawnee",
        },
        "sonnet_vision_guess": {
            "name": "Belle Birdie Bruno",
            "allotment": "unknown",
        },
        "user_arbitration": {
            "name": "Belle Bruno (middle name illegible — could be Binia, Bridie, Birdie)",
            "allotment": "not visible on source",
        },
        "shawnee_master_list_cross_reference": "part10_shawnee_03 (Belle Bino Bruno)",
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Patched part10_affidavit_003:")
    print(f"  Name:      {previous['Name']:30s} -> Belle Bruno")
    print(f"  Allotment: {previous['Allotment number']:30s} -> not stated (not visible)")
    print(f"  Tribe:     {previous['Tribe/Reservation']:30s} -> Shawnee")


if __name__ == "__main__":
    main()
