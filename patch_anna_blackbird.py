#!/usr/bin/env python3
"""
Substantive correction for Anna Blackbird's Form 5-105 application
(part1_questionnaire_017).

Background: A Task 6 spot-check on 2026-04-29 surfaced multiple substantive
extraction errors on this record beyond just the document type misrouting:

  Sonnet text-extraction errors found:
    1. Name OCR error: "Ann Black" -- Sonnet dropped "bird" from "Blackbird"
       and split "Anna" into "Ann". Source clearly reads "Anna Blackbird".
    2. Allotment number error: "3518" -- the source form has 35918 written
       in the allotment-number field, but that's actually the patent
       reference number, not her allotment. Per BLM accession 716639,
       her actual allotment is 6475.
    3. Document type wrong: "questionnaire" -- this is a Form 5-105
       Application for Patent in Fee (Act of May 8, 1906), not a Circular
       2464 questionnaire response.
    4. Tribe field empty -- per BLM, she is Rosebud Sioux. Note the source
       NOTES correctly identify her HUSBAND as Standing Rock Sioux; Anna
       herself is Rosebud.

  BLM Patent Record (accession 716639):
    Document Type: Serial Patent
    State: South Dakota
    Issue Date: 11/5/1919
    Tribe: Rosebud Sioux
    Names On Document: BLACKBIRD, ANNA
    Indian Allot. Nr: 6475
    Total Acres: 159.15

  Source Form details (Form 5-105):
    Application sworn April 18, 1918, before E. E. Empey, Notary Public
    Stamped received Office of Indian Affairs, Feb 11 1929
    Rosebud Agency
    Land: NW Quarter Section 3, Township 28 N, Range 74 W of 5th Principal
      Meridian, South Dakota; 159.15 acres
    Applicant: Anna Blackbird, age 21, one-fourth blood, married
    Schools: Genoa Nebraska 3 yrs, Chamberlain SD 5 yrs, Tripp County SD 3 yrs
    Land value $5,600.00
    Husband: 175 acres, Standing Rock Sioux, has fee patent

CORPUS RELATIONAL FINDING: Anna Blackbird appears in THREE distinct corpus
records:
  - part1_questionnaire_017 (THIS RECORD): her 1918 Form 5-105 application
  - part1_agency_narrative_page046: Feb 1929 letter from Rosebud Supt.
    E. E. McKean to Commissioner of Indian Affairs about her case
  - part1_agency_narrative_page049: same letter, page-split duplicate

This documentary thread (1918 application -> 1929 administrative inquiry)
is exactly the kind of biographical trace the corpus exists to surface.
The thread is only visible when Name + Allotment + Tribe are normalized
across the three records — which is the methodological argument for
investing in the corrections this patch represents.

This patch is run BEFORE the bulk Form 5-105 Document type tagging,
so when that script runs it will see this record as already correctly
tagged (Document type = "Form 5-105 Application for Patent in Fee").
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
    / "part1_questionnaire_017.json"
)

CORRECTION_NOTE = (
    " | SUBSTANTIVE CORRECTION 2026-04-29: BLM accession 716639 (Serial Patent, "
    "South Dakota, 11/5/1919, Tribe = Rosebud Sioux) confirms canonical "
    "record details. Four Sonnet text-extraction errors corrected: "
    "(1) Name 'Ann Black' is OCR misread of 'Anna Blackbird' — Sonnet dropped "
    "'bird' suffix and truncated 'Anna' to 'Ann'; "
    "(2) Allotment number 3518 corrected to 6475 — the form had '35918' "
    "written in the allotment field but that is a patent reference number, "
    "not the allotment; BLM confirms allotment is 6475; "
    "(3) Document type corrected to Form 5-105 Application for Patent in Fee "
    "(Act of May 8, 1906, 34 Stat. 182) — was misclassified as 'questionnaire'; "
    "(4) Tribe added: 'Rosebud Sioux' per BLM. Original NOTES had identified "
    "her HUSBAND as Standing Rock Sioux; Anna herself is Rosebud. "
    "| RELATIONAL CORPUS DATA: Anna Blackbird appears in three distinct "
    "corpus records that together form a documentary thread. Her 1918 Form "
    "5-105 application (this record), and two records of a Feb 5, 1929 "
    "letter from Rosebud Superintendent E. E. McKean to the Commissioner "
    "of Indian Affairs (part1_agency_narrative_page046 and page049) inquiring "
    "whether the Office wanted Circular 2464 information collected for her "
    "case. The 1918→1929 thread illustrates the kind of biographical trace "
    "that becomes visible only when Name + Allotment + Tribe are normalized "
    "across the corpus."
)


def main():
    if not RECORD_PATH.exists():
        print(f"ERROR: target record not found: {RECORD_PATH}")
        sys.exit(1)

    with open(RECORD_PATH) as f:
        record = json.load(f)
    current = record["extraction"]

    expected = {
        "Name": "Ann Black",
        "Allotment number": "3518",
        "Document type": "questionnaire",
    }
    for field, expected_value in expected.items():
        actual = current.get(field)
        if actual != expected_value:
            print(f"WARNING: {field} = '{actual}', expected '{expected_value}'")
            sys.exit(1)

    # Apply corrections
    current["Name"] = "Anna Blackbird"
    current["Allotment number"] = "6475"
    current["Tribe/Reservation"] = "Rosebud Sioux"
    current["Document type"] = "Form 5-105 Application for Patent in Fee"
    current["NOTES"] = (current.get("NOTES") or "") + CORRECTION_NOTE

    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-29",
        "type": "substantive_record_correction_with_blm_and_sibling_documents",
        "method": "user_source_review_with_blm_cross_reference",
        "fields_corrected": [
            "Name", "Allotment number", "Tribe/Reservation",
            "Document type", "NOTES",
        ],
        "previous_values": {
            "Name": "Ann Black",
            "Allotment number": "3518",
            "Tribe/Reservation": current.get("Tribe/Reservation_pre_patch", "(empty)"),
            "Document type": "questionnaire",
        },
        "corrected_values": {
            "Name": "Anna Blackbird",
            "Allotment number": "6475",
            "Tribe/Reservation": "Rosebud Sioux",
            "Document type": "Form 5-105 Application for Patent in Fee",
        },
        "external_refs": {
            "BLM_accession": "716639",
            "BLM_doc_type": "Serial Patent",
            "BLM_state": "South Dakota",
            "BLM_tribe": "Rosebud Sioux",
            "BLM_issue_date": "1919-11-05",
            "BLM_total_acres": "159.15",
            "BLM_url": "https://glorecords.blm.gov/details/patent/default.aspx?accession=716639&docClass=SER",
        },
        "sibling_documents": {
            "part1_agency_narrative_page046": (
                "Feb 5, 1929 letter from Rosebud Supt. E. E. McKean to "
                "Commissioner of Indian Affairs re: Anna Blackbird, allotment "
                "6475, asking whether Office wanted Circular 2464 information "
                "collected for her case"
            ),
            "part1_agency_narrative_page049": (
                "Same letter as page046; page-split duplicate"
            ),
        },
        "user_confirmed": True,
        "extraction_failure_modes": [
            "Name OCR truncation: 'Anna Blackbird' -> 'Ann Black' (lost 'bird' "
            "suffix and truncated first name)",
            "Allotment number captured wrong number from form layout: form "
            "had patent reference '35918' in the allotment field, Sonnet "
            "captured '3518' (likely OCR digit drop), neither is her actual "
            "allotment which is 6475 per BLM",
            "Document type misrouted: Form 5-105 application classified as "
            "questionnaire because it was placed in the questionnaires/ "
            "directory by the splitter",
            "Tribe field empty despite tribal affiliation being inferable "
            "from BLM and from form's Rosebud Agency header",
        ],
        "methodological_note": (
            "This record demonstrates why entity resolution (canonical Name, "
            "Allotment, Tribe) across the corpus matters: without normalization, "
            "Anna Blackbird's 1918 application and 1929 administrative inquiry "
            "appear as unrelated records. With normalization, they form a "
            "documentary biographical thread."
        ),
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patch applied successfully.")
    print(f"  Record: part1_questionnaire_017.json")
    print(f"  Name: 'Ann Black' -> 'Anna Blackbird' (OCR truncation fix)")
    print(f"  Allotment: 3518 -> 6475 (BLM-confirmed)")
    print(f"  Tribe: (empty) -> Rosebud Sioux (BLM-confirmed)")
    print(f"  Document type: questionnaire -> Form 5-105 Application for Patent in Fee")
    print(f"  BLM cross-ref: accession 716639")
    print(f"  Sibling docs: page046, page049 (Feb 5, 1929 McKean letter)")
    print()
    print("Note: this record is now canonical; the bulk Form 5-105 tagging")
    print("will see Document type already correct and skip it.")


if __name__ == "__main__":
    main()
