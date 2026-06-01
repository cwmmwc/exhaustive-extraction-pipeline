#!/usr/bin/env python3
"""
Patch three part 4 records confirmed by Kimi v3/v4/v5 cross-reference.

1. part4_agency_narrative_003 (Oliver Guerue):
   Allotment '170. 10G9' (garbled OCR of handwritten '1069') -> '1069'
   Kimi v3, v4, v5 all confirm 1069. Sibling questionnaire
   (part4_questionnaire_003) also has 1069.

2. part4_questionnaire_001 (John Guerue):
   Allotment 'not stated' -> '1067'
   Kimi v3, v4, v5 all confirm 1067. Sibling agency_narrative
   (part4_agency_narrative_001) also has 1067.

3. part4_questionnaire_007 (Rose Cordier):
   Allotment 'not stated' -> '1200'
   Kimi v3, v4, v5 all confirm 1200. Sibling agency_narrative
   (part4_agency_narrative_011) also has 1200.

All three are direct cross-references between Sonnet and Kimi parallel
extractions of the same source PDF — no source-page render needed since
both models converge on the same answer.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {
        "filename": "part4_agency_narrative_003.json",
        "expected_name_prefix": "Oliver Guerue",
        "previous_allotment_pattern": "170. 10G9",
        "new_allotment": "1069",
        "rationale": (
            "Garbled OCR of handwritten allotment number '1069'. Kimi v3, v4, "
            "and v5 all confirm 1069. Sibling record part4_questionnaire_003 "
            "also has allotment 1069. Sonnet's '170. 10G9' is a misread — "
            "almost certainly the digit grouping plus the cursive '6' read "
            "as 'G'."
        ),
        "extraction_failure_mode": "garbled_ocr_handwritten_allotment",
    },
    {
        "filename": "part4_questionnaire_001.json",
        "expected_name_prefix": "John Guerue",
        "previous_allotment_pattern": "not stated",
        "new_allotment": "1067",
        "rationale": (
            "Sonnet missed allotment number on the questionnaire form. Kimi "
            "v3, v4, and v5 all confirm 1067. Sibling record "
            "part4_agency_narrative_001 also has allotment 1067. The same "
            "Sonnet-misses-handwritten-allotment-on-questionnaire pattern "
            "we saw in many other questionnaire records this session."
        ),
        "extraction_failure_mode": "sonnet_missed_handwritten_allotment_on_questionnaire",
    },
    {
        "filename": "part4_questionnaire_007.json",
        "expected_name_prefix": "Rose Cordier",
        "previous_allotment_pattern": "not stated",
        "new_allotment": "1200",
        "rationale": (
            "Sonnet missed allotment number on the questionnaire form. Kimi "
            "v3, v4, and v5 all confirm 1200. Sibling record "
            "part4_agency_narrative_011 also has allotment 1200."
        ),
        "extraction_failure_mode": "sonnet_missed_handwritten_allotment_on_questionnaire",
    },
]

CORRECTION_NOTE_PREFIX = (
    " | TASK 5 PART 4 KIMI CROSS-REFERENCE PATCH 2026-05-02: "
)


def patch_one(spec):
    path = EXTRACTIONS / spec["filename"]
    if not path.exists():
        return False, "NOT FOUND"

    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]

    if isinstance(e, list):
        return False, "List-shaped extraction"
    if not isinstance(e, dict):
        return False, f"Unexpected shape: {type(e).__name__}"

    actual_name = e.get("Name") or ""
    if not actual_name.startswith(spec["expected_name_prefix"]):
        return False, (
            f"Name mismatch: expected name to start with '{spec['expected_name_prefix']}', "
            f"got '{actual_name}'"
        )

    actual_allot = (e.get("Allotment number") or "").strip()
    expected_pattern = spec["previous_allotment_pattern"]
    if actual_allot != expected_pattern:
        return False, (
            f"Allotment mismatch: expected previous='{expected_pattern}', "
            f"got '{actual_allot}'"
        )

    e["Allotment number"] = spec["new_allotment"]
    e["NOTES"] = (e.get("NOTES") or "") + CORRECTION_NOTE_PREFIX + (
        f"Allotment number corrected from '{expected_pattern}' to "
        f"'{spec['new_allotment']}' per Kimi v3/v4/v5 cross-reference. "
        f"{spec['rationale']}"
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-02",
        "type": "task5_part4_kimi_cross_reference_correction",
        "method": "kimi_v3_v4_v5_parallel_extraction_unanimous",
        "fields_corrected": ["Allotment number", "NOTES"],
        "previous_allotment": expected_pattern,
        "corrected_allotment": spec["new_allotment"],
        "extraction_failure_mode": spec["extraction_failure_mode"],
        "rationale": spec["rationale"],
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    return True, f"Allotment: '{expected_pattern}' -> '{spec['new_allotment']}'"


def main():
    print("=" * 70)
    print(f"Part 4 Kimi cross-reference corrections: {len(PATCHES)} records")
    print("=" * 70)

    ok = 0
    for spec in PATCHES:
        success, msg = patch_one(spec)
        marker = "  " if success else "  ! "
        print(f"{marker}{spec['filename']:46s} {msg}")
        if success:
            ok += 1

    print()
    print(f"Patches applied: {ok}/{len(PATCHES)}")


if __name__ == "__main__":
    main()
