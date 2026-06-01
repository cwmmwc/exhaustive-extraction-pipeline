#!/usr/bin/env python3
"""
Patch 6 records — 5 scattered single-tribe CAT_3 records plus a tribe
normalization for Jasper Ellston.

REVISED 2026-05-04: corrects the Jesse Ellston handling. An earlier
draft of this patch described the Sonnet extraction as having "wrongly
merged" Jasper Ellston's name into Jesse's record. That was incorrect.
Jesse Ellston's affidavit contains his OWN statement:

  "My name is known also as Jasper J. Ellston, and I am sometimes
   called Jay Ellston."

So the aliases on part2_questionnaire_001 are not an extraction error —
they are Jesse Ellston's own words about his own names.

Decision (Christian, 2026-05-04): treat Jesse Ellston and Jasper
Ellston as TWO SEPARATE PEOPLE. The evidence is two distinct names with
two distinct allotment numbers (Jesse = 241, Jasper = 243) and two
distinct corpus records (part2_questionnaire_001 page 5;
part2_agency_narrative_004 page 6). Why Jesse Ellston stated that he is
"also known as Jasper J. Ellston" is unresolved. The conservative,
evidence-respecting treatment is to keep them separate, preserve
Jesse's affidavit statement verbatim, and explicitly NOT collapse the
two into one identity.

CAT_3 backfills (allotment from Christian's research 2026-05-04):

  part11_affidavit_006     Mrs. Louisa Dougherty -> 1350, Crow Creek Sioux
    Filing as mother and heir of the deceased original allottee Dolly
    Dougherty. Allotment 1350 is Dolly Dougherty's allotment.

  part13_questionnaire_024 Henry Chapman -> 573, Pawnee

  part2_questionnaire_001  Jesse Ellston -> 241, Rosebud Sioux
    Name kept as "Jesse Ellston" (record's primary name; this
    questionnaire at part 2 page 5 is Jesse's, allotment 241). Jesse's
    affidavit statement about his aliases is preserved verbatim in
    NOTES. Tribe corrected from the erroneous "Ponca" (extraction
    derived it from a "policeman from the Ponca station" mention) to
    Rosebud Sioux.

  part8_questionnaire_017  Annie Desersa Bonser -> 3014, Rosebud Sioux
    Patents database spelling "Annie Deserea". Generic "Sioux" label
    corrected to "Rosebud Sioux".

  part3_affidavit_009      Louis Richard -> 4743, Oglala Lakota
    Corpus label "Shannon County (South Dakota)" is a county, not a
    tribe. Corrected to Oglala Lakota.

Tribe normalization (no allotment change):

  part2_agency_narrative_004  Jasper Ellston: tribe "Rosebud" ->
    "Rosebud Sioux". Name (Jasper Ellston) and allotment (243) already
    correct. Treated as a separate person from Jesse Ellston.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"


def patch_record(stem, updates, note_addition, recovery_note):
    path = EXTRACTIONS / f"{stem}.json"
    if not path.exists():
        return False, "NOT FOUND"
    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        return False, "list-shaped extraction"

    previous = {k: e.get(k, "") for k in updates}
    for k, v in updates.items():
        e[k] = v
    e["NOTES"] = (e.get("NOTES") or "") + note_addition

    rn = dict(recovery_note)
    rn["previous_values"] = previous
    rn["corrected_values"] = dict(updates)
    record.setdefault("recovery_notes", []).append(rn)

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    summary = ", ".join(f"{k}={v}" for k, v in updates.items())
    return True, summary


def main():
    print("=" * 70)
    print("Scattered CAT_3 + Ellston handling (revised): 6 records")
    print("=" * 70)

    results = []

    # 1. Mrs. Louisa Dougherty
    results.append(("part11_affidavit_006", patch_record(
        "part11_affidavit_006",
        {"Allotment number": "1350", "Tribe/Reservation": "Crow Creek Sioux"},
        (" | TASK 5 CAT_3 BACKFILL 2026-05-04 (patents database): "
         "Allotment 1350 sourced from federal-register-app patents "
         "database. The original allottee is Dolly Dougherty (deceased); "
         "Mrs. Louisa Dougherty is filing as her mother and heir. "
         "Allotment 1350 is Dolly Dougherty's allotment. Tribe set to "
         "Crow Creek Sioux."),
        {
            "date": "2026-05-04",
            "type": "task5_cat3_backfill_patents_database",
            "method": "user_research_federal_register_app_patents_database",
            "source_url": "https://federal-register-app-996830241007.us-east1.run.app/patents",
            "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
            "note": ("Original allottee Dolly Dougherty (deceased); Louisa "
                     "Dougherty filing as mother/heir."),
            "user_confirmed": True,
        },
    )))

    # 2. Henry Chapman
    results.append(("part13_questionnaire_024", patch_record(
        "part13_questionnaire_024",
        {"Allotment number": "573", "Tribe/Reservation": "Pawnee"},
        (" | TASK 5 CAT_3 BACKFILL 2026-05-04 (patents database): "
         "Allotment 573 sourced from federal-register-app patents "
         "database. Tribe Pawnee confirmed."),
        {
            "date": "2026-05-04",
            "type": "task5_cat3_backfill_patents_database",
            "method": "user_research_federal_register_app_patents_database",
            "source_url": "https://federal-register-app-996830241007.us-east1.run.app/patents",
            "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
            "user_confirmed": True,
        },
    )))

    # 3. Jesse Ellston — allotment + tribe correction; aliases preserved as his own words
    results.append(("part2_questionnaire_001", patch_record(
        "part2_questionnaire_001",
        {
            "Name": "Jesse Ellston",
            "Allotment number": "241",
            "Tribe/Reservation": "Rosebud Sioux",
        },
        (" | TASK 5 CAT_3 CORRECTION 2026-05-04: ALLOTMENT 241 sourced "
         "from federal-register-app patents database. TRIBE corrected "
         "from 'Ponca' to 'Rosebud Sioux' — the extraction derived "
         "'Ponca' from a mention of a 'policeman from the Ponca "
         "station', but Jesse Ellston is Rosebud Sioux. "
         "ALIASES: Jesse Ellston's affidavit contains his own statement: "
         "'My name is known also as Jasper J. Ellston, and I am "
         "sometimes called Jay Ellston.' These aliases are Jesse "
         "Ellston's own words and are retained as data — they are NOT "
         "an extraction error. SEPARATE-PERSON NOTE: the patents "
         "database also records a 'Jasper Ellston' at a DIFFERENT "
         "allotment (243), with his own corpus record at "
         "part2_agency_narrative_004 (part 2 page 6). Because there are "
         "two distinct names AND two distinct allotment numbers, Jesse "
         "Ellston (241) and Jasper Ellston (243) are treated as two "
         "separate people. Why Jesse Ellston stated he is 'also known "
         "as Jasper J. Ellston' is unresolved and is deliberately left "
         "unresolved rather than collapsing the two records into one "
         "identity. This questionnaire (part 2 page 5) is Jesse "
         "Ellston's; its substantive content (the $1500 loan, the "
         "'poor judgment' quote, the policeman delivery at the Bank of "
         "Herrick) is retained."),
        {
            "date": "2026-05-04",
            "type": "task5_cat3_backfill_with_identity_note",
            "method": "user_research_with_corpus_cross_reference",
            "source_url": "https://federal-register-app-996830241007.us-east1.run.app/patents",
            "fields_corrected": ["Name", "Allotment number", "Tribe/Reservation", "NOTES"],
            "aliases_from_affidavit": [
                "Jasper J. Ellston", "Jay Ellston",
            ],
            "aliases_source": (
                "Jesse Ellston's own affidavit statement: 'My name is "
                "known also as Jasper J. Ellston, and I am sometimes "
                "called Jay Ellston.' Not an extraction error."
            ),
            "identity_decision": (
                "Jesse Ellston (allotment 241) and Jasper Ellston "
                "(allotment 243, record part2_agency_narrative_004) are "
                "treated as TWO SEPARATE PEOPLE — two names, two "
                "allotment numbers. The relationship between them, and "
                "the reason for Jesse's stated alias, is unresolved and "
                "deliberately not collapsed."
            ),
            "separate_person_record": "part2_agency_narrative_004 (Jasper Ellston, allotment 243)",
            "tribe_correction": "Extraction labeled tribe 'Ponca' from a 'Ponca station' mention; corrected to Rosebud Sioux.",
            "user_confirmed": True,
        },
    )))

    # 4. Annie Desersa Bonser
    results.append(("part8_questionnaire_017", patch_record(
        "part8_questionnaire_017",
        {"Allotment number": "3014", "Tribe/Reservation": "Rosebud Sioux"},
        (" | TASK 5 CAT_3 BACKFILL 2026-05-04 (patents database): "
         "Allotment 3014 sourced from federal-register-app patents "
         "database, where she is recorded as 'Annie Deserea' (Desersa/"
         "Deserea spelling variant). Corpus tribe label 'Sioux' (generic) "
         "corrected to the specific 'Rosebud Sioux'."),
        {
            "date": "2026-05-04",
            "type": "task5_cat3_backfill_patents_database",
            "method": "user_research_federal_register_app_patents_database",
            "source_url": "https://federal-register-app-996830241007.us-east1.run.app/patents",
            "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
            "name_variant_note": "Database spelling 'Annie Deserea' vs corpus 'Annie Desersa Bonser'.",
            "user_confirmed": True,
        },
    )))

    # 5. Louis Richard
    results.append(("part3_affidavit_009", patch_record(
        "part3_affidavit_009",
        {"Allotment number": "4743", "Tribe/Reservation": "Oglala Lakota"},
        (" | TASK 5 CAT_3 BACKFILL 2026-05-04 (patents database): "
         "Allotment 4743 sourced from federal-register-app patents "
         "database. TRIBE CORRECTION: corpus label was 'Shannon County "
         "(South Dakota)' — a county, not a tribe. Shannon County "
         "contains the Pine Ridge Reservation. Louis Richard is Oglala "
         "Lakota."),
        {
            "date": "2026-05-04",
            "type": "task5_cat3_backfill_patents_database",
            "method": "user_research_federal_register_app_patents_database",
            "source_url": "https://federal-register-app-996830241007.us-east1.run.app/patents",
            "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
            "tribe_correction_note": (
                "Corpus label 'Shannon County (South Dakota)' is a county, "
                "not a tribe. Corrected to Oglala Lakota."
            ),
            "user_confirmed": True,
        },
    )))

    # 6. Jasper Ellston — tribe normalization only
    results.append(("part2_agency_narrative_004", patch_record(
        "part2_agency_narrative_004",
        {"Tribe/Reservation": "Rosebud Sioux"},
        (" | TASK 5 TRIBE NORMALIZATION 2026-05-04: tribe label 'Rosebud' "
         "normalized to canonical 'Rosebud Sioux'. Name (Jasper Ellston) "
         "and allotment (243) already correct. IDENTITY NOTE: Jesse "
         "Ellston (part2_questionnaire_001, allotment 241) stated in his "
         "affidavit that he is 'also known as Jasper J. Ellston'. "
         "Despite that statement, Jesse Ellston and Jasper Ellston are "
         "treated as two separate people in this corpus — two names, "
         "two allotment numbers (241 and 243). The relationship is "
         "unresolved. See part2_questionnaire_001 recovery_notes for "
         "the full identity note."),
        {
            "date": "2026-05-04",
            "type": "task5_tribe_normalization",
            "method": "tribe_label_normalization",
            "fields_corrected": ["Tribe/Reservation", "NOTES"],
            "identity_note": (
                "Jesse Ellston (part2_questionnaire_001, allotment 241) "
                "stated he is 'also known as Jasper J. Ellston'. Jesse "
                "and Jasper are treated as two separate people (two "
                "names, two allotments). Relationship unresolved."
            ),
            "related_record": "part2_questionnaire_001 (Jesse Ellston, allotment 241)",
            "user_confirmed": True,
        },
    )))

    for stem, (success, msg) in results:
        marker = "  " if success else "  ! "
        print(f"{marker}{stem:38s} {msg}")

    ok = sum(1 for _, (s, _) in results if s)
    print()
    print(f"Patched: {ok}/{len(results)}")


if __name__ == "__main__":
    main()
