#!/usr/bin/env python3
"""
Split Circular 2464 PDFs into per-document files based on Kimi page classifications.

Uses boundary detection rules specific to each document type:
- affidavit_content: "No. XXX" or "being first duly sworn" markers
- questionnaire_content: "Name of Allottee" or "Questions and Answers to Circular"
- agency_narrative_content: "ALLOTMENT NO." header
- ledger_entry_page: aggregate all into one ledger PDF per source
- transmittal_letter, cover_sheet, other: save individually to non_extracted/

Usage:
    python3 split_corpus.py
    python3 split_corpus.py --dry-run    # report boundaries without writing PDFs
"""

import argparse
import csv
import os
import re
import sys

import fitz

# ── Source PDF paths ──

PDF_BASE = "/Users/cwm6W/Library/CloudStorage/OneDrive-UniversityofVirginia/Circular 2464"

LABEL_TO_PDF = {
    "vol1": f"{PDF_BASE}/Pine Ridge Affidavits in Reply to Circular 2464/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3].pdf",
    "vol2": f"{PDF_BASE}/Pine Ridge Affidavits in Reply to Circular 2464/312 Affidavits by Indians who accepted land patents under protest 1928 [2 of 3].pdf",
    "vol3": f"{PDF_BASE}/Pine Ridge Affidavits in Reply to Circular 2464/312 Affidavits by Indians who accepted land patents under protest 1928 [3 of 3].pdf",
    "RG_75_1929_Circular_2464_part_1": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 Circular 2464 part 1.pdf",
    "RG_75_1929_circular_2464_part_2": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2464 part 2.pdf",
    "RG_75_1929_circular_2464_part_3": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2464 part 3.pdf",
    "RG_75_1929_circular_2464_part_6": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2464 part 6.pdf",
    "RG_75_1929_circular_2464_part_7": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2464 part 7.pdf",
    "RG_75_1929_circular_2464_part_8": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2464 part 8.pdf",
    "RG_75_1929_circular_2464_part_9": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2464 part 9.pdf",
    "RG_75_1929_circular_2464_part_10": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2464 part 10.pdf",
    "RG_75_1929_circular_2564_part_11": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2564 part 11.pdf",
    "RG_75_1929_circular_2464_part_12": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2464 part 12.pdf",
    "RG_75_1929_circular_2464_part_13": f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2464 part 13.pdf",
}

# Short labels for output filenames
LABEL_SHORT = {
    "vol1": "pine_ridge_vol1",
    "vol2": "pine_ridge_vol2",
    "vol3": "pine_ridge_vol3",
    "RG_75_1929_Circular_2464_part_1": "part1",
    "RG_75_1929_circular_2464_part_2": "part2",
    "RG_75_1929_circular_2464_part_3": "part3",
    "RG_75_1929_circular_2464_part_6": "part6",
    "RG_75_1929_circular_2464_part_7": "part7",
    "RG_75_1929_circular_2464_part_8": "part8",
    "RG_75_1929_circular_2464_part_9": "part9",
    "RG_75_1929_circular_2464_part_10": "part10",
    "RG_75_1929_circular_2564_part_11": "part11",
    "RG_75_1929_circular_2464_part_12": "part12",
    "RG_75_1929_circular_2464_part_13": "part13",
}

CLS_DIR = "circular_2464_extractions/classifications_kimi_corpus"
OUT_BASE = "circular_2464_extractions/split_documents"


# ── Boundary detection ──

def detect_affidavit_boundary(text):
    """Returns True if this page starts a new affidavit."""
    t = text.strip()
    # "No. XXXX" at or near the start (within first 200 chars)
    if re.search(r'(?<![a-zA-Z] )No\s*\.?\s*\d{1,5}', t[:300]):
        return True
    # "being first duly sworn" near the start
    if re.search(r'being\s+(?:first\s+)?duly\s+sworn', t[:500], re.IGNORECASE):
        return True
    # "first being sworn under oath" (Crow Creek variant)
    if re.search(r'first\s+being\s+sworn\s+under\s+oath', t[:500], re.IGNORECASE):
        return True
    # "Personally appeared" or "personally came"
    if re.search(r'[Pp]ersonally\s+(?:appeared|came)', t[:300]):
        return True
    # "Deponent further states" at very start (Pine Ridge standard)
    if re.search(r'Deponent\s+further\s+states', t[:200], re.IGNORECASE):
        return True
    # Crow Creek county/state header: "County of Buffalo / State of South Dakota. S.S."
    # followed by "I, [Name]" — marks start of a new sworn statement
    if re.search(r'County\s+of\s+Buffalo', t[:300], re.IGNORECASE) and re.search(r'I,\s+[A-Z]', t[:500]):
        return True
    return False


