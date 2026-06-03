#!/usr/bin/env python3
"""
Patch three testimony records to record a historian-arbitrated merge
between Citizen Potawatomi testimony and BLM Potawatami patents.

Background:
  Jacob Haskell and Lucius Eldridge gave testimony to the 1928 Circular
  2464 investigation identifying themselves as Citizen Potawatomi. Their
  BLM allotment patents (accessions 715705 and 715714 respectively) are
  recorded under BLM's `preferred_name = "Potawatami"` (no terminal "i"),
  a distinct tribe label in the IATH crosswalk vocabulary.

  Christian (historian) reviewed the records 2026-06-03 and confirmed
  that the name + allotment match identifies the same individuals despite
  the tribe-label divergence. The merge is a deliberate cross-vocabulary
  decision, not a string-match accident.

What this patch does:
  Adds a top-level field `"manual_authoritative_tribe": "Potawatami"` to
  each affected record. The Circular 2464 loader honors this field when
  present and uses its value as `authoritative_tribe` instead of the value
  resolved from `tribe_crosswalk`. This routes the testimony→BLM join to
  the correct patent without falsifying the source's tribe_reservation
  string ("Citizen Potawatomie" remains as recorded in the affidavit).

  Each record also gains a recovery_notes entry documenting the merge.

Confirmed by Christian 2026-06-03:
  "JACOB HASKELL: good catch. you can merge his record. LUCIUS ELDRIDGE:
   ditto, merge."

External cross-references:
  Jacob Haskell    -> BLM accession 715705 (Indian Fee Patent, 1919-10-30)
  Lucius Eldridge  -> BLM accession 715714 (Indian Fee Patent, 1919-10-30)

Affected files:
  part10_shawnee_21.json         Jacob Haskell    (agency_narrative)
  part10_questionnaire_010.json  Lucius Eldridge  (questionnaire)
  part10_shawnee_12.json         Lucius Eldridge  (agency_narrative)
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
SONNET_DIR = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

OVERRIDE_TRIBE = "Potawatami"

TARGETS = [
    ("part10_shawnee_21.json",         "Jacob Haskell",   "1170", "715705"),
    ("part10_questionnaire_010.json",  "Lucius Eldridge", "86",   "715714"),
    ("part10_shawnee_12.json",         "Lucius Eldridge", "86",   "715714"),
]


def patch_file(path: Path, expected_name: str, expected_allot: str,
                blm_accession: str) -> bool:
    with open(path) as f:
        record = json.load(f)
    if record.get("manual_authoritative_tribe") == OVERRIDE_TRIBE:
        print(f"  {path.name}: already has manual_authoritative_tribe={OVERRIDE_TRIBE!r}, skipping")
        return False
    ext = record.get("extraction", {})
    if ext.get("Name") != expected_name:
        print(f"  {path.name}: Name is {ext.get('Name')!r}, expected {expected_name!r} — refusing")
        return False
    if ext.get("Allotment number") != expected_allot:
        print(f"  {path.name}: Allotment is {ext.get('Allotment number')!r}, expected {expected_allot!r} — refusing")
        return False

    record["manual_authoritative_tribe"] = OVERRIDE_TRIBE
    record.setdefault("recovery_notes", []).append({
        "date": "2026-06-03",
        "type": "blm_tribe_merge_override",
        "method": "historian_arbitration_with_blm_cross_reference",
        "fields_added": ["manual_authoritative_tribe"],
        "manual_authoritative_tribe": OVERRIDE_TRIBE,
        "rationale": (
            f"Testimony records {expected_name} (allotment {expected_allot}) "
            "as Citizen Potawatomie. The matching BLM patent (accession "
            f"{blm_accession}) carries preferred_name = 'Potawatami' (a "
            "distinct IATH-canonical tribe from 'Citizen Potawatomi'). "
            "Historian arbitration confirms the same individual; this field "
            "overrides the crosswalk-resolved authoritative_tribe at load "
            "time so the testimony joins to the correct BLM record. The "
            "source-document tribe_reservation 'Citizen Potawatomie' is "
            "preserved as-recorded."
        ),
        "external_refs": {
            "BLM_accession": blm_accession,
            "BLM_url": (
                f"https://glorecords.blm.gov/details/patent/default.aspx?"
                f"accession={blm_accession}&docClass=SER"
            ),
        },
        "user_confirmed": True,
    })
    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"  {path.name}: added manual_authoritative_tribe={OVERRIDE_TRIBE!r}  ({expected_name}, allot {expected_allot} -> BLM {blm_accession})")
    return True


def main() -> None:
    if not SONNET_DIR.is_dir():
        print(f"ERROR: not found: {SONNET_DIR}")
        sys.exit(1)
    print(f"Adding manual_authoritative_tribe={OVERRIDE_TRIBE!r} to {len(TARGETS)} files")
    changed = 0
    for name, expected_name, expected_allot, blm_acc in TARGETS:
        path = SONNET_DIR / name
        if not path.exists():
            print(f"  {name}: file missing, skipping")
            continue
        if patch_file(path, expected_name, expected_allot, blm_acc):
            changed += 1
    print(f"\n{changed} file(s) patched.")


if __name__ == "__main__":
    main()
