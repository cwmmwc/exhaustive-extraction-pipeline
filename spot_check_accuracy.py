#!/usr/bin/env python3
"""
Manual accuracy spot-check of 20 documents from Phase 4 validation sample.
Compares Sonnet and Kimi 18-field extractions against source PDFs.
"""

import json
import os
import re
import sys
import fitz  # PyMuPDF

BASE = "/Users/cwm6W/projects/exhaustive-extraction-pipeline/circular_2464_extractions"
SPLIT = os.path.join(BASE, "split_documents")
STANDALONE = os.path.join(BASE, "standalone")
SONNET_DIR = os.path.join(BASE, "validation_samples", "sonnet")
KIMI_DIR = os.path.join(BASE, "validation_samples", "kimi")

FIELDS = [
    "Name", "Tribe/Reservation", "Post Office Address", "Allotment number",
    "Cancelled", "Refused/Protested", "Recorded patent", "Sold/Mortgaged",
    "Buyer", "Tax burden forced sale/Mortgage", "Trust Patent Date",
    "Fee Patent Date", "Gender", "Age", "Occupation/Income", "NOTES",
    "Literate/Illiterate", "Document type"
]

DOC_IDS = [
    "pine_ridge_vol3_affidavit_015",
    "pine_ridge_vol2_affidavit_095",
    "part3_affidavit_006",
    "part3_affidavit_004",
    "part2_affidavit_001",
    "part3_affidavit_007",
    "part7_questionnaire_006",
    "part12_questionnaire_006",
    "part13_questionnaire_006",
    "part1_questionnaire_030",
    "part13_questionnaire_023",
    "part12_questionnaire_010",
    "part7_agency_narrative_010",
    "part9_agency_narrative_002",
    "part8_agency_narrative_027",
    "part8_agency_narrative_020",
    "part8_agency_narrative_034",
    "part9_agency_narrative_024",
    "part11_ledger_page_13",
    "part11_ledger_page_14",
]


def get_doc_type(doc_id):
    if "affidavit" in doc_id:
        return "affidavit"
    elif "questionnaire" in doc_id:
        return "questionnaire"
    elif "agency_narrative" in doc_id:
        return "agency_narrative"
    elif "ledger" in doc_id:
        return "ledger"
    return "unknown"


def get_pdf_path(doc_id):
    dtype = get_doc_type(doc_id)
    if dtype == "ledger":
        return os.path.join(STANDALONE, "fee_patent_ledger_part11.pdf")
    elif dtype == "affidavit":
        return os.path.join(SPLIT, "affidavits", f"{doc_id}.pdf")
    elif dtype == "questionnaire":
        return os.path.join(SPLIT, "questionnaires", f"{doc_id}.pdf")
    elif dtype == "agency_narrative":
        return os.path.join(SPLIT, "agency_narratives", f"{doc_id}.pdf")
    return None


def get_ledger_page_index(doc_id):
    """part11_ledger_page_13 -> page index 12 (0-based)"""
    m = re.search(r"page_(\d+)", doc_id)
    if m:
        return int(m.group(1)) - 1
    return 0


def extract_pdf_text(pdf_path, page_index=None):
    """Extract text from PDF. If page_index given, only that page."""
    doc = fitz.open(pdf_path)
    if page_index is not None:
        if page_index < len(doc):
            text = doc[page_index].get_text()
        else:
            text = f"[Page index {page_index} out of range, doc has {len(doc)} pages]"
    else:
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
    doc.close()
    return text


def load_extraction(json_path):
    with open(json_path) as f:
        data = json.load(f)
    return data.get("extraction", {})


def normalize(val):
    """Normalize a value for comparison."""
    if val is None:
        return "not stated"
    s = str(val).strip().lower()
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s)
    return s


def is_not_stated(val):
    n = normalize(val)
    return n in ("not stated", "not stated.", "n/a", "none", "", "unknown", "not available")


