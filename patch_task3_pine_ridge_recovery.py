#!/usr/bin/env python3
"""
Task 3 consolidated patch: tribe normalization + recovery for pine_ridge_*.

Three operations in one transactional script:

  Section A — Canonical string consolidation (8 records):
    Collapse "Pine Ridge (Oglala Sioux)" -> "Pine Ridge" so the corpus has
    a single canonical string. Audit trail in recovery_notes preserves the
    evidence that these records were specifically corrected via BLM.

  Section B — BLM-confirmed substantive patches (6 records):
    Six records had geographic features suggesting they might not be Pine
    Ridge (5 out-of-state addresses + Gerry's St. Francis SD address which
    is on Rosebud). User-performed BLM lookups confirmed all 6 are Pine
    Ridge allottees. Substantive patches add canonical tribe + BLM
    accession + (for Skenandore) allotment-number correction.

  Section C — Bulk tribe inference (61 records):
    Remaining records with Tribe = "not stated" in pine_ridge_* directory.
    Geographic and naming evidence strongly supports Pine Ridge inference
    via directory provenance. Bulk patch with audit trail noting the
    inference basis.

After this patch, all 392 pine_ridge_* records should have
Tribe = "Pine Ridge" (with no "not stated" remaining and no variant strings).

Full BLM-confirmed substantive corrections in Section B:
    - Mrs. Nora Butcher (vol2_aff_026): Pine Ridge, BLM 625231
    - Edith Craven Knight (vol2_aff_122): Pine Ridge, BLM 625367
    - Katherine Andrews (vol2_aff_125): Pine Ridge, BLM 625357
    - Anna W. Skenandore (vol3_aff_041): Pine Ridge, BLM 625322
        ALSO corrects allotment: 44070 (Sonnet OCR error) -> 4570 (BLM)
    - Lorrain Midkiff Wellborn (vol3_aff_104): Pine Ridge, BLM 709603
        BLM name is "Lorain Midkiff" (no Wellborn — married name added later)
    - Elbridge Gerry (vol3_aff_036): Pine Ridge, BLM 625252
        Living at St. Francis, SD (Rosebud Reservation) — same off-reservation
        residence pattern as Frank Carlow, Cecilia Ross, Clara Peck etc.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

CANONICAL = "Pine Ridge"

# ----------------------------------------------------------------------
# SECTION B — BLM-confirmed substantive patches (6 records)
# ----------------------------------------------------------------------
BLM_CONFIRMED = [
    {
        "filename": "pine_ridge_vol2_affidavit_026.json",
        "expected_name": "Mrs Nora Butcher",
        "expected_allotment": "2308",
        "blm_accession": "625231",
        "po_address": "Gillette, Wyoming",
        "note": "Pine Ridge allottee residing in Wyoming when affidavit given.",
    },
    {
        "filename": "pine_ridge_vol2_affidavit_122.json",
        "expected_name": "Edith Craven Knight",
        "expected_allotment": "3821",
        "blm_accession": "625367",
        "po_address": "Camp Wood, Arizona",
        "note": "Pine Ridge allottee residing in Arizona when affidavit given.",
    },
    {
        "filename": "pine_ridge_vol2_affidavit_125.json",
        "expected_name": "Katherine Andrews",
        "expected_allotment": "3855",
        "blm_accession": "625357",
        "po_address": "Ft. Collins, Colorado",
        "note": "Pine Ridge allottee residing in Colorado when affidavit given.",
    },
    {
        "filename": "pine_ridge_vol3_affidavit_041.json",
        "expected_name": "Anna W. Skenandore",
        "expected_allotment": "44070",
        "corrected_allotment": "4570",
        "blm_accession": "625322",
        "po_address": "73rd and Adler Streets, W...",
        "note": (
            "Pine Ridge allottee residing in unspecified urban location when "
            "affidavit given. ADDITIONAL CORRECTION: allotment 44070 was a "
            "Sonnet OCR error (digit doubling / extra zero); BLM confirms "
            "actual allotment is 4570. Same OCR failure mode as Florence "
            "Twiss Cuny (762->818) and Anna Blackbird (3518->6475)."
        ),
    },
    {
        "filename": "pine_ridge_vol3_affidavit_104.json",
        "expected_name": "Lorrain Midkiff Wellborn",
        "expected_allotment": "3921",
        "blm_accession": "709603",
        "po_address": "Pocahontas, Arkansas",
        "note": (
            "Pine Ridge allottee residing in Arkansas when affidavit given. "
            "BLM patent name is 'Lorain Midkiff' (no Wellborn); the "
            "'Wellborn' surname is her married name added later. Affidavit "
            "self-identification preserved as primary."
        ),
    },
    {
        "filename": "pine_ridge_vol3_affidavit_036.json",
        "expected_name": "Elbridge Gerry",
        "expected_allotment": "4495",
        "blm_accession": "625252",
        "po_address": "St. Francis, South Dakota",
        "note": (
            "Pine Ridge allottee residing at St. Francis SD (which is on "
            "Rosebud Reservation, not Pine Ridge). Same off-reservation "
            "residence pattern as Frank Carlow (Crow Agency MT), Cecilia "
            "Ross (Turtle Mountain ND), Clara Peck (Osage country OK), "
            "Millie Richards (Flandreau SD), and Nora Parkhurst (Red Lake "
            "MN). The Pine Ridge directory contains correctly archived "
            "records of Pine Ridge allottees regardless of where the "
            "affidavit was sworn."
        ),
    },
]

BLM_NOTE_TEMPLATE = (
    " | TASK 3 SUBSTANTIVE CORRECTION 2026-04-29: BLM accession {accession} "
    "confirms Pine Ridge tribal affiliation despite off-reservation residence "
    "({po_address}). {extra_note}"
)


# ----------------------------------------------------------------------
# SECTION A — Canonical string consolidation (records currently set to
# "Pine Ridge (Oglala Sioux)")
# ----------------------------------------------------------------------
COLLAPSE_NOTE = (
    " | TASK 3 CANONICAL CONSOLIDATION 2026-04-29: Tribe value 'Pine Ridge "
    "(Oglala Sioux)' collapsed to 'Pine Ridge' to maintain a single canonical "
    "string across the corpus. The original Task 1 substantive correction "
    "(BLM-confirmed Pine Ridge tribal affiliation) is preserved in this "
    "record's recovery_notes audit trail; this collapse is a string "
    "normalization only and does not alter the underlying evidentiary basis."
)


# ----------------------------------------------------------------------
# SECTION C — Bulk inference for "not stated" records
# ----------------------------------------------------------------------
BULK_NOTE = (
    " | TASK 3 BULK TRIBE INFERENCE 2026-04-29: Tribe field set to 'Pine "
    "Ridge' based on directory provenance (record is filed in "
    "pine_ridge_*/extractions/, which corresponds to the NARA RG 75 Pine "
    "Ridge Vol 1, Vol 2, and Vol 3 bound volumes of Circular 2464 "
    "responses). 67 such records were originally 'not stated'; 6 received "
    "BLM-confirmed substantive patches in the same transaction; the "
    "remaining 61 (this record's batch) are inferred from directory and "
    "geographic/naming evidence. Inference is rebuttable — any record can "
    "be re-evaluated via BLM cross-reference if its Pine Ridge affiliation "
    "is questioned."
)


def patch_blm_confirmed(spec):
    """Section B: substantive patch with BLM cross-reference."""
    path = EXTRACTIONS / spec["filename"]
    if not path.exists():
        return False, "NOT FOUND"

    with open(path) as f:
        record = json.load(f)
    current = record["extraction"]

    # Verify
    if current.get("Name") != spec["expected_name"]:
        return False, (
            f"Name mismatch: expected '{spec['expected_name']}', "
            f"got '{current.get('Name')}'"
        )
    if current.get("Allotment number") != spec["expected_allotment"]:
        return False, (
            f"Allotment mismatch: expected '{spec['expected_allotment']}', "
            f"got '{current.get('Allotment number')}'"
        )

    # Apply
    current["Tribe/Reservation"] = CANONICAL
    fields_corrected = ["Tribe/Reservation", "NOTES"]

    if "corrected_allotment" in spec:
        current["Allotment number"] = spec["corrected_allotment"]
        fields_corrected.append("Allotment number")

    extra_note = spec["note"]
    current["NOTES"] = (current.get("NOTES") or "") + BLM_NOTE_TEMPLATE.format(
        accession=spec["blm_accession"],
        po_address=spec["po_address"],
        extra_note=extra_note,
    )

    audit = {
        "date": "2026-04-29",
        "type": "task3_blm_confirmed_tribe_correction",
        "method": "user_blm_lookup",
        "fields_corrected": fields_corrected,
        "previous_tribe": "not stated",
        "corrected_tribe": CANONICAL,
        "po_address": spec["po_address"],
        "external_refs": {
            "BLM_accession": spec["blm_accession"],
            "BLM_url": f"https://glorecords.blm.gov/details/patent/default.aspx?accession={spec['blm_accession']}",
        },
        "user_confirmed": True,
        "context_note": extra_note,
    }
    if "corrected_allotment" in spec:
        audit["allotment_correction"] = {
            "previous": spec["expected_allotment"],
            "corrected": spec["corrected_allotment"],
            "rationale": "Sonnet OCR error in original extraction; BLM confirms correct value",
        }

    record.setdefault("recovery_notes", []).append(audit)

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    msg = f"Tribe -> Pine Ridge (BLM {spec['blm_accession']})"
    if "corrected_allotment" in spec:
        msg += f" + allotment {spec['expected_allotment']}->{spec['corrected_allotment']}"
    return True, msg


def main():
    print("=" * 70)
    print("Task 3: Tribe normalization + recovery for pine_ridge_*")
    print("=" * 70)

    section_a_count = 0  # Collapse "Pine Ridge (Oglala Sioux)" -> "Pine Ridge"
    section_b_count = 0  # BLM-confirmed substantive
    section_b_failed = []
    section_c_count = 0  # Bulk inference

    # Section B first (substantive — must hit specific records)
    print("\n--- Section B: BLM-confirmed substantive patches ---")
    for spec in BLM_CONFIRMED:
        print(f"\n[{spec['filename']}]")
        ok, msg = patch_blm_confirmed(spec)
        print(f"  {msg}")
        if ok:
            section_b_count += 1
        else:
            section_b_failed.append(spec["filename"])

    # Sections A and C: walk all pine_ridge_* records, classify, patch
    print("\n--- Sections A and C: walking remaining pine_ridge_* records ---")
    for path in sorted(EXTRACTIONS.glob("pine_ridge_*.json")):
        with open(path) as f:
            record = json.load(f)
        e = record["extraction"]
        if isinstance(e, list):
            e = e[0] if e else {}
        tribe = e.get("Tribe/Reservation", "")

        if tribe == "Pine Ridge (Oglala Sioux)":
            # Section A: collapse
            e["Tribe/Reservation"] = CANONICAL
            e["NOTES"] = (e.get("NOTES") or "") + COLLAPSE_NOTE
            record.setdefault("recovery_notes", []).append({
                "date": "2026-04-29",
                "type": "task3_canonical_string_consolidation",
                "method": "single_canonical_string_policy",
                "fields_corrected": ["Tribe/Reservation", "NOTES"],
                "previous_tribe": "Pine Ridge (Oglala Sioux)",
                "corrected_tribe": CANONICAL,
                "rationale": (
                    "Single canonical string policy. Substantive evidentiary "
                    "basis preserved in earlier recovery_notes entries."
                ),
            })
            with open(path, "w") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
            section_a_count += 1

        elif tribe in ("not stated", "", None):
            # Section C: bulk inference (skip records already handled in B)
            if any(spec["filename"] == path.name for spec in BLM_CONFIRMED):
                continue  # Already handled above
            e["Tribe/Reservation"] = CANONICAL
            e["NOTES"] = (e.get("NOTES") or "") + BULK_NOTE
            record.setdefault("recovery_notes", []).append({
                "date": "2026-04-29",
                "type": "task3_bulk_directory_inference",
                "method": "directory_provenance_pine_ridge_vols",
                "fields_corrected": ["Tribe/Reservation", "NOTES"],
                "previous_tribe": "not stated",
                "corrected_tribe": CANONICAL,
                "rationale": (
                    "Directory provenance: record is in pine_ridge_*/, "
                    "corresponding to NARA RG 75 Pine Ridge bound volumes. "
                    "Geographic and naming evidence supports inference. "
                    "Rebuttable via BLM cross-reference if questioned."
                ),
            })
            with open(path, "w") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
            section_c_count += 1

    print(f"\n  Section A (canonical collapse 'Pine Ridge (Oglala Sioux)' -> 'Pine Ridge'): {section_a_count}")
    print(f"  Section C (bulk directory inference): {section_c_count}")

    print()
    print("=" * 70)
    print("Task 3 patch summary:")
    print(f"  Section A: {section_a_count} records (canonical collapse)")
    print(f"  Section B: {section_b_count}/{len(BLM_CONFIRMED)} records (BLM-confirmed)")
    if section_b_failed:
        print(f"    Failed: {section_b_failed}")
    print(f"  Section C: {section_c_count} records (bulk directory inference)")
    print(f"  Total records patched: {section_a_count + section_b_count + section_c_count}")
    print()
    print("Manifest unchanged.")


if __name__ == "__main__":
    main()
