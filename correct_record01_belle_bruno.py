#!/usr/bin/env python3
"""
Correct part10_affidavit_003 — Belle Binia Bruno (verified).

User verification (2026-05-04) corrects three fields from the prior patch:
  - Name: Belle Binia Bruno (middle name confirmed as 'Binia')
  - Allotment number: 110 (verified by user, was 'not stated')
  - Tribe/Reservation: Citizen Potawatomie (NOT Shawnee — corrects prior
    patch's incorrect tribe assignment)

The prior patch (patch_record01_belle_bruno.py) made incorrect inferences:
  - Marked tribe as 'Shawnee' from Shawnee master list cross-reference
  - Left middle name as illegible
  - Left allotment as 'not stated'
User has verified these are wrong via independent research.
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

    e["Name"] = "Belle Binia Bruno"
    e["Allotment number"] = "110"
    e["Tribe/Reservation"] = "Citizen Potawatomie"
    e["NOTES"] = (e.get("NOTES") or "") + (
        " | TASK 5 CORRECTION 2026-05-04: Prior patch had incorrect tribe "
        "(Shawnee) and missing allotment/middle name. User verified the "
        "correct values: Name='Belle Binia Bruno', Allotment=110, "
        "Tribe='Citizen Potawatomie'. The prior cross-reference to "
        "Shawnee master list row 3 (Belle Bino Bruno) was a name-similarity "
        "false positive — Belle Binia Bruno is Citizen Potawatomie, not "
        "Shawnee."
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat1_correction_user_verified",
        "method": "user_independent_verification",
        "fields_corrected": [
            "Name", "Allotment number", "Tribe/Reservation", "NOTES",
        ],
        "previous_values": previous,
        "corrected_values": {
            "Name": "Belle Binia Bruno",
            "Allotment number": "110",
            "Tribe/Reservation": "Citizen Potawatomie",
        },
        "rationale": (
            "Prior patch made incorrect tribe inference based on Shawnee "
            "master list name similarity. User verified the correct tribe "
            "is Citizen Potawatomie, allotment is 110, middle name is Binia."
        ),
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Corrected part10_affidavit_003:")
    print(f"  Name:      {previous['Name']:35s} -> Belle Binia Bruno")
    print(f"  Allotment: {previous['Allotment number']:35s} -> 110")
    print(f"  Tribe:     {previous['Tribe/Reservation']:35s} -> Citizen Potawatomie")


if __name__ == "__main__":
    main()
