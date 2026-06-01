#!/usr/bin/env python3
"""
Update Laura Dean's NOTES to capture both source attestations.

Master list (part10_page_036, row 32):
  'James J. Sweeney for his deceased wife, Laura Dean and their minor child'

Detail report (this record, part10_questionnaire_017):
  'Laura Dean — deceased wife of William J. Sweeney, Sr., and mother of
   William J. Sweeney, Jr., only heirs: Allottee'

The two sources name the husband differently. User chose to keep 'James J.
Sweeney' in the Name field per the master list, and capture the William J.
detail-report attestation in NOTES.

This patch replaces the earlier (speculative) NOTES correction with an
accurate cross-reference note.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
RECORD_PATH = (
    PROJECT_ROOT
    / "circular_2464_extractions"
    / "extractions"
    / "sonnet"
    / "part10_questionnaire_017.json"
)

# The exact text appended by patch_sweeney_name.py to be removed
ERRONEOUS_NOTE = (
    " | TASK 5 NAME CORRECTION 2026-04-30: Husband's name corrected from "
    "'William J. Sweeney, Sr.' to 'James J. Sweeney' per Shawnee master "
    "list (row 32: 'James J. Sweeney for his deceased wife, Laura Dean "
    "and their minor child'). Sonnet misread 'Jas.' as 'Wm.' — common "
    "OCR confusion on abbreviated first names. The minor child is "
    "currently captured as 'William J. Sweeney, Jr.' but the master "
    "list does not name the child; this name may itself be a Sonnet "
    "reconstruction and should be verified against the detail report."
)

REPLACEMENT_NOTE = (
    " | TASK 5 SOURCE CROSS-REFERENCE 2026-04-30: Two source documents name "
    "the husband differently. The Shawnee master list (part10_page_036, "
    "row 32) reads: 'James J. Sweeney for his deceased wife, Laura Dean "
    "and their minor child' — followed in the canonical Name field of this "
    "record. The detail report itself (this PDF) reads: 'Laura Dean — "
    "deceased wife of William J. Sweeney, Sr., and mother of William J. "
    "Sweeney, Jr., only heirs: Allottee'. The William J. text is preserved "
    "here as supplementary documentation. The disagreement may reflect a "
    "typist's Wm./Jas. abbreviation confusion at one of the two source "
    "documents; without external evidence (BLM patent record, census, etc.) "
    "the question of the husband's true first name is unresolved."
)


def main():
    with open(RECORD_PATH) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        print("ERROR: list-shaped extraction")
        return

    # Strip the earlier (now-superseded) NOTES correction; append the new one
    notes = e.get("NOTES") or ""
    if ERRONEOUS_NOTE in notes:
        notes = notes.replace(ERRONEOUS_NOTE, "")
        print("Stripped earlier NOTES correction.")
    else:
        print("Earlier NOTES correction not found — already removed?")

    notes += REPLACEMENT_NOTE
    e["NOTES"] = notes

    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-30",
        "type": "task5_source_cross_reference_annotation",
        "method": "user_master_list_and_detail_report_comparison",
        "fields_corrected": ["NOTES"],
        "preserved_in_name_field": "James J. Sweeney (per master list)",
        "preserved_in_notes": (
            "William J. Sweeney, Sr. (husband) and William J. Sweeney, Jr. "
            "(son), per detail report family self-attestation"
        ),
        "rationale": (
            "Two source documents name the husband differently. Per user "
            "decision, the master list's 'James J.' is canonical for the "
            "Name field; the detail report's 'William J.' attestation is "
            "preserved in NOTES."
        ),
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Name (unchanged): {e['Name']}")
    print("NOTES updated with cross-reference annotation.")


if __name__ == "__main__":
    main()
