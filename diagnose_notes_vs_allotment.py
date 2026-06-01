#!/usr/bin/env python3
"""
NOTES-vs-Allotment consistency diagnostic.

Background: Florence Twiss Cuny's record (pine_ridge_vol1_affidavit_123) had
Allotment number = 762 in the structured field, but NOTES contained the
phrase "document references No. 818" — and 818 turned out to be the correct
allotment per BLM accession 709333. The Sonnet text-extraction had captured
the right number in supporting text but set the wrong number in the primary
field.

This diagnostic finds other records with the same failure mode:
  - Extract any allotment-like numbers from NOTES via regex
  - Compare to the structured Allotment number field
  - Flag mismatches for human review

Patterns that suggest "this is an allotment number" in NOTES:
  - "No. NNNN" or "No. NNN" (capitalized, with period)
  - "Allotment NNNN" (any case)
  - "allotment No. NNNN"
  - "allotment number NNNN"

Patterns that are NOT allotment numbers (skip):
  - Years (1900-1950 range) — common in NOTES dates
  - Dollar amounts ($NNNN, $NN.NN)
  - Section numbers in land descriptions ("Section NN")
  - Township/Range numbers
  - Form numbers (5-105, 6-2543, etc.)
  - "page NNN" or "p. NNN"
  - 5-digit+ numbers (likely document numbers, not allotments)

Output: TSV with columns
  filename | structured_allotment | notes_candidates | confidence

Usage:
  python3 diagnose_notes_vs_allotment.py
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

# Patterns that strongly suggest "this is an allotment number"
ALLOTMENT_PATTERNS = [
    re.compile(r"[Aa]llotment\s+No\.?\s*(\d{1,4})\b"),
    re.compile(r"[Aa]llotment\s+number\s+(\d{1,4})\b"),
    re.compile(r"[Aa]llotment\s+#\s*(\d{1,4})\b"),
    re.compile(r"\bNo\.\s*(\d{1,4})\s*\.?\s*(?:and|of|allotment|patent|fee)", re.IGNORECASE),
    re.compile(r"references\s+No\.\s*(\d{1,4})\b", re.IGNORECASE),
    re.compile(r"trust\s+patent\s+(?:on|of)?\s*[Aa]llotment\s+No\.?\s*(\d{1,4})\b"),
    # "No. 818" pattern when not preceded by Section, Form, etc
    re.compile(r"(?<!\bForm\s)(?<!\bSection\s)(?<!\bSec\.\s)(?<!\bRecord\s)(?<!\bPage\s)\bNo\.\s+(\d{1,4})\b"),
]

# Patterns to EXCLUDE (these aren't allotment numbers even if they look like one)
EXCLUSION_PATTERNS = [
    re.compile(r"Section\s+\d+", re.IGNORECASE),
    re.compile(r"Sec\.\s+\d+", re.IGNORECASE),
    re.compile(r"Township\s+\d+", re.IGNORECASE),
    re.compile(r"Range\s+\d+", re.IGNORECASE),
    re.compile(r"Form\s+\d+(-\d+)?", re.IGNORECASE),
    re.compile(r"page\s+\d+", re.IGNORECASE),
    re.compile(r"p\.\s+\d+", re.IGNORECASE),
    re.compile(r"\$\s*\d"),
    re.compile(r"\bRG\s+\d+", re.IGNORECASE),
]


def extract_normalized_allotment(value):
    """Pull the leading number from an Allotment number field value.

    Field can be like '762', '818', 'not stated', '6 (or 1080)', etc.
    Returns the first number found, or None.
    """
    if not value or value == "not stated":
        return None
    m = re.search(r"\d+", str(value))
    return m.group(0) if m else None


def find_notes_allotment_candidates(notes):
    """Find numbers in NOTES that look like allotment references.

    Returns list of (number_string, matching_phrase) tuples.
    """
    if not notes:
        return []

    candidates = []
    seen_nums = set()

    for pat in ALLOTMENT_PATTERNS:
        for m in pat.finditer(notes):
            num = m.group(1) if m.lastindex else m.group(0)
            num = re.search(r"\d+", num).group(0)

            # Year filter (years are common in NOTES)
            if 1850 <= int(num) <= 1960:
                continue

            # Skip very large numbers (likely document numbers, accession numbers)
            if int(num) > 9999:
                continue

            if num in seen_nums:
                continue
            seen_nums.add(num)

            # Get surrounding context (40 chars before, 40 after)
            start = max(0, m.start() - 40)
            end = min(len(notes), m.end() + 40)
            context = notes[start:end].replace("\n", " ")
            candidates.append((num, context.strip()))

    return candidates


def assess_confidence(structured_value, notes_candidates):
    """Estimate confidence that there's a real mismatch."""
    if not notes_candidates:
        return "no_notes_candidates"
    if structured_value is None:
        return "structured_field_missing"

    notes_nums = [c[0] for c in notes_candidates]

    # Exact match — no problem
    if structured_value in notes_nums:
        return "match"

    # Mismatch — possible error like Florence's case
    return "mismatch"