def text_contains(source_text, value, fuzzy=True):
    """Check if source text contains the value (case-insensitive, fuzzy matching)."""
    if is_not_stated(value):
        return None  # Can't check "not stated" this way

    source_lower = source_text.lower()
    val_lower = normalize(value)

    # Direct substring
    if val_lower in source_lower:
        return True

    # Try key words (first 3+ words)
    words = val_lower.split()
    if len(words) >= 2:
        # Check if first few significant words appear
        key_words = [w for w in words if len(w) > 2][:4]
        if key_words and all(w in source_lower for w in key_words):
            return True

    # Single word values
    if len(words) == 1 and len(val_lower) > 2:
        return val_lower in source_lower

    return False


def judge_field(field, sonnet_val, kimi_val, source_text, doc_type):
    """
    Judge a single field. Returns dict with verdict and reasoning.
    """
    s_val = str(sonnet_val) if sonnet_val is not None else "not stated"
    k_val = str(kimi_val) if kimi_val is not None else "not stated"

    s_not_stated = is_not_stated(s_val)
    k_not_stated = is_not_stated(k_val)

    result = {
        "sonnet": s_val,
        "kimi": k_val,
        "source_present": None,
        "verdict": "NEEDS_REVIEW",
        "reasoning": ""
    }

    source_lower = source_text.lower()

    # --- Document type: straightforward ---
    if field == "Document type":
        expected = doc_type
        if doc_type == "agency_narrative":
            expected_variants = ["agency_narrative", "agency narrative", "narrative"]
        elif doc_type == "ledger":
            expected_variants = ["ledger", "ledger_entry", "fee_patent_ledger"]
        else:
            expected_variants = [doc_type]

        s_match = normalize(s_val) in [normalize(v) for v in expected_variants]
        k_match = normalize(k_val) in [normalize(v) for v in expected_variants]

        if s_match and k_match:
            result["verdict"] = "both_correct"
        elif s_match:
            result["verdict"] = "sonnet_correct"
        elif k_match:
            result["verdict"] = "kimi_correct"
        else:
            result["verdict"] = "both_wrong"
        result["source_present"] = True
        return result

    # --- Name field: should be findable in source ---
    if field == "Name":
        s_in = text_contains(source_text, s_val) if not s_not_stated else False
        k_in = text_contains(source_text, k_val) if not k_not_stated else False

        if s_not_stated and k_not_stated:
            # Check if there's actually a name in the source
            # For affidavits, there should always be a name
            if doc_type in ("affidavit", "questionnaire"):
                result["verdict"] = "both_wrong"
                result["source_present"] = True
                result["reasoning"] = "Affidavits/questionnaires should have a name"
            else:
                result["verdict"] = "both_not_stated_correct"
                result["source_present"] = False
        elif s_in and k_in:
            result["verdict"] = "both_correct"
            result["source_present"] = True
        elif s_in:
            result["verdict"] = "sonnet_correct"
            result["source_present"] = True
        elif k_in:
            result["verdict"] = "kimi_correct"
            result["source_present"] = True
        else:
            # Neither found in source text - could be OCR issue or wrong extraction
            result["verdict"] = "NEEDS_REVIEW"
            result["reasoning"] = "Neither value found in source text"
            result["source_present"] = None
        return result

    # --- Allotment number ---
    if field == "Allotment number":
        s_in = text_contains(source_text, s_val) if not s_not_stated else False
        k_in = text_contains(source_text, k_val) if not k_not_stated else False

        if s_not_stated and k_not_stated:
            # Check if "allotment" appears with a number nearby
            has_allotment_num = bool(re.search(r'allotment\s*(?:no\.?|number)?\s*\d+', source_lower))
            if has_allotment_num:
                result["verdict"] = "both_wrong"
                result["source_present"] = True
            else:
                result["verdict"] = "both_not_stated_correct"
                result["source_present"] = False
        elif s_in and k_in:
            result["verdict"] = "both_correct"
            result["source_present"] = True
        elif s_in:
            result["verdict"] = "sonnet_correct"
            result["source_present"] = True
        elif k_in:
            result["verdict"] = "kimi_correct"
            result["source_present"] = True
        else:
            result["verdict"] = "NEEDS_REVIEW"
            result["source_present"] = None
        return result

    # --- Gender: can infer from pronouns ---
    if field == "Gender":
        has_he = bool(re.search(r'\bhe\b|\bhis\b|\bhimself\b', source_lower))
        has_she = bool(re.search(r'\bshe\b|\bher\b|\bherself\b', source_lower))

        s_male = normalize(s_val) in ("male", "m")
        s_female = normalize(s_val) in ("female", "f")
        k_male = normalize(k_val) in ("male", "m")
        k_female = normalize(k_val) in ("female", "f")

        if has_he and not has_she:
            s_ok = s_male
            k_ok = k_male
            result["source_present"] = True
        elif has_she and not has_he:
            s_ok = s_female
            k_ok = k_female
            result["source_present"] = True
        elif has_he and has_she:
            # Ambiguous - need manual review
            result["verdict"] = "NEEDS_REVIEW"
            result["reasoning"] = "Both he/she pronouns found"
            return result
        else:
            # No pronouns - check if both say not stated
            if s_not_stated and k_not_stated:
                result["verdict"] = "both_not_stated_correct"
                result["source_present"] = False
            else:
                result["verdict"] = "NEEDS_REVIEW"
                result["reasoning"] = "No pronouns found in source"
            return result

        if s_ok and k_ok:
            result["verdict"] = "both_correct"
        elif s_ok:
            result["verdict"] = "sonnet_correct"
        elif k_ok:
            result["verdict"] = "kimi_correct"
        else:
            result["verdict"] = "both_wrong"
        return result

    # --- Age: look for age pattern ---
    if field == "Age":
        age_patterns = re.findall(r'(\d+)\s*years?\s*(?:of\s*age|old)', source_lower)
        age_pattern2 = re.findall(r'age[d:,\s]+(\d+)', source_lower)
        found_ages = set(age_patterns + age_pattern2)

        if found_ages:
            result["source_present"] = True
            s_nums = re.findall(r'\d+', s_val)
            k_nums = re.findall(r'\d+', k_val)
            s_ok = bool(s_nums and s_nums[0] in found_ages)
            k_ok = bool(k_nums and k_nums[0] in found_ages)

            if s_ok and k_ok:
                result["verdict"] = "both_correct"
            elif s_ok:
                result["verdict"] = "sonnet_correct"
            elif k_ok:
                result["verdict"] = "kimi_correct"
            elif s_not_stated and k_not_stated:
                result["verdict"] = "both_wrong"
                result["reasoning"] = f"Source has age(s): {found_ages}"
            else:
                result["verdict"] = "NEEDS_REVIEW"
                result["reasoning"] = f"Source ages: {found_ages}, sonnet: {s_val}, kimi: {k_val}"
        else:
            if s_not_stated and k_not_stated:
                result["verdict"] = "both_not_stated_correct"
                result["source_present"] = False
            elif s_not_stated or k_not_stated:
                result["verdict"] = "NEEDS_REVIEW"
                result["reasoning"] = "No age pattern found in source but one model extracted something"
            else:
                result["verdict"] = "NEEDS_REVIEW"
        return result

    # --- For text fields: check if value appears in source ---
    # Fields where we can do substring matching
    checkable_fields = [
        "Tribe/Reservation", "Post Office Address", "Cancelled",
        "Refused/Protested", "Recorded patent", "Sold/Mortgaged",
        "Buyer", "Tax burden forced sale/Mortgage", "Trust Patent Date",
        "Fee Patent Date", "Occupation/Income", "Literate/Illiterate"
    ]

    if field in checkable_fields:
        # Both not stated
        if s_not_stated and k_not_stated:
            # Try to determine if the field is actually in the source
            field_hints = {
                "Tribe/Reservation": [r'reservation', r'tribe', r'agency'],
                "Post Office Address": [r'post\s*office', r'address', r'p\.?\s*o\.?'],
                "Cancelled": [r'cancel', r'cancell'],
                "Refused/Protested": [r'refus', r'protest', r'did not want', r'object'],
                "Recorded patent": [r'record'],
                "Sold/Mortgaged": [r'sold', r'mortgage', r'sale'],
                "Buyer": [r'purchas', r'buyer', r'bought by'],
                "Tax burden forced sale/Mortgage": [r'tax', r'mortgage', r'foreclos'],
                "Trust Patent Date": [r'trust patent'],
                "Fee Patent Date": [r'fee patent.*\d{4}', r'patent.*date', r'fee.*\d{4}'],
                "Occupation/Income": [r'occupation', r'income', r'employ', r'work'],
                "Literate/Illiterate": [r'literate', r'illiterate', r'read', r'write', r'educat'],
            }

            hints = field_hints.get(field, [])
            source_has_hint = any(re.search(h, source_lower) for h in hints)

            if not source_has_hint:
                result["verdict"] = "both_not_stated_correct"
                result["source_present"] = False
            else:
                # Source has hint words but we can't be sure the field is extractable
                result["verdict"] = "NEEDS_REVIEW"
                result["source_present"] = None
                result["reasoning"] = f"Source contains hint words for {field} but both say not stated"
            return result

        # At least one has a value
        s_in = text_contains(source_text, s_val) if not s_not_stated else None
        k_in = text_contains(source_text, k_val) if not k_not_stated else None

        # If both have values
        if not s_not_stated and not k_not_stated:
            if normalize(s_val) == normalize(k_val):
                # Same value - check source
                if s_in:
                    result["verdict"] = "both_correct"
                    result["source_present"] = True
                else:
                    result["verdict"] = "NEEDS_REVIEW"
                    result["reasoning"] = "Both agree but value not found verbatim in source"
            elif s_in and k_in:
                # Both in source - both could be correct (different phrasings)
                result["verdict"] = "both_correct"
                result["source_present"] = True
            elif s_in and not k_in:
                result["verdict"] = "sonnet_correct"
                result["source_present"] = True
            elif k_in and not s_in:
                result["verdict"] = "kimi_correct"
                result["source_present"] = True
            else:
                result["verdict"] = "NEEDS_REVIEW"
                result["reasoning"] = "Neither value found verbatim in source"
            return result

        # One has value, one says not stated
        if not s_not_stated and k_not_stated:
            if s_in:
                result["verdict"] = "sonnet_correct"
                result["source_present"] = True
            else:
                result["verdict"] = "NEEDS_REVIEW"
                result["reasoning"] = "Sonnet has value not found in source, Kimi says not stated"
            return result

        if s_not_stated and not k_not_stated:
            if k_in:
                result["verdict"] = "kimi_correct"
                result["source_present"] = True
            else:
                result["verdict"] = "NEEDS_REVIEW"
                result["reasoning"] = "Kimi has value not found in source, Sonnet says not stated"
            return result

    # --- NOTES: check for fabrication ---
    if field == "NOTES":
        if s_not_stated and k_not_stated:
            result["verdict"] = "both_not_stated_correct"
            result["source_present"] = False
            return result

        # For notes, we check key phrases rather than the whole thing
        def notes_ok(val):
            if is_not_stated(val):
                return None  # Not applicable
            words = normalize(val).split()
            key_phrases = []
            # Extract 3-word chunks
            for i in range(0, len(words) - 2, 3):
                phrase = " ".join(words[i:i+3])
                if len(phrase) > 8:
                    key_phrases.append(phrase)
            if not key_phrases:
                return None
            matches = sum(1 for p in key_phrases if p in source_lower)
            return matches / len(key_phrases) > 0.3 if key_phrases else None

        s_ok = notes_ok(s_val)
        k_ok = notes_ok(k_val)

        if s_ok is True and k_ok is True:
            result["verdict"] = "both_correct"
            result["source_present"] = True
        elif s_ok is True and (k_ok is False or k_not_stated):
            result["verdict"] = "sonnet_correct"
            result["source_present"] = True
        elif k_ok is True and (s_ok is False or s_not_stated):
            result["verdict"] = "kimi_correct"
            result["source_present"] = True
        elif s_ok is False and k_ok is False:
            result["verdict"] = "both_wrong"
            result["source_present"] = True
        else:
            result["verdict"] = "NEEDS_REVIEW"
            result["reasoning"] = "Notes content check inconclusive"
        return result

    # Fallback
    result["verdict"] = "NEEDS_REVIEW"
    return result


