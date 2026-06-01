#!/usr/bin/env python3
"""
Final tribe-not-stated CAT_3 batch (2026-05-04).

Allotments from Christian's research in the federal-register-app
patents database. This completes the CAT_3 campaign.

27 clean allotment + tribe backfills (Rosebud Sioux unless noted).
6 special cases.
2 non-allottee reclassifications.

See inline comments for each special case.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
PATENTS_URL = "https://federal-register-app-996830241007.us-east1.run.app/patents"


def load(stem):
    path = EXTRACTIONS / f"{stem}.json"
    if not path.exists():
        return None, None
    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        return None, None
    return record, e


def save(stem, record):
    with open(EXTRACTIONS / f"{stem}.json", "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)


def backfill(stem, allotment, tribe, extra_note="", cross_ref=""):
    """Standard CAT_3 allotment + tribe backfill."""
    record, e = load(stem)
    if record is None:
        return False, f"{stem}: NOT FOUND or list-shaped"
    previous = {
        "Name": e.get("Name", ""),
        "Allotment number": e.get("Allotment number", ""),
        "Tribe/Reservation": e.get("Tribe/Reservation", ""),
    }
    e["Allotment number"] = allotment
    e["Tribe/Reservation"] = tribe

    note = (
        f" | TASK 5 CAT_3 BACKFILL 2026-05-04 (patents database): "
        f"Allotment {allotment}, tribe {tribe}, sourced from "
        f"federal-register-app patents database (Christian's research). "
        f"CAT_3 record — Sonnet text extraction captured the allottee "
        f"Name but not the Allotment number."
    )
    if extra_note:
        note += f" {extra_note}"
    if cross_ref:
        note += f" CROSS-REFERENCE: {cross_ref}"
    e["NOTES"] = (e.get("NOTES") or "") + note

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat3_backfill_patents_database",
        "method": "user_research_federal_register_app_patents_database",
        "source_url": PATENTS_URL,
        "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
        "previous_values": previous,
        "corrected_values": {"Allotment number": allotment, "Tribe/Reservation": tribe},
        "extra_note": extra_note,
        "cross_reference": cross_ref,
        "user_confirmed": True,
    })
    save(stem, record)
    return True, f"{e['Name'][:34]:34s} allot={allotment}, {tribe}"


def mark_non_allottee(stem, role_note):
    """Reclassify a record as a non-allottee record."""
    record, e = load(stem)
    if record is None:
        return False, f"{stem}: NOT FOUND or list-shaped"
    previous = {
        "Name": e.get("Name", ""),
        "Allotment number": e.get("Allotment number", ""),
        "Tribe/Reservation": e.get("Tribe/Reservation", ""),
        "Document type": e.get("Document type", ""),
    }
    e["Allotment number"] = "(not applicable — non-allottee record)"
    e["Document type"] = "non_allottee_record"
    e["NOTES"] = (e.get("NOTES") or "") + (
        f" | TASK 5 NON-ALLOTTEE RECLASSIFICATION 2026-05-04: {role_note} "
        f"This record is reclassified as a non-allottee record "
        f"(Document type = 'non_allottee_record'). The named individuals "
        f"are not allottees; the document is retained in the corpus for "
        f"its evidentiary value but does not represent a forced-fee "
        f"allotment case."
    )
    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_non_allottee_reclassification",
        "method": "user_confirmed_non_allottee",
        "fields_corrected": ["Allotment number", "Document type", "NOTES"],
        "previous_values": previous,
        "corrected_values": {
            "Allotment number": "(not applicable — non-allottee record)",
            "Document type": "non_allottee_record",
        },
        "role_note": role_note,
        "user_confirmed": True,
    })
    save(stem, record)
    return True, f"{e['Name'][:34]:34s} -> non_allottee_record"


def mark_not_in_database(stem, note):
    record, e = load(stem)
    if record is None:
        return False, f"{stem}: NOT FOUND or list-shaped"
    previous = {
        "Allotment number": e.get("Allotment number", ""),
        "Tribe/Reservation": e.get("Tribe/Reservation", ""),
    }
    e["Allotment number"] = "(not in patents database)"
    e["Tribe/Reservation"] = "(actual tribe unknown)"
    e["NOTES"] = (e.get("NOTES") or "") + (
        f" | TASK 5 CAT_3 PATENTS-DATABASE LOOKUP 2026-05-04: {note} "
        f"Allotment and tribe marked explicitly unknown to flag this "
        f"row as unresolved (option-3 schema)."
    )
    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat3_not_in_patents_database",
        "method": "user_research_federal_register_app_patents_database",
        "source_url": PATENTS_URL,
        "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
        "previous_values": previous,
        "corrected_values": {
            "Allotment number": "(not in patents database)",
            "Tribe/Reservation": "(actual tribe unknown)",
        },
        "note": note,
        "user_confirmed": True,
    })
    save(stem, record)
    return True, f"{e.get('Name','')[:34]:34s} -> not in patents database"


def main():
    results = []

    # --- 27 clean backfills (Rosebud Sioux unless noted) ---
    R = "Rosebud Sioux"
    clean = [
        ("part1_affidavit_001", "156", R, ""),
        ("part1_questionnaire_001", "488", R, ""),
        ("part1_questionnaire_030", "148", R,
         "Recorded as Clara Bonser at the time the patent was issued; "
         "Monteau is her later married name."),
        ("part2_affidavit_001", "240", R, ""),
        ("part2_questionnaire_002", "263", R,
         "Samuel Miller is the deceased original allottee; Mary Haukaas "
         "Miller is the deponent (wife/widow)."),
        ("part2_questionnaire_004", "266", R, ""),
        ("part2_questionnaire_012", "484", R,
         "Benjamin Beauvais also holds allotment 483; the forced fee "
         "patent at issue refers to allotment 484."),
        ("part2_questionnaire_013", "486", R, ""),
        ("part2_questionnaire_025", "724", R, ""),
        ("part2_questionnaire_028", "979", R, ""),
        ("part3_questionnaire_017", "1504.5", R, ""),
        ("part3_questionnaire_021", "1534", R, ""),
        ("part6_affidavit_004", "521", R, ""),
        ("part6_questionnaire_006", "1070", R, ""),
        ("part6_questionnaire_017", "1938", R, ""),
        ("part7_questionnaire_001", "2098", R, ""),
        ("part7_questionnaire_018", "2304", R, ""),
        ("part7_questionnaire_024", "2376", R, ""),
        ("part8_questionnaire_007", "2570", R, ""),
        ("part8_questionnaire_011", "2903", R, ""),
        ("part8_questionnaire_014", "2974", R, ""),
        ("part9_questionnaire_004", "3160", R, ""),
        ("part7_questionnaire_002", "2178", R,
         "Surname pre-sort guessed Pine Ridge (Larvie/Brown), but the "
         "patents database confirms Rosebud Sioux."),
        ("part8_questionnaire_015", "2992", R,
         "Surname pre-sort guessed Pine Ridge (Swallow), but the patents "
         "database confirms Rosebud Sioux."),
        ("part11_agency_narrative_002", "800", "Crow Creek Sioux", ""),
        ("part13_questionnaire_001", "393", "Ponca", ""),
        ("part2_questionnaire_003", "265", R, ""),
    ]
    for stem, allot, tribe, note in clean:
        results.append(backfill(stem, allot, tribe, extra_note=note))

    # --- Special cases ---

    # David Whiting — Old Ponca
    results.append(backfill(
        "part1_questionnaire_023", "9", "Old Ponca",
        extra_note=(
            "David Whiting's allotment 9 is on the Old Ponca Indian "
            "Reservation. Tribe/Reservation set to 'Old Ponca'. The "
            "Whiting family also appears in the buyer-network records "
            "(David B. Whiting, and Hattie Whiting Whitcher at "
            "part1_questionnaire_024)."),
    ))

    # Josephine Collins — same person as the 2862.5 records
    results.append(backfill(
        "part2_questionnaire_020", "2862.5", R,
        cross_ref=(
            "Same Josephine Collins as part2_agency_narrative_page059 and "
            "part6_agency_narrative_page046 (all allotment 2862.5). This "
            "is her questionnaire; the other two are agency narratives."),
    ))

    # Mary Dillon — two records, same person, allotment 481
    results.append(backfill(
        "part7_affidavit_005", "481", R,
        cross_ref=(
            "Same Mary Dillon as part7_questionnaire_016 (widow of William "
            "McClosky/Dillon, dec'd). Both records are the same person, "
            "allotment 481."),
    ))
    results.append(backfill(
        "part7_questionnaire_016", "481", R,
        cross_ref=(
            "Same Mary Dillon as part7_affidavit_005. Both records are the "
            "same person, allotment 481. McCloskey connects to the "
            "Whipple-related Rosebud family."),
    ))

    # Joseph St John — same person as Joe St John (547)
    results.append(backfill(
        "part11_questionnaire_012", "547", "Crow Creek Sioux",
        cross_ref=(
            "Joseph St John is the same person as Joe St John "
            "(part11_agency_narrative_005, allotment 547, Crow Creek "
            "Sioux). 'Joe' is short for 'Joseph'. This is his "
            "questionnaire; part11_agency_narrative_005 is his agency "
            "narrative. Distinct from Peter St John "
            "(part11_agency_narrative_006, allotment 546)."),
    ))

    # William J. Bordeaux — non-allottee witness
    record, e = load("part6_questionnaire_021")
    if record is not None:
        previous = {
            "Allotment number": e.get("Allotment number", ""),
            "Tribe/Reservation": e.get("Tribe/Reservation", ""),
        }
        e["Allotment number"] = "(non-allottee record — witness)"
        e["NOTES"] = (e.get("NOTES") or "") + (
            " | TASK 5 NON-ALLOTTEE NOTE 2026-05-04: William J. Bordeaux "
            "appears in this record as a WITNESS on others' affidavits, "
            "not as an allottee. No allotment is associated with him in "
            "this capacity. Allotment field marked '(non-allottee record "
            "— witness)'. The record is retained for its evidentiary "
            "value (Bordeaux as a recurring witness in the Rosebud "
            "forced-fee cases)."
        )
        record.setdefault("recovery_notes", []).append({
            "date": "2026-05-04",
            "type": "task5_non_allottee_witness_note",
            "method": "user_confirmed_witness_not_allottee",
            "fields_corrected": ["Allotment number", "NOTES"],
            "previous_values": previous,
            "corrected_values": {"Allotment number": "(non-allottee record — witness)"},
            "user_confirmed": True,
        })
        save("part6_questionnaire_021", record)
        results.append((True, f"{e['Name'][:34]:34s} -> non-allottee witness"))
    else:
        results.append((False, "part6_questionnaire_021: NOT FOUND"))

    # Hattie Whiting Whitcher — not in database
    results.append(mark_not_in_database(
        "part1_questionnaire_024",
        "Hattie Whiting Whitcher not found in the federal-register-app "
        "patents database despite search. The Whiting/Whitcher surnames "
        "appear in the buyer-network records (David B. Whiting, W.H. "
        "Whitcher), but Hattie herself could not be located.",
    ))

    # --- 2 non-allottee reclassifications ---
    results.append(mark_non_allottee(
        "part6_affidavit_002",
        "T. C. Montgomery (primary affiant) and J. D. Keller (secondary "
        "affiant) are neither allottees. ",
    ))
    results.append(mark_non_allottee(
        "part7_agency_narrative_page056",
        "Eugene Sturdevant is white and holds no allotment. (Sturdevant "
        "is the married name of Lucy DuBray Sturdevant, a separate "
        "allottee at part7_agency_narrative_025b / part7_questionnaire_020, "
        "allotment 2341.) ",
    ))

    # --- Report ---
    print("=" * 70)
    print("Final tribe-not-stated CAT_3 batch")
    print("=" * 70)
    ok = 0
    for success, msg in results:
        marker = "  " if success else "  ! "
        print(f"{marker}{msg}")
        if success:
            ok += 1
    print()
    print(f"Records handled: {ok}/{len(results)}")


if __name__ == "__main__":
    main()
