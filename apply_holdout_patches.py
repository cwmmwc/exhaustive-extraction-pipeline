#!/usr/bin/env python3
"""
Apply 4 holdout allotment patches.

Records held back from earlier bulk patches because the regex couldn't
disambiguate without source review. User confirmed all four via direct
source inspection; Mary Julia Neiss additionally confirmed via Kimi v5
parallel extraction.

Patches:
  1. Mary Julia Neiss (part3_agency_narrative_014) -> allotment 1463
     Sonnet's original NOTES misattributed 1463 to Alphonse Charbonneau
     and 1466 to "another allottee." User source-page review confirmed
     1463 is Mary Julia's, 1466 is Alphonse's. Kimi v5 extraction at
     /circular_2464_extractions/v5/RG 75 1929 circular 2464 part 3/
     Kimi K2.5.json confirms: entity "Mary Julia Neiss" context
     "Allottee No. 1463" and entity "Alphonse Charbonneau" context
     "Allottee No. 1466". Patch adds cross-reference note to Alphonse
     Charbonneau (no primary record in extractions/sonnet, but Kimi v5
     captures him + purchaser Jesse E. Keeler).

  2. William Courtis (part1_questionnaire_025) -> allotment 50
     Sonnet's NOTES called 50 a "File reference"; user confirmed it's
     the allotment number.

  3. part3_agency_narrative_page059 -> allotment 112
     User source-page review confirmed.

  4. part3_agency_narrative_page060 -> allotment 112
     User source-page review confirmed; same case as page059 (likely
     two-page sequential narrative about the same case 112).
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {
        "filename": "part3_agency_narrative_014.json",
        "expected_name": "Mary Julia Neiss",
        "allotment": "1463",
        "extra_note": (
            "Sonnet's original NOTES misattributed 1463 to Alphonse Charbonneau "
            "and described 1466 as belonging to another allottee. User source-"
            "page review confirms 1463 is Mary Julia Neiss's allotment, 1466 "
            "is Alphonse Charbonneau's. Confirmed by Kimi v5 parallel "
            "extraction (entity 'Mary Julia Neiss', context 'Allottee No. "
            "1463'). CROSS-REFERENCE: Alphonse Charbonneau (allotment 1466) "
            "has no primary record in extractions/sonnet but is captured in "
            "Kimi v5 corpus; his land was purchased by Jesse E. Keeler. "
            "Mary Julia's purchaser per Kimi v5: Kenneth Sellers."
        ),
    },
    {
        "filename": "part1_questionnaire_025.json",
        "expected_name": "William Courtis",
        "allotment": "50",
        "extra_note": (
            "Sonnet's original NOTES labeled 50 as 'File reference: No. 50' but "
            "user source-page review confirms 50 is the allotment number. Same "
            "misclassification pattern as the bulk allotment recovery batch "
            "(Pine Ridge typewritten affidavit headers)."
        ),
    },
    {
        "filename": "part3_agency_narrative_page059.json",
        "expected_name": "not stated",
        "allotment": "112",
        "extra_note": (
            "Sonnet's original NOTES described 112 as part of a 'File reference: "
            "5-114-2, Circular 2464, No. 112' but user source-page review "
            "confirms 112 is the allotment number for the case discussed."
        ),
    },
    {
        "filename": "part3_agency_narrative_page060.json",
        "expected_name": "not stated",
        "allotment": "112",
        "extra_note": (
            "Sonnet's original NOTES described 112 as 'Document reference: "
            "5-1142, No. 112' but user source-page review confirms 112 is the "
            "allotment number. Likely two-page sequential narrative (page059 "
            "and page060) about the same case 112."
        ),
    },
]

CORRECTION_NOTE_PREFIX = (
    " | TASK 5 HOLDOUT ALLOTMENT RECOVERY 2026-04-30: "
)


def patch_one(spec):
    path = EXTRACTIONS / spec["filename"]
    if not path.exists():
        return False, "NOT FOUND"

    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]

    if isinstance(e, list):
        return False, "List-shaped extraction (multi-allottee bundle?). Manual review needed."
    if not isinstance(e, dict):
        return False, f"Unexpected shape: {type(e).__name__}"

    actual_name = e.get("Name") or ""
    if actual_name != spec["expected_name"]:
        return False, (
            f"Name mismatch: expected '{spec['expected_name']}', "
            f"got '{actual_name}'"
        )

    actual_allot = (e.get("Allotment number") or "").strip()
    if actual_allot not in ("", "not stated"):
        return False, f"Allotment already set ('{actual_allot}'); refusing to overwrite"

    e["Allotment number"] = spec["allotment"]
    e["NOTES"] = (e.get("NOTES") or "") + CORRECTION_NOTE_PREFIX + spec["extra_note"]

    record.setdefault("recovery_notes", []).append({
        "date": "2026-04-30",
        "type": "task5_holdout_allotment_recovery",
        "method": "user_source_page_review",
        "fields_corrected": ["Allotment number", "NOTES"],
        "previous_allotment": "not stated",
        "corrected_allotment": spec["allotment"],
        "rationale": spec["extra_note"],
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    return True, f"Allotment: not stated -> {spec['allotment']}"


def main():
    print("=" * 70)
    print(f"Task 5 holdout allotment recovery: {len(PATCHES)} records")
    print("=" * 70)

    ok = 0
    for spec in PATCHES:
        success, msg = patch_one(spec)
        marker = "  " if success else "  - "
        print(f"{marker}{spec['filename']:50s} {msg}")
        if success:
            ok += 1

    print()
    print(f"Patches applied: {ok}/{len(PATCHES)}")


if __name__ == "__main__":
    main()