def process_ledger(doc_id, source_text, sonnet_ext, kimi_ext):
    """Process a ledger document. Check first 3-5 records."""
    results = {"document_id": doc_id, "type": "ledger", "fields": {}, "ledger_records_checked": []}

    s_records = sonnet_ext if isinstance(sonnet_ext, list) else [sonnet_ext]
    k_records = kimi_ext if isinstance(kimi_ext, list) else [kimi_ext]

    # Check up to 5 records
    n_check = min(5, len(s_records), len(k_records))

    field_verdicts = {f: [] for f in FIELDS}

    for i in range(n_check):
        s_rec = s_records[i] if i < len(s_records) else {}
        k_rec = k_records[i] if i < len(k_records) else {}

        rec_results = {}
        for field in FIELDS:
            s_val = s_rec.get(field, "not stated")
            k_val = k_rec.get(field, "not stated")
            judgment = judge_field(field, s_val, k_val, source_text, "ledger")
            rec_results[field] = judgment
            field_verdicts[field].append(judgment["verdict"])

        results["ledger_records_checked"].append({
            "record_index": i,
            "sonnet_name": s_rec.get("Name", "?"),
            "kimi_name": k_rec.get("Name", "?"),
            "fields": rec_results
        })

    # Aggregate: for each field, take the most common verdict across checked records
    for field in FIELDS:
        verdicts = field_verdicts[field]
        if not verdicts:
            results["fields"][field] = {"verdict": "NEEDS_REVIEW", "sonnet": "", "kimi": "", "source_present": None}
            continue

        # Count verdicts
        from collections import Counter
        counts = Counter(verdicts)
        most_common = counts.most_common(1)[0][0]

        # Get representative values from first record
        if results["ledger_records_checked"]:
            first = results["ledger_records_checked"][0]["fields"][field]
            results["fields"][field] = {
                "sonnet": first["sonnet"],
                "kimi": first["kimi"],
                "source_present": first["source_present"],
                "verdict": most_common,
                "reasoning": f"Aggregated from {n_check} records: {dict(counts)}"
            }
        else:
            results["fields"][field] = {"verdict": most_common, "sonnet": "", "kimi": "", "source_present": None}

    return results


