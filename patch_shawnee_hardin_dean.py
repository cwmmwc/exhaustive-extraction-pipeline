#!/usr/bin/env python3
"""
Patch two Shawnee Indian Agency master list cross-references.

Hannah Hardin (master list row 18) -> part10_questionnaire_012:
  - Sonnet captured allotment as '715412' but that's a patent number, not
    an allotment. User confirmed actual allotment is 42.
  - Tribe: Citizen Potawatomie (per user research).

Laura Dean (master list row 32) -> part10_questionnaire_017:
  - James J. Sweeney filed the response on behalf of his deceased wife
    Laura Dean (per the master list: 'James J. Sweeney for his deceased
    wife, Laura Dean and their minor child').
  - Allotment 845 already captured correctly.
  - Tribe: Citizen Potawatomie (per user research).

Both records had Tribe='not stated' or similar before this patch.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"


def patch_hannah_hardin():
    path = EXTRACTIONS / "part10_questionnaire_012.json"
    if not path.exists():
        return False, "NOT FOUND"
    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        return False, "List-shaped extraction"

    # Capture the previous (wrong) allotment for audit
    previous_allot = e.get("Allotment number", "")

    e["Allotment number"] = "42"
    e["Tribe/Reservation"] = "Citizen Potawatomie"
    e["NOTES"] = (e.get("NOTES") or "") + (
        " | TASK 5 SHAWNEE CROSS-REFERENCE 2026-04-30: Hannah Hardin is "
        "row 18 on the Shawnee Indian Agency master list (part10_page_035, "
        "transmitted by Supt. A. W. Leech, March 20, 1929). Her status on "
        "the master list is 'Report in detail attached' — this record IS "
        f"her detail report. Allotment number corrected from '{previous_allot}' "
        "(which is the patent number, not the allotment) to '42' per user "
        "research. Tribe set to 'Citizen Potawatomie' per user BLM research. "
        "Same patent-vs-allotment Sonnet misclassification we saw with Anna "
        "Blackbird's Form 5-105 record (where allotment field captured a "
        "patent reference number instead)."
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-30",
        "type": "task5_shawnee_cross_reference_with_blm_correction",
        "method": "user_research_with_master_list_cross_reference",
        "fields_corrected": ["Allotment number", "Tribe/Reservation", "NOTES"],
        "previous_values": {
            "Allotment number": previous_allot,
            "Tribe/Reservation": e.get("Tribe/Reservation_pre_patch", "(not captured)"),
        },
        "corrected_values": {
            "Allotment number": "42",
            "Tribe/Reservation": "Citizen Potawatomie",
        },
        "shawnee_master_list_row": 18,
        "user_confirmed": True,
        "extraction_failure_mode": (
            f"Sonnet captured patent number ('{previous_allot}') in the "
            "Allotment field. Same misclassification as Anna Blackbird's "
            "Form 5-105 record."
        ),
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"Allotment: '{previous_allot}' -> '42'; Tribe -> Citizen Potawatomie"


def patch_laura_dean():
    path = EXTRACTIONS / "part10_questionnaire_017.json"
    if not path.exists():
        return False, "NOT FOUND"
    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        return False, "List-shaped extraction"

    previous_allot = e.get("Allotment number", "")
    if previous_allot != "845":
        return False, f"Expected allotment 845, got '{previous_allot}' — manual review needed"

    e["Tribe/Reservation"] = "Citizen Potawatomie"
    e["NOTES"] = (e.get("NOTES") or "") + (
        " | TASK 5 SHAWNEE CROSS-REFERENCE 2026-04-30: Laura Dean is the "
        "deceased allottee whose Circular 2464 response was filed by her "
        "husband James J. Sweeney on her behalf. She is row 32 on the "
        "Shawnee Indian Agency master list (part10_page_036) where the "
        "entry reads 'James J. Sweeney for his deceased wife, Laura Dean "
        "and their minor child' — this record IS her detail report. "
        "Allotment 845 confirmed; tribe set to 'Citizen Potawatomie' per "
        "user BLM research."
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-30",
        "type": "task5_shawnee_cross_reference_tribe_assignment",
        "method": "user_research_with_master_list_cross_reference",
        "fields_corrected": ["Tribe/Reservation", "NOTES"],
        "corrected_values": {
            "Tribe/Reservation": "Citizen Potawatomie",
        },
        "shawnee_master_list_row": 32,
        "filed_by": "James J. Sweeney (husband, on behalf of deceased wife)",
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, "Tribe -> Citizen Potawatomie (allotment 845 already correct)"


def main():
    print("=" * 70)
    print("Shawnee master list cross-references: Hannah Hardin + Laura Dean")
    print("=" * 70)

    ok, msg = patch_hannah_hardin()
    print(f"\nHannah Hardin (row 18, part10_questionnaire_012):")
    print(f"  {msg}")

    ok2, msg2 = patch_laura_dean()
    print(f"\nLaura Dean (row 32, part10_questionnaire_017):")
    print(f"  {msg2}")

    print()
    successes = sum([ok, ok2])
    print(f"Patches applied: {successes}/2")


if __name__ == "__main__":
    main()
