#!/usr/bin/env python3
"""
Patch pine_ridge_vol1_affidavit_086 to recover Samuel Allen's name.

Background: Sonnet text-extraction captured the body of Samuel Allen's affidavit
correctly, including allotment number 1119, but failed to recover his name.
The name appears on the source page in handwriting (signature) and was missed
by text-mode OCR.

Vision recovery on 2026-04-28 produced an AGREE result:
  - Sonnet vision (anthropic API):  "Samuel Allen / 1119"
  - Qwen2.5-VL-72B (HPC):           "Samuel Allen / 1119"

Source review by user on 2026-04-28 confirmed the reading.

This is a conservative in-place patch:
  - Sets Name = "Samuel Allen"
  - Appends an IDENTITY RECOVERY note to NOTES
  - Adds a recovery_notes audit entry
  - Leaves all 16 other fields untouched (text extraction got those right)

No new files. No retirement. No manifest changes.

Source PDF: split_documents/affidavits/pine_ridge_vol1_affidavit_086.pdf
Source image: vision_recovery_sample/images/pine_ridge_vol1_affidavit_086_*.png
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
    / "pine_ridge_vol1_affidavit_086.json"
)

RECOVERY_NOTE = (
    " | IDENTITY RECOVERY 2026-04-28: Sonnet text-extraction captured the body "
    "of this affidavit (allotment 1119, mortgage history, foreclosure, fee patent "
    "date) but failed to recover the allottee's name. Name was handwritten on the "
    "source page and not picked up by text-mode OCR. Vision recovery campaign "
    "(vision_recovery_sample/) produced AGREE between Sonnet vision and "
    "Qwen2.5-VL-72B: both read 'Samuel Allen' on the source page. User confirmed "
    "the reading via source-page review. Name field patched in place; all other "
    "fields preserved from original Sonnet text extraction."
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
        print("This script expects to patch a record where Name='not stated'.")
        print("Aborting to avoid overwriting unintended data.")
        sys.exit(1)

    if current.get("Allotment number") != "1119":
        print(f"WARNING: record's Allotment number is '{current.get('Allotment number')}', expected '1119'.")
        print("This script targets pine_ridge_vol1_affidavit_086 specifically.")
        print("Aborting because record content doesn't match expected.")
        sys.exit(1)

    # Apply patch: Name only, plus recovery note appended to NOTES
    current["Name"] = "Samuel Allen"
    current["NOTES"] = current.get("NOTES", "") + RECOVERY_NOTE

    # Audit entry at record level
    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-28",
        "type": "identity_recovery",
        "method": "vision_recovery_with_user_confirmation",
        "fields_recovered": ["Name"],
        "fields_corrected": ["NOTES"],
        "source_image": "vision_recovery_sample/images/pine_ridge_vol1_affidavit_086_*.png",
        "vision_models_agreed": ["sonnet-vision", "qwen2.5-vl-72b"],
        "vision_recovery_report": "vision_recovery_sample/RECOVERY_REPORT.md",
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patch applied successfully.")
    print(f"  Record: pine_ridge_vol1_affidavit_086.json")
    print(f"  Name recovered: Samuel Allen (allot 1119, Pine Ridge)")
    print(f"  Method: vision recovery (Sonnet vision + Qwen-VL AGREE), user confirmed")
    print()
    print("Manifest unchanged (in-place patch, not a split or addition).")


if __name__ == "__main__":
    main()
