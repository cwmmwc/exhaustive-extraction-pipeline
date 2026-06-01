#!/usr/bin/env python3
"""
Correct part4_questionnaire_012 sale details per user source-page verification.

User rendered the source PDF and verified that the questionnaire actually
says: part of allotment sold for $2,000 cash. No buyer name, no date.

Implications:
  - Sonnet vision's '$7,000' is a hallucination or misread
  - Sonnet vision's 'NW 1/4' may also be unsupported by source
  - Kimi v5's Jesse E. Keeler / April 2, 1924 / Tri County Abstract details
    are NOT from this questionnaire — they're from the separate agency
    narrative record (part4_agency_narrative_016), which is the agency's
    third-party account of his case

This patch:
  1. Updates the substantive NOTES section to reflect the corrected sale
     details ($2,000 cash, partial allotment, buyer/date unknown)
  2. Removes the inaccurate Sonnet-vision-vs-Kimi disagreement framing
     since the disagreement is between Sonnet vision (wrong about $7,000)
     and the questionnaire source (correct: $2,000)
  3. Keeps the cross-reference to part4_agency_narrative_016 for the agency-
     side detail on Keeler/1924, with a note that that's the source for
     those details (not the questionnaire)
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
RECORD_PATH = (
    PROJECT_ROOT
    / "circular_2464_extractions"
    / "extractions"
    / "sonnet"
    / "part4_questionnaire_012.json"
)

OLD_SALE_PHRASE = (
    "SALE: NW 1/4 sold for $7,000 cash (buyer name not captured by "
    "vision extraction; date not specified). "
)
NEW_SALE_PHRASE = (
    "SALE (per source-page verification): Part of allotment sold for "
    "$2,000 cash. Buyer name and date NOT in questionnaire source. "
    "(Sonnet vision had reported '$7,000' and 'NW 1/4' — both "
    "unsupported by the source page; vision extraction errors.) "
)

OLD_DISCREPANCY_PHRASE = (
    "DISCREPANCY WITH KIMI v5: Kimi v5 reports a $2000 sale to Jesse "
    "E. Keeler on April 2, 1924, with patent recorded by Tri County "
    "Abstract Company on April 18, 1924. Sonnet vision reports a $7000 "
    "NW 1/4 sale (buyer unknown). These may be the same transaction "
    "with different details, or separate transactions. BLM has patent "
    "ISSUANCE data (patent number, allottee, acreage, date) but NOT "
    "subsequent sale or transaction data — sale prices and buyers live "
    "in county deed records, not BLM. Resolution requires user source-"
    "page review."
)
NEW_AGENCY_REFERENCE_PHRASE = (
    "AGENCY-SIDE DETAILS (from sibling record part4_agency_narrative_016, "
    "not from this questionnaire): Per Kimi v5 extraction of part 4, the "
    "agency narrative reports the buyer as Jesse E. Keeler, sale on "
    "April 2, 1924, patent recorded by Tri County Abstract Company on "
    "April 18, 1924. The questionnaire source confirms only the $2,000 "
    "cash amount and partial-allotment scope; buyer identity and date "
    "come from the agency narrative. The $2,000 figure is consistent "
    "between the two sources."
)


def main():
    with open(RECORD_PATH) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        print("ERROR: list-shaped extraction")
        return

    notes = e.get("NOTES") or ""
    changes = []

    if OLD_SALE_PHRASE in notes:
        notes = notes.replace(OLD_SALE_PHRASE, NEW_SALE_PHRASE)
        changes.append("sale phrase corrected")
    else:
        print("WARNING: OLD_SALE_PHRASE not found exactly. NOTES last 800 chars:")
        print(notes[-800:])
        return

    if OLD_DISCREPANCY_PHRASE in notes:
        notes = notes.replace(OLD_DISCREPANCY_PHRASE, NEW_AGENCY_REFERENCE_PHRASE)
        changes.append("discrepancy framing replaced with agency-source attribution")
    else:
        print("Note: discrepancy phrase not found (may have been corrected previously).")

    e["NOTES"] = notes

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-02",
        "type": "task5_sale_detail_correction_per_source_verification",
        "method": "user_source_page_verification",
        "fields_corrected": ["NOTES"],
        "changes": changes,
        "rationale": (
            "User rendered the source PDF and verified the questionnaire "
            "says part of allotment sold for $2000 cash, no buyer or date. "
            "Sonnet vision had reported $7000 and NW 1/4 — both errors. "
            "Kimi v5's Keeler/1924 detail is from the agency narrative "
            "(part4_agency_narrative_016), not from this questionnaire."
        ),
        "source_says": {
            "sale_amount": "$2,000 cash",
            "scope": "part of allotment",
            "buyer": "not stated in questionnaire source",
            "date": "not stated in questionnaire source",
        },
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Corrected sale details in part4_questionnaire_012 NOTES.")
    for c in changes:
        print(f"  - {c}")


if __name__ == "__main__":
    main()
