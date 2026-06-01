#!/usr/bin/env python3
"""
Patch 6 Crow Creek / Big Bend District CAT_3 records.

Allotments from Christian's research (2026-05-04).

  part11_agency_narrative_005  Joe St John       -> 547, Crow Creek Sioux
  part11_agency_narrative_006  Peter St John     -> 546, Crow Creek Sioux
  part11_questionnaire_007     Cleveland Fallis  -> 928, Lower Brule
  part12_agency_narrative_001  William Walker    -> 18, Crow Creek Sioux
  part12_questionnaire_001     William Walker    -> 18, Crow Creek Sioux
  part12_questionnaire_002     William Walker    -> 18, Crow Creek Sioux

Notes:

1. Cleveland Fallis is LOWER BRULE, not Crow Creek Sioux. The corpus
   had him labeled 'Big Bend District'. Big Bend District is an
   administrative district associated with the Crow Creek Reservation,
   but Cleveland Fallis is a Lower Brule allottee — his tribe is set
   to 'Lower Brule' per Christian's research, overriding the district
   label.

2. The three William Walker records (part12_agency_narrative_001,
   part12_questionnaire_001, part12_questionnaire_002) are the SAME
   person — confirmed by Christian. They span consecutive pages 2-5 of
   part 12 (a questionnaire across pages 2-3, an agency narrative page
   4, a second questionnaire page 5). All three get allotment 18 and
   are cross-referenced to each other.

3. 'Big Bond District' (the extraction's tribe label on
   part11_agency_narrative_005, Joe St John) is an extraction error
   for 'Big Bend District'. The patch sets the correct tribe
   (Crow Creek Sioux) and the error is noted.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

WALKER_RECORDS = [
    "part12_agency_narrative_001",
    "part12_questionnaire_001",
    "part12_questionnaire_002",
]

PATCHES = [
    {
        "stem": "part11_agency_narrative_005",
        "name": "Joe St John",
        "allotment": "547",
        "tribe": "Crow Creek Sioux",
        "cross_ref": "",
        "extra_note": (
            "The extraction's tribe label 'Big Bond District' is an error "
            "for 'Big Bend District' (a district of the Crow Creek "
            "Reservation). Tribe set to Crow Creek Sioux."
        ),
    },
    {
        "stem": "part11_agency_narrative_006",
        "name": "Peter St John",
        "allotment": "546",
        "tribe": "Crow Creek Sioux",
        "cross_ref": (
            "Joe St John (part11_agency_narrative_005, allotment 547) "
            "appears at an adjacent allotment number — possibly related."
        ),
        "extra_note": "",
    },
    {
        "stem": "part11_questionnaire_007",
        "name": "Cleveland Fallis",
        "allotment": "928",
        "tribe": "Lower Brule",
        "cross_ref": "",
        "extra_note": (
            "TRIBE: Cleveland Fallis is LOWER BRULE, not Crow Creek Sioux. "
            "The corpus extraction labeled him 'Big Bend District' (a "
            "district associated with the Crow Creek Reservation), but "
            "his tribal affiliation is Lower Brule per Christian's "
            "research. The district label is administrative; the tribe "
            "field carries his actual affiliation."
        ),
    },
    {
        "stem": "part12_agency_narrative_001",
        "name": "William Walker",
        "allotment": "18",
        "tribe": "Crow Creek Sioux",
        "cross_ref": (
            "Same William Walker as part12_questionnaire_001 (pages 2-3) "
            "and part12_questionnaire_002 (page 5). Three corpus records "
            "for one allottee, spanning consecutive pages 2-5 of part 12. "
            "This record is the agency narrative (page 4)."
        ),
        "extra_note": "",
    },
    {
        "stem": "part12_questionnaire_001",
        "name": "William Walker",
        "allotment": "18",
        "tribe": "Crow Creek Sioux",
        "cross_ref": (
            "Same William Walker as part12_agency_narrative_001 (page 4) "
            "and part12_questionnaire_002 (page 5). Three corpus records "
            "for one allottee. This record is the questionnaire "
            "(pages 2-3)."
        ),
        "extra_note": "",
    },
    {
        "stem": "part12_questionnaire_002",
        "name": "William Walker",
        "allotment": "18",
        "tribe": "Crow Creek Sioux",
        "cross_ref": (
            "Same William Walker as part12_agency_narrative_001 (page 4) "
            "and part12_questionnaire_001 (pages 2-3). Three corpus "
            "records for one allottee. This record is the second "
            "questionnaire page (page 5)."
        ),
        "extra_note": "",
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
    e["Tribe/Reservation"] = spec["tribe"]

    tribe_norm_note = ""
    if previous["Tribe/Reservation"] not in (spec["tribe"], ""):
        tribe_norm_note = (
            f" TRIBE: previous label '{previous['Tribe/Reservation']}' "
            f"updated to '{spec['tribe']}'."
        )

    cross_ref_note = ""
    if spec["cross_ref"]:
        cross_ref_note = f" CROSS-REFERENCE: {spec['cross_ref']}"

    extra = ""
    if spec["extra_note"]:
        extra = f" {spec['extra_note']}"

    note_addition = (
        f" | TASK 5 CAT_3 BACKFILL 2026-05-04 (patents database): "
        f"Allotment {spec['allotment']} sourced from federal-register-app "
        f"patents database (Christian's research, 2026-05-04). CAT_3 "
        f"record — Sonnet text extraction captured the allottee Name but "
        f"not the Allotment number.{tribe_norm_note}{extra}{cross_ref_note}"
    )
    e["NOTES"] = (e.get("NOTES") or "") + note_addition

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat3_backfill_patents_database",
        "method": "user_research_federal_register_app_patents_database",
        "source_url": "https://federal-register-app-996830241007.us-east1.run.app/patents",
        "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
        "previous_values": previous,
        "corrected_values": {
            "Allotment number": spec["allotment"],
            "Tribe/Reservation": spec["tribe"],
        },
        "cross_reference": spec["cross_ref"],
        "extra_note": spec["extra_note"],
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"{spec['name']}, allot={spec['allotment']}, {spec['tribe']}"


def main():
    print("=" * 70)
    print(f"Crow Creek / Big Bend District CAT_3 backfill: {len(PATCHES)} records")
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


if __name__ == "__main__":
    main()
