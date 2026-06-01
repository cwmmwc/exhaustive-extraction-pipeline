#!/usr/bin/env python3
"""
Correct the resolution-path language in Alphonse Charbonneau's NOTES.

The previous patch (patch_part4_q012_substantive.py) incorrectly said
'Worth future cross-reference against BLM patent records' to resolve the
Kimi v5 vs Sonnet vision discrepancy on the sale details ($2000 to
Keeler vs $7000 NW 1/4 unknown buyer). BLM has patent ISSUANCE data
(patent number, allottee, acreage, date) — not subsequent sale or
transaction data. Sale prices and buyers come from county deed records.

The correct resolution path for this discrepancy is user source-page
review: render the source PDF, compare both model outputs against what
the page actually says.
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

WRONG_PHRASE = (
    "These may be the same transaction with different details, or separate "
    "transactions. Worth future cross-reference against BLM patent records."
)

CORRECTED_PHRASE = (
    "These may be the same transaction with different details, or separate "
    "transactions. BLM has patent ISSUANCE data (patent number, allottee, "
    "acreage, date) but NOT subsequent sale or transaction data — sale "
    "prices and buyers live in county deed records, not BLM. Resolution "
    "requires user source-page review."
)


def main():
    with open(RECORD_PATH) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        print("ERROR: list-shaped extraction")
        return

    notes = e.get("NOTES") or ""

    if WRONG_PHRASE not in notes:
        print("WARNING: target phrase not found exactly. NOTES last 600 chars:")
        print(notes[-600:])
        return

    notes = notes.replace(WRONG_PHRASE, CORRECTED_PHRASE)
    e["NOTES"] = notes

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-02",
        "type": "task5_correction_resolution_path_language",
        "method": "user_correction_blm_does_not_have_transaction_data",
        "fields_corrected": ["NOTES"],
        "rationale": (
            "Previous patch incorrectly said BLM cross-reference would "
            "resolve the Kimi vs Sonnet vision sale-detail discrepancy. "
            "BLM has patent issuance data only, not transaction data. "
            "Correct resolution path is user source-page review."
        ),
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Corrected resolution-path language in NOTES.")


if __name__ == "__main__":
    main()
