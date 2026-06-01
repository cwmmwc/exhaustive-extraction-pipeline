#!/usr/bin/env python3
"""
Backfill 2 Shawnee master list rows that the automated triage missed.

The triage script's exact normalized-name match did not catch:
  - Row 14 Lizzie Hartman → corpus record uses her married name
    'Lizzie Lyons (née Hartman)' at part10_questionnaire_011
    (allotment 765, Citizen Potawatomie). Same person.
  - Row 32 James J. Sweeney → corpus record uses the deceased
    allottee's primary name 'Laura Dean (deceased allottee); filed
    by James J. Sweeney...' at part10_questionnaire_017 (allotment
    845, Citizen Potawatomie). Sweeney is filing on behalf of his
    deceased wife Laura Dean (the actual allottee) and their minor
    son William J. Sweeney Jr.

Row 32 already has allotment 845 (from the RA spreadsheet);
this script only normalizes the tribe from 'Shawnee' to
'Citizen Potawatomie' and adds the cross-reference to q017.

Row 14 needs both allotment (765) and tribe (Citizen Potawatomie)
backfilled from q011.

This case is methodologically important: the automated triage
matches names exactly, but the corpus contains married-name and
deceased-filing variants where the master list and corpus refer
to the same person under different headings. Future master-list
backfills should manually verify residual rows against the
corpus, looking for these patterns.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

BACKFILLS = [
    {
        "master_stem": "part10_shawnee_14",
        "fields_to_update": {
            "Allotment number": "765",
            "Tribe/Reservation": "Citizen Potawatomie",
        },
        "matched_record": "part10_questionnaire_011",
        "cross_ref_note": (
            "Lizzie Hartman (master list maiden name) is the same "
            "person as Lizzie Lyons (née Hartman) at "
            "part10_questionnaire_011 (allotment 765, Citizen "
            "Potawatomie). Master list captures her under her maiden "
            "name; the corpus questionnaire captures her under her "
            "married name with maiden name parenthetical. Source page "
            "of q011 contains the statement 'patent was forced on me' "
            "— directly relevant to forced-fee patent argumentation."
        ),
    },
    {
        "master_stem": "part10_shawnee_32",
        "fields_to_update": {
            "Tribe/Reservation": "Citizen Potawatomie",
            # Allotment 845 already present from RA spreadsheet, don't change
        },
        "matched_record": "part10_questionnaire_017",
        "cross_ref_note": (
            "James J. Sweeney is filing on behalf of his deceased wife "
            "Laura Dean (the original allottee, allotment 845, Citizen "
            "Potawatomie) and their minor son William J. Sweeney Jr. "
            "Master list captures the petitioner (Sweeney); the corpus "
            "questionnaire at part10_questionnaire_017 captures the "
            "deceased allottee (Laura Dean) as the primary subject. "
            "Allotment 845 was already present on this record from "
            "the RA spreadsheet (Replies_to_Circular_2464.xlsx); this "
            "patch normalizes the tribe from 'Shawnee' (agency) to "
            "'Citizen Potawatomie' (actual tribe) per option-A schema "
            "decision and adds the cross-reference."
        ),
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

    previous = {k: e.get(k, "") for k in spec["fields_to_update"]}

    for k, v in spec["fields_to_update"].items():
        e[k] = v

    note_addition = (
        f" | TASK 5 SHAWNEE MASTER LIST BACKFILL 2026-05-04 (manual triage): "
        f"{spec['cross_ref_note']} CROSS-REFERENCE: {spec['matched_record']}. "
        f"AGENCY CONTEXT: This record is from the Shawnee Indian Agency "
        f"master list; agency administered Citizen Potawatomie, Iowa, "
        f"Sac & Fox, etc. Tribe/Reservation field carries the actual "
        f"tribe per option-A schema decision."
    )
    e["NOTES"] = (e.get("NOTES") or "") + note_addition

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_shawnee_master_list_backfill_manual_triage",
        "method": "manual_corpus_search_for_name_variants",
        "fields_corrected": list(spec["fields_to_update"].keys()) + ["NOTES"],
        "previous_values": previous,
        "corrected_values": dict(spec["fields_to_update"]),
        "matched_corpus_record": spec["matched_record"],
        "name_variant_note": spec["cross_ref_note"],
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    summary = ", ".join(f"{k}={v}" for k, v in spec["fields_to_update"].items())
    return True, summary


def main():
    print("=" * 70)
    print(f"Shawnee master list manual-triage backfill: {len(BACKFILLS)} records")
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
