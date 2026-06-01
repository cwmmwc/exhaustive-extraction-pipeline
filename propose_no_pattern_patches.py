#!/usr/bin/env python3
"""
Proposal script: identify Allotment number candidates from NOTES patterns.

Walks every record with Allotment='not stated' and looks for patterns like
"No. NNNN", "Document No. NNNN", "document number NNNN", "File No. NNNN"
in NOTES. These are typewritten Pine Ridge affidavits and similar forms
where Sonnet captured the allotment number from the page header but
classified it as a "document number" instead of an allotment.

User-confirmed exemplars:
  - Eugene Means: NOTES "document number No. 2249" → allotment 2249
  - Lucy Patton: NOTES "document No. 6802" → allotment 6802

The hypothesis was confirmed via BLM cross-reference. This script proposes
the bulk patch but does NOT apply it. Output is a TSV manifest for user
review BEFORE applying.

Excludes:
  - Numbers known to be wrong: 2464 (Circular number itself), 3464
    (hallucinated by Sonnet on part11_questionnaire_002 — confirmed via
    source review that it does not exist on the page)
  - Multi-allottee bundled record part11_questionnaire_002 (Rosa
    Vanderbloom AND Viola Wallace; needs separate splitting patch)
  - Numbers in suspicious contexts ("Allotment No. NNNN (someone else's
    name)", file references, etc.)

Output:
  /mnt/user-data/outputs/no_pattern_proposals.tsv

Columns:
  filename, name, allotment_candidate, confidence, action, notes_snippet

Confidence values:
  HIGH    Strong allotment-pattern context (Document No., document number,
          No. NNNN immediately before/after demographic data on Pine Ridge
          typewritten affidavits)
  MEDIUM  Plausible but should be verified
  LOW     Unusual context, very low number, or ambiguous
  SKIP    Demonstrably wrong (file reference, narrative about other person)

Action values:
  APPLY   Confidence is HIGH and we recommend bulk-applying
  REVIEW  User should look before applying
  SKIP    Do not apply

Usage:
  python3 propose_no_pattern_patches.py
  # then review the TSV
  # then run apply_no_pattern_patches.py
"""
import json
import re
from pathlib import Path

PROJECT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT / "circular_2464_extractions" / "extractions" / "sonnet"
OUTPUT_TSV = PROJECT / "validation_samples" / "task5_campaign" / "no_pattern_proposals.tsv"
OUTPUT_TSV.parent.mkdir(parents=True, exist_ok=True)

# Numbers known NOT to be allotment numbers
EXCLUDE_NUMBERS = {
    "2464",   # Circular No. 2464 itself
    "3464",   # hallucinated by Sonnet on part11_q_002, confirmed not on source
    "1142",   # File reference 5-1142 appears in Shawnee Agency NOTES
    "1928",   # Year, often appears as "sworn ... 1928"
    "1929",   # Year
    "1919",   # Year
    "1920",   # Year
    "1921",   # Year (Shawnee cover letter says "prior to year 1921")
    "5563",   # File reference for Whitcher etc.
}

# Records to skip entirely (need separate handling)
SKIP_RECORDS = {
    "part11_questionnaire_002.json",  # multi-allottee bundle (Vanderbloom + Wallace)
}

# Patterns to extract candidate numbers
# Order matters: more-specific patterns first
PATTERNS = [
    ("Document_No",      re.compile(r"\bDocument\s+No\.?\s*(\d{2,5})\b", re.IGNORECASE)),
    ("document_number",  re.compile(r"\bdocument\s+number\s+(?:No\.?\s*)?(\d{2,5})\b", re.IGNORECASE)),
    ("File_No",          re.compile(r"\bFile\s+No\.?\s*(\d{2,5})\b", re.IGNORECASE)),
    ("No_NNNN",          re.compile(r"\bNo\.\s*(\d{2,5})\b")),
]

# Substrings that suggest the number is NOT an allotment for this allottee
SUSPICIOUS_CONTEXT_KEYWORDS = [
    "file reference",
    "circular ",
    "another allottee",
    "someone else",
]


def context_around(notes, num, radius=70):
    idx = notes.find(num)
    if idx < 0:
        return ""
    start = max(0, idx - radius)
    end = min(len(notes), idx + len(num) + radius)
    snippet = notes[start:end].replace("\n", " ").replace("\t", " ")
    return ("..." if start > 0 else "") + snippet + ("..." if end < len(notes) else "")


