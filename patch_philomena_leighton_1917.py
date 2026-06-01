#!/usr/bin/env python3
"""
Patch part1_questionnaire_002 with Philomena Leighton née Beauvais's 1917
fee patent application.

Background: Sonnet text-extraction failed substantively:
  - Name: "not stated"
  - Allotment: 72 (misread; source clearly shows 488)
  - All Q&A fields: "not stated"
  - NOTES claimed "heavily illegible" — page is actually fully legible
  - NOTES did correctly identify Form 5-105 / Act of May 8, 1906

Vision recovery 2026-04-28 produced DISAGREE between models:
  - Sonnet vision read three different names across three pages
    (Philadelphia Lightfoot McCauley / 479 page 1; allot 1296 page 2;
    Philomena Leighton page 3)
  - Qwen vision: "Philomena Leighton née Beauvais / 478"

Sonnet vision's "three different names" reading was hallucinated. User
source-page review on 2026-04-28 confirmed all three pages are one document
filed by Philomena Leighton née Beauvais. Qwen was correct on identity;
allotment is 488 not 478.

KEY FINDING: This record is a SIBLING document to part2_questionnaire_014
(also Philomena Leighton née Beauvais, also Form 5-105, also allotment 488,
also Rosebud). The two filings are NOT duplicates — they are two distinct
filings by the same person about the same allotment, one year apart:

  part1_questionnaire_002 (THIS RECORD):
    - Sworn 25 July 1917
    - Age 33
    - Land value $4,800
    - Family dependents: husband George + 4 children
      (William age 9, Alice age 6, Levi age 3, Leona age 1)
    - Schooled: White Thunder Day School + Haskell Institute
    - Subscribed before Superintendent + Notary Public

  part2_questionnaire_014 (sibling, patched separately on 2026-04-28):
    - Date: not visible on page (likely 1918+)
    - Age 34
    - Land value $2,500
    - Family dependents: infant Emma Louise Leighton (11 months)
    - Schooled: Day school 8 yrs + Haskell 4 yrs
    - All other field details left unpatched pending revisit

Both records describe the same allotment (S half NE quarter, Section 2,
Township 39 N, Range 28), filed by the same person, about one year apart.
This may indicate a refiling, an amended application, or a separate
application for a different portion of the same allotment.

Substantive patch transcribing the 1917 application from all three pages.

Source PDF: split_documents/questionnaires/part1_questionnaire_002.pdf (3 pages)
Source images: vision_recovery_sample/images/part1_questionnaire_002_page-{1,2,3}.png
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
    / "part1_questionnaire_002.json"
)


def patched_extraction():
    """Build corrected extraction from source pages 1-3."""
    return {
        "Name": "Philomena Leighton née Beauvais",
        "Tribe/Reservation": "Rosebud Agency",
        "Post Office Address": "not stated",
        "Allotment number": "488",
        "Cancelled": "not applicable (this is an APPLICATION for a fee patent, not a response to one already issued)",
        "Refused/Protested": "not applicable (application document)",
        "Recorded patent": "not applicable (application document)",
        "Sold/Mortgaged": "Q21: No contract to sell. Q22: No one asked her to procure a patent for purpose of disposing of land.",
        "Buyer": "not applicable (application document)",
        "Tax burden forced sale/Mortgage": "not applicable (application document)",
        "Trust Patent Date": "not stated",
        "Fee Patent Date": "not applicable — applying for fee patent, sworn 25 July 1917",
        "Gender": "Female",
        "Age": "33 (Q1)",
        "Occupation/Income": (
            "Q10 cultivates land: none. "
            "Q11 other occupation: sewing & cooking. "
            "Q25 practical business experience: sewing."
        ),
        "NOTES": (
            "FORM 5-105 APPLICATION FOR PATENT IN FEE (Act of May 8, 1906, 34 Stat. 182). "
            "Sworn 25 July 1917 before Superintendent and Notary Public. "
            "Land: 'The South half of the North East quarter and the lots numbered "
            "one and two of Section two in Township thirty nine North of Range twenty "
            "eight' — value $4,800 (Q7). "
            "Q1-Q11: age 33, half blood, married, schooled at White Thunder Day School "
            "and Haskell Institute, no intoxicants, good physical condition. Application "
            "covers all of own allotment, not inherited; does not cultivate; sewing & "
            "cooking as occupation. "
            "Q23 family allotments: George (husband, age 29, 160 acres @ $4,800); "
            "William (son, age 9, 160 acres @ $2,500); Alice (daughter, age 6, 160 "
            "acres @ $2,500); Levi (son, age 3, 160 acres @ $2,500); Leona (daughter, "
            "age 1, 160 acres @ $2,500). "
            "Q24 dependents: 'None — my family as stated to question no 23 are my "
            "dependents.' "
            "Q26: no other lands held in trust. "
            "Q27 reasons for requesting patent (verbatim): 'Owing to the fact that I "
            "am a half blood Indian and that my husband is a quarter blood I really "
            "believe that we need not be held under further restrictions any longer "
            "by the Indian Bureau.' "
            "Signature: 'Philomena Leighton onee Beauvais' (handwritten — 'onee' "
            "appears to be her abbreviation of 'née'). "
            "| IDENTITY RECOVERY 2026-04-28: Sonnet text-extraction failed substantively "
            "(Name='not stated', Allotment=72 misread of 488, all Q&A 'not stated', "
            "NOTES claimed 'heavily illegible' but page is fully legible). Vision "
            "recovery DISAGREE: Sonnet vision hallucinated three different names "
            "across three pages (Philadelphia Lightfoot McCauley / 479 page 1; allot "
            "1296 page 2; Philomena Leighton page 3) — none of these readings are "
            "supported by the source. Qwen-VL read 'Philomena Leighton née Beauvais "
            "/ 478' (name correct, allotment off by one digit). User source review "
            "confirmed all three pages are one document, all by Philomena Leighton "
            "née Beauvais, allotment 488. Sonnet vision's multi-name reading was "
            "hallucinated. "
            "| SIBLING DOCUMENT: part2_questionnaire_014 is also Philomena Leighton "
            "née Beauvais's Form 5-105 application for the same allotment 488 at "
            "Rosebud, but is a distinct filing approximately one year later (age 34, "
            "land value $2,500, infant Emma Louise Leighton listed as dependent). "
            "These are two real, distinct filings by the same person — not duplicates. "
            "Possible interpretations: refiling, amendment, separate application for "
            "different portion of same allotment, or one application that was withdrawn "
            "and resubmitted. Both records preserved in the corpus. Christian to "
            "investigate the relationship in source archival research."
        ),
        "Literate/Illiterate": "Signed her own name (handwritten signature visible)",
        "Document type": "Form 5-105 Application for Patent in Fee",
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

    if current.get("Allotment number") != "72":
        print(f"WARNING: Allotment is currently '{current.get('Allotment number')}', expected '72'.")
        print("This script targets part1_questionnaire_002 specifically.")
        sys.exit(1)

    record["extraction"] = patched_extraction()

    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-28",
        "type": "substantive_record_recovery_with_sibling_finding",
        "method": "vision_recovery_disagree_user_arbitrated",
        "fields_recovered_or_corrected": [
            "Name", "Tribe/Reservation", "Allotment number", "Cancelled",
            "Refused/Protested", "Recorded patent", "Sold/Mortgaged", "Buyer",
            "Tax burden forced sale/Mortgage", "Fee Patent Date", "Gender",
            "Age", "Occupation/Income", "NOTES", "Literate/Illiterate",
            "Document type",
        ],
        "source_images": [
            "vision_recovery_sample/images/part1_questionnaire_002_page-1.png",
            "vision_recovery_sample/images/part1_questionnaire_002_page-2.png",
            "vision_recovery_sample/images/part1_questionnaire_002_page-3.png",
        ],
        "vision_model_readings": {
            "sonnet-vision": (
                "HALLUCINATED three names across three pages: Philadelphia "
                "Lightfoot McCauley / 479 (page 1); allot 1296 (page 2); "
                "Philomena Leighton (page 3). None of these are correct."
            ),
            "qwen2.5-vl-72b": "Philomena Leighton née Beauvais / 478",
            "user_source_review": "Philomena Leighton née Beauvais / 488",
        },
        "user_confirmed": True,
        "document_type": "Form 5-105 Application for Patent in Fee, NOT Circular 2464 questionnaire",
        "tribe_reservation": "Rosebud Agency",
        "sibling_document": {
            "record_id": "part2_questionnaire_014",
            "relationship": "Same person, same allotment, distinct filing approximately one year later",
            "differences_summary": (
                "This record (part1_q002): sworn 25 July 1917, age 33, land value "
                "$4,800, family dependents = husband + 4 children. "
                "Sibling (part2_q014): age 34, land value $2,500, infant Emma Louise "
                "Leighton listed as dependent. "
                "Possible interpretations: refiling, amendment, withdrawal+resubmission, "
                "or separate application for different portion. Christian to investigate."
            ),
        },
        "data_quality_correction": (
            "Sonnet text NOTES claimed document was 'heavily illegible'; user "
            "source review found all three pages fully legible. Sonnet vision "
            "hallucinated a multi-document multi-name reading from a single-document "
            "three-page application."
        ),
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patch applied successfully.")
    print(f"  Record: part1_questionnaire_002.json")
    print(f"  Name: Philomena Leighton née Beauvais (allot 488, Rosebud)")
    print(f"  Allotment correction: 72 (Sonnet text misread) -> 488")
    print(f"  Document type: Form 5-105 Application for Patent in Fee")
    print(f"  KEY FINDING: sibling document part2_questionnaire_014 is the same person's")
    print(f"               distinct later filing (age 34, $2,500, with infant Emma Louise)")
    print(f"  Substantive patch: all 3 pages transcribed; Q23 family allotments captured")
    print()
    print("Manifest unchanged (in-place patch).")


if __name__ == "__main__":
    main()
