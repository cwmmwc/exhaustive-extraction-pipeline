#!/usr/bin/env python3
"""
Apply allotment-number patches for 49 HIGH-confidence records.

Background: Sonnet text-extraction systematically misclassified the allotment
numbers on Pine Ridge typewritten affidavits and similar forms. The "No. NNNN"
header on each page (which IS the allotment number) was captured in NOTES as
a "document number" or "Document No." instead of being placed in the
structured Allotment number field.

User-confirmed exemplars (BLM verified):
  - Eugene Means: NOTES "document number No. 2249" → BLM allotment 2249
  - Lucy Patton: NOTES "document No. 6802" → BLM allotment 6802

The hypothesis was confirmed via BLM cross-reference. A regex diagnostic
identified 64 candidate records; user review of the 49 HIGH-confidence
proposals confirmed 47 clean cases plus 2 split-digit cases (where the
number on the source had a stray space, breaking the regex):

  Split-digit corrections (manually verified from snippet):
    - pine_ridge_vol2_affidavit_082 (Prudy Cuny):
        regex captured "27"; source says "27 60" → allotment 2760
    - pine_ridge_vol2_affidavit_097 (Emma Black Feather):
        regex captured "30"; source says "30 34" → allotment 3034

  Name-alternate annotation (no allotment change needed):
    - pine_ridge_vol3_affidavit_089 (Ellen Running Hawk, nee Jarvis):
        allotment 6502 is correct; BLM patent name is "Jarvis" (maiden name
        only, married surname added after patent issuance). Same pattern as
        Lorrain Midkiff Wellborn / Lorain Midkiff (Task 3, Section B).

This patch script:
  1. Walks the 49 HIGH records
  2. Verifies current Allotment field is "not stated" (safety guard)
  3. For 47 clean cases: writes the candidate number to Allotment field
  4. For 2 split-digit cases: writes the manually corrected number
  5. For Ellen Running Hawk: writes the allotment AND adds name-alternate note
  6. Adds audit entry to each record's recovery_notes

The 15 lower-confidence records (REVIEW, LOW, SKIP categories from the
proposal TSV) are NOT touched by this script. They remain available for
individual review later.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

# --------------------------------------------------------------------------
# Patch manifest. Each entry is (filename, allotment, optional_extra_note).
# 47 clean HIGH-confidence patches + 2 split-digit corrections.
# Order matches the TSV for ease of review.
# --------------------------------------------------------------------------
PATCHES = [
    # Clean HIGH (regex got the number right)
    ("part1_questionnaire_011.json", "10662", None),
    ("part2_affidavit_002.json", "424", None),
    ("part2_questionnaire_022.json", "620", None),
    ("part3_affidavit_004.json", "4447", None),
    ("part6_questionnaire_003.json", "1196", None),
    ("part6_questionnaire_025.json", "1936", None),
    ("part7_questionnaire_011.json", "22991", None),
    ("part8_affidavit_001.json", "24232", None),
    ("part8_affidavit_002.json", "2572", None),
    ("part8_questionnaire_008.json", "2878", None),
    ("part9_questionnaire_020.json", "5569", None),
    ("pine_ridge_vol1_affidavit_002.json", "45", None),
    ("pine_ridge_vol1_affidavit_003.json", "51", None),
    ("pine_ridge_vol1_affidavit_004.json", "53", None),
    ("pine_ridge_vol1_affidavit_011.json", "211", None),
    ("pine_ridge_vol1_affidavit_014.json", "279", None),
    ("pine_ridge_vol1_affidavit_015.json", "286", None),
    ("pine_ridge_vol1_affidavit_020.json", "312", None),
    ("pine_ridge_vol1_affidavit_036.json", "406", None),
    ("pine_ridge_vol1_affidavit_041.json", "479", None),
    ("pine_ridge_vol1_affidavit_044.json", "710", None),
    ("pine_ridge_vol1_affidavit_100.json", "1353", None),
    ("pine_ridge_vol2_affidavit_021.json", "2249", None),
    ("pine_ridge_vol2_affidavit_025.json", "2296", None),
    ("pine_ridge_vol2_affidavit_033.json", "2460", None),
    ("pine_ridge_vol2_affidavit_040.json", "2552", None),
    ("pine_ridge_vol2_affidavit_057.json", "2665", None),
    ("pine_ridge_vol2_affidavit_058.json", "2667", None),
    ("pine_ridge_vol2_affidavit_081.json", "2759", None),

    # Split-digit corrections (regex captured first chunk only)
    ("pine_ridge_vol2_affidavit_082.json", "2760",
     "Split-digit fix: NOTES read 'Document No. 27 60' (stray space "
     "between digits in source); regex captured '27' but actual allotment "
     "is 2760. Confirmed by user review."),
    ("pine_ridge_vol2_affidavit_097.json", "3034",
     "Split-digit fix: NOTES read 'document number No. 30 34' (stray space "
     "between digits in source); regex captured '30' but actual allotment "
     "is 3034. Confirmed by user review."),

    # Continuing clean HIGH
    ("pine_ridge_vol2_affidavit_098.json", "3037", None),
    ("pine_ridge_vol3_affidavit_021.json", "4202", None),
    ("pine_ridge_vol3_affidavit_026.json", "4441", None),
    ("pine_ridge_vol3_affidavit_042.json", "4572", None),
    ("pine_ridge_vol3_affidavit_043.json", "4574", None),
    ("pine_ridge_vol3_affidavit_051.json", "4707", None),
    ("pine_ridge_vol3_affidavit_063.json", "5460", None),
    ("pine_ridge_vol3_affidavit_067.json", "5544", None),
    ("pine_ridge_vol3_affidavit_075.json", "5755", None),
    ("pine_ridge_vol3_affidavit_077.json", "5845", None),
    ("pine_ridge_vol3_affidavit_082.json", "6094", None),

    # Name-alternate annotation case
    ("pine_ridge_vol3_affidavit_089.json", "6502",
     "Name-alternate note: BLM patent record uses surname 'Jarvis' (maiden "
     "name); the corpus name 'Ellen Running Hawk, nee Jarvis' captures both. "
     "Same pattern as Lorrain Midkiff Wellborn / Lorain Midkiff in Task 3."),

    # Continuing clean HIGH
    ("pine_ridge_vol3_affidavit_090.json", "6753", None),
    ("pine_ridge_vol3_affidavit_091.json", "6801", None),
    ("pine_ridge_vol3_affidavit_092.json", "6802", None),
    ("pine_ridge_vol3_affidavit_097.json", "7390", None),
    ("pine_ridge_vol3_affidavit_099.json", "7584", None),
    ("pine_ridge_vol3_affidavit_101.json", "7917", None),
]

CORPUS_NOTE = (
    " | TASK 5 BULK ALLOTMENT RECOVERY 2026-04-29: Sonnet text-extraction "
    "captured the allotment number from the source page header but classified "
    "it in NOTES as a 'document number' / 'Document No.' / 'No. NNNN' instead "
    "of placing it in the structured Allotment number field. The hypothesis "
    "that these document/file references are actually allotment numbers was "
    "confirmed via BLM cross-reference (exemplars: Eugene Means 2249, Lucy "
    "Patton 6802). This patch corrects 49 records via bulk regex extraction "
    "from NOTES with user-supervised review of every HIGH-confidence proposal."
)


def patch_one(filename, allotment, extra_note):
    path = EXTRACTIONS / filename
    if not path.exists():
        return False, f"NOT FOUND"

    with open(path) as f:
        record = json.load(f)
    current = record["extraction"]

    actual_allot = (current.get("Allotment number") or "").strip()
    if actual_allot not in ("", "not stated"):
        return False, (
            f"Allotment field already populated ('{actual_allot}'); "
            f"refusing to overwrite. Manual review needed."
        )

    # Apply
    current["Allotment number"] = allotment
    note = CORPUS_NOTE
    if extra_note:
        note += " | " + extra_note
    current["NOTES"] = (current.get("NOTES") or "") + note

    audit = {
        "date": "2026-04-29",
        "type": "task5_bulk_allotment_recovery_from_notes",
        "method": "regex_extraction_with_user_review",
        "fields_corrected": ["Allotment number", "NOTES"],
        "previous_allotment": "not stated",
        "corrected_allotment": allotment,
        "rationale": (
            "Source page header contained 'No. NNNN' which Sonnet captured "
            "in NOTES as 'document number' rather than placing in structured "
            "Allotment field. Hypothesis confirmed via BLM cross-reference."
        ),
        "user_confirmed": True,
    }
    if extra_note:
        audit["additional_note"] = extra_note

    record.setdefault("recovery_notes", []).append(audit)

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    return True, f"Allotment: not stated -> {allotment}"


def main():
    print("=" * 70)
    print(f"Task 5 bulk allotment recovery: {len(PATCHES)} records")
    print("=" * 70)

    ok = 0
    failed = []
    for filename, allotment, extra in PATCHES:
        path_exists = (EXTRACTIONS / filename).exists()
        success, msg = patch_one(filename, allotment, extra)
        marker = "  " if success else "X "
        print(f"{marker}{filename:50s} {msg}")
        if success:
            ok += 1
        else:
            failed.append(filename)

    print()
    print("=" * 70)
    print(f"Patches applied: {ok}/{len(PATCHES)}")
    if failed:
        print(f"Failed: {failed}")
    print()
    print("These records are now searchable by allotment number in the corpus.")


if __name__ == "__main__":
    main()
