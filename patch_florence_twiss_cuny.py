#!/usr/bin/env python3
"""
Substantive correction for Florence Twiss Cuny (pine_ridge_vol1_affidavit_123).

Background: A diagnostic flagged this record as a borderline case during the
Pine Ridge tribe normalization pass — the Tribe field read "Shannon County,
South Dakota (likely Pine Ridge or Rosebud)" with explicit uncertainty.
A BLM cross-reference (accession 709333) resolved the uncertainty AND
revealed two further extraction errors:

  - Name: "Florence Twiis Cuny" -> "Florence Twiss Cuny"
    Sonnet text-OCR read "ss" as "ii" (two adjacent vertical strokes).
    "Twiss" is a documented Pine Ridge surname (Frank Twiss was a
    Pine Ridge BIA Superintendent ~1908-1913).

  - Allotment number: 762 -> 818
    Sonnet text-extraction misread the handwritten allotment number.
    Original NOTES had even captured the correct number ("document
    references No. 818") but the Allotment number field was set to 762.
    BLM accession 709333 confirms Florence Twiss / allotment 818.

  - Tribe: "Shannon County, SD (likely Pine Ridge or Rosebud)" -> "Pine Ridge"
    BLM Tribe field reads "Pine Ridge Sioux".

BLM Patent Record:
  Accession: 709333
  Document Type: Serial Patent
  Issue Date: 9/29/1919
  State: South Dakota
  Tribe: Pine Ridge Sioux
  Names On Document: TWISS, FLORENCE
  Indian Allot. Nr: 818
  Total Acres: 160.00
  Authority: October 14, 1865: Indian Fee Patent (14 Stat. 703)

This patch is run BEFORE the bulk Pine Ridge normalization so that when
the normalization runs, it will see this record as already canonical and
skip it.

Note about allotment numbers: a state-wide BLM search for allotment "762"
in South Dakota returned no Florence (the "762" appearing in BLM is a
document number for a different person, not an allotment). This confirms
the 762 in our corpus was a misread of 818, not a different allotment
that happened to belong to Florence.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
RECORD_PATH = (
    PROJECT_ROOT
    / "circular_2464_extractions"
    / "extractions"
    / "sonnet"
    / "pine_ridge_vol1_affidavit_123.json"
)

CORRECTION_NOTE = (
    " | SUBSTANTIVE CORRECTION 2026-04-29: BLM accession 709333 (Serial Patent, "
    "South Dakota, 9/29/1919) confirms canonical record details. Three "
    "Sonnet text-extraction errors corrected: "
    "(1) Name 'Twiis' is OCR misread of 'Twiss' (the s-s ligature read as i-i); "
    "(2) Allotment number 762 corrected to 818 — original Sonnet NOTES even "
    "captured the correct '818' as 'document references No. 818' but the "
    "primary field was set to 762; "
    "(3) Tribe normalized from 'Shannon County, SD (likely Pine Ridge or "
    "Rosebud)' to 'Pine Ridge' — BLM Tribe field reads 'Pine Ridge Sioux', "
    "and Florence's PO address (Rocky Ford, SD — a Pine Ridge community in "
    "Shannon County) confirms. "
    "Original allottee name on patent was 'Florence Twiss' (Cuny is married "
    "name; preserved as primary form per affidavit self-identification)."
)


def main():
    if not RECORD_PATH.exists():
        print(f"ERROR: target record not found: {RECORD_PATH}")
        sys.exit(1)

    with open(RECORD_PATH) as f:
        record = json.load(f)

    current = record["extraction"]

    # Verify expected pre-patch state
    expected = {
        "Name": "Florence Twiis Cuny",
        "Allotment number": "762",
        "Tribe/Reservation": "Shannon County, South Dakota (likely Pine Ridge or Rosebud)",
    }
    for field, expected_value in expected.items():
        actual = current.get(field)
        if actual != expected_value:
            print(f"WARNING: {field} = '{actual}', expected '{expected_value}'")
            print("Aborting to avoid overwriting unintended data.")
            sys.exit(1)

    # Apply corrections
    current["Name"] = "Florence Twiss Cuny"
    current["Allotment number"] = "818"
    current["Tribe/Reservation"] = "Pine Ridge"
    current["NOTES"] = (current.get("NOTES") or "") + CORRECTION_NOTE

    # Audit entry
    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-29",
        "type": "substantive_record_correction_with_blm_cross_reference",
        "method": "user_blm_lookup",
        "fields_corrected": ["Name", "Allotment number", "Tribe/Reservation", "NOTES"],
        "previous_values": expected,
        "corrected_values": {
            "Name": "Florence Twiss Cuny",
            "Allotment number": "818",
            "Tribe/Reservation": "Pine Ridge",
        },
        "external_refs": {
            "BLM_accession": "709333",
            "BLM_doc_type": "Serial Patent",
            "BLM_state": "South Dakota",
            "BLM_tribe": "Pine Ridge Sioux",
            "BLM_issue_date": "1919-09-29",
            "BLM_total_acres": "160.00",
            "BLM_authority": "October 14, 1865: Indian Fee Patent (14 Stat. 703)",
            "BLM_url": "https://glorecords.blm.gov/details/patent/default.aspx?accession=709333&docClass=SER",
        },
        "user_confirmed": True,
        "extraction_failure_modes": [
            "OCR letter-pair confusion: 'ss' read as 'ii' in Twiss/Twiis",
            "Handwritten allotment number misread: 818 -> 762",
            "Allotment number was correctly captured in NOTES ('No. 818') but "
            "primary Allotment number field set to 762 — indicates field-level "
            "extraction inconsistency where supporting text was richer than the "
            "structured field value",
        ],
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patch applied successfully.")
    print(f"  Record: pine_ridge_vol1_affidavit_123.json")
    print(f"  Name: 'Florence Twiis Cuny' -> 'Florence Twiss Cuny' (OCR fix)")
    print(f"  Allotment: 762 -> 818 (BLM-confirmed)")
    print(f"  Tribe: '...likely Pine Ridge or Rosebud' -> 'Pine Ridge' (BLM-confirmed)")
    print(f"  BLM cross-ref: accession 709333")
    print()
    print("Note: this record is now canonical; bulk normalization will skip it.")


if __name__ == "__main__":
    main()
