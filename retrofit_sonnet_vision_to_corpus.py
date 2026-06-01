#!/usr/bin/env python3
"""
Retrofit Sonnet vision structured data onto corpus records.

Background: when records were patched via Sonnet vision (multi-allottee
bundle splits 2026-05-03 and CAT_1 recovery 2026-05-04), the structured
v5 data (fee_patents, financial_transactions, mortgages, events,
entities, relationships, testimony, taxes, correspondence,
legislative_actions) from vision_merged.json was collapsed into the
NOTES string instead of preserved as structured fields. The original
JSONs in validation_samples/ still have the structured data.

This retrofit walks corpus records and for each one that has a
corresponding vision_merged.json, adds the structured v5 fields onto
the corpus record under a new top-level key 'vision_extraction_v5'.
This way:
  - Existing 'extraction' object stays unchanged (no breakage of
    code that reads Name/Allotment/Tribe/etc.)
  - Existing NOTES stays unchanged (no information loss in the
    prose representation)
  - New structured data is available for database load and analytical
    queries

Vision JSON locations checked, in order of preference:
  1. validation_samples/cat1_sonnet_vision/<rid>/vision_merged.json
     (CAT_1 recovery batch 2026-05-04)
  2. validation_samples/<rid>_vision/vision_merged.json
     (bundle-split records 2026-05-03; e.g.,
     validation_samples/part1_agency_narrative_003_vision/...)
  3. validation_samples/part1_an003_vision/vision_merged.json
     (a few one-off vision runs that used non-standard dir names)
  4. validation_samples/part4_q012_vision/vision_merged.json
     (Alphonse Charbonneau full content recovery 2026-05-02)

Bundle-split records have stem like 'part1_agency_narrative_003a' but
the vision JSON was on the bundle PRE-split (e.g.,
'part1_agency_narrative_003_vision'). For these, both 003a and 003b
should retrofit from the SAME vision JSON, with each record getting
the relevant subset (for fee_patents, the entry whose allottee_name
matches that record's Name field).

Idempotent: re-running the script does not duplicate; it skips records
whose 'vision_extraction_v5' already exists.
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
VAL_BASE = PROJECT_ROOT / "validation_samples"

V5_TABLES = [
    "entities",
    "fee_patents",
    "financial_transactions",
    "mortgages",
    "events",
    "relationships",
    "testimony",
    "taxes",
    "correspondence",
    "legislative_actions",
    "tables",
]


def find_vision_json(rid):
    """Find the vision_merged.json for a record_id. Returns Path or None.
    Bundle splits like 'part1_agency_narrative_003a' map to the parent
    bundle's vision dir 'part1_agency_narrative_003_vision'."""
    candidates = []

    # 1. CAT_1 recovery directory
    candidates.append(VAL_BASE / "cat1_sonnet_vision" / rid / "vision_merged.json")

    # 2. Standard per-record vision dir
    candidates.append(VAL_BASE / f"{rid}_vision" / "vision_merged.json")

    # 3. Bundle parent dir (strip _NNNa/_NNNb suffix)
    m = re.match(r"^(.*_\d+)[ab]$", rid)
    if m:
        parent_rid = m.group(1)
        candidates.append(VAL_BASE / f"{parent_rid}_vision" / "vision_merged.json")
        # Some early one-off naming variants
        if parent_rid == "part1_agency_narrative_003":
            candidates.append(VAL_BASE / "part1_an003_vision" / "vision_merged.json")

    # 4. Special one-off cases
    if rid == "part4_questionnaire_012":
        candidates.append(VAL_BASE / "part4_q012_vision" / "vision_merged.json")
    if rid == "part3_questionnaire_012":
        # No special case yet, but flag if we want to add part3-specific
        pass

    for path in candidates:
        if path.exists():
            return path
    return None


def get_corpus_record_name(record):
    """Extract the corpus record's Name field for matching against vision fee_patents."""
    e = record.get("extraction") or {}
    if isinstance(e, list):
        e = e[0] if e else {}
    return (e.get("Name") or "").strip()


