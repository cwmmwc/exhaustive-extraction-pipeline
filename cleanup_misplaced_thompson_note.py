#!/usr/bin/env python3
"""
Strip misplaced Thompson/Merrivall meta-sentence from 31 records.

Background: An earlier bulk allotment-recovery patch (apply_no_pattern_
patches_v2.py) used a CORPUS_NOTE template that ended with this sentence:

  "Sarah Thompson (pine_ridge_vol1_affidavit_020) was held out of this
  batch because that record is a multi-allottee bundle (Thompson +
  Merrivall) needing separate splitting work."

That sentence was meta-commentary about a different record (Sarah
Thompson's) but it got appended to NOTES of every record the bulk patch
touched — 31 records that have nothing to do with Sarah Thompson.

This script removes ONLY that sentence from NOTES, leaving everything
else intact. The records' actual extraction data (names, allotments,
substantive content) is unaffected.

Strategy: literal string replacement of the offending sentence(s),
leaving any other NOTES content untouched. The script is idempotent —
running it twice produces the same result as running it once.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

# The offending sentence as it appears in NOTES, plus the leading separator.
# The CORPUS_NOTE in the v2 script ends with this exact string.
TO_STRIP = (
    " Sarah Thompson (pine_ridge_vol1_affidavit_020) was held out of this "
    "batch because that record is a multi-allottee bundle (Thompson + "
    "Merrivall) needing separate splitting work."
)


def cleanup_one(path):
    with open(path) as f:
        record = json.load(f)
    extraction = record["extraction"]
    if isinstance(extraction, list):
        items = extraction
    else:
        items = [extraction]

    changed = False
    for item in items:
        if not isinstance(item, dict):
            continue
        notes = item.get("NOTES") or ""
        if TO_STRIP in notes:
            item["NOTES"] = notes.replace(TO_STRIP, "")
            changed = True

    if changed:
        with open(path, "w") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
    return changed


def main():
    fixed = 0
    scanned = 0
    for path in sorted(EXTRACTIONS.glob("*.json")):
        scanned += 1
        if cleanup_one(path):
            fixed += 1
            print(f"  cleaned: {path.name}")

    print()
    print(f"Scanned: {scanned} records")
    print(f"Cleaned: {fixed} records")


if __name__ == "__main__":
    main()
