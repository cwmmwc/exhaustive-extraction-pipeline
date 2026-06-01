#!/usr/bin/env python3
"""
Patch part10_questionnaire_014 with Albion Ogee's source-verified
Circular 2464 questionnaire response.

Background: Sonnet text-extraction failed completely on this record.
  - Name: "not stated"
  - Allotment: "70757" (garbage; not a real allotment number, likely OCR
    artifact from scanner noise or page-boundary contamination)
  - All other fields: "not stated"
  - NOTES claimed document was "heavily degraded and largely illegible"
    — user source review confirms page is actually quite legible.

Vision recovery on 2026-04-28 produced DISAGREE between models:
  - Sonnet vision: "(no name) / 1050"
  - Qwen vision:   "Albion Ogee / 1080"

User source-page review on 2026-04-28 confirmed Qwen was correct,
cross-referenced with BLM patent accession 715735:
  - Name: Albion Ogee
  - Allotment: 1080
  - Tribe/Reservation: Citizen Pottawatomie
  - Document type: Circular 2464 questionnaire (real)

This is the second BLM-confirmed Citizen Pottawatomie record from part 10/11
(after Nicholas Trombla, allotment 464). Suggests a tribal grouping in the
splitter chunks — worth checking whether part 10 and part 11 are largely
or entirely Citizen Pottawatomie material.

Substantive patch transcribing Q1 through Q13 from page 1 source.

Source PDF: split_documents/questionnaires/part10_questionnaire_014.pdf (1 page)
Source image: vision_recovery_sample/images/part10_questionnaire_014_page-1.png
External cross-reference: BLM patent accession 715735
  https://glorecords.blm.gov/details/patent/default.aspx?accession=715735&docClass=SER

NOTABLE FINDING ON THIS RECORD: Q3 indicates Albion Ogee accepted the patent
under PROTEST — this is a real Circular 2464 dispossession-protest record.
The substantive corpus value of this record was previously hidden by a total
extraction failure.
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
    / "part10_questionnaire_014.json"
)


def patched_extraction():
    """Build corrected extraction from source page 1 review."""
    return {
        "Name": "Albion Ogee",
        "Tribe/Reservation": "Citizen Pottawatomie",
        "Post Office Address": "not stated",
        "Allotment number": "1080",
        "Cancelled": "No (Q8: patent not cancelled)",
        "Refused/Protested": (
            "PROTESTED (Q3). Filed for record in person shortly after "
            "receiving same."
        ),
        "Recorded patent": (
            "Filed for record in person shortly after receiving the patent (Q3)."
        ),
        "Sold/Mortgaged": "No (Q4, Q5: not sold, not mortgaged)",
        "Buyer": "not stated (no sale)",
        "Tax burden forced sale/Mortgage": (
            "All taxes paid (Q7); no land sold for debts or taxes"
        ),
        "Trust Patent Date": "not stated",
        "Fee Patent Date": (
            "October 30, 1919 (Q1; patent received in person 5/18/1921 per Q2)"
        ),
        "Gender": "not stated (likely Male given allottee context)",
        "Age": "64 years (Q10)",
        "Occupation/Income": (
            "Operation of land; all lease (Q11). No dependents (Q12). "
            "Physical condition poor (Q10)."
        ),
        "NOTES": (
            "Land description: NE quarter, Section 17, Township 8, Range 5. "
            "Q3: PROTESTED acceptance — this is a real protest record, the "
            "core target of Circular 2464 investigation. "
            "Q10: age 64, physical condition poor. "
            "Q11: income from leasing the entire allotment. "
            "Q12: no dependents. "
            "| IDENTITY RECOVERY 2026-04-28: Sonnet text-extraction completely "
            "failed: Name 'not stated', Allotment '70757' (garbage — not a real "
            "allotment number, likely OCR artifact from scanner noise or "
            "page-boundary contamination), all Q&A fields 'not stated', NOTES "
            "claimed document was 'heavily degraded and largely illegible'. "
            "User source review on 2026-04-28 confirmed page is actually quite "
            "legible; Sonnet's degradation claim was incorrect. Vision recovery "
            "DISAGREE: Sonnet vision returned no name with allotment 1050; "
            "Qwen-VL returned 'Albion Ogee / 1080'. User confirmed Qwen reading. "
            "BLM patent accession 715735 confirms Albion Ogee, allotment 1080, "
            "Citizen Pottawatomie. "
            "| EXTERNAL CROSS-REFERENCE: BLM accession 715735, URL: "
            "https://glorecords.blm.gov/details/patent/default.aspx?accession=715735&docClass=SER "
            "| RELATED: Nicholas Trombla (part11_questionnaire_001, allotment 464, "
            "BLM accession 715720) is also Citizen Pottawatomie. Suggests parts "
            "10 and 11 may be largely or entirely Citizen Pottawatomie material — "
            "worth a systematic check."
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

    if current.get("Allotment number") != "70757":
        print(f"WARNING: Allotment is currently '{current.get('Allotment number')}', expected '70757'.")
        print("This script targets part10_questionnaire_014 specifically.")
        sys.exit(1)

    record["extraction"] = patched_extraction()

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
        "source_image": "vision_recovery_sample/images/part10_questionnaire_014_page-1.png",
        "vision_model_readings": {
            "sonnet-vision": "(no name) / 1050",
            "qwen2.5-vl-72b": "Albion Ogee / 1080",
            "user_source_review": "Albion Ogee / 1080",
            "blm_canonical": "Albion Ogee / 1080",
        },
        "external_refs": {
            "BLM_accession": "715735",
            "BLM_url": "https://glorecords.blm.gov/details/patent/default.aspx?accession=715735&docClass=SER",
        },
        "user_confirmed": True,
        "document_type": "Circular 2464 questionnaire (real)",
        "tribe_reservation": "Citizen Pottawatomie",
        "notable_content": (
            "Q3 indicates Albion Ogee PROTESTED acceptance of the fee patent — "
            "this is a real protest record, the core target of the Circular 2464 "
            "investigation. Substantive corpus value was hidden by total "
            "extraction failure."
        ),
        "data_quality_correction": (
            "Sonnet text NOTES claimed document was 'heavily degraded and largely "
            "illegible'; user source review found page is actually quite legible. "
            "Garbage allotment '70757' was likely OCR artifact, not a meaningful "
            "value."
        ),
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patch applied successfully.")
    print(f"  Record: part10_questionnaire_014.json")
    print(f"  Name: Albion Ogee (allot 1080, Citizen Pottawatomie)")
    print(f"  BLM cross-ref: accession 715735")
    print(f"  Substantive patch: Q1-Q13 transcribed; PROTESTED acceptance noted")
    print(f"  Allotment correction: 70757 (garbage) -> 1080 (source + BLM)")
    print()
    print("Manifest unchanged (in-place patch).")


if __name__ == "__main__":
    main()
