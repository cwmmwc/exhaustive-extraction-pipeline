#!/usr/bin/env python3
"""
Patch part2_questionnaire_015 to recover George Menard's identity and flag
the document for later return.

Background: Sonnet text-extraction failed on this record (Name="not stated").
Vision recovery on 2026-04-28 produced PARTIAL_AGREE between models:
  - Sonnet vision (anthropic API):  "George Munard / 548"  (vowel misread)
  - Qwen2.5-VL-72B (HPC):           "George Wencard / 548" (full surname misread)

User source-page review on 2026-04-28 confirmed the correct reading:
  - Name: George Menard (M-e-n-a-r-d, common Métis surname)
  - Allotment: 548
  - Both vision models were wrong on the surname; user's eyeball is canonical.

CRITICAL FINDING: Like part2_questionnaire_014 (Philomena Leighton), this
document is NOT a Circular 2464 questionnaire — it is a Form 5-105
"Application for a Patent in Fee" (Act of May 8, 1906, 34 Stat. 182).
The splitter routed it into questionnaires/ but it is structurally
George's prospective fee patent application.

This patch is intentionally minimal (matches Philomena Leighton pattern):
  - Set Name = "George Menard"
  - Add document-type-mismatch flag
  - Add NEEDS_REVISIT flag for full transcription pass
  - Add recovery_notes audit entry

Visible from source (for future transcription):
  - Allotment 548, Part of SE quarter
  - East 1/2 of Section 35, Township 41 N, Range 27 W of 6th Principal
    Meridian, South Dakota
  - Age 45, 1/2 blood, married
  - Schooled: Reservation School 3 yrs + Genoa, Nebraska 3 yrs
    (Genoa Indian Industrial School)
  - Land value $3,000
  - Farming, cultivates own land

Source PDF: split_documents/questionnaires/part2_questionnaire_015.pdf
Source image: vision_recovery_sample/images/part2_questionnaire_015_page-1.png
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
    / "part2_questionnaire_015.json"
)

RECOVERY_NOTE = (
    " | IDENTITY RECOVERY 2026-04-28: Sonnet text-extraction failed (Name='not "
    "stated'). Vision recovery PARTIAL_AGREE: Sonnet vision read 'George Munard', "
    "Qwen-VL read 'George Wencard'. User source-page review confirmed correct "
    "reading is 'George Menard' (M-e-n-a-r-d) — both vision models misread the "
    "surname. Document type mismatch: this is a Form 5-105 'Application for a "
    "Patent in Fee' (Act of May 8, 1906, 34 Stat. 182), NOT a Circular 2464 "
    "questionnaire response — same pattern as part2_questionnaire_014 (Philomena "
    "Leighton). NEEDS_REVISIT: source page 1 contains full handwritten answers "
    "to questions 1-11 (age 45, 1/2 blood, married, Reservation School 3 yrs + "
    "Genoa, Nebraska 3 yrs, $3,000 land value, farming on own allotment, "
    "East 1/2 Section 35, Township 41 N, Range 27 W, 6th Principal Meridian SD); "
    "additional pages may exist. Christian to return for full transcription pass."
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

    # Apply patch
    current["Name"] = "George Menard"
    current["NOTES"] = current.get("NOTES", "") + RECOVERY_NOTE

    # Audit entry
    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-28",
        "type": "identity_recovery_with_revisit_flag",
        "method": "vision_recovery_partial_agree_user_arbitrated",
        "fields_recovered": ["Name"],
        "fields_corrected": ["NOTES"],
        "source_image": "vision_recovery_sample/images/part2_questionnaire_015_page-1.png",
        "vision_model_readings": {
            "sonnet-vision": "George Munard / 548",
            "qwen2.5-vl-72b": "George Wencard / 548",
            "user_source_review": "George Menard / 548",
        },
        "vision_recovery_report": "vision_recovery_sample/RECOVERY_REPORT.md",
        "user_confirmed": True,
        "document_type_mismatch": (
            "Form 5-105 Application for Patent in Fee, NOT a Circular 2464 "
            "questionnaire response. Splitter and manifest treat as questionnaire."
        ),
        "needs_revisit": (
            "Source page 1 contains rich handwritten answers to questions 1-11 "
            "(age, blood quantum, marriage, education, farming, land description). "
            "Other 'not stated' fields await full transcription pass by Christian."
        ),
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patch applied successfully.")
    print(f"  Record: part2_questionnaire_015.json")
    print(f"  Name recovered: George Menard (allot 548, Rosebud)")
    print(f"  Both vision models had surname wrong (Munard / Wencard); user arbitration canonical")
    print(f"  Document type flagged: Form 5-105 Application, not Circular 2464 questionnaire")
    print(f"  NEEDS_REVISIT flag set: form fields await full transcription")
    print()
    print("Manifest unchanged (in-place patch, not a split or addition).")


if __name__ == "__main__":
    main()
