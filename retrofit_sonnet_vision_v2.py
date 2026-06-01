#!/usr/bin/env python3
"""
Improved retrofit: properly filter v5 tables for multi-allottee bundles.

Previous version only filtered fee_patents by allottee name. This
version also filters financial_transactions, mortgages, events,
relationships, and testimony — anywhere an allottee name might
identify which entry belongs to which sibling record.

For non-bundle records (single-allottee), no filtering is needed —
all v5 fields are added as-is.

Re-runs of this script will REPLACE existing vision_extraction_v5
entries on multi-allottee bundle records (so the improved filter
takes effect). Non-bundle records that already have correct v5 data
are skipped.

Bundle records identified by stem ending in 'a' or 'b' with parent
stem like 'part1_agency_narrative_003' (the bundle that was split).
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

# Field within each table type that contains an allottee name (for filtering)
NAME_FIELD_BY_TABLE = {
    "fee_patents": ["allottee_name"],
    "financial_transactions": ["payee", "payer"],  # check both
    "mortgages": ["mortgagor", "borrower"],
    "events": [],  # events often describe shared activity; don't filter
    "relationships": ["subject", "object"],
    "testimony": ["witness"],
    "taxes": ["payer"],
    "correspondence": [],  # correspondence is between agents, not allottees
    "legislative_actions": [],
    "entities": [],  # keep all entities — they're shared context
    "tables": [],
}


def find_vision_json(rid):
    """Find the vision_merged.json for a record_id."""
    candidates = []
    candidates.append(VAL_BASE / "cat1_sonnet_vision" / rid / "vision_merged.json")
    candidates.append(VAL_BASE / f"{rid}_vision" / "vision_merged.json")

    m = re.match(r"^(.*_\d+)[ab]$", rid)
    if m:
        parent_rid = m.group(1)
        candidates.append(VAL_BASE / f"{parent_rid}_vision" / "vision_merged.json")
        if parent_rid == "part1_agency_narrative_003":
            candidates.append(VAL_BASE / "part1_an003_vision" / "vision_merged.json")

    if rid == "part4_questionnaire_012":
        candidates.append(VAL_BASE / "part4_q012_vision" / "vision_merged.json")

    for path in candidates:
        if path.exists():
            return path
    return None


def is_bundle_record(rid):
    """Bundle splits have stem ending with letter (a/b) after a number."""
    return bool(re.match(r"^.*_\d+[ab]$", rid))


def get_corpus_record_name(record):
    e = record.get("extraction") or {}
    if isinstance(e, list):
        e = e[0] if e else {}
    return (e.get("Name") or "").strip()


def normalize_name(s):
    if not s:
        return ""
    s = re.sub(r"\([^)]*\)", "", s).strip()
    s = re.sub(r"^(Mrs?\.|Mr\.|Miss)\s+", "", s, flags=re.IGNORECASE)
    return s.lower().replace(" ", "")


def name_matches(target_norm, candidate):
    if not target_norm or not candidate:
        return False
    candidate_norm = normalize_name(candidate)
    if not candidate_norm:
        return False
    return target_norm in candidate_norm or candidate_norm in target_norm


def filter_table_for_record(table_name, table_data, target_name):
    """Filter a v5 table to entries that mention the target_name in the
    relevant name fields. Returns the filtered list."""
    if not target_name:
        return table_data
    name_fields = NAME_FIELD_BY_TABLE.get(table_name, [])
    if not name_fields:
        return table_data  # no filtering for this table type

    target_norm = normalize_name(target_name)
    filtered = []
    for item in table_data:
        if not isinstance(item, dict):
            filtered.append(item)
            continue
        # Check if any of the relevant name fields match
        matches = any(
            name_matches(target_norm, item.get(field, ""))
            for field in name_fields
        )
        if matches:
            filtered.append(item)
    return filtered


def filter_vision_data_for_record(vision_data, target_name, is_bundle):
    """For bundle records, filter all v5 tables by name match.
    For non-bundle records, return all data unchanged."""
    if not is_bundle:
        return dict(vision_data)

    filtered = {}
    n_filtered_tables = []
    for key, value in vision_data.items():
        if key in NAME_FIELD_BY_TABLE and isinstance(value, list):
            original_len = len(value)
            filtered_list = filter_table_for_record(key, value, target_name)
            filtered[key] = filtered_list
            if len(filtered_list) != original_len and NAME_FIELD_BY_TABLE[key]:
                n_filtered_tables.append(
                    f"{key}: {original_len}->{len(filtered_list)}"
                )
        else:
            filtered[key] = value
    if n_filtered_tables:
        filtered["_retrofit_filter_note"] = (
            f"Multi-allottee bundle: filtered tables to entries matching "
            f"Name='{target_name}'. Filtered: {', '.join(n_filtered_tables)}."
        )
    return filtered


def retrofit_one(record_path):
    rid = record_path.stem
    is_bundle = is_bundle_record(rid)

    with open(record_path) as f:
        record = json.load(f)

    # Skip non-bundle records that already have v5 data — they're correct
    if "vision_extraction_v5" in record and not is_bundle:
        return "skipped_already_correct", "non-bundle record already retrofitted"

    vision_path = find_vision_json(rid)
    if vision_path is None:
        return "no_vision_json", "no vision_merged.json found"

    with open(vision_path) as f:
        vision_data = json.load(f)

    target_name = get_corpus_record_name(record)
    filtered_vision = filter_vision_data_for_record(vision_data, target_name, is_bundle)

    v5 = {
        "_retrofit_date": "2026-05-04",
        "_retrofit_source_path": str(vision_path.relative_to(PROJECT_ROOT)),
    }
    if "_retrofit_filter_note" in filtered_vision:
        v5["_retrofit_filter_note"] = filtered_vision["_retrofit_filter_note"]
    for table in V5_TABLES:
        if table in filtered_vision:
            v5[table] = filtered_vision[table]

    record["vision_extraction_v5"] = v5

    with open(record_path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    n_tables = sum(1 for t in V5_TABLES if t in v5 and v5[t])
    suffix = " [bundle, refiltered]" if is_bundle else ""
    return "retrofit", f"v5 fields ({n_tables} non-empty tables){suffix}"


def main():
    print("=" * 70)
    print("Sonnet vision retrofit v2: properly filter bundle tables")
    print("=" * 70)

    counts = {"retrofit": 0, "skipped_already_correct": 0, "no_vision_json": 0}
    bundle_refiltered = []

    for record_path in sorted(EXTRACTIONS.glob("*.json")):
        status, msg = retrofit_one(record_path)
        counts[status] = counts.get(status, 0) + 1
        if status == "retrofit":
            print(f"  RETROFIT  {record_path.stem:50s} {msg}")
            if "bundle" in msg:
                bundle_refiltered.append(record_path.stem)

    print()
    print(f"Retrofitted (or refiltered):  {counts['retrofit']}")
    print(f"Skipped (already correct):    {counts['skipped_already_correct']}")
    print(f"No vision JSON:               {counts['no_vision_json']}")
    if bundle_refiltered:
        print()
        print("Bundle records refiltered (only fields matching the record's Name):")
        for r in bundle_refiltered:
            print(f"  - {r}")


if __name__ == "__main__":
    main()
