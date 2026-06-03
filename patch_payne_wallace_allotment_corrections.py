#!/usr/bin/env python3
"""
Patch four testimony records whose allotment numbers were misread by
Sonnet's text extraction. Both allottees self-identified as Citizen
Potawatomi in 1928 and the corrected allotments cross-reference to
real BLM Citizen Potawatomi patents.

Confirmed by Christian (historian) 2026-06-03:
  "Addie Easton Payne is allotment 162, Citizen Potawatami.
   Viola Wallace is allotment 1159 and she is Citizen Potawatami."

Corrections:
  Mrs. Addie Easton Payne:  '168'   -> '162'    (BLM accession 715702)
  Viola Wallace:            '15609' -> '1159'   (BLM accession 715737)

Both BLM patents are Indian Fee Patents signed 1919-10-30 — the same
day as Haskell and Eldridge, suggesting a single batch of Citizen
Potawatomi forced fee patents whose receipts produced the 1928
testimony corpus.

Affected files:
  part10_questionnaire_015.json   Payne     (questionnaire)
  part10_shawnee_30.json          Payne     (agency_narrative)
  part10_shawnee_35.json          Wallace   (agency_narrative)
  part11_questionnaire_002b.json  Wallace   (questionnaire; post-split file)

The existing patch_addie_payne.py was a substantive Q&A recovery and
did not touch the allotment number. This patch is allotment-only.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
SONNET_DIR = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

# (json_filename, expected_name, expected_old_allot, corrected_allot, blm_accession)
TARGETS = [
    ("part10_questionnaire_015.json",  "Mrs. Addie Easton Payne", "168",   "162",  "715702"),
    ("part10_shawnee_30.json",         "Mrs. Addie Easton Payne", "168",   "162",  "715702"),
    ("part10_shawnee_35.json",         "Viola Wallace",           "15609", "1159", "715737"),
    ("part11_questionnaire_002b.json", "Viola Wallace",           "15609", "1159", "715737"),
]


def patch_file(path: Path, expected_name: str, old_allot: str,
                new_allot: str, blm_accession: str) -> bool:
    with open(path) as f:
        record = json.load(f)
    ext = record.get("extraction", {})
    if ext.get("Name") != expected_name:
        print(f"  {path.name}: Name is {ext.get('Name')!r}, expected {expected_name!r} — refusing")
        return False
    current = ext.get("Allotment number")
    if current == new_allot:
        print(f"  {path.name}: already {new_allot}, skipping")
        return False
    if current != old_allot:
        print(f"  {path.name}: allotment is {current!r}, expected {old_allot!r} — refusing")
        return False

    ext["Allotment number"] = new_allot
    record.setdefault("recovery_notes", []).append({
        "date": "2026-06-03",
        "type": "allotment_number_correction",
        "method": "historian_arbitration_with_blm_cross_reference",
        "previous_values": {"Allotment number": old_allot},
        "corrected_values": {"Allotment number": new_allot},
        "rationale": (
            f"Sonnet text extraction misread the allotment number as "
            f"{old_allot!r}. Source-verified correct allotment is "
            f"{new_allot!r}; cross-referenced with BLM accession "
            f"{blm_accession} (Indian Fee Patent, 1919-10-30, "
            "Citizen Potawatomi)."
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
    print(f"  {path.name}: {expected_name} {old_allot} -> {new_allot}  (BLM {blm_accession})")
    return True


def main() -> None:
    if not SONNET_DIR.is_dir():
        print(f"ERROR: not found: {SONNET_DIR}")
        sys.exit(1)
    print(f"Patching allotment misreads in {len(TARGETS)} files")
    changed = 0
    for name, expected_name, old, new, blm in TARGETS:
        path = SONNET_DIR / name
        if not path.exists():
            print(f"  {name}: file missing, skipping")
            continue
        if patch_file(path, expected_name, old, new, blm):
            changed += 1
    print(f"\n{changed} file(s) patched.")


if __name__ == "__main__":
    main()