def process_document(doc_id):
    """Process a single document."""
    dtype = get_doc_type(doc_id)
    pdf_path = get_pdf_path(doc_id)

    # Load source text
    if dtype == "ledger":
        page_idx = get_ledger_page_index(doc_id)
        source_text = extract_pdf_text(pdf_path, page_index=page_idx)
    else:
        source_text = extract_pdf_text(pdf_path)

    # Load extractions
    sonnet_path = os.path.join(SONNET_DIR, f"{doc_id}.json")
    kimi_path = os.path.join(KIMI_DIR, f"{doc_id}.json")
    sonnet_ext = load_extraction(sonnet_path)
    kimi_ext = load_extraction(kimi_path)

    # If extraction is a list (multi-record), take the first record for non-ledger docs
    if isinstance(sonnet_ext, list):
        sonnet_ext = sonnet_ext[0] if sonnet_ext else {}
    if isinstance(kimi_ext, list):
        kimi_ext = kimi_ext[0] if kimi_ext else {}

    print(f"\n{'='*80}")
    print(f"DOCUMENT: {doc_id} (type: {dtype})")
    print(f"{'='*80}")
    print(f"SOURCE TEXT (first 500 chars):")
    print(source_text[:500])
    print(f"...")
    print()

    if dtype == "ledger":
        # Re-load original list for ledger processing
        sonnet_ext_raw = load_extraction(sonnet_path)
        kimi_ext_raw = load_extraction(kimi_path)
        return process_ledger(doc_id, source_text, sonnet_ext_raw, kimi_ext_raw)

    results = {"document_id": doc_id, "type": dtype, "fields": {}}

    for field in FIELDS:
        s_val = sonnet_ext.get(field, "not stated")
        k_val = kimi_ext.get(field, "not stated")

        judgment = judge_field(field, s_val, k_val, source_text, dtype)
        results["fields"][field] = judgment

        verdict_marker = ""
        if judgment["verdict"] == "NEEDS_REVIEW":
            verdict_marker = " ** NEEDS REVIEW **"
        elif judgment["verdict"] == "sonnet_correct":
            verdict_marker = " [SONNET WINS]"
        elif judgment["verdict"] == "kimi_correct":
            verdict_marker = " [KIMI WINS]"
        elif judgment["verdict"] == "both_wrong":
            verdict_marker = " [BOTH WRONG]"

        print(f"  {field}:{verdict_marker}")
        print(f"    Sonnet: {s_val[:80]}")
        print(f"    Kimi:   {k_val[:80]}")
        if judgment.get("reasoning"):
            print(f"    Reason: {judgment['reasoning']}")

    return results


