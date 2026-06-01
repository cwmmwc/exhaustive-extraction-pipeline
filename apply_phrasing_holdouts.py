#!/usr/bin/env python3
"""
Apply 3 phrasing-holdout allotment patches.

Background: The bulk allotment recovery (apply_no_pattern_patches_v2.py)
patched 48 records where NOTES contained 'Document No. NNNN' or 'document
number NNNN' patterns. Three records were held back because the regex
flagged alternate phrasings as MEDIUM/REVIEW rather than HIGH:

  - Ben Irving (vol1_aff_001):    "document reference No. 18"
  - Martha Irving (vol1_aff_005): bare "No. 63"
  - John Conry Jr (vol1_aff_030): "document numbered No. 361"

User source-page review on 2026-04-30 confirmed all three follow the same
Pine Ridge typewritten affidavit pattern as the 48 already-patched records:
the "No. NNNN" header at top right is the allotment number.

This patch applies these 3 corrections.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {
        "filename": "pine_ridge_vol1_affidavit_001.json",
        "expected_name": "Ben Irving",
        "allotment": "18",
        "phrasing": "document reference No. 18",
    },
    {
        "filename": "pine_ridge_vol1_affidavit_005.json",
        "expected_name": "Martha Irving",
        "allotment": "63",
        "phrasing": "No. 63 (bare 'No. NNNN' pattern)",
    },
    {
        "filename": "pine_ridge_vol1_affidavit_030.json",
        "expected_name": "John Conry, Jr.",
        "allotment": "361",
        "phrasing": "document numbered No. 361",
    },
]

CORRECTION_NOTE = (
    " | TASK 5 PHRASING-HOLDOUT ALLOTMENT RECOVERY 2026-04-30: Source page "
    "header 'No. NNNN' is the allotment number, captured by Sonnet in NOTES "
    "as a 'document reference' / 'document numbered' / bare 'No. NNNN' "
    "(alternate phrasings of the same Pine Ridge typewritten affidavit "
    "pattern). User source-page review confirmed. Applied alongside the "
    "48-record bulk allotment recovery batch."
)


def patch_one(spec):
    path = EXTRACTIONS / spec["filename"]
    if not path.exists():
        return False, "NOT FOUND"

    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]

    if isinstance(e, list):
        return False, "List-shaped extraction (multi-allottee bundle?). Manual review needed."
    if not isinstance(e, dict):
        return False, f"Unexpected shape: {type(e).__name__}"

    if e.get("Name") != spec["expected_name"]:
        return False, (
            f"Name mismatch: expected '{spec['expected_name']}', "
            f"got '{e.get('Name')}'"
        )

    actual = (e.get("Allotment number") or "").strip()
    if actual not in ("", "not stated"):
        return False, f"Allotment already set ('{actual}'); refusing to overwrite"

    e["Allotment number"] = spec["allotment"]
    e["NOTES"] = (e.get("NOTES") or "") + CORRECTION_NOTE

    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-30",
        "type": "task5_phrasing_holdout_allotment_recovery",
        "method": "user_source_page_review_alternate_phrasing",
        "fields_corrected": ["Allotment number", "NOTES"],
        "previous_allotment": "not stated",
        "corrected_allotment": spec["allotment"],
        "phrasing_pattern": spec["phrasing"],
        "rationale": (
            "Same Pine Ridge typewritten affidavit pattern as the 48 records "
            "in the bulk allotment recovery batch, but with alternate phrasing "
            "of the document-number reference. User source review confirmed "
            "the 'No. NNNN' header is the allotment number."
        ),
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    return True, f"Allotment: not stated -> {spec['allotment']}"


def main():
    print("=" * 70)
    print(f"Task 5 phrasing-holdout patches: {len(PATCHES)} records")
    print("=" * 70)

    ok = 0
    for spec in PATCHES:
        success, msg = patch_one(spec)
        marker = "  " if success else "  - "
        print(f"{marker}{spec['filename']:50s} {msg}")
        if success:
            ok += 1

    print()
    print(f"Patches applied: {ok}/{len(PATCHES)}")


if __name__ == "__main__":
    main()
