#!/usr/bin/env python3
"""
Patch part1_questionnaire_015 (Anna Shuck) and remove part1_questionnaire_016
as splitter-produced duplicate.

User source-page review (2026-05-04) confirmed q015 and q016 are NOT
separate filings — they are the same Form 5-105 source document, with
the splitter accidentally producing two corpus records covering
overlapping/repeated pages. q015 is the 4-page version (canonical);
q016 is a 2-page subset.

Action:
  1. Patch q015 with verified values: Mrs. Anna Shuck, Rosebud Sioux,
     allotment 7394.
  2. Archive q016's content into q015's recovery_notes (so the audit
     trail isn't lost when q016 is removed).
  3. Delete q016 from extractions/sonnet/.

Allotment 7394 is Anna Shuck's forced-fee patent (per user's
allotments database: 7394 = Indian Trust Patent 1915-07-15, forced fee.
Note: she also had allotment 7222, an Indian Fee Patent dated
1920-02-04 acquired via purchase from Francis Iron-Shell. That is a
DIFFERENT case and is not the subject of this Circular 2464 filing
since 2464 was specifically about forced fee patents).
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

Q015_PATH = EXTRACTIONS / "part1_questionnaire_015.json"
Q016_PATH = EXTRACTIONS / "part1_questionnaire_016.json"


def main():
    if not Q015_PATH.exists():
        print("ERROR: q015 not found")
        return
    if not Q016_PATH.exists():
        print("WARNING: q016 already absent; will only patch q015")

    # Read q016 first (to archive)
    q016_archive = None
    if Q016_PATH.exists():
        with open(Q016_PATH) as f:
            q016_archive = json.load(f)

    # Patch q015
    with open(Q015_PATH) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        print("ERROR: q015 has list-shaped extraction")
        return

    previous = {
        "Name": e.get("Name", ""),
        "Allotment number": e.get("Allotment number", ""),
        "Tribe/Reservation": e.get("Tribe/Reservation", ""),
    }

    e["Name"] = "Mrs. Anna Shuck"
    e["Allotment number"] = "7394"
    e["Tribe/Reservation"] = "Rosebud Sioux"
    e["NOTES"] = (e.get("NOTES") or "") + (
        " | TASK 5 CAT_1 PATCH 2026-05-04: Identified via dual-model "
        "vision recovery (Sonnet vision + Qwen vision) — both models read "
        "Mrs. Anna Shuck / 7394 across all 4 pages. User confirmed tribe "
        "Rosebud Sioux. Allotment 7394 is her forced-fee patent (per "
        "user's allotments database: Indian Trust Patent 1915-07-15, "
        "forced fee). Note: she has a SEPARATE allotment 7222 (Indian "
        "Fee Patent 1920-02-04, acquired via purchase from Francis Iron-"
        "Shell) which is NOT the subject of this 2464 filing. "
        "DUPLICATE REMOVAL: User source-page review confirmed that "
        "part1_questionnaire_016 was NOT a separate filing — the "
        "splitter accidentally produced two corpus records (q015: 4 "
        "pages; q016: 2 pages) covering overlapping/repeated pages of "
        "the same Form 5-105 source document. q016 has been removed and "
        "its content archived in this record's recovery_notes."
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat1_dual_model_with_duplicate_removal",
        "method": "sonnet_vision_plus_qwen_vision_with_user_source_review",
        "fields_corrected": [
            "Name", "Allotment number", "Tribe/Reservation", "NOTES",
        ],
        "previous_values": previous,
        "corrected_values": {
            "Name": "Mrs. Anna Shuck",
            "Allotment number": "7394",
            "Tribe/Reservation": "Rosebud Sioux",
        },
        "models_summary": (
            "Both Sonnet and Qwen vision agree on name='Mrs. Anna Shuck' "
            "and allotment='7394' across all pages of both q015 and q016."
        ),
        "user_confirmed_tribe": True,
        "user_confirmed_duplicate_removal": True,
        "removed_duplicate_record": "part1_questionnaire_016.json",
        "archived_q016_extraction": (
            q016_archive.get("extraction") if q016_archive else None
        ),
        "rationale": (
            "User source-page review on 2026-05-04 confirmed q015 (4 "
            "pages) and q016 (2 pages) are the same Form 5-105 source "
            "document — splitter produced two records with overlapping/"
            "repeated pages. q016 removed as duplicate; q015 retained "
            "as canonical record."
        ),
    })

    with open(Q015_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    # Delete q016
    if Q016_PATH.exists():
        Q016_PATH.unlink()
        print(f"Deleted duplicate: {Q016_PATH.name}")
    print(f"Patched canonical record: {Q015_PATH.name}")
    print(f"  Name:      Mrs. Anna Shuck")
    print(f"  Allotment: 7394")
    print(f"  Tribe:     Rosebud Sioux")
    print(f"  q016 content archived in q015 recovery_notes")


if __name__ == "__main__":
    main()
