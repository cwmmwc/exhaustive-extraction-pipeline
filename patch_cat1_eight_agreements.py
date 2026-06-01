#!/usr/bin/env python3
"""
Patch 8 CAT_1 agreement records — both vision models converged on
name and (in 7 of 8) allotment; user supplied tribes and corrected
the one allotment outlier.

Records:
  - part10_questionnaire_002: Myrtle Last, Rosebud Sioux, 5406
  - part10_questionnaire_010: Lucius Eldridge, Citizen Potawatomie, 86
    (Sonnet read '1-2 (partially legible)', Qwen read '1/2'; user
     verified correct allotment is 86)
  - part1_questionnaire_003: W. G. Emery, Rosebud Sioux, 2902
  - part1_questionnaire_015: Mrs. Anna Shuck, Rosebud Sioux, 7394
    (4-page Form 5-105 — separate filing from q016)
  - part1_questionnaire_016: Mrs. Anna Shuck, Rosebud Sioux, 7394
    (2-page form — separate filing from q015 by same allottee)
  - part1_questionnaire_019: George Sully, Rosebud Sioux, 6465
  - part7_questionnaire_023: Lily Rice DuBray, Rosebud Sioux, 2370
  - part8_questionnaire_022: John Mullen, Rosebud Sioux, 3152

Both Anna Shuck records (q015 and q016) are real, separate filings
verified by different page counts (4 vs 2 pages) and different file
sizes — they are not duplicates.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {
        "filename": "part10_questionnaire_002.json",
        "name": "Myrtle Last",
        "allotment": "5406",
        "tribe": "Rosebud Sioux",
        "models_summary": "Both Sonnet and Qwen vision agree on name='Myrtle Last' and allotment='5406'.",
        "rationale": "Dual-model agreement; user confirmed tribe Rosebud Sioux.",
    },
    {
        "filename": "part10_questionnaire_010.json",
        "name": "Lucius Eldridge",
        "allotment": "86",
        "tribe": "Citizen Potawatomie",
        "models_summary": (
            "Both Sonnet and Qwen vision agree on name='Lucius Eldridge'. "
            "Sonnet vision read allotment as '1-2 (partially legible)'; "
            "Qwen vision read '1/2'. Both wrong. User verified correct "
            "allotment is 86."
        ),
        "rationale": "Name confirmed by both models; allotment corrected per user verification.",
    },
    {
        "filename": "part1_questionnaire_003.json",
        "name": "W. G. Emery",
        "allotment": "2902",
        "tribe": "Rosebud Sioux",
        "models_summary": "Both Sonnet and Qwen vision agree on name='W. G. Emery' (slight punctuation variation) and allotment='2902'.",
        "rationale": "Dual-model agreement; user confirmed tribe Rosebud Sioux.",
    },
    {
        "filename": "part1_questionnaire_015.json",
        "name": "Mrs. Anna Shuck",
        "allotment": "7394",
        "tribe": "Rosebud Sioux",
        "models_summary": (
            "Both Sonnet and Qwen vision agree on name='Mrs. Anna Shuck' "
            "and allotment='7394' across all 4 pages of the Form 5-105."
        ),
        "rationale": (
            "Dual-model agreement; user confirmed tribe Rosebud Sioux. "
            "This is the 4-page Form 5-105 filing; part1_questionnaire_016 "
            "is a separate 2-page filing by the same allottee (different "
            "page counts and file sizes confirm they are distinct documents)."
        ),
    },
    {
        "filename": "part1_questionnaire_016.json",
        "name": "Mrs. Anna Shuck",
        "allotment": "7394",
        "tribe": "Rosebud Sioux",
        "models_summary": (
            "Both Sonnet and Qwen vision agree on name='Mrs. Anna Shuck' "
            "and allotment='7394' across both pages."
        ),
        "rationale": (
            "Dual-model agreement; user confirmed tribe Rosebud Sioux. "
            "This is a 2-page form, separate from the 4-page Form 5-105 "
            "filing at part1_questionnaire_015 (same allottee, different "
            "filing — different page counts and file sizes confirm distinct "
            "source documents)."
        ),
    },
    {
        "filename": "part1_questionnaire_019.json",
        "name": "George Sully",
        "allotment": "6465",
        "tribe": "Rosebud Sioux",
        "models_summary": "Both Sonnet and Qwen vision agree on name='George Sully' and allotment='6465'.",
        "rationale": (
            "Dual-model agreement; user confirmed tribe Rosebud Sioux. "
            "Likely related to John Sully (Rosebud Sioux 6470, "
            "part1_questionnaire_018) — adjacent allotments suggest "
            "family relationship."
        ),
    },
    {
        "filename": "part7_questionnaire_023.json",
        "name": "Lily Rice DuBray",
        "allotment": "2370",
        "tribe": "Rosebud Sioux",
        "models_summary": (
            "Both Sonnet and Qwen vision agree on name='Lily Rice DuBray' "
            "(Qwen wrote 'Du Bray' with space) and allotment='2370'."
        ),
        "rationale": (
            "Dual-model agreement; user confirmed tribe Rosebud Sioux. "
            "DuBray family — see also part7_agency_narrative_025a (John "
            "DuBray Boyd, allotment 2338) and part7_agency_narrative_025b "
            "(Lucy DuBray Sturdevant, allotment 2341)."
        ),
    },
    {
        "filename": "part8_questionnaire_022.json",
        "name": "John Mullen",
        "allotment": "3152",
        "tribe": "Rosebud Sioux",
        "models_summary": "Both Sonnet and Qwen vision agree on name='John Mullen' and allotment='3152' across both pages.",
        "rationale": "Dual-model agreement; user confirmed tribe Rosebud Sioux.",
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
        f" | TASK 5 CAT_1 DUAL-MODEL VISION + USER VERIFICATION 2026-05-04: "
        f"{spec['rationale']} {spec['models_summary']}"
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat1_dual_model_agreement_user_tribe_confirmed",
        "method": "sonnet_vision_plus_qwen_vision_with_user_tribe_assignment",
        "fields_corrected": [
            "Name", "Allotment number", "Tribe/Reservation", "NOTES",
        ],
        "previous_values": previous,
        "corrected_values": {
            "Name": spec["name"],
            "Allotment number": spec["allotment"],
            "Tribe/Reservation": spec["tribe"],
        },
        "models_summary": spec["models_summary"],
        "rationale": spec["rationale"],
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"-> {spec['name']}, {spec['allotment']}, {spec['tribe']}"


def main():
    print("=" * 70)
    print(f"CAT_1 dual-model agreement patches: {len(PATCHES)} records")
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
