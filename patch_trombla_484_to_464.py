#!/usr/bin/env python3
"""
Patch the two remaining Nicholas Trombla records that still carry the
wrong allotment number 484.

Background:
  Sonnet text-extraction wrote allotment "484" for both
    - part10_shawnee_33.json   (agency_narrative)
    - part11_affidavit_001.json (affidavit)
  but Trombla's source-verified allotment is 464 (Citizen Potawatomi,
  BLM accession 715720). The third Trombla record,
  part11_questionnaire_001.json, was already corrected on 2026-04-28
  by patch_nicholas_trombla.py. These two were missed.

  484 happens to be another real Citizen Potawatomi allotment in BLM,
  belonging to KE-WAH-O-MEK (Prairie Band Of Potawatami Nation,
  accession 0541-477) — an unrelated allottee. Leaving the corpus at
  484 would cross-link Trombla's testimony to the wrong patent.

Confirmed by Christian (historian) 2026-06-03:
  "Trombla is 464, not 484 and has no discernible relationship to
   KE-WAH-O-MEK. KE-WAH-O-MEK is allotment 484 but he is Prairie
   Band Of Potawatami Nation."

This script:
  - Changes extraction["Allotment number"] from "484" to "464" in both files
  - Appends a recovery_notes entry documenting the correction
  - Idempotent: refuses to act on a file whose allotment is not "484"

External cross-reference:
  BLM patent accession 715720 (Indian Fee Patent, 1919-10-13)
  https://glorecords.blm.gov/details/patent/default.aspx?accession=715720&docClass=SER
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
SONNET_DIR = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

TARGETS = [
    "part10_shawnee_33.json",
    "part11_affidavit_001.json",
]

RECOVERY_NOTE = {
    "date": "2026-06-03",
    "type": "allotment_number_correction",
    "method": "historian_arbitration_with_blm_cross_reference",
    "previous_values": {"Allotment number": "484"},
    "corrected_values": {"Allotment number": "464"},
    "rationale": (
        "Allotment 484 in BLM belongs to KE-WAH-O-MEK (Prairie Band Of "
        "Potawatami Nation, accession 0541-477), unrelated to Trombla. "
        "Trombla's source-verified allotment is 464 (Citizen Potawatomi); "
        "cross-referenced with BLM accession 715720. The other Trombla "
        "record (part11_questionnaire_001) was corrected 2026-04-28 by "
        "patch_nicholas_trombla.py; these two records were missed in that pass."
    ),
    "external_refs": {
        "BLM_accession": "715720",
        "BLM_url": (
            "https://glorecords.blm.gov/details/patent/default.aspx?"
            "accession=715720&docClass=SER"
        ),
    },
    "user_confirmed": True,
}


def patch_file(path: Path) -> bool:
    with open(path) as f:
        record = json.load(f)
    ext = record.get("extraction", {})
    current = ext.get("Allotment number")
    if current == "464":
        print(f"  {path.name}: already 464, skipping")
        return False
    if current != "484":
        print(f"  {path.name}: allotment is {current!r}, expected '484' — refusing")
        return False
    ext["Allotment number"] = "464"
    record.setdefault("recovery_notes", []).append(RECOVERY_NOTE)
    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"  {path.name}: 484 -> 464")
    return True


def main() -> None:
    if not SONNET_DIR.is_dir():
        print(f"ERROR: not found: {SONNET_DIR}")
        sys.exit(1)
    print(f"Patching Trombla allotment 484 -> 464 in {len(TARGETS)} files")
    changed = 0
    for name in TARGETS:
        path = SONNET_DIR / name
        if not path.exists():
            print(f"  {name}: file missing, skipping")
            continue
        if patch_file(path):
            changed += 1
    print(f"\n{changed} file(s) patched.")


if __name__ == "__main__":
    main()
