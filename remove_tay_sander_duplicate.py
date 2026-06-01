#!/usr/bin/env python3
"""
Remove part3_affidavit_010 as a duplicate of part3_affidavit_011.

User source-page review (2026-05-04) of part 3 pages 79-80 confirmed
that part3_affidavit_010 ("Tay Sander", page 79) and
part3_affidavit_011 ("Nora Tway Sandery", page 80) are the same
person's affidavit. Page 79 is a garbled extraction of the same
document captured more cleanly at page 80 — the "Tay Sander" reading
is a degraded mis-transcription of "Nora Tway / Nora Sanders".

This follows the duplicate-removal precedent established for Anna
Shuck (part1_questionnaire_016 removed as duplicate of
part1_questionnaire_015):
  - The garbled/partial record (part3_affidavit_010) is removed
  - Its extraction is archived in the canonical record's recovery_notes
  - The canonical record (part3_affidavit_011) is retained

part3_affidavit_011 was already patched (allotment 4839, Oglala
Lakota) in the Pine Ridge CAT_3 batch. This script only removes the
duplicate and archives it.

Distinguish from continuation pages: this is a DUPLICATE (same content,
garbled second copy), not a continuation page (different page of the
same form). Continuation pages are kept; duplicates are removed.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

DUPLICATE_PATH = EXTRACTIONS / "part3_affidavit_010.json"
CANONICAL_PATH = EXTRACTIONS / "part3_affidavit_011.json"


def main():
    if not CANONICAL_PATH.exists():
        print(f"ERROR: canonical record {CANONICAL_PATH.name} not found")
        return

    # Read the duplicate (to archive) if it still exists
    duplicate_archive = None
    if DUPLICATE_PATH.exists():
        with open(DUPLICATE_PATH) as f:
            duplicate_archive = json.load(f)
    else:
        print(f"WARNING: {DUPLICATE_PATH.name} already absent; "
              f"will only annotate the canonical record")

    # Annotate the canonical record
    with open(CANONICAL_PATH) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        print("ERROR: canonical record has list-shaped extraction")
        return

    e["NOTES"] = (e.get("NOTES") or "") + (
        " | TASK 5 DUPLICATE REMOVAL 2026-05-04: part3_affidavit_010 "
        "('Tay Sander', part 3 page 79) was removed as a duplicate of "
        "this record. User source-page review confirmed pages 79 and 80 "
        "are the same person's affidavit; page 79 is a garbled extraction "
        "(the 'Tay Sander' reading is a degraded mis-transcription of "
        "'Nora Tway / Nora Sanders'). The removed record's extraction is "
        "archived in this record's recovery_notes."
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_duplicate_removal",
        "method": "user_source_page_review",
        "removed_duplicate_record": "part3_affidavit_010.json",
        "removed_duplicate_source_pages": "79",
        "canonical_record_source_pages": "80",
        "rationale": (
            "User confirmed via source pages 79-80 that part3_affidavit_010 "
            "and part3_affidavit_011 are the same person's affidavit. Page "
            "79 is a garbled extraction of the same document. 'Tay Sander' "
            "is a degraded mis-transcription of 'Nora Tway / Nora Sanders'. "
            "Removed as duplicate following the Anna Shuck "
            "(part1_questionnaire_016) precedent."
        ),
        "archived_duplicate_extraction": (
            duplicate_archive.get("extraction") if duplicate_archive else None
        ),
        "archived_duplicate_full_record": duplicate_archive,
        "user_confirmed": True,
    })

    with open(CANONICAL_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    # Delete the duplicate
    if DUPLICATE_PATH.exists():
        DUPLICATE_PATH.unlink()
        print(f"Deleted duplicate: {DUPLICATE_PATH.name}")
    print(f"Annotated canonical record: {CANONICAL_PATH.name}")
    print(f"  Removed record's extraction archived in recovery_notes")
    print()
    print(f"Canonical record stands as:")
    print(f"  Name:      {e.get('Name')}")
    print(f"  Allotment: {e.get('Allotment number')}")
    print(f"  Tribe:     {e.get('Tribe/Reservation')}")


if __name__ == "__main__":
    main()
