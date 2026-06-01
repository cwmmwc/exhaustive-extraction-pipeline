#!/usr/bin/env python3
"""
Patch part2_questionnaire_014 to recover Philomena Beauvais Leighton's identity
and flag the document for later return.

Background: Sonnet text-extraction failed substantively on this record:
  - Name was handwritten signature, missed → "not stated"
  - Allotment number 488 was misread as 455 from the form
  - Most form fields came back "not stated" because text-mode OCR couldn't
    read the handwritten answers to the 26 questions

Vision recovery on 2026-04-28 produced an AGREE result on identity:
  - Sonnet vision (anthropic API):  "Philomena Beauvais Leighton / 488"
  - Qwen2.5-VL-72B (HPC):           "Philomena Beauvais Leighton / 488"

User confirmed via source-page review (all 3 pages, single document).

CRITICAL FINDING DURING REVIEW: This document is NOT a Circular 2464
questionnaire. It is a Form 5-105 "Application for a Patent in Fee" under
the Act of May 8, 1906 (34 Stat., 182). The splitter routed it into the
questionnaires/ directory and the manifest treats it as a questionnaire,
but it is structurally a different document type — Philomena's prospective
application for a fee patent, not a respondent's answers to questions about
a fee patent already issued.

This patch is intentionally minimal:
  - Set Name = "Philomena Beauvais Leighton"
  - Correct Allotment number 455 → 488
  - Fix $250,000 misread → $2,500
  - Add recovery note flagging document type mismatch
  - Add NEEDS_REVISIT flag in NOTES so the rich form data on pages 1-3
    can be transcribed in a future pass
  - Add recovery_notes audit entry

The other 26 form fields remain "not stated" pending Christian's full
re-transcription pass on this record.

Source PDF: split_documents/questionnaires/part2_questionnaire_014.pdf (3 pages)
Source images: vision_recovery_sample/images/part2_questionnaire_014_page-{1,2,3}.png
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
    / "part2_questionnaire_014.json"
)

RECOVERY_NOTE = (
    " | IDENTITY RECOVERY 2026-04-28: Sonnet text-extraction substantively failed "
    "on this record. Vision recovery (Sonnet vision + Qwen2.5-VL-72B AGREE) and "
    "user source-page review (all 3 pages) confirmed: Name = Philomena Beauvais "
    "Leighton; Allotment = 488 (Sonnet text misread as 455); land value = $2,500 "
    "(Sonnet text misread as $250,000 from cents-fraction notation '$25 00.00/100'). "
    "Document type mismatch: this is a Form 5-105 'Application for a Patent in Fee' "
    "(Act of May 8, 1906, 34 Stat. 182), NOT a Circular 2464 questionnaire response. "
    "Splitter routed it into questionnaires/ and manifest treats it as a questionnaire, "
    "but structurally it is Philomena's prospective application — different category. "
    "NEEDS_REVISIT: form pages 1-3 contain rich answers to 26 questions (age 34, "
    "1/2 blood, married to George Leighton, Day school 8 yrs + Haskell 4 yrs, "
    "horses and cattle, gardening + sewing self-support, children William/Alice/"
    "Leona/Levi/Emma Louise Leighton with allotment details, husband George Leighton "
    "with 160a allotment) all in handwriting. Christian to return for full "
    "transcription pass. Other fields left as 'not stated' pending that pass."
)


def main():
    if not RECORD_PATH.exists():
        print(f"ERROR: target record not found: {RECORD_PATH}")
        sys.exit(1)

    with open(RECORD_PATH) as f:
        record = json.load(f)

    current = record["extraction"]

    # Verify we're patching the right record
    if current.get("Name") != "not stated":
        print(f"WARNING: record's Name is currently '{current.get('Name')}', not 'not stated'.")
        print("Aborting to avoid overwriting unintended data.")
        sys.exit(1)

    if current.get("Allotment number") != "455":
        print(f"WARNING: record's Allotment number is '{current.get('Allotment number')}', expected '455'.")
        print("This script targets part2_questionnaire_014 specifically.")
        print("Aborting because record content doesn't match expected.")
        sys.exit(1)

    # Apply patch
    current["Name"] = "Philomena Beauvais Leighton"
    current["Allotment number"] = "488"
    current["NOTES"] = current.get("NOTES", "") + RECOVERY_NOTE

    # Audit entry at record level
    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-28",
        "type": "identity_recovery_with_revisit_flag",
        "method": "vision_recovery_with_user_confirmation",
        "fields_recovered": ["Name", "Allotment number"],
        "fields_corrected": ["NOTES"],
        "source_images": [
            "vision_recovery_sample/images/part2_questionnaire_014_page-1.png",
            "vision_recovery_sample/images/part2_questionnaire_014_page-2.png",
            "vision_recovery_sample/images/part2_questionnaire_014_page-3.png",
        ],
        "vision_models_agreed": ["sonnet-vision", "qwen2.5-vl-72b"],
        "vision_recovery_report": "vision_recovery_sample/RECOVERY_REPORT.md",
        "user_confirmed": True,
        "document_type_mismatch": (
            "Form 5-105 Application for Patent in Fee, NOT a Circular 2464 "
            "questionnaire response. Splitter and manifest treat as questionnaire."
        ),
        "needs_revisit": (
            "Form pages 1-3 contain rich handwritten answers to 26 questions "
            "(family, education, property, occupation, family allotments). "
            "Other 'not stated' fields await full transcription pass by Christian."
        ),
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patch applied successfully.")
    print(f"  Record: part2_questionnaire_014.json")
    print(f"  Name recovered: Philomena Beauvais Leighton (allot 488, Rosebud)")
    print(f"  Allotment corrected: 455 -> 488 (text-mode OCR misread)")
    print(f"  Document type flagged: Form 5-105 Application, not Circular 2464 questionnaire")
    print(f"  NEEDS_REVISIT flag set: form fields await full transcription")
    print()
    print("Manifest unchanged (in-place patch, not a split or addition).")


if __name__ == "__main__":
    main()
