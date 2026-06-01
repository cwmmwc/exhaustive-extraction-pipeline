#!/usr/bin/env python3
"""
Correct part9_questionnaire_010: "Hazel" -> Helena Larvie.

The Sonnet text extraction read the degraded handwriting on this
questionnaire as "Hazel (last name not fully legible)". User source-
page review (2026-05-04) of part 9 pages 31-32 confirmed the
questionnaire is Helena Larvie's.

Supporting evidence:
  - Page position: pages 31-32 fall between Helena Larvie's agency
    narrative (part9_agency_narrative_017, page 30) and Peter Larvie's
    agency narrative (part9_agency_narrative_018, page 33).
  - Part 9 pairing pattern: every allottee in part 9 has both an
    agency_narrative and a questionnaire on consecutive pages. Helena
    Larvie had an agency_narrative at page 30 but no questionnaire in
    the record set; pages 31-32 are exactly where her questionnaire
    belongs.
  - User confirmed there is no allottee named "Hazel" on those pages.

Correction:
  Name:             Hazel (last name not fully legible) -> Helena Larvie
  Allotment number: not stated -> 3432
  Tribe:            Rosebud Sioux (unchanged — already correct)

Allotment 3432 verified via BLM General Land Office records, accession
SD2610__.247 (same source used for her agency narrative record
part9_agency_narrative_017, patched earlier 2026-05-04).
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
RECORD_PATH = (
    PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
    / "part9_questionnaire_010.json"
)


def main():
    with open(RECORD_PATH) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        print("ERROR: list-shaped extraction")
        return

    previous = {
        "Name": e.get("Name", ""),
        "Allotment number": e.get("Allotment number", ""),
        "Tribe/Reservation": e.get("Tribe/Reservation", ""),
    }

    e["Name"] = "Helena Larvie"
    e["Allotment number"] = "3432"
    e["Tribe/Reservation"] = "Rosebud Sioux"
    e["NOTES"] = (e.get("NOTES") or "") + (
        " | TASK 5 CAT_3 CORRECTION 2026-05-04: Sonnet text extraction "
        "misread the degraded handwriting as 'Hazel (last name not fully "
        "legible)'. User source-page review of part 9 pages 31-32 "
        "confirmed the questionnaire is Helena Larvie's. The page "
        "position (between Helena Larvie's agency narrative at page 30 "
        "and Peter Larvie's at page 33) and the part 9 pairing pattern "
        "(every allottee has both an agency_narrative and a "
        "questionnaire) confirm this. Name corrected to Helena Larvie; "
        "allotment 3432 backfilled (verified via BLM General Land Office "
        "records, accession SD2610__.247). CROSS-REFERENCE: Helena "
        "Larvie's agency narrative is part9_agency_narrative_017 (page "
        "30, same allotment 3432)."
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat3_name_correction_and_backfill",
        "method": "user_source_page_review_with_blm_glo_cross_reference",
        "source_url": (
            "https://glorecords.blm.gov/details/patent/default.aspx"
            "?accession=SD2610__.247&docClass=STA"
        ),
        "fields_corrected": [
            "Name", "Allotment number", "Tribe/Reservation", "NOTES",
        ],
        "previous_values": previous,
        "corrected_values": {
            "Name": "Helena Larvie",
            "Allotment number": "3432",
            "Tribe/Reservation": "Rosebud Sioux",
        },
        "rationale": (
            "Sonnet text extraction misread 'Helena' as 'Hazel' on "
            "degraded handwriting. User confirmed via source pages 31-32. "
            "Page position and part 9 narrative+questionnaire pairing "
            "pattern corroborate. Allotment from BLM GLO records."
        ),
        "cross_reference": "part9_agency_narrative_017 (Helena Larvie agency narrative, page 30)",
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Corrected part9_questionnaire_010:")
    print(f"  Name:      {previous['Name']}")
    print(f"             -> Helena Larvie")
    print(f"  Allotment: {previous['Allotment number']} -> 3432")
    print(f"  Tribe:     Rosebud Sioux (unchanged)")


if __name__ == "__main__":
    main()
