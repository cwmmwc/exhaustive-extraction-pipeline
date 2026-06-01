#!/usr/bin/env python3
"""
Fix pine_ridge_vol1_affidavit_020 — Sarah Thompson record.

Background: This record's 'extraction' field is a 2-item list, but
inspection of the source PDF (single page) confirmed only Sarah Thompson
is present on the source. Item 1 (Hermos Merrivall) is leaked/duplicated
content from elsewhere; his canonical record exists separately at
pine_ridge_vol1_affidavit_122.json.

Source page details (single page PDF):
  Document No. 312
  State of South Dakota, County of Shannon
  Sarah Thompson, age 45, Batesland, South Dakota
  Applied for patent in 1913, refused; forced patent issued April 13, 1918
  640 acre allotment; never mortgaged or sold
  Husband farms her land; 9 children
  Sworn December 12, 1928 before Mark Maistri, Notary Public

BLM cross-reference:
  Accession 625165, Serial Patent, South Dakota
  Issue Date 4/13/1918, Tribe: Pine Ridge Sioux
  Indian Allot. Nr: 312, Total Acres: 640.00
  Authority: October 14, 1865 Indian Fee Patent (14 Stat. 703)

Fix:
  1. Convert extraction from list to dict (single-allottee structure)
  2. Keep Sarah's data as the canonical content
  3. Set Allotment number = 312
  4. Add BLM accession 625165 to NOTES
  5. Drop Item 1 (Hermos Merrivall) — his real record is vol1_affidavit_122
  6. Add audit note explaining the structural change
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
RECORD_PATH = (
    PROJECT_ROOT
    / "circular_2464_extractions"
    / "extractions"
    / "sonnet"
    / "pine_ridge_vol1_affidavit_020.json"
)

CORRECTION_NOTE = (
    " | TASK 5 STRUCTURAL CORRECTION 2026-04-29: This record's 'extraction' "
    "field was originally a 2-item list (Sarah Thompson + Hermos Merrivall). "
    "Source PDF render confirmed the page contains ONLY Sarah Thompson's "
    "affidavit — the Hermos Merrivall data was leaked/duplicated content "
    "from elsewhere during Sonnet text-extraction. Hermos Merrivall's "
    "canonical record exists separately at pine_ridge_vol1_affidavit_122.json. "
    "This patch: (1) flattens extraction to dict (single allottee), (2) sets "
    "Allotment number = 312 (BLM accession 625165 confirms), (3) drops the "
    "leaked Item 1 data."
)


def main():
    with open(RECORD_PATH) as f:
        record = json.load(f)

    extraction = record["extraction"]
    if not isinstance(extraction, list):
        print(f"ERROR: extraction is not a list (current type: {type(extraction).__name__}). "
              f"Already fixed? Aborting.")
        return

    if len(extraction) != 2:
        print(f"ERROR: expected 2-item list, got {len(extraction)}-item list. Aborting.")
        return

    sarah = extraction[0]
    hermos = extraction[1]

    if "Thompson" not in (sarah.get("Name") or ""):
        print(f"ERROR: Item 0 name is '{sarah.get('Name')}', expected to contain 'Thompson'. Aborting.")
        return
    if "Merrivall" not in (hermos.get("Name") or ""):
        print(f"ERROR: Item 1 name is '{hermos.get('Name')}', expected to contain 'Merrivall'. Aborting.")
        return

    # Apply corrections to Sarah's data
    sarah["Allotment number"] = "312"
    sarah["NOTES"] = (sarah.get("NOTES") or "") + CORRECTION_NOTE

    # Replace the list with just Sarah's flat dict
    record["extraction"] = sarah

    # Audit trail
    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-29",
        "type": "task5_structural_fix_list_to_dict_with_blm_confirmation",
        "method": "user_source_pdf_render_with_blm_cross_reference",
        "fields_corrected": ["extraction (structural)", "Allotment number", "NOTES"],
        "previous_structure": "list[2] containing Sarah Thompson + Hermos Merrivall",
        "corrected_structure": "dict (Sarah Thompson only)",
        "previous_allotment": "not stated",
        "corrected_allotment": "312",
        "external_refs": {
            "BLM_accession": "625165",
            "BLM_doc_type": "Serial Patent",
            "BLM_state": "South Dakota",
            "BLM_tribe": "Pine Ridge Sioux",
            "BLM_issue_date": "1918-04-13",
            "BLM_total_acres": "640.00",
        },
        "dropped_data": {
            "name": "Hermos Merrivall",
            "rationale": (
                "Item 1 of the original list was Hermos Merrivall; not present "
                "on source PDF (single-page Sarah Thompson affidavit confirmed "
                "by user render). Hermos's canonical record is preserved at "
                "pine_ridge_vol1_affidavit_122.json."
            ),
        },
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Fixed: {RECORD_PATH.name}")
    print(f"  Structure: list[2] -> dict")
    print(f"  Name: Sarah Thompson")
    print(f"  Allotment: not stated -> 312")
    print(f"  BLM accession 625165")
    print(f"  Dropped duplicate Hermos data (canonical at vol1_affidavit_122)")


if __name__ == "__main__":
    main()
