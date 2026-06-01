#!/usr/bin/env python3
"""
Normalize the Tribe/Reservation field across all pine_ridge_* records.

Background: A corpus diagnostic on 2026-04-28 revealed that 325 of 392
pine_ridge_* records have a populated Tribe/Reservation field, but the
populated values use 40+ different strings to mean roughly the same thing:
  - "Pine Ridge"
  - "Pine Ridge Agency"
  - "Shannon County, South Dakota (Pine Ridge area)"
  - "Bennett County, South Dakota"
  - "Washabaugh County, South Dakota (Pine Ridge area)"
  - ... and 35+ more variants

This script normalizes all of them to a canonical "Pine Ridge", preserving
the original string in NOTES so the patch is reversible.

Records explicitly NOT touched:
  - Tribe = "not stated" (these are recovery candidates, not normalization)
  - Tribe values from Task 1 cross-routing fix (already set to "Pine Ridge
    (Oglala Sioux)" — the explicit "(Oglala Sioux)" form should not be
    overwritten with the bare "Pine Ridge")

Patterns matched (case-insensitive):
  - "pine ridge" anywhere in the string
  - "shannon county" (Shannon County is the historic Pine Ridge core)
  - "bennett county" (Bennett County, SD, in Pine Ridge area)
  - "washabaugh county" (Washabaugh County, SD, in Pine Ridge area)
  - "oglala" (the Oglala Sioux are the Pine Ridge tribe)

Patterns NOT matched (left alone, even if in pine_ridge_* directory):
  - Anything explicitly Crow, Osage, Turtle Mountain, Beltrami, Flandreau,
    etc. (Task 1 cross-routing fix already corrected these to canonical form)

Usage:
  python3 patch_pine_ridge_normalization.py --dry-run    # preview only
  python3 patch_pine_ridge_normalization.py --apply      # commit changes
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

CANONICAL_TRIBE = "Pine Ridge"

# Regex patterns that indicate a Pine Ridge area record.
# Case-insensitive. Tested against original Tribe/Reservation string.
PINE_RIDGE_PATTERNS = [
    re.compile(r"pine\s*ridge", re.IGNORECASE),
    re.compile(r"shannon\s*county", re.IGNORECASE),
    re.compile(r"bennett\s*county", re.IGNORECASE),
    re.compile(r"washabaugh\s*county", re.IGNORECASE),
    re.compile(r"oglala", re.IGNORECASE),
]

# These tribe values were explicitly set by Task 1 (cross-routing correction).
# They are already canonical and should not be overwritten by this normalization.
PROTECTED_VALUES = {
    "Pine Ridge (Oglala Sioux)",  # Task 1's canonical form
}


def matches_pine_ridge(tribe_value):
    """Return True if the tribe value is a Pine Ridge variant."""
    if not tribe_value or tribe_value == "not stated":
        return False
    if tribe_value in PROTECTED_VALUES:
        return False
    for pat in PINE_RIDGE_PATTERNS:
        if pat.search(tribe_value):
            return True
    return False


def collect_changes():
    """Walk all pine_ridge_* records, identify what would change."""
    changes = []
    no_change_already_canonical = 0
    no_change_protected = 0
    no_change_not_stated = 0
    no_change_other = []

    for path in sorted(EXTRACTIONS.glob("pine_ridge_*.json")):
        with open(path) as f:
            record = json.load(f)
        e = record.get("extraction", {})
        if isinstance(e, list):
            e = e[0] if e else {}
        current = e.get("Tribe/Reservation", "") or ""

        if current == CANONICAL_TRIBE:
            no_change_already_canonical += 1
            continue
        if current in PROTECTED_VALUES:
            no_change_protected += 1
            continue
        if current in ("", "not stated"):
            no_change_not_stated += 1
            continue
        if matches_pine_ridge(current):
            changes.append({
                "filename": path.name,
                "old_value": current,
                "new_value": CANONICAL_TRIBE,
            })
        else:
            no_change_other.append((path.name, current))

    return {
        "changes": changes,
        "no_change_already_canonical": no_change_already_canonical,
        "no_change_protected": no_change_protected,
        "no_change_not_stated": no_change_not_stated,
        "no_change_other": no_change_other,
    }


def print_dry_run(result):
    print("=" * 70)
    print("DRY RUN: Pine Ridge tribe normalization preview")
    print("=" * 70)
    print()

    changes = result["changes"]
    print(f"Records that WOULD change: {len(changes)}")
    print(f"Records already canonical (\"{CANONICAL_TRIBE}\"): {result['no_change_already_canonical']}")
    print(f"Records protected (Task 1 corrections): {result['no_change_protected']}")
    print(f"Records with Tribe='not stated': {result['no_change_not_stated']}")
    print(f"Records left alone (no Pine Ridge match): {len(result['no_change_other'])}")
    print()

    # Show distribution of values being normalized
    counter = Counter(c["old_value"] for c in changes)
    print("Variant strings that would be consolidated:")
    print("-" * 70)
    for value, count in counter.most_common():
        print(f"  {count:4d}  {value}")
    print()

    # Show records left alone (sanity check — should be the Task-1-fixed cross-routings)
    if result["no_change_other"]:
        print("Records with non-Pine-Ridge tribe values (left alone):")
        print("-" * 70)
        for filename, value in result["no_change_other"]:
            print(f"  {filename}  ->  {value}")
        print()

    print("=" * 70)
    print(f"To apply: python3 {Path(sys.argv[0]).name} --apply")
    print("=" * 70)


def apply_changes(result):
    changes = result["changes"]
    print(f"Applying {len(changes)} normalizations...")
    print()

    for c in changes:
        path = EXTRACTIONS / c["filename"]
        with open(path) as f:
            record = json.load(f)
        e = record["extraction"]
        if isinstance(e, list):
            # If extraction is a list, normalize the first dict
            if e:
                e = e[0]
                record["extraction"][0] = e
            else:
                continue

        old_value = e.get("Tribe/Reservation", "")

        # Apply normalization
        e["Tribe/Reservation"] = CANONICAL_TRIBE

        # Preserve original in NOTES (only append if not already present)
        original_marker = f"ORIGINAL_TRIBE_VALUE: \"{old_value}\""
        notes = e.get("NOTES", "") or ""
        if original_marker not in notes:
            e["NOTES"] = notes + f" | {original_marker} (normalized 2026-04-28 to canonical 'Pine Ridge')"

        # Audit entry
        record.setdefault("recovery_notes", []).append({
            "date": "2026-04-28",
            "type": "tribe_field_normalization",
            "method": "regex_consolidation_pine_ridge_variants",
            "fields_corrected": ["Tribe/Reservation", "NOTES"],
            "previous_value": old_value,
            "canonical_value": CANONICAL_TRIBE,
            "rationale": (
                "Pine Ridge tribe field had 40+ string variants across the "
                "corpus. Consolidating to canonical 'Pine Ridge' for clean "
                "tabulation while preserving original variant in NOTES for audit."
            ),
        })

        with open(path, "w") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Done. {len(changes)} records normalized.")
    print()
    print("Manifest unchanged (in-place patches only).")


def main():
    parser = argparse.ArgumentParser(description="Normalize Pine Ridge tribe field variants")
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    parser.add_argument("--apply", action="store_true", help="Apply the normalization")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.print_help()
        print("\nERROR: must specify either --dry-run or --apply")
        sys.exit(1)
    if args.dry_run and args.apply:
        print("ERROR: cannot specify both --dry-run and --apply")
        sys.exit(1)

    result = collect_changes()

    if args.dry_run:
        print_dry_run(result)
    elif args.apply:
        apply_changes(result)


if __name__ == "__main__":
    main()