def main():
    results = {
        "match": [],
        "mismatch": [],
        "structured_field_missing": [],
        "no_notes_candidates_skip": 0,
    }

    for path in sorted(EXTRACTIONS.glob("*.json")):
        # Skip non-record files
        if path.name == "usage_summary.json":
            continue

        try:
            with open(path) as f:
                record = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        e = record.get("extraction", {})
        if isinstance(e, list):
            e = e[0] if e else {}

        structured = extract_normalized_allotment(e.get("Allotment number"))
        notes = e.get("NOTES") or ""
        candidates = find_notes_allotment_candidates(notes)

        if not candidates:
            results["no_notes_candidates_skip"] += 1
            continue

        confidence = assess_confidence(structured, candidates)

        entry = {
            "filename": path.name,
            "structured": structured,
            "notes_candidates": candidates,
            "name": e.get("Name", ""),
            "tribe": e.get("Tribe/Reservation", ""),
        }

        if confidence == "match":
            results["match"].append(entry)
        elif confidence == "mismatch":
            results["mismatch"].append(entry)
        elif confidence == "structured_field_missing":
            results["structured_field_missing"].append(entry)

    # Print summary
    print("=" * 70)
    print("NOTES-vs-Allotment consistency diagnostic")
    print("=" * 70)
    print()
    print(f"Records examined: {sum(len(v) if isinstance(v, list) else v for v in results.values())}")
    print(f"  Skipped (no allotment-like numbers in NOTES): {results['no_notes_candidates_skip']}")
    print(f"  Match (structured == NOTES allotment): {len(results['match'])}")
    print(f"  MISMATCH (structured != NOTES allotment): {len(results['mismatch'])}")
    print(f"  Structured field missing but NOTES has candidate: {len(results['structured_field_missing'])}")
    print()

    if results["mismatch"]:
        print("=" * 70)
        print("MISMATCHES — review candidates for Florence-style errors")
        print("=" * 70)
        for entry in results["mismatch"]:
            print(f"\n{entry['filename']}")
            print(f"  Name: {entry['name']}")
            print(f"  Tribe: {entry['tribe']}")
            print(f"  Structured Allotment: {entry['structured']}")
            print(f"  NOTES candidates: {[c[0] for c in entry['notes_candidates']]}")
            for num, ctx in entry["notes_candidates"][:3]:
                print(f"    [{num}] ...{ctx}...")

    if results["structured_field_missing"]:
        print()
        print("=" * 70)
        print("STRUCTURED FIELD MISSING — but NOTES has candidates")
        print("(May be records where allotment can be recovered from NOTES)")
        print("=" * 70)
        for entry in results["structured_field_missing"][:20]:  # cap output
            print(f"\n{entry['filename']}")
            print(f"  Name: {entry['name']}")
            print(f"  NOTES candidates: {[c[0] for c in entry['notes_candidates']]}")
        if len(results["structured_field_missing"]) > 20:
            print(f"\n  ... and {len(results['structured_field_missing']) - 20} more")


if __name__ == "__main__":
    main()
