#!/usr/bin/env python3
"""
Update Mary Julia Neiss's cross-reference now that Alphonse Charbonneau
has his own corpus record.

Earlier today (2026-04-30), the Mary Julia Neiss patch on
part3_agency_narrative_014 included a NOTES annotation saying:
  'CROSS-REFERENCE: Alphonse Charbonneau (allotment 1466) has no primary
   record in extractions/sonnet but is captured in Kimi v5 corpus...'

That statement is now obsolete. Part 4 has been extracted (2026-05-02) and
Alphonse Charbonneau's primary corpus record now exists at
part4_agency_narrative_016 with allotment 1466 confirmed by all three
extractions (Sonnet, Kimi v3, Kimi v4).

This patch updates the NOTES annotation to point to Alphonse's actual
corpus record location instead of saying he has none.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
RECORD_PATH = (
    PROJECT_ROOT
    / "circular_2464_extractions"
    / "extractions"
    / "sonnet"
    / "part3_agency_narrative_014.json"
)

OBSOLETE_FRAGMENT = (
    "CROSS-REFERENCE: Alphonse Charbonneau (allotment 1466) "
    "has no primary record in extractions/sonnet but is captured in "
    "Kimi v5 corpus; his land was purchased by Jesse E. Keeler. "
)

REPLACEMENT_FRAGMENT = (
    "CROSS-REFERENCE: Alphonse Charbonneau (allotment 1466) has his own "
    "primary corpus record at part4_agency_narrative_016.json (created "
    "2026-05-02 when part 4 was extracted; allotment 1466 confirmed by "
    "Sonnet, Kimi v3, and Kimi v4). His land was purchased by Jesse E. "
    "Keeler. "
)


def main():
    with open(RECORD_PATH) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        print("ERROR: list-shaped extraction")
        return

    notes = e.get("NOTES") or ""
    if OBSOLETE_FRAGMENT not in notes:
        print("WARNING: obsolete fragment not found in NOTES.")
        print("Either it was already updated, or the wording differs.")
        print("Aborting — manual review needed.")
        return

    notes = notes.replace(OBSOLETE_FRAGMENT, REPLACEMENT_FRAGMENT)
    e["NOTES"] = notes

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-02",
        "type": "cross_reference_update_after_part4_extraction",
        "method": "automated_post_extraction_audit",
        "fields_corrected": ["NOTES"],
        "rationale": (
            "Earlier annotation said Alphonse Charbonneau had no primary "
            "corpus record. Part 4 extraction on 2026-05-02 created his "
            "primary record at part4_agency_narrative_016 with allotment "
            "1466 confirmed by Sonnet, Kimi v3, and Kimi v4. NOTES updated "
            "to point to the actual record location."
        ),
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patch applied.")
    print(f"NOTES (last 400 chars):")
    print((notes)[-400:])


if __name__ == "__main__":
    main()
