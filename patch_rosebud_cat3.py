#!/usr/bin/env python3
"""
Batch patch 19 Rosebud-area CAT_3 records.

Allotment numbers sourced from Christian's federal-register-app patents
database (https://federal-register-app-996830241007.us-east1.run.app/patents),
research 2026-05-04.

All 19 records get Tribe/Reservation normalized to 'Rosebud Sioux'.
Some were previously labeled just 'Rosebud' (Group B) or 'Rosebud
Agency' (Lucy Kincaid) — these are normalized to the canonical
'Rosebud Sioux' tribe label.

CAT_3 = Sonnet captured the Name but not the Allotment. This batch
backfills the allotment.

Two same-person cases handled with cross-references:
  - Josephine Collins appears in two records (part2_agency_narrative_page059
    and part6_agency_narrative_page046), both allotment 2862.5. Same
    person; both records cross-referenced.
  - George Menard at part2_questionnaire_017 (allotment 548) is the
    same person as George Menard at part2_questionnaire_016 (allotment
    548, patched earlier 2026-05-04). Both records cross-referenced.

3 records NOT in this batch (pending):
  - part9_questionnaire_010 (Hazel) — last name illegible, awaiting
    source review
  - part7_questionnaire_022 (Thomas Wright) — multiple Thomas Wrights
    at Rosebud in the patents database, awaiting source review for
    disambiguation
  - part9_agency_narrative_017 (Helena Larvie) — not found in patents
    database; will be handled separately with the option-3 convention
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {"stem": "part1_questionnaire_004", "name": "William Z. Emery", "allotment": "2902"},
    {"stem": "part1_questionnaire_007", "name": "Alice Cunningham", "allotment": "844"},
    {"stem": "part1_questionnaire_008", "name": "Rudolph D. Anderson", "allotment": "4220"},
    {"stem": "part1_questionnaire_009", "name": "Louise Anderson Ernst", "allotment": "12.5"},
    {"stem": "part1_questionnaire_012", "name": "John B. DeCory", "allotment": "3"},
    {"stem": "part1_questionnaire_029", "name": "Belle Bonser Harris", "allotment": "143"},
    {"stem": "part2_questionnaire_008", "name": "Ada McCloskey Whipple", "allotment": "414"},
    {"stem": "part2_questionnaire_021", "name": "Ida Houston Roubideaux", "allotment": "5480"},
    {"stem": "part3_questionnaire_007", "name": "Rose Cordier Setter", "allotment": "1200"},
    {"stem": "part6_questionnaire_001", "name": "Henry Benedict Emery", "allotment": "2903"},
    {"stem": "part8_questionnaire_005", "name": "Maude Utterback Estes", "allotment": "2434"},
    {"stem": "part9_questionnaire_001", "name": "Julia Turgeon Grauel", "allotment": "3154"},
    {"stem": "part3_agency_narrative_001", "name": "John Guerue", "allotment": "1062"},
    {"stem": "part6_questionnaire_013", "name": "Ruth Josephine Smith Point At Him", "allotment": "521"},
    {"stem": "part1_questionnaire_014", "name": "Lucy Kincaid", "allotment": "474"},
    {
        "stem": "part9_questionnaire_005",
        "name": "Susie McCloskey Whipple",
        "allotment": "3212",
    },
    # Two Josephine Collins records — same person, cross-referenced
    {
        "stem": "part2_agency_narrative_page059",
        "name": "Josephine Collins",
        "allotment": "2862.5",
        "cross_ref": (
            "Josephine Collins also appears at part6_agency_narrative_page046 "
            "(same person, same allotment 2862.5). Two agency narrative "
            "records referencing the same allottee."
        ),
    },
    {
        "stem": "part6_agency_narrative_page046",
        "name": "Josephine Collins",
        "allotment": "2862.5",
        "cross_ref": (
            "Josephine Collins also appears at part2_agency_narrative_page059 "
            "(same person, same allotment 2862.5). Two agency narrative "
            "records referencing the same allottee."
        ),
    },
    # George Menard q017 — same person as q016
    {
        "stem": "part2_questionnaire_017",
        "name": "George Menard",
        "allotment": "548",
        "cross_ref": (
            "George Menard at allotment 548 is the same person as George "
            "Menard at part2_questionnaire_016 (also allotment 548, patched "
            "2026-05-04 via dual-model vision recovery). Two corpus records "
            "for the same allottee."
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

    cross_ref_str = ""
    if spec.get("cross_ref"):
        cross_ref_str = f" CROSS-REFERENCE: {spec['cross_ref']}"

    tribe_norm_note = ""
    if previous["Tribe/Reservation"] not in ("Rosebud Sioux", ""):
        tribe_norm_note = (
            f" TRIBE NORMALIZATION: previous label "
            f"'{previous['Tribe/Reservation']}' normalized to canonical "
            f"'Rosebud Sioux'."
        )

    note_addition = (
        f" | TASK 5 CAT_3 BACKFILL 2026-05-04 (patents database): "
        f"Allotment {spec['allotment']} sourced from federal-register-app "
        f"patents database (Christian's research, 2026-05-04). CAT_3 "
        f"record — Sonnet text extraction captured the allottee Name but "
        f"not the Allotment number; this patch backfills the allotment."
        f"{tribe_norm_note}{cross_ref_str}"
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
            "Tribe/Reservation": "Rosebud Sioux",
        },
        "cross_reference": spec.get("cross_ref", ""),
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"{spec['name']}, allot={spec['allotment']}, Rosebud Sioux"


def main():
    print("=" * 70)
    print(f"Rosebud CAT_3 backfill: {len(PATCHES)} records")
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
    print("Pending (not in this batch):")
    print("  part9_questionnaire_010   Hazel — last name illegible, needs source review")
    print("  part7_questionnaire_022   Thomas Wright — needs source review to disambiguate")
    print("  part9_agency_narrative_017 Helena Larvie — not in patents database")


if __name__ == "__main__":
    main()
