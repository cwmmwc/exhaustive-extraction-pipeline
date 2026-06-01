#!/usr/bin/env python3
"""
Patch part11_questionnaire_001 with Nicholas Trombla's source-verified
Circular 2464 questionnaire response.

Background: Sonnet text-extraction substantively failed on this record.
  - Name: "not stated" (handwritten, not captured)
  - Allotment: 6 (Sonnet text misread; source clearly shows 464)
  - Fee Patent Date: "9-22" (Sonnet text misread; source: Oct 13 1919)
  - Most Q&A answers: "not stated" or "U/Know" despite source legibility

Vision recovery on 2026-04-28 produced DISAGREE between models:
  - Sonnet vision: "Nicholas Tremble / 2464"
    (allotment is wrong: read circular reference number from form header)
  - Qwen vision:   "Nicholas Trombley / 464"
    (allotment correct; surname close but not canonical)

User source-page review on 2026-04-28 confirmed correct readings,
cross-referenced with BLM patent accession 715720:
  - Name: Nicholas Trombla
  - Allotment: 464
  - Tribe/Reservation: Citizen Pottawatomie
  - Document type: Circular 2464 questionnaire (genuine, not Form 5-105)

This is a substantive patch — transcribes Q1 through Q13 from page 1 source
since the answers are mostly legible and this is a real Circular 2464 record
(corpus's primary document type). Other "not stated" fields without legible
source content are left as-is.

Source PDF: split_documents/questionnaires/part11_questionnaire_001.pdf
Source image: vision_recovery_sample/images/part11_questionnaire_001_page-1.png
External cross-reference: BLM patent accession 715720
  https://glorecords.blm.gov/details/patent/default.aspx?accession=715720&docClass=SER
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
    / "part11_questionnaire_001.json"
)


def patched_extraction():
    """Build corrected extraction from source page 1 review."""
    return {
        "Name": "Nicholas Trombla",
        "Tribe/Reservation": "Citizen Pottawatomie",
        "Post Office Address": "not stated",
        "Allotment number": "464",
        "Cancelled": "No (Q8 answered: patent not cancelled)",
        "Refused/Protested": "Without protest (Q3); not filed for record with County",
        "Recorded patent": "Not filed for record with County (Q3)",
        "Sold/Mortgaged": "Sold by patentee (Q4); mortgage has been released (Q5)",
        "Buyer": (
            "Sale: $8,000.00, fair consideration, no settlement of debt (Q6). "
            "Buyer name not legible on this page; sale by patentee."
        ),
        "Tax burden forced sale/Mortgage": "No (Q7: land not sold for debts or taxes)",
        "Trust Patent Date": "not stated",
        "Fee Patent Date": "October 13, 1919 (Q1; patent received 12/19/1919 by mail per Q2)",
        "Gender": "not stated (likely Male given allottee context)",
        "Age": "74 years (Q10)",
        "Occupation/Income": (
            "No support from government, State, or County (Q11). "
            "No persons dependent for support (Q12)."
        ),
        "NOTES": (
            "Land description: NW NE quarter of Section 7, Township 9 North, "
            "Range 3 East of [Indian/Principal] Meridian. "
            "Q4 sale answer indicates sold by patentee for fair consideration. "
            "Q10: age 74, mental condition good, physical condition fair. "
            "Q13: no, was not defrauded. "
            "| IDENTITY RECOVERY 2026-04-28: Sonnet text-extraction failed on Name "
            "(handwritten) and misread Allotment number as '6' (source is '464'). "
            "Vision recovery DISAGREE between models: Sonnet vision read "
            "'Nicholas Tremble / 2464' (incorrectly grabbed circular reference "
            "number from form header as allotment); Qwen-VL read 'Nicholas Trombley "
            "/ 464' (allotment correct, surname close but not canonical). User "
            "source-page review and BLM patent accession 715720 confirm correct "
            "name is 'Nicholas Trombla' and tribe is 'Citizen Pottawatomie'. "
            "Most Q&A fields previously 'not stated' or 'U/Know' have been "
            "transcribed from source page 1 in this patch. "
            "| EXTERNAL CROSS-REFERENCE: BLM patent accession 715720 confirms "
            "Nicholas Trombla, allotment 464, Citizen Pottawatomie. URL: "
            "https://glorecords.blm.gov/details/patent/default.aspx?accession=715720&docClass=SER"
        ),
        "Literate/Illiterate": "not stated",
        "Document type": "questionnaire (Circular 2464)",
    }


def main():
    if not RECORD_PATH.exists():
        print(f"ERROR: target record not found: {RECORD_PATH}")
        sys.exit(1)

    with open(RECORD_PATH) as f:
        record = json.load(f)

    current = record["extraction"]

    if current.get("Name") != "not stated":
        print(f"WARNING: Name is currently '{current.get('Name')}', not 'not stated'.")
        print("Aborting to avoid overwriting unintended data.")
        sys.exit(1)

    if current.get("Allotment number") != "6":
        print(f"WARNING: Allotment is currently '{current.get('Allotment number')}', expected '6'.")
        print("This script targets part11_questionnaire_001 specifically.")
        sys.exit(1)

    # Apply substantive patch
    record["extraction"] = patched_extraction()

    # Audit entry
    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-28",
        "type": "substantive_record_recovery",
        "method": "vision_recovery_disagree_user_arbitrated_with_blm_cross_reference",
        "fields_recovered_or_corrected": [
            "Name", "Tribe/Reservation", "Allotment number", "Cancelled",
            "Refused/Protested", "Recorded patent", "Sold/Mortgaged", "Buyer",
            "Tax burden forced sale/Mortgage", "Fee Patent Date", "Age",
            "Occupation/Income", "NOTES", "Document type",
        ],
        "source_image": "vision_recovery_sample/images/part11_questionnaire_001_page-1.png",
        "vision_model_readings": {
            "sonnet-vision": "Nicholas Tremble / 2464 (allotment WRONG - read circular ref)",
            "qwen2.5-vl-72b": "Nicholas Trombley / 464 (allotment correct, surname close)",
            "user_source_review": "Nicholas Trombla / 464",
            "blm_canonical": "Nicholas Trombla / 464",
        },
        "external_refs": {
            "BLM_accession": "715720",
            "BLM_url": "https://glorecords.blm.gov/details/patent/default.aspx?accession=715720&docClass=SER",
        },
        "user_confirmed": True,
        "document_type": "Circular 2464 questionnaire (real, not Form 5-105)",
        "tribe_reservation": "Citizen Pottawatomie",
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patch applied successfully.")
    print(f"  Record: part11_questionnaire_001.json")
    print(f"  Name: Nicholas Trombla (allot 464, Citizen Pottawatomie)")
    print(f"  BLM cross-ref: accession 715720")
    print(f"  Substantive patch: Q1-Q13 transcribed from page 1 source")
    print(f"  Allotment correction: 6 (Sonnet text misread) -> 464 (source + BLM)")
    print()
    print("Manifest unchanged (in-place patch).")


if __name__ == "__main__":
    main()
