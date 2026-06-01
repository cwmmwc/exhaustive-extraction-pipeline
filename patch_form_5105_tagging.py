#!/usr/bin/env python3
"""
Tag 6 misrouted Form 5-105 fee patent applications.

Background: A Task 6 diagnostic on 2026-04-29 surfaced 16 records in the
corpus matching Form 5-105 indicators (Act of May 8, 1906; 34 Stat., 182;
"Application for Patent in Fee"). Categorization:

  Category A — Genuine Form 5-105 misrouted as questionnaires (9 records):
    Already corrected in pilot:
      part1_questionnaire_002 (Philomena Leighton 1917)
      part2_questionnaire_014 (Philomena Leighton later filing)
      part2_questionnaire_015 (George Menard)
    Tagged by THIS script (6 records):
      part1_questionnaire_015
      part1_questionnaire_016
      part1_questionnaire_017 (Ann Black, Standing Rock Sioux)
      part1_questionnaire_018
      part1_questionnaire_019
      part1_questionnaire_020
      part2_questionnaire_016

  Category B — Affidavits referencing prior Form 5-105 (2 records):
    pine_ridge_vol1_affidavit_085, pine_ridge_vol3_affidavit_051
    These are correctly classified as affidavits; their NOTES reference
    the allottee's earlier Form 5-105 application as background.
    NO ACTION on these.

  Category C — Agency narrative pages mentioning Form 5-105 (4 records):
    part1_agency_narrative_page046, _049, _055, _066
    These are all from a sequence of letters by Rosebud Superintendent
    E. E. McKean (Feb 1929) asking the Commissioner of Indian Affairs
    whether Circular 2464 information should be collected for specific
    allottees who had previously signed Form 5-105 applications. The
    documents themselves are agency correspondence, not Form 5-105.
    Document type "agency_narrative" is correct.
    NO ACTION on these.

This patch is intentionally minimal:
  - Sets Document type = "Form 5-105 Application for Patent in Fee"
  - Adds a NEEDS_REVISIT flag matching the pattern from Philomena/George
    patches (most fields are "not stated" and would benefit from full
    transcription in the Task 5 vision recovery campaign)
  - Adds recovery_notes audit entry

Records 015, 016, 018, 019, 020 (5 of 6) currently have Name = "not stated".
They overlap with Task 5's vision recovery candidate list. Tagging the
Document type now means the recovery campaign will know they're Form 5-105
going in and can structure patches accordingly.

Record 017 (Ann Black) has Name captured; substantive transcription is
already in NOTES. Tagging Document type makes the classification correct.

NOTABLE: Ann Black (017) is a Standing Rock Sioux whose Form 5-105 was
filed at Rosebud — same off-reservation pattern as Frank Carlow (Pine Ridge
allottee living at Crow Agency) from Task 1. The "tribal affiliation vs
filing location" disjunction is more common in this corpus than initially
expected.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

NEW_DOCTYPE = "Form 5-105 Application for Patent in Fee"

PATCHES = [
    {
        "filename": "part1_questionnaire_015.json",
        "expected_doctype": "questionnaire",
        "name_status": "not stated (vision recovery candidate)",
    },
    {
        "filename": "part1_questionnaire_016.json",
        "expected_doctype": "questionnaire",
        "name_status": "not stated (vision recovery candidate)",
    },
    {
        "filename": "part1_questionnaire_017.json",
        "expected_doctype": "questionnaire",
        "name_status": "Ann Black (Standing Rock Sioux per NOTES)",
        "additional_note": (
            "Off-reservation pattern: Ann Black is a Standing Rock Sioux "
            "(per husband's tribal affiliation in NOTES), but this Form 5-105 "
            "is filed at Rosebud Agency. Same disjunction as Frank Carlow "
            "(Pine Ridge allottee living at Crow Agency) from Task 1."
        ),
    },
    {
        "filename": "part1_questionnaire_018.json",
        "expected_doctype": "questionnaire",
        "name_status": "not stated (vision recovery candidate)",
    },
    {
        "filename": "part1_questionnaire_019.json",
        "expected_doctype": "questionnaire",
        "name_status": "not stated (vision recovery candidate)",
    },
    {
        "filename": "part1_questionnaire_020.json",
        "expected_doctype": "questionnaire",
        "name_status": "not stated (vision recovery candidate)",
    },
    {
        "filename": "part2_questionnaire_016.json",
        "expected_doctype": "questionnaire",
        "name_status": "not stated (vision recovery candidate)",
    },
]

CORPUS_PATTERN_NOTE = (
    " | DOCUMENT TYPE CORRECTION 2026-04-29: This record is a Form 5-105 "
    "Application for Patent in Fee (Act of May 8, 1906, 34 Stat., 182), NOT "
    "a Circular 2464 questionnaire response. Identified as one of 9 Form "
    "5-105 records misrouted into the questionnaires/ directory during "
    "Task 6 corpus diagnostic. Document type field updated; other fields "
    "preserved from original Sonnet extraction. NEEDS_REVISIT for full "
    "transcription via Task 5 vision recovery campaign if Name and Allotment "
    "are 'not stated'."
)


def patch_one(spec):
    path = EXTRACTIONS / spec["filename"]
    if not path.exists():
        return False, f"NOT FOUND: {path}"

    with open(path) as f:
        record = json.load(f)
    current = record["extraction"]

    if current.get("Document type") != spec["expected_doctype"]:
        return False, (
            f"Document type mismatch: expected '{spec['expected_doctype']}', "
            f"got '{current.get('Document type')}'. Aborting this record."
        )

    current["Document type"] = NEW_DOCTYPE
    current["NOTES"] = (current.get("NOTES") or "") + CORPUS_PATTERN_NOTE

    audit = {
        "date": "2026-04-29",
        "type": "document_type_correction_form_5105",
        "method": "task6_diagnostic_with_notes_content_review",
        "fields_corrected": ["Document type", "NOTES"],
        "previous_value": spec["expected_doctype"],
        "corrected_value": NEW_DOCTYPE,
        "name_status": spec["name_status"],
        "user_confirmed": True,
        "corpus_pattern": (
            "One of 9 Form 5-105 records misrouted into questionnaires/. "
            "3 already corrected in pilot (Philomena Leighton 1917, "
            "Philomena Leighton later, George Menard); 6 tagged in this batch."
        ),
    }
    if "additional_note" in spec:
        audit["additional_note"] = spec["additional_note"]

    record.setdefault("recovery_notes", []).append(audit)

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    return True, f"  Tagged: '{spec['expected_doctype']}' -> '{NEW_DOCTYPE}'"


def main():
    print("Form 5-105 misrouting correction: 6 records")
    print("=" * 60)

    successes = 0
    for spec in PATCHES:
        print(f"\n[{spec['filename']}]")
        ok, msg = patch_one(spec)
        print(msg)
        if ok:
            successes += 1
        else:
            print(f"  STATUS: FAILED")

    print()
    print("=" * 60)
    print(f"Patches applied: {successes}/{len(PATCHES)}")
    print()
    print("Manifest unchanged (in-place patches only).")


if __name__ == "__main__":
    main()
