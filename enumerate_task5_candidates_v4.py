#!/usr/bin/env python3
"""
Enumerate Task 5 candidates v4 — corrects recovery_note type names.

v3 had the wrong type label for administrative reclassifications:
  - Bad:  'administrative_reclassification'
  - Good: 'task5_reclassification_administrative_correspondence'

Also adds 'tribe_field_normalization' (appears on
pine_ridge_vol1_agency_narrative_page005).

These corrections clear the 6 agency_correspondence records from the
spurious CAT_1 bucket.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
OUTPUT_DIR = PROJECT_ROOT / "validation_samples" / "task5_campaign"

ALREADY_CORRECTED_TYPES = {
    # Original pre-May-3 types
    "identity_recovery",
    "identity_recovery_with_revisit_flag",
    "substantive_record_recovery",
    "substantive_record_correction_with_blm_cross_reference",
    "substantive_record_correction_with_blm_and_sibling_documents",
    "substantive_record_recovery_with_sibling_finding",
    "cross_routing_correction",
    "task3_blm_confirmed_tribe_correction",
    # Reclassification types (correct labels)
    "task5_reclassification_administrative_correspondence",
    "tribe_field_normalization",
    # Bundle splits
    "bundle_split_multi_allottee",
    # 2026-05-03 types
    "task5_cat1_sonnet_only_arbitration",
    "task5_cat1_correction_user_verified",
    # 2026-05-04 types
    "task5_cat1_dual_model_vision_recovery_user_verified",
    "task5_cat1_dual_model_agreement_user_tribe_confirmed",
    "task5_cat1_dual_model_with_corpus_cross_reference",
    "task5_cat1_dual_model_with_user_verification",
    "task5_cat1_dual_model_with_duplicate_removal",
    "task5_shawnee_master_list_backfill",
    "task5_shawnee_master_list_backfill_manual_triage",
    "task5_shawnee_master_list_backfill_patents_database",
    "task5_shawnee_master_list_not_in_patents_database",
}

EXPLICITLY_LEFT = {
    "part10_affidavit_004.json": (
        "Hannah Hardin signature page (excluded from CAT_1 batch 2026-05-03)"
    ),
    "part3_questionnaire_022.json": (
        "Blank Circular 2464 instruction template (no analytical value)"
    ),
}


def already_corrected(record):
    for note in record.get("recovery_notes", []):
        if note.get("type") in ALREADY_CORRECTED_TYPES:
            return True
    return False


def main():
    cat1 = []
    cat2 = []
    cat3 = []
    explicitly_left_found = []

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

        if path.name in EXPLICITLY_LEFT:
            explicitly_left_found.append(
                (path.name, EXPLICITLY_LEFT[path.name])
            )
            continue

        if already_corrected(record):
            continue

        name = (e.get("Name") or "").strip()
        allot = (e.get("Allotment number") or "").strip()
        doc_type = (e.get("Document type") or "").strip()
        po_addr = (e.get("Post Office Address") or "").strip()
        tribe = (e.get("Tribe/Reservation") or "").strip()

        name_missing = name in ("", "not stated")
        allot_resolved_marker = (
            "(not in patents database)" in allot
            or "non-allottee" in allot.lower()
        )
        allot_missing = allot in ("", "not stated") and not allot_resolved_marker

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

    print("=" * 70)
    print("Task 5 candidate enumeration v4 (final, corrected filters)")
    print("=" * 70)
    print()
    print(f"CAT_1 (Name + Allotment both missing):    {len(cat1)}")
    print(f"CAT_2 (Name missing, allotment captured): {len(cat2)}")
    print(f"CAT_3 (Name captured, allotment missing): {len(cat3)}")
    print(f"Explicitly left unpatched:                {len(explicitly_left_found)}")
    print(f"Total remaining candidates:                {len(cat1) + len(cat2) + len(cat3)}")
    print()

    if cat1:
        print(f"--- CAT_1 ({len(cat1)}) ---")
        for e in cat1:
            print(f"  {e['filename']:50s} doc={e['doc_type']:30s} PO={e['po_address'][:30]}")
        print()

    if cat2:
        print(f"--- CAT_2 ({len(cat2)}) ---")
        for e in cat2:
            print(f"  {e['filename']:50s} allot={e['allotment']:8s} PO={e['po_address'][:30]}")
        print()

    if cat3:
        print(f"--- CAT_3 ({len(cat3)}) — grouped by tribe ---")
        by_tribe = {}
        for e in cat3:
            tribe_key = e["tribe"] or "(blank)"
            by_tribe.setdefault(tribe_key, []).append(e)
        for tribe_key in sorted(by_tribe.keys()):
            entries = by_tribe[tribe_key]
            print(f"  Tribe='{tribe_key}' ({len(entries)} records):")
            for e in entries:
                print(f"    {e['filename']:50s} name={e['name'][:40]:40s} PO={e['po_address'][:25]}")
            print()

    manifest_path = OUTPUT_DIR / "candidates_post_20260504_v4.tsv"
    with open(manifest_path, "w") as f:
        f.write("category\tfilename\tname\tallotment\ttribe\tpo_address\tdoc_type\tbody_chars\n")
        for cat_label, cat_list in [("CAT_1", cat1), ("CAT_2", cat2), ("CAT_3", cat3)]:
            for e in cat_list:
                f.write(f"{cat_label}\t{e['filename']}\t{e['name']}\t{e['allotment']}\t{e['tribe']}\t{e['po_address']}\t{e['doc_type']}\t{e['body_chars']}\n")

    print(f"Manifest written: {manifest_path}")


if __name__ == "__main__":
    main()