def filter_vision_data_for_record(vision_data, target_name):
    """For a corpus record that's part of a multi-allottee bundle, filter
    the vision data's fee_patents (and related) to just the entries that
    match the record's Name. For non-bundle records, return all vision
    data unchanged."""
    if not target_name:
        return dict(vision_data)

    # Normalize target name for matching (drop case, parenthetical aliases, prefixes)
    def norm(s):
        if not s:
            return ""
        s = re.sub(r"\([^)]*\)", "", s).strip()
        s = re.sub(r"^(Mrs?\.|Mr\.|Miss)\s+", "", s, flags=re.IGNORECASE)
        return s.lower().replace(" ", "")

    target_norm = norm(target_name)

    # Check if vision has multiple fee_patents (bundle case)
    fee_patents = vision_data.get("fee_patents") or []
    if len(fee_patents) <= 1:
        return dict(vision_data)

    # It's a bundle. Filter fee_patents to the one matching this record.
    matching_fp = None
    for fp in fee_patents:
        fp_name = norm(fp.get("allottee_name") or "")
        # Match either way: record name in fp name, or fp name in record name
        if target_norm and fp_name and (target_norm in fp_name or fp_name in target_norm):
            matching_fp = fp
            break

    if matching_fp is None:
        # Couldn't match; return ALL data with a note
        return {
            **dict(vision_data),
            "_retrofit_note": (
                f"Could not match record Name='{target_name}' to any "
                f"fee_patent allottee_name in this multi-allottee bundle "
                f"vision JSON. All vision fields preserved as-is."
            ),
        }

    # Build a filtered version: keep only the matching fee_patent
    filtered = dict(vision_data)
    filtered["fee_patents"] = [matching_fp]
    filtered["_retrofit_note"] = (
        f"This record is part of a multi-allottee bundle. fee_patents "
        f"filtered to the entry matching Name='{target_name}'. Other "
        f"v5 tables (entities, events, etc.) retained as-is from the "
        f"shared vision JSON."
    )
    return filtered


def retrofit_one(record_path):
    """Add vision_extraction_v5 to one corpus record. Returns (status, msg)."""
    rid = record_path.stem

    with open(record_path) as f:
        record = json.load(f)

    if "vision_extraction_v5" in record:
        return "skipped_already_present", "already has vision_extraction_v5"

    vision_path = find_vision_json(rid)
    if vision_path is None:
        return "no_vision_json", "no vision_merged.json found"

    with open(vision_path) as f:
        vision_data = json.load(f)

    # Filter for multi-allottee bundles
    target_name = get_corpus_record_name(record)
    filtered_vision = filter_vision_data_for_record(vision_data, target_name)

    # Build the v5 structured object
    v5 = {
        "_retrofit_date": "2026-05-04",
        "_retrofit_source_path": str(vision_path.relative_to(PROJECT_ROOT)),
    }
    if "_retrofit_note" in filtered_vision:
        v5["_retrofit_note"] = filtered_vision["_retrofit_note"]
    for table in V5_TABLES:
        if table in filtered_vision:
            v5[table] = filtered_vision[table]

    # Attach to record
    record["vision_extraction_v5"] = v5

    with open(record_path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    n_tables = sum(1 for t in V5_TABLES if t in v5 and v5[t])
    return "retrofit", f"added v5 fields ({n_tables} non-empty tables) from {vision_path.parent.name}"


def main():
    print("=" * 70)
    print("Sonnet vision retrofit: adding v5 structured fields to corpus records")
    print("=" * 70)
    print()

    counts = {
        "retrofit": 0,
        "skipped_already_present": 0,
        "no_vision_json": 0,
    }
    retrofitted = []

    for record_path in sorted(EXTRACTIONS.glob("*.json")):
        status, msg = retrofit_one(record_path)
        counts[status] = counts.get(status, 0) + 1
        if status == "retrofit":
            retrofitted.append(record_path.stem)
            print(f"  RETROFIT  {record_path.stem:50s} {msg}")
        elif status == "skipped_already_present":
            print(f"  SKIP      {record_path.stem:50s} (already retrofitted)")
        # Don't print no_vision_json (would flood output)

    print()
    print("=" * 70)
    print(f"Records retrofitted:           {counts['retrofit']}")
    print(f"Records already retrofitted:   {counts['skipped_already_present']}")
    print(f"Records without vision JSON:   {counts['no_vision_json']}")
    print("=" * 70)

    if retrofitted:
        print()
        print("Retrofitted records:")
        for r in retrofitted:
            print(f"  - {r}")


if __name__ == "__main__":
    main()
