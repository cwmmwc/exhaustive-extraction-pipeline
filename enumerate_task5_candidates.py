#!/usr/bin/env python3
"""
Task 5 candidate enumeration: vision recovery campaign on remaining records.

Identifies records where Sonnet text-extraction failed on identifying fields
(Name, Allotment number) and have NOT already been corrected via earlier
patches (Tasks 1, 3, 6, the pilot, Florence, Anna Blackbird).

Categorizes candidates by failure mode:
  CAT_1: Both Name AND Allotment "not stated" (hardest — no anchor)
  CAT_2: Name "not stated", Allotment captured (anchor by allotment)
  CAT_3: Name captured, Allotment "not stated" (anchor by name + BLM lookup)

Outputs a TSV manifest at validation_samples/task5_campaign/candidates.tsv
that the next session can use to drive the campaign.

Usage:
  python3 enumerate_task5_candidates.py
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
OUTPUT_DIR = PROJECT_ROOT / "validation_samples" / "task5_campaign"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Records already corrected in earlier work — exclude from candidate list.
# Matches recovery_notes entries with relevant types.
ALREADY_CORRECTED_TYPES = {
    "identity_recovery",
    "identity_recovery_with_revisit_flag",
    "substantive_record_recovery",
    "substantive_record_correction_with_blm_cross_reference",
    "substantive_record_correction_with_blm_and_sibling_documents",
    "substantive_record_recovery_with_sibling_finding",
    "cross_routing_correction",
    "task3_blm_confirmed_tribe_correction",
}


def already_corrected(record):
    """Has this record had any identity-correcting patch applied?"""
    for note in record.get("recovery_notes", []):
        if note.get("type") in ALREADY_CORRECTED_TYPES:
            return True
    return False


def main():
    cat1 = []  # both missing
    cat2 = []  # name missing only
    cat3 = []  # allotment missing only

    for path in sorted(EXTRACTIONS.glob("*.json")):
        if path.name == "usage_summary.json":
            continue

        try:
            record = json.load(open(path))
        except (json.JSONDecodeError, OSError):
            continue

        e = record.get("extraction", {})
        if isinstance(e, list):
            e = e[0] if e else {}

        # Skip records that have been corrected by earlier patches
        if already_corrected(record):
            continue

        name = (e.get("Name") or "").strip()
        allot = (e.get("Allotment number") or "").strip()
        doc_type = (e.get("Document type") or "").strip()
        po_addr = (e.get("Post Office Address") or "").strip()
        tribe = (e.get("Tribe/Reservation") or "").strip()

        name_missing = name in ("", "not stated")
        allot_missing = allot in ("", "not stated")

        # Filter out trivially-empty records (likely structural, not recoverable)
        # Use combined-content length as rough proxy for "is there any data here?"
        body_chars = sum(
            len(str(v)) for k, v in e.items()
            if k not in ("Name", "Allotment number") and v not in ("not stated", "", None)
        )
        if body_chars < 100:
            continue

        entry = {
            "filename": path.name,
            "name": name if name else "(blank)",
            "allotment": allot if allot else "(blank)",
            "tribe": tribe if tribe else "(blank)",
            "po_address": po_addr if po_addr else "(blank)",
            "doc_type": doc_type if doc_type else "(blank)",
            "body_chars": body_chars,
        }

        if name_missing and allot_missing:
            cat1.append(entry)
        elif name_missing:
            cat2.append(entry)
        elif allot_missing:
            cat3.append(entry)

    # Console summary
    print("=" * 70)
    print("Task 5 candidate enumeration")
    print("=" * 70)
    print()
    print(f"CAT 1 (Name + Allotment both missing): {len(cat1)}")
    print(f"CAT 2 (Name missing, allotment captured): {len(cat2)}")
    print(f"CAT 3 (Name captured, allotment missing): {len(cat3)}")
    print(f"Total candidates: {len(cat1) + len(cat2) + len(cat3)}")
    print()

    if cat1:
        print("--- CAT 1: Both fields missing (hardest recovery) ---")
        for e in cat1:
            print(f"  {e['filename']:50s}  doc={e['doc_type']:30s}  PO={e['po_address']}")
        print()

    if cat2:
        print("--- CAT 2: Name missing, allotment captured ---")
        for e in cat2:
            print(f"  {e['filename']:50s}  allot={e['allotment']:8s}  PO={e['po_address']}")
        print()

    if cat3:
        print("--- CAT 3: Name captured, allotment missing ---")
        for e in cat3:
            print(f"  {e['filename']:50s}  name={e['name'][:30]:30s}  PO={e['po_address']}")
        print()

    # Write TSV manifest
    manifest_path = OUTPUT_DIR / "candidates.tsv"
    with open(manifest_path, "w") as f:
        f.write("category\tfilename\tname\tallotment\ttribe\tpo_address\tdoc_type\tbody_chars\n")
        for cat_label, cat_list in [("CAT_1", cat1), ("CAT_2", cat2), ("CAT_3", cat3)]:
            for e in cat_list:
                f.write(f"{cat_label}\t{e['filename']}\t{e['name']}\t{e['allotment']}\t{e['tribe']}\t{e['po_address']}\t{e['doc_type']}\t{e['body_chars']}\n")

    print(f"Manifest written: {manifest_path}")
    print(f"Use as input for the Task 5 campaign in the next session.")


if __name__ == "__main__":
    main()
