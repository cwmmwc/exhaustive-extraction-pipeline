#!/usr/bin/env python3
"""
Patch 4 user-verified CAT_1 records.

Each record had its identifying values verified by user research
(2026-05-04) on top of dual-model vision recovery (Sonnet vision +
Qwen vision via HPC). Records:

  - part10_questionnaire_013: Edward Hutton, Citizen Potawatomie, 863
    (Sonnet vision read allotment as '4-457N', Qwen read '44570' —
     both wrong; user verified 863)
  - part1_questionnaire_018: John Sully, Rosebud Sioux, 6470
    (Sonnet correct on allotment 6470; Qwen read '359816' — wrong)
  - part1_questionnaire_020: Louise Drapeau, Rosebud Sioux, 6493
    (Sonnet read 'NW/4-15-99-74' as allotment which is a land
     description; Qwen read 'Arapahoe' as surname which is wrong;
     user verified surname Drapeau and allotment 6493)
  - part3_questionnaire_013: Della Charbonneau, Rosebud Sioux, 1467
    (Sonnet correct on Della; Qwen read 'Bessie' — wrong; allotment
     1467 confirmed by both models and matches part 4 Charbonneau
     family cluster)

Other 21 CAT_1 records await individual user review.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {
        "filename": "part10_questionnaire_013.json",
        "name": "Edward Hutton",
        "allotment": "863",
        "tribe": "Citizen Potawatomie",
        "rationale": (
            "Sonnet vision read allotment as '4-457N'. Qwen vision read "
            "'44570'. Both wrong. User verified correct allotment is 863."
        ),
        "models_summary": (
            "Sonnet vision: name='Edward Hutton' (correct), allotment="
            "'4-457N' (wrong). Qwen vision: name='Edward Hutton' (correct), "
            "allotment='44570' (wrong)."
        ),
    },
    {
        "filename": "part1_questionnaire_018.json",
        "name": "John Sully",
        "allotment": "6470",
        "tribe": "Rosebud Sioux",
        "rationale": (
            "Sonnet vision read allotment correctly as 6470. Qwen vision "
            "read '359816' (wrong). User confirmed Sonnet's reading."
        ),
        "models_summary": (
            "Sonnet vision: name='John Sully' (correct), allotment='6470' "
            "(correct). Qwen vision: name='John Sully' (correct), "
            "allotment='359816' (wrong)."
        ),
    },
    {
        "filename": "part1_questionnaire_020.json",
        "name": "Louise Drapeau",
        "allotment": "6493",
        "tribe": "Rosebud Sioux",
        "rationale": (
            "Sonnet vision read allotment as 'NW/4-15-99-74' (land "
            "description, not an allotment number) and surname 'Drapeau' "
            "(correct). Qwen vision read surname 'Drapaceaux' (wrong "
            "garbling). User verified correct allotment is 6493 and "
            "Drapeau is the correct surname (Drapeau is a known Sioux/"
            "French family name on Rosebud)."
        ),
        "models_summary": (
            "Sonnet vision: name='Louise Drapeau' (correct), allotment="
            "'NW/4-15-99-74' (wrong — land description). Qwen vision: "
            "name='Louise Drapaceaux' (wrong garbling), allotment="
            "'NW/4 - 15 = 99-74' (wrong — same land description)."
        ),
    },
    {
        "filename": "part3_questionnaire_013.json",
        "name": "Della Charbonneau",
        "allotment": "1467",
        "tribe": "Rosebud Sioux",
        "rationale": (
            "Sonnet vision read first name as 'Della'. Qwen vision read "
            "'Bessie' (wrong). User confirmed Della. Allotment 1467 "
            "confirmed by both models and matches the part 4 Charbonneau "
            "family cluster (Alphonse Charbonneau at adjacent allotment "
            "1466, recorded at part4_questionnaire_012)."
        ),
        "models_summary": (
            "Sonnet vision: name='Della Charbonneau' (correct), allotment="
            "'1467' (correct). Qwen vision: name='Bessie Charbonneau' "
            "(first name wrong), allotment='1467' (correct)."
        ),
    },
]


def patch_one(spec):
    path = EXTRACTIONS / spec["filename"]
    if not path.exists():
        return False, "NOT FOUND"
    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        return False, "list-shaped extraction"

    previous = {
        "Name": e.get("Name", ""),
        "Allotment number": e.get("Allotment number", ""),
        "Tribe/Reservation": e.get("Tribe/Reservation", ""),
    }

    e["Name"] = spec["name"]
    e["Allotment number"] = spec["allotment"]
    e["Tribe/Reservation"] = spec["tribe"]
    e["NOTES"] = (e.get("NOTES") or "") + (
        f" | TASK 5 CAT_1 USER-VERIFIED PATCH 2026-05-04: Identified via "
        f"dual-model vision recovery (Sonnet vision + Qwen vision via HPC) "
        f"with user verification. {spec['rationale']} {spec['models_summary']}"
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat1_dual_model_vision_recovery_user_verified",
        "method": "sonnet_vision_plus_qwen_vision_with_user_verification",
        "fields_corrected": [
            "Name", "Allotment number", "Tribe/Reservation", "NOTES",
        ],
        "previous_values": previous,
        "corrected_values": {
            "Name": spec["name"],
            "Allotment number": spec["allotment"],
            "Tribe/Reservation": spec["tribe"],
        },
        "rationale": spec["rationale"],
        "models_summary": spec["models_summary"],
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"-> {spec['name']}, {spec['allotment']}, {spec['tribe']}"


def main():
    print("=" * 70)
    print(f"CAT_1 user-verified patches: {len(PATCHES)} records")
    print("=" * 70)

    ok = 0
    for spec in PATCHES:
        success, msg = patch_one(spec)
        marker = "  " if success else "  ! "
        print(f"{marker}{spec['filename']:42s} {msg}")
        if success:
            ok += 1

    print()
    print(f"Patches applied: {ok}/{len(PATCHES)}")


if __name__ == "__main__":
    main()
