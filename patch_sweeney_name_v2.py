#!/usr/bin/env python3
"""
Update Laura Dean record's Name field to use 'James J. Sweeney'.

Current state:
  Name: 'Laura Dean (deceased allottee); heirs are William J. Sweeney, Sr.
         (husband) and William J. Sweeney, Jr. (son)'
  NOTES already contain a cross-reference annotation explaining that the
  master list says 'James J.' and the detail report says 'William J.'

User decision (2026-04-30): use 'James J. Sweeney' in the Name field per
the Shawnee master list (the canonical naming source for this record's
position on the master list); preserve the William J. detail-report text
in NOTES.

This patch updates only the Name field. The existing NOTES annotation is
already accurate.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
RECORD_PATH = (
    PROJECT_ROOT
    / "circular_2464_extractions"
    / "extractions"
    / "sonnet"
    / "part10_questionnaire_017.json"
)

# The Name we want, reflecting master list while acknowledging the family
# composition documented in the detail report.
NEW_NAME = (
    "Laura Dean (deceased allottee); filed by James J. Sweeney (husband) "
    "for the deceased wife and their minor child"
)


def main():
    with open(RECORD_PATH) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        print("ERROR: list-shaped extraction")
        return

    previous_name = e.get("Name", "")
    e["Name"] = NEW_NAME

    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-30",
        "type": "task5_name_field_update_per_master_list",
        "method": "user_decision_to_use_master_list_attestation",
        "fields_corrected": ["Name"],
        "previous_name": previous_name,
        "corrected_name": NEW_NAME,
        "rationale": (
            "Per user decision, the Shawnee master list's 'James J. Sweeney' "
            "is the canonical husband name in the Name field. The detail "
            "report's William J. Sweeney text is preserved in NOTES via the "
            "earlier source cross-reference annotation."
        ),
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Previous: {previous_name}")
    print(f"Updated:  {NEW_NAME}")


if __name__ == "__main__":
    main()
