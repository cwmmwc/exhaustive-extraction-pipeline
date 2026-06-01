#!/usr/bin/env python3
"""
Normalize Tribe field for 5 part 4 questionnaires.

Sonnet captured Tribe='not stated' for these records because it failed to
extract the tribal affiliation from the questionnaire forms. The matching
agency narrative records (paired by allotment number) all show 'Rosebud',
and Kimi v3/v4/v5 entities for the same allottees show Rosebud Sioux.

Setting Tribe='Rosebud Sioux' (matching the existing questionnaire
convention used in q001, q007, q010, q011, rather than the plainer
'Rosebud' used in agency_narratives).

Records to patch:
  - part4_questionnaire_002 (Martha Guerue Richards, allotment 1068)
  - part4_questionnaire_004 (Louise Beauvais Young, allotment 1071)
  - part4_questionnaire_006 (Frank Arcoren, allotment 1197)
  - part4_questionnaire_008 (John Cordier, allotment 1201)
  - part4_questionnaire_009 (Alexander Whipple, allotment 1258)

These are all Sonnet form-field extraction failures (tribe field on the
questionnaire was either blank, handwritten, or otherwise unreadable to
Sonnet's text extraction). Cross-reference confirmation comes from:
  - Sibling agency narrative (same allotment number, says 'Rosebud')
  - Kimi v3, v4, v5 entities (all show Rosebud Sioux)
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {
        "filename": "part4_questionnaire_002.json",
        "expected_name_prefix": "Martha Guerue",
        "allotment": "1068",
    },
    {
        "filename": "part4_questionnaire_004.json",
        "expected_name_prefix": "Louise Beauvais Young",
        "allotment": "1071",
    },
    {
        "filename": "part4_questionnaire_006.json",
        "expected_name_prefix": "Frank Arcoren",
        "allotment": "1197",
    },
    {
        "filename": "part4_questionnaire_008.json",
        "expected_name_prefix": "John Cordier",
        "allotment": "1201",
    },
    {
        "filename": "part4_questionnaire_009.json",
        "expected_name_prefix": "Alexander Whipple",
        "allotment": "1258",
    },
]

NEW_TRIBE = "Rosebud Sioux"

NOTE = (
    " | TASK 5 PART 4 TRIBE NORMALIZATION 2026-05-02: Tribe field updated "
    "from 'not stated' to 'Rosebud Sioux' per cross-reference with sibling "
    "agency narrative record (same allotment number, confirms Rosebud) and "
    "Kimi v3/v4/v5 entities (all confirm Rosebud Sioux). Sonnet failed to "
    "extract the tribe from the questionnaire form. Using 'Rosebud Sioux' "
    "convention to match other part 4 questionnaire records (q001, q007, "
    "q010, q011) rather than the plainer 'Rosebud' used in the agency "
    "narratives."
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

    actual_name = e.get("Name") or ""
    if not actual_name.startswith(spec["expected_name_prefix"]):
        return False, (
            f"Name mismatch: expected starting with "
            f"'{spec['expected_name_prefix']}', got '{actual_name}'"
        )

    actual_tribe = (e.get("Tribe/Reservation") or "").strip()
    if actual_tribe not in ("", "not stated"):
        return False, (
            f"Tribe already set ('{actual_tribe}'); "
            f"refusing to overwrite"
        )

    e["Tribe/Reservation"] = NEW_TRIBE
    e["NOTES"] = (e.get("NOTES") or "") + NOTE

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-02",
        "type": "task5_part4_tribe_normalization",
        "method": "sibling_agency_narrative_and_kimi_cross_reference",
        "fields_corrected": ["Tribe/Reservation", "NOTES"],
        "previous_tribe": actual_tribe or "(empty)",
        "corrected_tribe": NEW_TRIBE,
        "allotment_number": spec["allotment"],
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"Tribe: '{actual_tribe or '(empty)'}' -> '{NEW_TRIBE}'"


def main():
    print("=" * 70)
    print(f"Part 4 questionnaire tribe normalization: {len(PATCHES)} records")
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
