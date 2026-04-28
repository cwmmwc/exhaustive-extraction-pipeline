#!/usr/bin/env python3
"""
Compare affidavit extraction results against the hand-transcribed ground truth.

This script is the canonical comparison tool for Circular 2464 extractions.
It enforces:
  - Explicit file path verification (crashes if files don't exist)
  - Named dedup method (fuzzy matching with stated criteria)
  - Plausibility checks on all reported counts
  - Spot-check output for manual verification

Usage:
    python3 compare_affidavit_extractions.py
    python3 compare_affidavit_extractions.py --spot-check 10
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher

import openpyxl


# ── Ground truth ──

GT_PATH = '/Users/cwm6W/Library/CloudStorage/OneDrive-UniversityofVirginia/Circular 2464/Replies to Circular 2464.xlsx'


def load_ground_truth():
    """Load the hand-transcribed Circular 2464 spreadsheet."""
    assert os.path.exists(GT_PATH), f"Ground truth not found: {GT_PATH}"
    wb = openpyxl.load_workbook(GT_PATH, read_only=True)
    ws = wb['Sheet1']
    rows = list(ws.iter_rows(values_only=True))
    headers = rows[0]
    records = []
    for r in rows[1:]:
        if not r[0]:
            continue
        records.append({
            'name': str(r[0]).strip(),
            'reservation': str(r[1] or '').strip(),
            'allotment': str(r[3] or '').strip(),
            'canceled': str(r[4] or '').strip(),
            'consent': str(r[5] or '').strip(),
            'sold_mortgaged': str(r[7] or '').strip(),
            'buyer': str(r[8] or '').strip(),
        })
    return records


# ── Name normalization and matching ──

# Suffix normalization map
_SUFFIX_MAP = {
    'jr': 'jr', 'jr.': 'jr', 'junior': 'jr',
    'sr': 'sr', 'sr.': 'sr', 'senior': 'sr',
    'ii': 'ii', 'iii': 'iii', 'iv': 'iv',
}


def normalize_name(name):
    """Normalize for matching: lowercase, strip nee/née, remove punctuation, collapse whitespace."""
    n = str(name).lower().strip()
    n = re.sub(r'\b(n[eé]e|formerly|nee)\b', '', n)
    n = re.sub(r'[—\-,\.\(\)\[\]]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def _split_suffix(parts):
    """Split name parts list into (core_parts, suffix).
    suffix is 'jr', 'sr', 'ii', 'iii', 'iv', or None.
    Input: list of name parts (already split by spaces).
    """
    if len(parts) >= 2 and parts[-1] in _SUFFIX_MAP:
        return parts[:-1], _SUFFIX_MAP[parts[-1]]
    return parts, None


def names_match_v1(a, b):
    """Original matcher, retained for reproducibility of earlier results.
    - Last names must match exactly (after normalization)
    - First names must match by: exact, initial, or SequenceMatcher > 0.7
    - If either name has < 2 parts, fall back to full-string SequenceMatcher > 0.85
    """
    a_parts = a.split()
    b_parts = b.split()
    if len(a_parts) < 2 or len(b_parts) < 2:
        return SequenceMatcher(None, a, b).ratio() > 0.85
    if a_parts[-1] != b_parts[-1]:
        return False
    if a_parts[0] == b_parts[0]:
        return True
    if len(a_parts[0]) <= 2 or len(b_parts[0]) <= 2:
        return a_parts[0][0] == b_parts[0][0]
    return SequenceMatcher(None, a_parts[0], b_parts[0]).ratio() > 0.7


def names_match(a, b):
    """Improved matcher (v2). Changes from v1:
    Fix 1 — Suffix handling:
      Normalize jr/jr./junior → 'jr', sr/sr./senior → 'sr'. Strip from name
      for last-name comparison. If BOTH names had a suffix, require they agree
      (jr↔jr, sr↔sr). If only one had a suffix, allow the match (the other
      name may simply omit it).
    Fix 2 — Fuzzy last name:
      If last names differ but SequenceMatcher > 0.85 AND first names match
      exactly, allow the match. Catches OCR variants like Mosseau/Mousseau.
    """
    a_core, a_suf = _split_suffix(a.split())
    b_core, b_suf = _split_suffix(b.split())

    if len(a_core) < 2 or len(b_core) < 2:
        # Fall back to full-string similarity (on core, without suffix)
        a_str = ' '.join(a_core)
        b_str = ' '.join(b_core)
        return SequenceMatcher(None, a_str, b_str).ratio() > 0.85

    a_last = a_core[-1]
    b_last = b_core[-1]
    a_first = a_core[0]
    b_first = b_core[0]

    # Last name comparison
    if a_last == b_last:
        last_ok = True
    elif SequenceMatcher(None, a_last, b_last).ratio() > 0.85 and a_first == b_first:
        # Fix 2: fuzzy last name only if first names match exactly
        last_ok = True
    else:
        return False

    # Suffix check (Fix 1):
    # If both have a suffix, they must agree (jr↔jr, sr↔sr)
    if a_suf and b_suf and a_suf != b_suf:
        return False
    # If only one has a suffix, require exact first name match
    # (prevents "Benjamin Janis" matching "Bejmain Janis Jr" where
    # these are different people with a typo in the spreadsheet)
    suffix_mismatch = bool(a_suf) != bool(b_suf)

    # First name comparison
    if a_first == b_first:
        return True
    if suffix_mismatch:
        # Strict: exact first name required when suffix status differs
        return False
    if len(a_first) <= 2 or len(b_first) <= 2:
        return a_first[0] == b_first[0]
    return SequenceMatcher(None, a_first, b_first).ratio() > 0.7


# ── Load extraction results ──

def load_extraction(dirpath):
    """Load affidavit extraction results from a directory.
    Handles both 'Kimi K2.5.json' and 'claude.json' filenames.
    Crashes if the directory doesn't exist or contains no JSON.
    """
    assert os.path.isdir(dirpath), f"Extraction directory not found: {dirpath}"

    # Find the merged JSON file (not chunk files)
    candidates = []
    for f in os.listdir(dirpath):
        if f.endswith('.json') and 'chunk' not in f.lower():
            candidates.append(os.path.join(dirpath, f))

    assert candidates, f"No merged JSON files found in {dirpath}. Files present: {os.listdir(dirpath)}"

    # If multiple, prefer claude.json over Kimi K2.5.json (warn about both)
    if len(candidates) > 1:
        print(f"  WARNING: Multiple JSON files in {dirpath}: {[os.path.basename(c) for c in candidates]}")

    # Read all and merge
    all_affs = []
    for path in candidates:
        with open(path) as f:
            data = json.load(f)
        affs = data.get('affidavits', [])

        # Normalize field names from alternate schemas (targeted prompt uses
        # deponent_name/consent_language/outcome instead of name/consent/sold)
        for a in affs:
            if 'deponent_name' in a and 'name' not in a:
                a['name'] = a['deponent_name']
            if 'consent_language' in a and 'consent' not in a:
                a['consent'] = a['consent_language']
            if 'outcome' in a and 'sold' not in a:
                a['sold'] = a['outcome']

        # Filter template rows
        affs = [a for a in affs if a.get('name') and str(a['name']) not in
                ('full name of the deponent/allottee', '', '...', 'None')]
        all_affs.extend(affs)
        print(f"  Loaded {len(affs)} records from {os.path.basename(path)}")

    return all_affs


# ── Deduplication ──

def dedup_records(records):
    """Fuzzy dedup by normalized name.
    Method: cluster records where normalize_name() + names_match() agree.
    Pick the best record per cluster (prefer one with allotment number, then longest consent text).
    Returns: (unique_records, clusters_info)
    """
    clusters = []
    for a in records:
        norm = normalize_name(a.get('name', ''))
        if not norm or norm in ('unknown', 'none'):
            continue
        matched_cluster = None
        for cluster in clusters:
            rep_norm = normalize_name(cluster[0].get('name', ''))
            if names_match(norm, rep_norm):
                matched_cluster = cluster
                break
        if matched_cluster:
            matched_cluster.append(a)
        else:
            clusters.append([a])

    unique = []
    for cluster in clusters:
        best = cluster[0]
        for a in cluster[1:]:
            has_allot = bool(a.get('allotment_number') and
                           str(a.get('allotment_number', '')).strip() not in
                           ('', 'None', 'not specified', 'Not specified', 'allotment number'))
            best_has = bool(best.get('allotment_number') and
                          str(best.get('allotment_number', '')).strip() not in
                          ('', 'None', 'not specified', 'Not specified', 'allotment number'))
            if has_allot and not best_has:
                best = a
            elif len(str(a.get('consent', ''))) > len(str(best.get('consent', ''))):
                best = a
        unique.append(best)

    info = {
        'raw': len(records),
        'clusters': len(clusters),
        'singletons': sum(1 for c in clusters if len(c) == 1),
        'merged': [(c[0]['name'], len(c), [a['name'] for a in c]) for c in clusters if len(c) > 1],
        'dropped_unknown': sum(1 for a in records if normalize_name(a.get('name', '')) in ('unknown', 'none', '')),
    }

    return unique, info


# ── Quality metrics ──

def compute_quality(records):
    """Compute per-field completeness metrics."""
    n = len(records)
    if n == 0:
        return {}

    def has_field(a, field):
        val = str(a.get(field, '') or '').strip()
        if field == 'allotment_number':
            # Allotment numbers can be short (e.g., "18", "85") — don't filter by length
            return len(val) > 0 and val.lower() not in ('none', 'not specified', 'n/a', 'unknown', '', 'allotment number')
        return len(val) > 5 and val.lower() not in ('none', 'not specified', 'n/a', 'unknown')

    return {
        'total': n,
        'with_allotment': sum(1 for a in records if has_field(a, 'allotment_number')),
        'with_consent': sum(1 for a in records if has_field(a, 'consent')),
        'with_sold': sum(1 for a in records if has_field(a, 'sold')),
        'with_mortgaged': sum(1 for a in records if has_field(a, 'mortgaged')),
        'with_any_outcome': sum(1 for a in records if has_field(a, 'sold') or has_field(a, 'mortgaged')),
    }


# ── Ground truth matching ──

def match_to_ground_truth(ai_records, gt_records, reservation_filter=None):
    """Match AI records to ground truth by fuzzy name matching.
    Returns: (matched_pairs, unmatched_ai, unmatched_gt)
    """
    if reservation_filter:
        gt_records = [r for r in gt_records if reservation_filter in r.get('reservation', '')]

    gt_norms = [(normalize_name(r['name']), r) for r in gt_records]
    ai_norms = [(normalize_name(a.get('name', '')), a) for a in ai_records]

    matched_pairs = []
    used_gt = set()
    unmatched_ai = []

    for ai_norm, ai_rec in ai_norms:
        found = False
        for i, (gt_norm, gt_rec) in enumerate(gt_norms):
            if i in used_gt:
                continue
            if names_match(ai_norm, gt_norm):
                matched_pairs.append((ai_rec, gt_rec))
                used_gt.add(i)
                found = True
                break
        if not found:
            unmatched_ai.append(ai_rec)

    unmatched_gt = [gt_rec for i, (_, gt_rec) in enumerate(gt_norms) if i not in used_gt]

    return matched_pairs, unmatched_ai, unmatched_gt


# ── Automated checks ──

def _normalize_allotment(val):
    """Normalize allotment number for accuracy comparison.
    Strips 'No.', 'Allot.', whitespace, leading zeros.
    """
    s = re.sub(r'(?i)no\.?|allot\.?|allotment|#', '', str(val or '')).strip()
    s = s.lstrip('0') or '0'
    return s


def check_allotment_accuracy(matched_pairs):
    """For matched pairs where both AI and GT have allotment numbers,
    compare the values. Returns dict with counts and any mismatches."""
    exact = 0
    normalized = 0
    mismatched = []
    both_have = 0

    for ai, gt in matched_pairs:
        ai_val = str(ai.get('allotment_number', '') or '').strip()
        gt_val = str(gt.get('allotment', '') or '').strip()
        ai_empty = ai_val.lower() in ('', 'none', 'not specified', 'n/a', 'unknown', 'allotment number')
        gt_empty = gt_val == ''

        if ai_empty or gt_empty:
            continue

        both_have += 1
        if ai_val == gt_val:
            exact += 1
        elif _normalize_allotment(ai_val) == _normalize_allotment(gt_val):
            normalized += 1
        else:
            mismatched.append((ai.get('name', '?'), ai_val, gt.get('name', '?'), gt_val))

    return {
        'both_have': both_have,
        'exact': exact,
        'normalized': normalized,
        'mismatched': mismatched,
    }


def print_repr_diagnostic(records, label, n=10):
    """Print repr() of key fields for the first n records."""
    print(f"\n  repr() diagnostic (first {min(n, len(records))} records):")
    print(f"  {'Name':<30} {'allotment_number':<20} {'consent':<15} {'sold':<15} {'mortgaged':<15}")
    print(f"  {'-'*93}")
    for a in records[:n]:
        name = str(a.get('name', ''))[:28]
        allot = repr(a.get('allotment_number'))[:18]
        consent = repr(str(a.get('consent', ''))[:10])[:13]
        sold = repr(str(a.get('sold', ''))[:10])[:13]
        mortgaged = repr(str(a.get('mortgaged', ''))[:10])[:13]
        print(f"  {name:<30} {allot:<20} {consent:<15} {sold:<15} {mortgaged:<15}")


def print_false_positive_sample(matched_pairs, n=5):
    """Print n random matched pairs for manual false-positive review."""
    import random
    sample = random.sample(matched_pairs, min(n, len(matched_pairs)))
    print(f"\n  False-positive sample ({len(sample)} pairs):")
    for ai, gt in sample:
        ai_allot = str(ai.get('allotment_number', ''))
        gt_allot = gt.get('allotment', '')
        ai_consent = str(ai.get('consent', ''))[:100]
        gt_consent = gt.get('consent', '')[:100]
        print(f"    AI: {ai.get('name','?'):<35} allot={ai_allot:<8}")
        print(f"    GT: {gt.get('name','?'):<35} allot={gt_allot:<8}")
        print(f"    AI consent: {ai_consent}")
        print(f"    GT consent: {gt_consent}")
        print()


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Compare affidavit extractions against ground truth")
    parser.add_argument("--spot-check", type=int, default=5,
                        help="Number of random matches/non-matches to display for manual verification")
    parser.add_argument("--reservation", default="Pine Ridge",
                        help="Filter ground truth by reservation (default: Pine Ridge)")
    parser.add_argument("--vol1-pdf",
                        default="/Users/cwm6W/Library/CloudStorage/OneDrive-UniversityofVirginia/Circular 2464/Pine Ridge Affidavits in Reply to Circular 2464/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3].pdf",
                        help="Path to Volume 1 PDF for verified denominator cross-reference")
    parser.add_argument("dirs", nargs="*",
                        help="Extraction directories to compare. If empty, uses defaults.")
    args = parser.parse_args()

    # Default extraction directories
    if not args.dirs:
        base = 'circular_2464_extractions'
        args.dirs = []
        for label, subdir in [
            ('Kimi 10K', 'affidavit/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3]'),
            ('Sonnet 10K', 'sonnet_affidavit/vol1'),
            ('Opus 10K', 'opus_affidavit/vol1'),
            ('Sonnet 5K', 'sonnet_affidavit_5k/vol1'),
            ('Opus 5K', 'opus_affidavit_5k/vol1'),
        ]:
            path = os.path.join(base, subdir)
            if os.path.isdir(path):
                args.dirs.append(f"{label}={path}")

    # Load ground truth
    print("Loading ground truth...")
    gt = load_ground_truth()
    gt_by_reservation = [r for r in gt if args.reservation in r.get('reservation', '')]
    print(f"  Total: {len(gt)}, {args.reservation}: {len(gt_by_reservation)}")

    # Verified Volume 1 denominator: cross-reference GT allotment numbers
    # against "No." markers in Volume 1's text. This replaces the earlier
    # proportional estimate (~126) which was 31% too high.
    # If no PDF path is provided, fall back to the full reservation set.
    vol1_pdf = args.vol1_pdf if hasattr(args, 'vol1_pdf') and args.vol1_pdf else None
    if vol1_pdf and os.path.exists(vol1_pdf):
        import fitz
        doc = fitz.open(vol1_pdf)
        vol1_text = ''.join(doc[pg].get_text() for pg in range(len(doc)))
        vol1_nos = set(re.findall(r'No\s*\.?\s*(\d+)', vol1_text))
        gt_filtered = [r for r in gt_by_reservation if r.get('allotment', '') in vol1_nos]
        print(f"  Verified Vol 1 allottees (by allotment cross-reference): {len(gt_filtered)}")
        # Audit assertion: verified denominator should be 96 for Pine Ridge Vol 1
        if 'Pine Ridge' in args.reservation and '1 of 3' in vol1_pdf:
            assert len(gt_filtered) == 96, (
                f"GT filtered to {len(gt_filtered)} records; audit specifies 96 "
                f"verified Volume 1 allottees. Check GT filter logic and verified "
                f"allottee list."
            )
    else:
        gt_filtered = gt_by_reservation
        print(f"  Using full reservation set (no Vol 1 PDF for cross-reference): {len(gt_filtered)}")
        print(f"  ⚠ WARNING: denominator is not volume-specific. Results may include cross-volume matches.")

    denominator = len(gt_filtered)
    print(f"  Denominator: {denominator}")

    # Process each extraction
    print("\n" + "=" * 80)
    results = []

    for dir_spec in args.dirs:
        if '=' in dir_spec:
            label, dirpath = dir_spec.split('=', 1)
        else:
            label = os.path.basename(dir_spec)
            dirpath = dir_spec

        print(f"\n── {label} ──")

        # Load with verification
        raw = load_extraction(dirpath)
        print(f"  Raw records: {len(raw)}")

        # Dedup with stated method
        unique, dedup_info = dedup_records(raw)
        print(f"  After fuzzy dedup: {len(unique)} unique")
        print(f"    Method: normalize(lowercase, strip nee/née, remove punctuation) + "
              f"SequenceMatcher(last_name_exact, first_name > 0.7)")
        print(f"    Dropped 'unknown': {dedup_info['dropped_unknown']}")
        print(f"    Merged clusters: {len(dedup_info['merged'])}")
        for name, count, variants in dedup_info['merged'][:5]:
            print(f"      {name} ({count}x): {variants[:3]}")

        # Quality metrics
        quality = compute_quality(unique)
        print(f"  Quality:")
        print(f"    Allotment #: {quality['with_allotment']}/{quality['total']} "
              f"({quality['with_allotment']*100//quality['total']}%)")
        print(f"    Consent:     {quality['with_consent']}/{quality['total']} "
              f"({quality['with_consent']*100//quality['total']}%)")
        print(f"    Outcome:     {quality['with_any_outcome']}/{quality['total']} "
              f"({quality['with_any_outcome']*100//quality['total']}%)")

        # Match to ground truth
        matched, unmatched_ai, unmatched_gt = match_to_ground_truth(unique, gt_filtered)
        recall = len(matched) / denominator * 100 if denominator > 0 else 0
        print(f"  Recall: {len(matched)}/{denominator} = {recall:.0f}%")
        print(f"  AI records not in GT: {len(unmatched_ai)}")

        # Automated check 1: Allotment accuracy
        allot_acc = check_allotment_accuracy(matched)
        print(f"  Allotment accuracy (pairs where both have values): "
              f"{allot_acc['exact']} exact, {allot_acc['normalized']} format-different, "
              f"{len(allot_acc['mismatched'])} mismatched (of {allot_acc['both_have']})")
        if allot_acc['mismatched']:
            print(f"  ⚠ MISMATCHES:")
            for ai_n, ai_a, gt_n, gt_a in allot_acc['mismatched']:
                print(f"    AI: {ai_n} allot={ai_a}  GT: {gt_n} allot={gt_a}")

        # Automated check 2: repr diagnostic
        print_repr_diagnostic(raw[:10], label)

        # Automated check 3: False-positive sample
        print_false_positive_sample(matched, n=5)

        # Plausibility check
        if len(unique) > denominator * 1.5:
            print(f"  ⚠ PLAUSIBILITY: {len(unique)} unique records from ~{denominator} allottees "
                  f"implies {(len(unique)/denominator - 1)*100:.0f}% over-extraction. Check for dedup failures.")
        if len(unique) < denominator * 0.3:
            print(f"  ⚠ PLAUSIBILITY: {len(unique)} unique records from ~{denominator} allottees "
                  f"implies {len(unique)/denominator*100:.0f}% recall. Check for extraction failures.")

        results.append({
            'label': label,
            'raw': len(raw),
            'unique': len(unique),
            'matched': len(matched),
            'recall': recall,
            'quality': quality,
            'allot_accuracy': allot_acc,
        })

    # Summary table
    print("\n" + "=" * 80)
    print(f"\n{'Model':<15} {'Raw':>6} {'Unique':>7} {'Match':>6} {'Recall':>7} {'Allot%':>7} {'AllotAcc':>9} {'Cons%':>7} {'Out%':>6}")
    print("-" * 80)
    for r in results:
        q = r['quality']
        aa = r['allot_accuracy']
        n = q['total'] or 1
        acc_str = f"{aa['exact']}/{aa['both_have']}" if aa['both_have'] > 0 else "—"
        print(f"{r['label']:<15} {r['raw']:>6} {r['unique']:>7} {r['matched']:>6} {r['recall']:>6.0f}% "
              f"{q['with_allotment']*100//n:>6}% {acc_str:>9} {q['with_consent']*100//n:>6}% {q['with_any_outcome']*100//n:>5}%")
    print(f"{'Human':<15} {'—':>6} {str(denominator):>7} {denominator:>6} {'100':>6}% {'~100':>6}% {'—':>9} {'~100':>6}% {'~95':>5}%")


if __name__ == "__main__":
    main()
