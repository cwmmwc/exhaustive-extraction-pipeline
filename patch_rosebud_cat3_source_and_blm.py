#!/usr/bin/env python3
"""
Patch 2 Rosebud-area CAT_3 records resolved via source review and
BLM GLO records.

  - part7_questionnaire_022: Thomas Wright, allotment 2357, Rosebud Sioux.
    The patents database had multiple Thomas Wrights at Rosebud; the
    allotment was disambiguated by user source-page review of part 7
    page 59 (the questionnaire form itself).

  - part9_agency_narrative_017: Helena Larvie, allotment 3432, Rosebud
    Sioux. Not present in the federal-register-app patents database.
    Allotment verified via BLM General Land Office records, accession
    SD2610__.247 (https://glorecords.blm.gov/details/patent/default.aspx
    ?accession=SD2610__.247&docClass=STA). Distinct provenance from the
    other CAT_3 backfills, recorded accordingly.

These complete the Rosebud-area CAT_3 group except for
part9_questionnaire_010 (Hazel), whose last name remains under review.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {
        "stem": "part7_questionnaire_022",
        "name": "Thomas Wright",
        "allotment": "2357",
        "source_type": "task5_cat3_backfill_source_review_disambiguation",
        "source_description": (
            "Allotment 2357 disambiguated by user source-page review of "
            "part 7 page 59 (the Circular 2464 questionnaire form). The "
            "federal-register-app patents database has multiple Thomas "
            "Wrights at Rosebud; the source page provided the specific "
            "allotment number for this individual."
        ),
        "source_url": None,
    },
    {
        "stem": "part9_agency_narrative_017",
        "name": "Helena Larvie",
        "allotment": "3432",
        "source_type": "task5_cat3_backfill_blm_glo_records",
        "source_description": (
            "Allotment 3432 verified via BLM General Land Office records, "
            "accession SD2610__.247. Helena Larvie is NOT present in the "
            "federal-register-app patents database; the BLM GLO records "
            "are the source for this allotment. This is a distinct "
            "provenance from the patents-database backfills."
        ),
        "source_url": (
            "https://glorecords.blm.gov/details/patent/default.aspx"
            "?accession=SD2610__.247&docClass=STA"
        ),
    },
]


def patch_one(spec):
    path = EXTRACTIONS / f"{spec['stem']}.json"
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

    e["Allotment number"] = spec["allotment"]
    e["Tribe/Reservation"] = "Rosebud Sioux"

    tribe_norm_note = ""
    if previous["Tribe/Reservation"] not in ("Rosebud Sioux", ""):
        tribe_norm_note = (
            f" TRIBE NORMALIZATION: previous label "
            f"'{previous['Tribe/Reservation']}' normalized to "
            f"'Rosebud Sioux'."
        )

    note_addition = (
        f" | TASK 5 CAT_3 BACKFILL 2026-05-04: Allotment {spec['allotment']}. "
        f"{spec['source_description']}{tribe_norm_note}"
    )
    e["NOTES"] = (e.get("NOTES") or "") + note_addition

    recovery_note = {
        "date": "2026-05-04",
        "type": spec["source_type"],
        "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
        "previous_values": previous,
        "corrected_values": {
            "Allotment number": spec["allotment"],
            "Tribe/Reservation": "Rosebud Sioux",
        },
        "source_description": spec["source_description"],
        "user_confirmed": True,
    }
    if spec["source_url"]:
        recovery_note["source_url"] = spec["source_url"]

    record.setdefault("recovery_notes", []).append(recovery_note)

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"{spec['name']}, allot={spec['allotment']}, Rosebud Sioux"


def main():
    print("=" * 70)
    print(f"Rosebud CAT_3 — source-review + BLM patches: {len(PATCHES)} records")
    print("=" * 70)

    ok = 0
    for spec in PATCHES:
        success, msg = patch_one(spec)
        marker = "  " if success else "  ! "
        print(f"{marker}{spec['stem']:38s} {msg}")
        if success:
            ok += 1

    print()
    print(f"Patched: {ok}/{len(PATCHES)}")
    print()
    print("Still pending in Rosebud CAT_3 group:")
    print("  part9_questionnaire_010   Hazel — last name under review")


if __name__ == "__main__":
    main()