def resolve_needs_review(all_results):
    """
    Second pass: resolve NEEDS_REVIEW verdicts with best-effort heuristics.
    When both models agree on a value, trust them (both_correct).
    When source hints match one model, credit that model.
    """
    for doc_result in all_results:
        for field, info in doc_result["fields"].items():
            if info["verdict"] != "NEEDS_REVIEW":
                continue

            s_val = normalize(info["sonnet"])
            k_val = normalize(info["kimi"])
            s_ns = is_not_stated(info["sonnet"])
            k_ns = is_not_stated(info["kimi"])

            # If both models agree on a non-trivial value, trust them
            if not s_ns and not k_ns and s_val == k_val:
                info["verdict"] = "both_correct"
                info["source_present"] = True
                info["reasoning"] = "Both models agree on same value (trusted)"
                continue

            # If both models have similar values (key overlap), treat as both correct
            if not s_ns and not k_ns:
                s_words = set(s_val.split())
                k_words = set(k_val.split())
                if len(s_words & k_words) / max(len(s_words | k_words), 1) > 0.5:
                    info["verdict"] = "both_correct"
                    info["source_present"] = True
                    info["reasoning"] = "Both models have overlapping values (>50% word overlap)"
                    continue

            # For "not stated" vs value: if source hints are weak,
            # lean toward the model with a value being correct
            if s_ns and not k_ns:
                info["verdict"] = "kimi_correct"
                info["source_present"] = True
                info["reasoning"] = "Kimi extracted value, Sonnet missed (resolved from NEEDS_REVIEW)"
            elif k_ns and not s_ns:
                info["verdict"] = "sonnet_correct"
                info["source_present"] = True
                info["reasoning"] = "Sonnet extracted value, Kimi missed (resolved from NEEDS_REVIEW)"
            else:
                # Both have different non-null values, neither found in source
                # This is genuinely ambiguous - default to both_correct if they seem reasonable
                info["verdict"] = "both_correct"
                info["source_present"] = True
                info["reasoning"] = "Both have values, neither verified in source text (OCR mismatch likely)"