def classify(filename, name, candidate_nums, notes, pattern_hits):
    """Return (confidence, action, primary_candidate, snippet, reason)."""
    if not candidate_nums:
        return None

    if len(candidate_nums) > 1:
        # Multiple candidates — needs review
        primary = sorted(candidate_nums)[0]
        snippet = context_around(notes, primary)
        return ("LOW", "REVIEW", primary, snippet,
                f"Multiple candidates: {sorted(candidate_nums)}")

    primary = list(candidate_nums)[0]
    snippet = context_around(notes, primary)

    # Check for suspicious context
    snippet_lower = snippet.lower()
    for keyword in SUSPICIOUS_CONTEXT_KEYWORDS:
        if keyword in snippet_lower:
            return ("LOW", "SKIP", primary, snippet,
                    f"Suspicious context contains '{keyword}'")

    # Check for "Allotment No. NNNN (Other Person)" pattern
    if re.search(rf"Allotment\s+No\.?\s*{primary}\s*\([A-Z]", snippet):
        return ("LOW", "SKIP", primary, snippet,
                "Number labeled as another person's allotment")

    # Number sanity: <10 too low for typical allotment, >100000 too high
    num = int(primary)
    if num < 10:
        return ("LOW", "REVIEW", primary, snippet,
                f"Suspiciously low number ({num}) — could be page/seq number")
    if num > 50000:
        return ("MEDIUM", "REVIEW", primary, snippet,
                f"High number ({num}) — verify against tribal allotment range")

    # Strong pattern: "Document No.", "document number" — confident
    pattern_labels = {p[0] for p in pattern_hits}
    if "Document_No" in pattern_labels or "document_number" in pattern_labels:
        return ("HIGH", "APPLY", primary, snippet, "Strong pattern match")

    # Just "No. NNNN" — moderate confidence; the pattern is right but more
    # ambiguous than explicit "Document No." labeling
    return ("MEDIUM", "REVIEW", primary, snippet, "Generic No. NNNN pattern")


def main():
    proposals = []
    skipped = []

    for path in sorted(EXTRACTIONS.glob("*.json")):
        if path.name == "usage_summary.json":
            continue
        if path.name in SKIP_RECORDS:
            skipped.append((path.name, "Multi-allottee bundle"))
            continue

        try:
            record = json.load(open(path))
        except (json.JSONDecodeError, OSError):
            continue

        e = record.get("extraction", {})
        if isinstance(e, list):
            e = e[0] if e else {}

        allot = (e.get("Allotment number") or "").strip()
        if allot not in ("", "not stated"):
            continue

        notes = e.get("NOTES") or ""
        candidate_nums = set()
        pattern_hits = []
        for label, pat in PATTERNS:
            for num in pat.findall(notes):
                if num in EXCLUDE_NUMBERS:
                    continue
                candidate_nums.add(num)
                pattern_hits.append((label, num))

        if not candidate_nums:
            continue

        result = classify(path.name, e.get("Name", ""),
                          candidate_nums, notes, pattern_hits)
        if result is None:
            continue

        confidence, action, primary, snippet, reason = result
        proposals.append({
            "filename": path.name,
            "name": e.get("Name", "") or "(blank)",
            "candidate": primary,
            "confidence": confidence,
            "action": action,
            "reason": reason,
            "snippet": snippet,
        })

    # Write TSV
    with open(OUTPUT_TSV, "w") as f:
        f.write("filename\tname\tcandidate\tconfidence\taction\treason\tsnippet\n")
        for p in proposals:
            f.write(f"{p['filename']}\t{p['name']}\t{p['candidate']}\t"
                    f"{p['confidence']}\t{p['action']}\t{p['reason']}\t"
                    f"{p['snippet']}\n")

    print(f"Proposals written: {OUTPUT_TSV}")
    print(f"Total: {len(proposals)} proposals")
    print()

    # Summary by action
    from collections import Counter
    by_action = Counter(p["action"] for p in proposals)
    by_confidence = Counter(p["confidence"] for p in proposals)
    print("By action:")
    for k, v in by_action.most_common():
        print(f"  {v:4d}  {k}")
    print()
    print("By confidence:")
    for k, v in by_confidence.most_common():
        print(f"  {v:4d}  {k}")
    print()

    if skipped:
        print(f"Records explicitly skipped ({len(skipped)}):")
        for fn, reason in skipped:
            print(f"  {fn}: {reason}")
    print()
    print("Next: review the TSV, then run apply_no_pattern_patches.py")


if __name__ == "__main__":
    main()
