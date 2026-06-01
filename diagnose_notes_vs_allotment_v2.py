#!/usr/bin/env python3
"""
NOTES-vs-Allotment consistency diagnostic v2 — with false-positive filters.

v1 surfaced 33 mismatches and 56 missing-field-with-candidates. Review
revealed three false-positive classes that the regex was matching:

  1. "Circular No. 2464" — the corpus's defining circular reference,
     not an allotment. Caught in 10+ records.
  2. "Warrant No. NNNN" — government payment vouchers (Mary W. Hume).
  3. "Document No. NNNN" / "Document numbered No. NN-NN" — file/page
     numbers (Elbridge Gerry, Lizzie Sherman).
  4. "Tax certificate No. NNNN" — county tax certs (James Roberts).
  5. "Fee patent No. NNNNNN" — 6-digit BLM document numbers.

This v2 adds those filters. The regex now requires the number be in a
context that strongly suggests "this is an allotment" rather than a
generic "No. NNNN".

It also adds a confidence tier for the genuine "field missing but NOTES
has candidate" cases, distinguishing high-confidence (the NOTES context
explicitly says "Allotment No. NNNN") from low-confidence (just a
"No. NNNN" reference).

Usage:
  python3 diagnose_notes_vs_allotment_v2.py
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

# HIGH-CONFIDENCE patterns — explicit "allotment" word adjacent to number
HIGH_CONFIDENCE_PATTERNS = [
    re.compile(r"[Aa]llotment\s+No\.?\s*(\d{1,4})\b"),
    re.compile(r"[Aa]llotment\s+number\s+(\d{1,4})\b"),
    re.compile(r"[Aa]llotment\s+#\s*(\d{1,4})\b"),
    re.compile(r"[Aa]llottee\s+No\.?\s*(\d{1,4})\b"),
]

# MEDIUM-CONFIDENCE patterns — "No. NNNN" without explicit allotment word,
# but in a context suggesting it's about the allotment subject
MEDIUM_CONFIDENCE_PATTERNS = [
    re.compile(r"references\s+No\.\s*(\d{1,4})\b", re.IGNORECASE),
    re.compile(r"trust\s+patent\s+(?:on|of)?\s*[Aa]llotment\s+No\.?\s*(\d{1,4})\b"),
]

# DISQUALIFYING contexts — if the number is preceded by these, it's NOT
# an allotment number, regardless of other patterns
DISQUALIFYING_PREFIXES = [
    re.compile(r"[Cc]ircular\s+No\.\s*$"),
    re.compile(r"[Ww]arrant\s+No\.\s*$"),
    re.compile(r"[Dd]ocument\s+No\.\s*$"),
    re.compile(r"[Dd]ocument\s+numbered\s+No\.\s*$"),
    re.compile(r"[Tt]ax\s+(?:certificate|cert\.?)\s+No\.\s*$"),
    re.compile(r"[Ff]ee\s+[Pp]atent\s+No\.\s*$"),
    re.compile(r"[Pp]atent\s+No\.\s*$"),
    re.compile(r"[Ff]ile\s+(?:reference\s+)?No\.\s*$"),
    re.compile(r"[Cc]ase\s+(?:file\s+)?No\.\s*$"),
    re.compile(r"[Pp]age\s+No\.\s*$"),
    re.compile(r"[Rr]eceipt\s+No\.\s*$"),
    re.compile(r"[Cc]ertificate\s+No\.\s*$"),
    re.compile(r"[Vv]oucher\s+No\.\s*$"),
    re.compile(r"[Ff]orm\s+(?:No\.\s*)?$"),
    re.compile(r"[Ss]ection\s*$"),
    re.compile(r"[Tt]ownship\s*$"),
    re.compile(r"[Rr]ange\s*$"),
    re.compile(r"[Bb]ook\s*$"),
    re.compile(r"[Pp]age\s*$"),
    re.compile(r"\$\s*$"),
]


def extract_normalized_allotment(value):
    """Pull the leading number from an Allotment number field value."""
    if not value or value == "not stated":
        return None
    m = re.search(r"\d+", str(value))
    return m.group(0) if m else None


def is_disqualified(notes, match_start):
    """Check whether the number at this position is in a disqualifying context."""
    # Look at the 50 chars before the match
    prefix_window = notes[max(0, match_start - 50):match_start]
    for pat in DISQUALIFYING_PREFIXES:
        if pat.search(prefix_window):
            return True
    return False


def find_allotment_candidates(notes):
    """Find numbers in NOTES that look like allotment references.

    Returns list of (number_string, confidence, context) tuples.
    confidence is 'high' or 'medium'.
    """
    if not notes:
        return []

    candidates = []
    seen_pos = set()  # avoid double-counting same match

    def consider(m, confidence):
        num_match = re.search(r"\d+", m.group(0))
        if not num_match:
            return
        num = num_match.group(0)
        # Position of the actual number in original text
        num_start = m.start() + num_match.start()
        if num_start in seen_pos:
            return

        # Year filter
        if 1850 <= int(num) <= 1960:
            return
        # Skip 5-digit+ (likely document/accession numbers)
        if int(num) > 9999:
            return
        # Disqualifying prefix check
        if is_disqualified(notes, num_start):
            return

        seen_pos.add(num_start)
        start = max(0, m.start() - 40)
        end = min(len(notes), m.end() + 40)
        context = notes[start:end].replace("\n", " ").strip()
        candidates.append((num, confidence, context))

    for pat in HIGH_CONFIDENCE_PATTERNS:
        for m in pat.finditer(notes):
            consider(m, "high")

    for pat in MEDIUM_CONFIDENCE_PATTERNS:
        for m in pat.finditer(notes):
            consider(m, "medium")

    return candidates


def main():
    results = {
        "match": [],
        "mismatch_high": [],
        "mismatch_medium_only": [],
        "missing_high": [],
        "missing_medium_only": [],
    }
    skipped = 0

    for path in sorted(EXTRACTIONS.glob("*.json")):
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
        candidates = find_allotment_candidates(notes)

        if not candidates:
            skipped += 1
            continue

        notes_nums = [c[0] for c in candidates]
        any_high = any(c[1] == "high" for c in candidates)

        entry = {
            "filename": path.name,
            "structured": structured,
            "candidates": candidates,
            "name": e.get("Name", ""),
            "tribe": e.get("Tribe/Reservation", ""),
        }

        if structured and structured in notes_nums:
            results["match"].append(entry)
        elif structured:
            # Mismatch
            if any_high:
                results["mismatch_high"].append(entry)
            else:
                results["mismatch_medium_only"].append(entry)
        else:
            # Field missing
            if any_high:
                results["missing_high"].append(entry)
            else:
                results["missing_medium_only"].append(entry)

    # Print summary
    print("=" * 70)
    print("NOTES-vs-Allotment consistency diagnostic v2 (with FP filters)")
    print("=" * 70)
    print()
    print(f"Records examined: {sum(len(v) for v in results.values()) + skipped}")
    print(f"  Skipped (no allotment-like numbers in NOTES): {skipped}")
    print(f"  Match (structured == NOTES allotment): {len(results['match'])}")
    print(f"  Mismatch (high-confidence NOTES candidate): {len(results['mismatch_high'])}")
    print(f"  Mismatch (medium-confidence only): {len(results['mismatch_medium_only'])}")
    print(f"  Field missing, high-confidence NOTES candidate: {len(results['missing_high'])}")
    print(f"  Field missing, medium-confidence only: {len(results['missing_medium_only'])}")
    print()

    if results["mismatch_high"]:
        print("=" * 70)
        print("HIGH-CONFIDENCE MISMATCHES")
        print("(Structured field disagrees with explicit 'Allotment No. X' in NOTES)")
        print("=" * 70)
        for entry in results["mismatch_high"]:
            print(f"\n{entry['filename']}")
            print(f"  Name: {entry['name']}")
            print(f"  Tribe: {entry['tribe']}")
            print(f"  Structured Allotment: {entry['structured']}")
            for num, conf, ctx in entry["candidates"][:3]:
                print(f"    [{conf}/{num}] ...{ctx}...")

    if results["missing_high"]:
        print()
        print("=" * 70)
        print("HIGH-CONFIDENCE FIELD-MISSING RECOVERIES")
        print("(Allotment field empty, but NOTES has explicit 'Allotment No. X')")
        print("=" * 70)
        for entry in results["missing_high"][:30]:
            print(f"\n{entry['filename']}")
            print(f"  Name: {entry['name']}")
            for num, conf, ctx in entry["candidates"][:3]:
                print(f"    [{conf}/{num}] ...{ctx}...")
        if len(results["missing_high"]) > 30:
            print(f"\n  ... and {len(results['missing_high']) - 30} more")


if __name__ == "__main__":
    main()