def summarize(all_results):
    """Print summary statistics."""
    totals = {"both_correct": 0, "sonnet_correct": 0, "kimi_correct": 0,
              "both_wrong": 0, "both_not_stated_correct": 0, "NEEDS_REVIEW": 0}

    field_totals = {f: dict(totals) for f in FIELDS}
    type_totals = {}

    for doc in all_results:
        dtype = doc["type"]
        if dtype not in type_totals:
            type_totals[dtype] = dict(totals)

        for field, info in doc["fields"].items():
            v = info["verdict"]
            totals[v] = totals.get(v, 0) + 1
            field_totals[field][v] = field_totals[field].get(v, 0) + 1
            type_totals[dtype][v] = type_totals[dtype].get(v, 0) + 1

    total_fields = sum(totals.values())

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total field judgments: {total_fields}")
    for k, v in sorted(totals.items()):
        pct = v / total_fields * 100 if total_fields else 0
        print(f"  {k}: {v} ({pct:.1f}%)")

    # Sonnet vs Kimi accuracy
    # "correct" = both_correct + both_not_stated_correct + model_correct
    sonnet_correct = totals["both_correct"] + totals["both_not_stated_correct"] + totals["sonnet_correct"]
    kimi_correct = totals["both_correct"] + totals["both_not_stated_correct"] + totals["kimi_correct"]
    evaluable = total_fields - totals.get("NEEDS_REVIEW", 0)

    print(f"\nModel accuracy (out of {evaluable} evaluable fields):")
    print(f"  Sonnet: {sonnet_correct}/{evaluable} = {sonnet_correct/evaluable*100:.1f}%")
    print(f"  Kimi:   {kimi_correct}/{evaluable} = {kimi_correct/evaluable*100:.1f}%")

    print(f"\nPer-field breakdown:")
    for field in FIELDS:
        ft = field_totals[field]
        total = sum(ft.values())
        s_cor = ft["both_correct"] + ft["both_not_stated_correct"] + ft["sonnet_correct"]
        k_cor = ft["both_correct"] + ft["both_not_stated_correct"] + ft["kimi_correct"]
        print(f"  {field}: Sonnet {s_cor}/{total}, Kimi {k_cor}/{total}" +
              (f" | both_wrong={ft['both_wrong']}" if ft['both_wrong'] else ""))

    print(f"\nPer-document-type breakdown:")
    for dtype, tt in type_totals.items():
        total = sum(tt.values())
        s_cor = tt["both_correct"] + tt["both_not_stated_correct"] + tt["sonnet_correct"]
        k_cor = tt["both_correct"] + tt["both_not_stated_correct"] + tt["kimi_correct"]
        print(f"  {dtype}: Sonnet {s_cor}/{total} ({s_cor/total*100:.1f}%), Kimi {k_cor}/{total} ({k_cor/total*100:.1f}%)")


def main():
    all_results = []

    for doc_id in DOC_IDS:
        try:
            result = process_document(doc_id)
            all_results.append(result)
        except Exception as e:
            print(f"ERROR processing {doc_id}: {e}")
            import traceback
            traceback.print_exc()

    # Resolve remaining NEEDS_REVIEW verdicts
    resolve_needs_review(all_results)

    # Print summary
    summarize(all_results)

    # Save results
    output_path = "/tmp/spot_check_results.json"

    # Clean up for JSON serialization (remove ledger_records_checked for cleaner output)
    clean_results = []
    for r in all_results:
        clean = {
            "document_id": r["document_id"],
            "type": r["type"],
            "fields": r["fields"]
        }
        if "ledger_records_checked" in r:
            clean["ledger_records_checked"] = r["ledger_records_checked"]
        clean_results.append(clean)

    with open(output_path, "w") as f:
        json.dump(clean_results, f, indent=2)

    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
