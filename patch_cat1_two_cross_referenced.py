#!/usr/bin/env python3
"""
Patch 2 CAT_1 records using cross-references already established
elsewhere in the corpus.

Both records had Sonnet vision reading the right name and Qwen
disagreeing or partially garbling. The cross-references resolve
the disagreement in Sonnet's favor:

  - part3_questionnaire_012: Alphonse Charbonneau, Rosebud Sioux, 1466
    Sonnet vision: 'Alphonse Charbonneau' / 1466 (correct)
    Qwen vision (page 1): 'Alphonse Chabonneau' / 1466
    Qwen vision (page 2): 'Alphonse M Charbonneau' / 1466
    Cross-reference: Alphonse Charbonneau is also documented at
    part4_questionnaire_012 (allotment 1466, Rosebud Sioux confirmed
    via that record's full content recovery 2026-05-02).

  - part7_questionnaire_020: Lucy DuBray (Sturdevant), Rosebud Sioux, 2341
    Sonnet vision: 'Lucy Dubray Sturdevant' / 2341 (correct)
    Qwen vision (page 1): 'Ducey Aubrey Murdewant' / 2341 (garbled name)
    Qwen vision (page 2): 'Ducy Dubray Sturdevant' / null
    Cross-reference: Lucy DuBray (Sturdevant) is also documented at
    part7_agency_narrative_025b (allotment 2341, Rosebud Sioux,
    paired with John DuBray (Boyd) at allotment 2338 in the bundle
    split 2026-05-03).
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {
        "filename": "part3_questionnaire_012.json",
        "name": "Alphonse Charbonneau",
        "allotment": "1466",
        "tribe": "Rosebud Sioux",
        "models_summary": (
            "Sonnet vision: 'Alphonse Charbonneau' / 1466 (correct). "
            "Qwen vision page 1: 'Alphonse Chabonneau' / 1466 (mis-spelled "
            "name; correct allotment). Qwen vision page 2: 'Alphonse M "
            "Charbonneau' / 1466 (correct on page 2)."
        ),
        "cross_reference": (
            "part4_questionnaire_012 (Alphonse Charbonneau, allotment "
            "1466, Rosebud Sioux — full content recovery via Sonnet "
            "vision on 2026-05-02 with user source-page verification "
            "of substantive details). This part 3 record is a separate "
            "appearance of Alphonse Charbonneau in the corpus."
        ),
    },
    {
        "filename": "part7_questionnaire_020.json",
        "name": "Lucy DuBray (Sturdevant)",
        "allotment": "2341",
        "tribe": "Rosebud Sioux",
        "models_summary": (
            "Sonnet vision: 'Lucy Dubray Sturdevant' / 2341 (correct). "
            "Qwen vision page 1: 'Ducey Aubrey Murdewant' / 2341 (badly "
            "garbled name; correct allotment). Qwen vision page 2: "
            "'Ducy Dubray Sturdevant' / null (closer name reading; no "
            "allotment captured)."
        ),
        "cross_reference": (
            "part7_agency_narrative_025b (Lucy DuBray (Sturdevant), "
            "allotment 2341, Rosebud Sioux — created via multi-allottee "
            "bundle split on 2026-05-03 with full Sonnet vision content "
            "recovery and user source-page confirmation). Sibling: John "
            "DuBray (Boyd) at allotment 2338 (part7_agency_narrative_025a). "
            "This questionnaire is a separate appearance of Lucy DuBray "
            "Sturdevant in the corpus."
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
        f" | TASK 5 CAT_1 PATCH 2026-05-04: Identified via dual-model "
        f"vision recovery (Sonnet vision + Qwen vision via HPC) with "
        f"cross-reference confirmation. {spec['models_summary']} "
        f"CROSS-REFERENCE: {spec['cross_reference']}"
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat1_dual_model_with_corpus_cross_reference",
        "method": "sonnet_vision_plus_qwen_vision_plus_corpus_cross_reference",
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
        "cross_reference": spec["cross_reference"],
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"-> {spec['name']}, {spec['allotment']}, {spec['tribe']}"


def main():
    print("=" * 70)
    print(f"CAT_1 cross-reference patches: {len(PATCHES)} records")
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