def detect_questionnaire_boundary(text):
    """Returns True if this page starts a new questionnaire."""
    t = text.strip()
    # Search the full page text — OCR may place markers anywhere
    # "Questions and Answers to Circular No. 2464"
    if re.search(r'[Qq]uestions?\s+and\s+[Aa]nswers?\s+to\s+[Cc]ircular', t):
        return True
    # "Name of Allottee" anywhere on the page
    if re.search(r'Name\s+of\s+Allottee', t):
        return True
    # "What is your name and age?" — primary start marker for Rosebud questionnaires
    if re.search(r'What\s+is\s+your\s+name\s+and\s+age', t, re.IGNORECASE):
        return True
    # "Date of patent" combined with "Circular" or "allot" — first page of form
    if re.search(r'[Dd]ate\s+of\s+patent', t) and re.search(r'(?:[Cc]ircular|allot|patent)', t):
        return True
    # Numbered questions restarting at "1." with patent/allotment context
    if re.search(r'(?:^|\n)\s*1\.\s', t[:300]) and re.search(r'(?:patent|allot|receipt|protest)', t, re.IGNORECASE):
        return True
    # Form 5-105 "Application for a Patent in Fee" (Act of May 8, 1906)
    if re.search(r'5[\-\s]*1(?:05|42)', t[:500]):
        return True
    if re.search(r'APPLICATION\s+FOR\s+(?:A\s+)?PATENT\s+IN\s+FEE', t[:500], re.IGNORECASE):
        return True
    if re.search(r'Act\s+of\s+May\s+8,?\s*1906', t[:500], re.IGNORECASE):
        return True
    return False


def detect_narrative_boundary(text):
    """Returns True if this page starts a new agency narrative."""
    t = text.strip()
    # "ALLOTMENT NO." or "ALLOTMENT No." at or near start
    if re.search(r'ALLOTMENT\s+(?:NO|No)\.?\s*\d+', t[:300]):
        return True
    # Also catch partial OCR: "ALLOTMENT Ko." etc.
    if re.search(r'ALLOTMENT\s+\w{1,3}\.?\s*\d+', t[:300]):
        return True
    return False


