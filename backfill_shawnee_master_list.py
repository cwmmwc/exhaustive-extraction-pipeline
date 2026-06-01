#!/usr/bin/env python3
"""
Backfill 10 Shawnee Indian Agency master list records.

Per triage results (2026-05-04), 10 master list rows have corresponding
affidavit/questionnaire records in the corpus with allotment + actual
tribe captured. This script backfills the master list records:
  - Allotment number from the matched record
  - Tribe/Reservation = actual tribe (e.g., 'Citizen Potawatomie'),
    NOT 'Shawnee' which is the agency context (Shawnee Indian Agency
    administered Citizen Potawatomie, Iowa, Sac & Fox, etc.)
  - NOTES enriched with cross-reference to the matched record AND
    explanation of the agency-vs-tribe distinction

Schema decision (option A, 2026-05-04):
  Tribe/Reservation field carries the ACTUAL TRIBE.
  Agency context (Shawnee Indian Agency) is preserved in NOTES.
  Agency is recoverable from the part10_shawnee_*.json filename pattern.

Backfilled records:
  Row 12 Lucius Eldridge      → 86, Citizen Potawatomie
  Row 18 Hannah Hardin        → 42, Citizen Potawatomie
  Row 19 Edward Hutton        → 863, Citizen Potawatomie
  Row 27 Albion Ogee          → 1080, Citizen Potawatomie
  Row 31 Olive Shepard        → 862, Citizen Potawatomie
  Row 33 Nicholas Trombla     → 484, Citizen Potawatomie
  Row 34 Rosa Vanderbloom     → 313, Citizen Potawatomie
  Row 35 Viola Wallace        → 15609, Citizen Potawatomie

Plus 2 manually-verified name-collision rows that the triage script
flagged but should be backfilled (verified by user/Claude as same person
with minor name variation):
  Row 3 Belle Bino Bruno      → 110, Citizen Potawatomie
                                 (matches part10_affidavit_003 'Belle
                                 Binia Bruno' — middle name variant)
  Row 30 Addie E. Payne       → 168, Citizen Potawatomie
                                 (matches part10_questionnaire_015 'Mrs.
                                 Addie Easton Payne' — fuller name)

Note on Row 27 Albion Ogee: triage found 2 exact matches
(part10_affidavit_005 and part10_questionnaire_014). Backfill from
part10_affidavit_005 (the patched record). Cross-reference notes both.

Note on Row 33 Nicholas Trombla: triage found 2 exact matches
(part11_affidavit_001 and part11_questionnaire_001). Backfill from
part11_affidavit_001 (the patched record). Cross-reference notes both.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

BACKFILLS = [
    {
        "master_stem": "part10_shawnee_03",
        "name": "Belle Binia Bruno",
        "allotment": "110",
        "tribe": "Citizen Potawatomie",
        "matched_record": "part10_affidavit_003",
        "name_variant_note": (
            "Master list reads 'Belle Bino Bruno'; corpus affidavit "
            "captures her as 'Belle Binia Bruno'. Same person — middle "
            "name handwriting variant. User verified the correct middle "
            "name is 'Binia'."
        ),
        "cross_refs": ["part10_affidavit_003"],
    },
    {
        "master_stem": "part10_shawnee_12",
        "name": "Lucius Eldridge",
        "allotment": "86",
        "tribe": "Citizen Potawatomie",
        "matched_record": "part10_questionnaire_010",
        "name_variant_note": "",
        "cross_refs": ["part10_questionnaire_010"],
    },
    {
        "master_stem": "part10_shawnee_18",
        "name": "Hannah Hardin",
        "allotment": "42",
        "tribe": "Citizen Potawatomie",
        "matched_record": "part10_questionnaire_012",
        "name_variant_note": "",
        "cross_refs": ["part10_questionnaire_012"],
    },
    {
        "master_stem": "part10_shawnee_19",
        "name": "Edward Hutton",
        "allotment": "863",
        "tribe": "Citizen Potawatomie",
        "matched_record": "part10_questionnaire_013",
        "name_variant_note": "",
        "cross_refs": ["part10_questionnaire_013"],
    },
    {
        "master_stem": "part10_shawnee_27",
        "name": "Albion Ogee",
        "allotment": "1080",
        "tribe": "Citizen Potawatomie",
        "matched_record": "part10_affidavit_005",
        "name_variant_note": "",
        "cross_refs": ["part10_affidavit_005", "part10_questionnaire_014"],
    },
    {
        "master_stem": "part10_shawnee_30",
        "name": "Mrs. Addie Easton Payne",
        "allotment": "168",
        "tribe": "Citizen Potawatomie",
        "matched_record": "part10_questionnaire_015",
        "name_variant_note": (
            "Master list reads 'Addie E. Payne'; corpus questionnaire "
            "captures her as 'Mrs. Addie Easton Payne'. Same person — "
            "the master list abbreviates her middle name 'Easton' to "
            "'E.'."
        ),
        "cross_refs": ["part10_questionnaire_015"],
    },
    {
        "master_stem": "part10_shawnee_31",
        "name": "Olive Shepard",
        "allotment": "862",
        "tribe": "Citizen Potawatomie",
        "matched_record": "part10_questionnaire_016",
        "name_variant_note": "",
        "cross_refs": ["part10_questionnaire_016"],
    },
    {
        "master_stem": "part10_shawnee_33",
        "name": "Nicholas Trombla",
        "allotment": "484",
        "tribe": "Citizen Potawatomie",
        "matched_record": "part11_affidavit_001",
        "name_variant_note": "",
        "cross_refs": ["part11_affidavit_001", "part11_questionnaire_001"],
    },
    {
        "master_stem": "part10_shawnee_34",
        "name": "Rosa Vanderbloom",
        "allotment": "313",
        "tribe": "Citizen Potawatomie",
        "matched_record": "part11_questionnaire_002a",
        "name_variant_note": "",
        "cross_refs": ["part11_questionnaire_002a"],
    },
    {
        "master_stem": "part10_shawnee_35",
        "name": "Viola Wallace",
        "allotment": "15609",
        "tribe": "Citizen Potawatomie",
        "matched_record": "part11_questionnaire_002b",
        "name_variant_note": "",
        "cross_refs": ["part11_questionnaire_002b"],
    },
]


def patch_one(spec):
    path = EXTRACTIONS / f"{spec['master_stem']}.json"
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

    # Update Name only if the variant note implies the corpus name is the
    # canonical form (Belle Binia Bruno, Addie Easton Payne)
    if spec["name_variant_note"]:
        e["Name"] = spec["name"]

    e["Allotment number"] = spec["allotment"]
    e["Tribe/Reservation"] = spec["tribe"]

    cross_ref_str = ", ".join(spec["cross_refs"])
    note_addition = (
        f" | TASK 5 SHAWNEE MASTER LIST BACKFILL 2026-05-04: "
        f"Allotment number ({spec['allotment']}) and actual tribe "
        f"({spec['tribe']}) backfilled from matched corpus record(s): "
        f"{cross_ref_str}. AGENCY CONTEXT: This record is from the "
        f"Shawnee Indian Agency master list (part10_shawnee_*). The "
        f"agency administered multiple tribes (Citizen Potawatomie, "
        f"Iowa, Sac & Fox, Eastern Shawnee, etc.); 'Shawnee' is the "
        f"agency name, not the tribal affiliation of individual "
        f"allottees. The Tribe/Reservation field on this record now "
        f"carries the actual tribe per option-A schema decision."
    )
    if spec["name_variant_note"]:
        note_addition += f" NAME VARIANT: {spec['name_variant_note']}"
    e["NOTES"] = (e.get("NOTES") or "") + note_addition

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_shawnee_master_list_backfill",
        "method": "corpus_cross_reference_with_user_verified_data",
        "fields_corrected": (
            ["Name", "Allotment number", "Tribe/Reservation", "NOTES"]
            if spec["name_variant_note"]
            else ["Allotment number", "Tribe/Reservation", "NOTES"]
        ),
        "previous_values": previous,
        "corrected_values": {
            "Name": spec["name"] if spec["name_variant_note"] else previous["Name"],
            "Allotment number": spec["allotment"],
            "Tribe/Reservation": spec["tribe"],
        },
        "matched_corpus_records": spec["cross_refs"],
        "primary_match": spec["matched_record"],
        "name_variant_note": spec["name_variant_note"],
        "agency_context_note": (
            "Shawnee Indian Agency administered Citizen Potawatomie, "
            "Iowa, Sac & Fox, Eastern Shawnee, and other tribes. "
            "Tribe/Reservation field now carries the actual tribe per "
            "option-A schema decision; agency context is recoverable "
            "from the filename pattern part10_shawnee_*."
        ),
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"-> {spec['name']}, {spec['allotment']}, {spec['tribe']}"


def main():
    print("=" * 70)
    print(f"Shawnee master list backfill: {len(BACKFILLS)} records")
    print("=" * 70)

    ok = 0
    for spec in BACKFILLS:
        success, msg = patch_one(spec)
        marker = "  " if success else "  ! "
        print(f"{marker}{spec['master_stem']:25s} {msg}")
        if success:
            ok += 1

    print()
    print(f"Backfilled: {ok}/{len(BACKFILLS)}")


if __name__ == "__main__":
    main()
