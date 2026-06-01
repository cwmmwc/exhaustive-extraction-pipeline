#!/usr/bin/env python3
"""
Apply allotment-number patches v2 — fixed after v1 crash.

V1 crashed on pine_ridge_vol1_affidavit_020 because that record's
'extraction' field is a 2-item list, not a dict. The list contains
two distinct allottees (Sarah Thompson AND Hermos Merrivall) — same
multi-allottee bundle pattern as part11_questionnaire_002 (Rosa
Vanderbloom + Viola Wallace).

Changes from v1:
  1. Skip Sarah Thompson record (multi-allottee bundle, needs separate
     splitting work — same handling as part11_questionnaire_002)
  2. Defensive list-handling: detect list shape, refuse to write to it,
     log clearly so we catch any other multi-allottee bundles
  3. The 17 records already patched in v1 will be safely skipped by the
     existing 'already populated' guard

Multi-allottee bundles known so far:
  - part11_questionnaire_002 (Rosa Vanderbloom + Viola Wallace)
  - pine_ridge_vol1_affidavit_020 (Sarah Thompson + Hermos Merrivall)

There may be more. A separate diagnostic should scan the corpus for
list-shaped extraction records to surface them all at once.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

# Records to skip entirely — multi-allottee bundles needing separate handling
SKIP_RECORDS = {
    "part11_questionnaire_002.json",        # Vanderbloom + Wallace
    "pine_ridge_vol1_affidavit_020.json",   # Thompson + Merrivall
}

# Patch manifest. 47 clean HIGH + 2 split-digit corrections.
# Sarah Thompson removed (now in SKIP_RECORDS).
PATCHES = [
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
    # ("pine_ridge_vol1_affidavit_020.json", "312", None),  # SKIPPED: multi-allottee bundle
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

    # Split-digit corrections
    ("pine_ridge_vol2_affidavit_082.json", "2760",
     "Split-digit fix: NOTES read 'Document No. 27 60' (stray space "
     "between digits in source); regex captured '27' but actual allotment "
     "is 2760. Confirmed by user review."),
    ("pine_ridge_vol2_affidavit_097.json", "3034",
     "Split-digit fix: NOTES read 'document number No. 30 34' (stray space "
     "between digits in source); regex captured '30' but actual allotment "
     "is 3034. Confirmed by user review."),

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

    # Name-alternate annotation
    ("pine_ridge_vol3_affidavit_089.json", "6502",
     "Name-alternate note: BLM patent record uses surname 'Jarvis' (maiden "
     "name); the corpus name 'Ellen Running Hawk, nee Jarvis' captures both. "
     "Same pattern as Lorrain Midkiff Wellborn / Lorain Midkiff in Task 3."),

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
    "Patton 6802). This patch corrects 48 records via bulk regex extraction "
    "from NOTES with user-supervised review of every HIGH-confidence proposal. "
    "Sarah Thompson (pine_ridge_vol1_affidavit_020) was held out of this batch "
    "because that record is a multi-allottee bundle (Thompson + Merrivall) "
    "needing separate splitting work."
)


def patch_one(filename, allotment, extra_note):
    path = EXTRACTIONS / filename

    if filename in SKIP_RECORDS:
        return False, "SKIP (multi-allottee bundle)"

    if not path.exists():
        return False, "NOT FOUND"

    with open(path) as f:
        record = json.load(f)
    extraction = record["extraction"]

    # Defensive: if extraction is a list, refuse to write
    if isinstance(extraction, list):
        names = [item.get("Name", "?") for item in extraction if isinstance(item, dict)]
        return False, (
            f"MULTI-ALLOTTEE BUNDLE detected (extraction is list with "
            f"{len(extraction)} items: {names}). Add to SKIP_RECORDS and "
            f"handle via separate splitting patch."
        )

    if not isinstance(extraction, dict):
        return False, f"Unexpected extraction shape: {type(extraction).__name__}"

    actual_allot = (extraction.get("Allotment number") or "").strip()
    if actual_allot not in ("", "not stated"):
        return False, (
            f"Allotment field already populated ('{actual_allot}'); "
            f"skipping (likely already patched in v1 run)"
        )

    # Apply
    extraction["Allotment number"] = allotment
    note = CORPUS_NOTE
    if extra_note:
        note += " | " + extra_note
    extraction["NOTES"] = (extraction.get("NOTES") or "") + note

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
    print(f"Task 5 bulk allotment recovery v2: {len(PATCHES)} records")
    print("(records already patched in v1 will be safely skipped)")
    print("=" * 70)

    applied = 0
    skipped_existing = 0
    skipped_bundle = 0
    failed = []

    for filename, allotment, extra in PATCHES:
        success, msg = patch_one(filename, allotment, extra)
        marker = "  " if success else "  - "
        print(f"{marker}{filename:50s} {msg}")

        if success:
            applied += 1
        elif "already populated" in msg:
            skipped_existing += 1
        elif "MULTI-ALLOTTEE" in msg or "bundle" in msg:
            skipped_bundle += 1
        else:
            failed.append((filename, msg))

    print()
    print("=" * 70)
    print(f"Patches applied this run: {applied}")
    print(f"Already patched (v1):     {skipped_existing}")
    print(f"Skipped (bundle):         {skipped_bundle}")
    if failed:
        print(f"Other failures: {failed}")
    print()
    print(f"Total HIGH records covered: {applied + skipped_existing} of {len(PATCHES)}")


if __name__ == "__main__":
    main()