def extract_allottee_name(text, doc_type):
    """Try to extract allottee name from the first page of a document."""
    if doc_type == "affidavit":
        # Pine Ridge: "No. XXX ... [Name], being first duly sworn"
        m = re.search(r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*,?\s*being\s+(?:first\s+)?duly\s+sworn', text[:500])
        if m:
            return m.group(1).strip()
        # "Deponent [Name]"
        m = re.search(r'No\.\s*\d+.*?([A-Z][a-z]+ [A-Z][a-z]+)', text[:300])
        if m:
            return m.group(1).strip()
    elif doc_type == "questionnaire":
        m = re.search(r'Name\s+of\s+Allottee\s*[:\-]?\s*([A-Za-z\s\.\(\),]+)', text[:500])
        if m:
            return m.group(1).strip().rstrip(',.- ')
    elif doc_type == "agency_narrative":
        m = re.search(r'ALLOTMENT\s+\w{1,3}\.?\s*\d+\s*\n\s*([A-Z][A-Za-z\s\.\(\),]+)', text[:400])
        if m:
            return m.group(1).strip()
    return None


# ── Main splitting logic ──

def load_classifications(label):
    """Load page classifications for a PDF label.
    Normalizes old uncollapsed categories to collapsed ones."""
    csv_path = os.path.join(CLS_DIR, f"{label}_classifications_kimi.csv")
    if not os.path.exists(csv_path):
        return None

    # Map old uncollapsed categories to collapsed
    COLLAPSE = {
        "affidavit": "affidavit_content",
        "affidavit_continuation": "affidavit_content",
        "questionnaire": "questionnaire_content",
        "questionnaire_continuation": "questionnaire_content",
        "agency_narrative": "agency_narrative_content",
        "agency_narrative_continuation": "agency_narrative_content",
    }

    pages = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            cls = row['classification']
            cls = COLLAPSE.get(cls, cls)
            pages[int(row['page_number'])] = cls
    return pages


def split_one_pdf(label, dry_run=False):
    """Split one PDF into per-document files. Returns manifest entries and issues."""
    pdf_path = LABEL_TO_PDF.get(label)
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"  ERROR: PDF not found for {label}")
        return [], []

    classifications = load_classifications(label)
    if not classifications:
        print(f"  ERROR: No classification CSV for {label}")
        return [], []

    doc = fitz.open(pdf_path)
    short = LABEL_SHORT.get(label, label)
    total_pages = len(doc)

    manifest = []
    issues = []

    # Group consecutive pages by classification type
    # Then apply boundary detection within each content-type group

    # Content types that get split into documents
    CONTENT_TYPES = {"affidavit_content", "questionnaire_content", "agency_narrative_content"}
    # Types that get aggregated
    AGGREGATE_TYPES = {"ledger_entry_page"}
    # Types saved individually to non_extracted
    NON_EXTRACT_TYPES = {"transmittal_letter", "cover_sheet", "other"}

    # Build page sequence with classifications
    page_seq = []
    for p in range(1, total_pages + 1):
        cls = classifications.get(p, "other")
        text = doc[p - 1].get_text()
        page_seq.append((p, cls, text))

    # Process content types: group runs of same type, then split at boundaries
    counters = {"affidavit": 0, "questionnaire": 0, "agency_narrative": 0, "ledger": 0}

    # Collect runs of consecutive pages with same content type
    current_type = None
    current_pages = []

    def flush_content_group(content_type, pages_group):
        """Split a group of same-type pages into individual documents."""
        if not pages_group:
            return

        if content_type == "affidavit_content":
            detect_fn = detect_affidavit_boundary
            doc_type = "affidavit"
            out_subdir = "affidavits"
        elif content_type == "questionnaire_content":
            detect_fn = detect_questionnaire_boundary
            doc_type = "questionnaire"
            out_subdir = "questionnaires"
        elif content_type == "agency_narrative_content":
            detect_fn = detect_narrative_boundary
            doc_type = "agency_narrative"
            out_subdir = "agency_narratives"
        else:
            return

        # Split at boundaries
        documents = []
        current_doc = []
        for p, cls, text in pages_group:
            if current_doc and detect_fn(text):
                documents.append(current_doc)
                current_doc = []
            current_doc.append((p, text))

        if current_doc:
            documents.append(current_doc)

        # Check for long documents (potential missing boundary)
        for d in documents:
            if len(d) > 6:
                issues.append(f"{short}: {doc_type} spanning {len(d)} pages ({d[0][0]}-{d[-1][0]}) — possible missing boundary")

        # Check for multi-page groups without boundary markers (3+ pages = suspicious)
        if len(pages_group) >= 3 and len(documents) == 1:
            first_text = pages_group[0][2]
            if not detect_fn(first_text):
                issues.append(f"{short}: {len(pages_group)} {doc_type} pages ({pages_group[0][0]}-{pages_group[-1][0]}) with no boundary marker on first page")

        # Write documents
        for d in documents:
            counters[doc_type] += 1
            idx = counters[doc_type]
            fname = f"{short}_{doc_type}_{idx:03d}.pdf"
            out_dir = os.path.join(OUT_BASE, out_subdir)
            out_path = os.path.join(out_dir, fname)

            page_nums = [p for p, _ in d]
            page_range = f"{page_nums[0]}-{page_nums[-1]}" if len(page_nums) > 1 else str(page_nums[0])

            allottee = extract_allottee_name(d[0][1], doc_type)

            if not dry_run:
                os.makedirs(out_dir, exist_ok=True)
                new_doc = fitz.open()
                for p, _ in d:
                    new_doc.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
                new_doc.save(out_path)

            manifest.append({
                "document_id": fname.replace(".pdf", ""),
                "type": doc_type,
                "source_pdf": os.path.basename(pdf_path),
                "source_pages": page_range,
                "output_path": f"{out_subdir}/{fname}",
                "allottee": allottee or "",
            })

    # Process ledger pages
    ledger_pages = [(p, cls, text) for p, cls, text in page_seq if cls == "ledger_entry_page"]
    if ledger_pages:
        counters["ledger"] += 1
        fname = f"{short}_ledger.pdf"
        out_dir = os.path.join(OUT_BASE, "ledgers")
        out_path = os.path.join(out_dir, fname)
        page_nums = [p for p, _, _ in ledger_pages]
        page_range = f"{page_nums[0]}-{page_nums[-1]}"

        if not dry_run:
            os.makedirs(out_dir, exist_ok=True)
            new_doc = fitz.open()
            for p, _, _ in ledger_pages:
                new_doc.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
            new_doc.save(out_path)

        manifest.append({
            "document_id": fname.replace(".pdf", ""),
            "type": "ledger",
            "source_pdf": os.path.basename(pdf_path),
            "source_pages": page_range,
            "output_path": f"ledgers/{fname}",
            "allottee": "",
        })

    # Process non-extracted pages
    for p, cls, text in page_seq:
        if cls in NON_EXTRACT_TYPES:
            subdir_map = {
                "transmittal_letter": "transmittal_letters",
                "cover_sheet": "cover_sheets",
                "other": "other",
            }
            sub = subdir_map[cls]
            out_dir = os.path.join(OUT_BASE, "non_extracted", sub)
            fname = f"{short}_page_{p:03d}.pdf"

            if not dry_run:
                os.makedirs(out_dir, exist_ok=True)
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
                new_doc.save(os.path.join(out_dir, fname))

    # Process content pages: iterate through page_seq, grouping consecutive same-type
    current_type = None
    current_pages = []

    for p, cls, text in page_seq:
        if cls in CONTENT_TYPES:
            if cls == current_type:
                current_pages.append((p, cls, text))
            else:
                flush_content_group(current_type, current_pages)
                current_type = cls
                current_pages = [(p, cls, text)]
        else:
            flush_content_group(current_type, current_pages)
            current_type = None
            current_pages = []

    flush_content_group(current_type, current_pages)

    return manifest, issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--labels", nargs="*", default=None,
                        help="Specific labels to process (default: all)")
    args = parser.parse_args()

    labels = args.labels or sorted(LABEL_TO_PDF.keys())

    all_manifest = []
    all_issues = []
    type_counts = {"affidavit": 0, "questionnaire": 0, "agency_narrative": 0, "ledger": 0}
    non_extract_counts = {"transmittal_letter": 0, "cover_sheet": 0, "other": 0}
    total_source_pages = 0

    for label in labels:
        if label not in LABEL_TO_PDF:
            print(f"Unknown label: {label}")
            continue

        pdf_path = LABEL_TO_PDF[label]
        if not os.path.exists(pdf_path):
            print(f"PDF not found: {pdf_path}")
            continue

        doc = fitz.open(pdf_path)
        total_source_pages += len(doc)
        print(f"\n{'='*60}")
        print(f"{LABEL_SHORT.get(label, label)} ({len(doc)} pages)")
        print(f"{'='*60}")

        manifest, issues = split_one_pdf(label, dry_run=args.dry_run)
        all_manifest.extend(manifest)
        all_issues.extend(issues)

        # Count
        for m in manifest:
            t = m["type"]
            if t in type_counts:
                type_counts[t] += 1

        # Count non-extracted
        classifications = load_classifications(label)
        if classifications:
            for p, cls in classifications.items():
                if cls in non_extract_counts:
                    non_extract_counts[cls] += 1

        # Print per-PDF summary
        pdf_types = {}
        for m in manifest:
            pdf_types[m["type"]] = pdf_types.get(m["type"], 0) + 1
        print(f"  Documents: {dict(pdf_types)}")
        if issues:
            for iss in issues:
                print(f"  ⚠ {iss}")

    # Write manifest
    if not args.dry_run:
        os.makedirs(OUT_BASE, exist_ok=True)
        manifest_path = os.path.join(OUT_BASE, "manifest.csv")
        with open(manifest_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["document_id", "type", "source_pdf", "source_pages", "output_path", "allottee"])
            w.writeheader()
            w.writerows(all_manifest)
        print(f"\nManifest: {manifest_path} ({len(all_manifest)} entries)")

    # Summary
    print(f"\n{'='*60}")
    print("CORPUS SPLIT SUMMARY")
    print(f"{'='*60}")
    print(f"Source PDFs: {len(labels)}")
    print(f"Source pages: {total_source_pages}")
    print(f"\nDocuments produced:")
    for t, count in sorted(type_counts.items()):
        print(f"  {t:<25} {count:>5}")
    print(f"  {'TOTAL':<25} {sum(type_counts.values()):>5}")
    print(f"\nNon-extracted pages:")
    for t, count in sorted(non_extract_counts.items()):
        print(f"  {t:<25} {count:>5}")
    print(f"  {'TOTAL':<25} {sum(non_extract_counts.values()):>5}")

    if all_issues:
        print(f"\nBoundary detection issues ({len(all_issues)}):")
        for iss in all_issues:
            print(f"  ⚠ {iss}")
    else:
        print(f"\nNo boundary detection issues.")


if __name__ == "__main__":
    main()
