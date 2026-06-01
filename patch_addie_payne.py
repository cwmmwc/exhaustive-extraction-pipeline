#!/usr/bin/env python3
"""
Patch part10_questionnaire_015 — Mrs. Addie Easton Payne.

Identified earlier in the session as Shawnee Indian Agency master list
row 30 (part10_page_036). User established her details:
  - Name: Mrs. Addie Easton Payne
  - Allotment: 168
  - Tribe: Citizen Potawatomie

This is a CAT_1 record (Sonnet captured neither name nor allotment), but
unlike most CAT_1 records, the answer is already known from prior cross-
reference work and doesn't need vision recovery.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
RECORD_PATH = (
    PROJECT_ROOT
    / "circular_2464_extractions"
    / "extractions"
    / "sonnet"
    / "part10_questionnaire_015.json"
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

    e["Name"] = "Mrs. Addie Easton Payne"
    e["Allotment number"] = "168"
    e["Tribe/Reservation"] = "Citizen Potawatomie"
    e["NOTES"] = (e.get("NOTES") or "") + (
        " | TASK 5 SHAWNEE CROSS-REFERENCE 2026-05-03: Mrs. Addie Easton "
        "Payne is row 30 on the Shawnee Indian Agency master list "
        "(part10_page_036, transmitted by Supt. A. W. Leech, March 20, "
        "1929). Master list row reads 'Mrs. Addie E. Payne — Report in "
        "detail attached' — this record IS her detail report. Allotment "
        "168 and tribe Citizen Potawatomie established by user research "
        "earlier in the project. Sonnet failed to extract any structured "
        "fields (CAT_1 record); patched directly from known cross-"
        "reference rather than via vision recovery."
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-03",
        "type": "task5_shawnee_cross_reference_known_answer",
        "method": "user_research_with_master_list_cross_reference",
        "fields_corrected": [
            "Name", "Allotment number", "Tribe/Reservation", "NOTES",
        ],
        "previous_values": previous,
        "corrected_values": {
            "Name": "Mrs. Addie Easton Payne",
            "Allotment number": "168",
            "Tribe/Reservation": "Citizen Potawatomie",
        },
        "shawnee_master_list_row": 30,
        "user_confirmed": True,
        "rationale": (
            "CAT_1 record (Sonnet captured neither name nor allotment) "
            "where the answer was already known from prior cross-reference "
            "work. Patched directly from user research rather than via "
            "vision recovery."
        ),
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patched part10_questionnaire_015:")
    print(f"  Name:      {previous['Name']:30s} -> Mrs. Addie Easton Payne")
    print(f"  Allotment: {previous['Allotment number']:30s} -> 168")
    print(f"  Tribe:     {previous['Tribe/Reservation']:30s} -> Citizen Potawatomie")


if __name__ == "__main__":
    main()
