#!/usr/bin/env python3
"""
Load full text from Survey of Conditions PDFs into the database.

Reads each PDF, extracts text with PyMuPDF, and updates the corresponding
document row's full_text, page_count, and file_size fields. This is needed
before running enrich_summaries.py to generate analytical summaries.

Usage:
    python3 load_survey_fulltext.py
    python3 load_survey_fulltext.py --db survey_of_conditions
    python3 load_survey_fulltext.py --force   # overwrite existing full_text
"""

import argparse
import glob
import os
import sys

import fitz  # PyMuPDF
import psycopg2

DB_NAME = "survey_of_conditions"
PDF_DIR = "/Users/cwm6W/projects/exhaustive-extraction-pipeline/survey_pdfs"


def extract_full_text(pdf_path: str) -> tuple:
    """Extract all text from PDF. Returns (text, page_count, file_size)."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += f"--- Page {page.number + 1} ---\n"
        text += page.get_text() + "\n"
    page_count = len(doc)
    file_size = os.path.getsize(pdf_path)
    return text, page_count, file_size


def main():
    parser = argparse.ArgumentParser(description="Load PDF full text into survey database")
    parser.add_argument("--db", default=DB_NAME, help=f"Database name (default: {DB_NAME})")
    parser.add_argument("--pdf-dir", default=PDF_DIR, help="PDF source directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing full_text")
    args = parser.parse_args()

    conn = psycopg2.connect(dbname=args.db, host="localhost")
    cur = conn.cursor()

    # Get all documents in the database
    cur.execute("SELECT id, file_name, display_title FROM documents ORDER BY id")
    docs = cur.fetchall()
    print(f"Found {len(docs)} documents in {args.db}")

    # Find all PDFs (excluding duplicates/partials)
    pdf_files = {}
    for pdf_path in glob.glob(os.path.join(args.pdf_dir, "*.pdf")):
        basename = os.path.basename(pdf_path)
        if "duplicate" in basename.lower() or "partial" in basename.lower():
            continue
        pdf_files[basename] = pdf_path

    updated = 0
    skipped = 0
    not_found = 0

    for doc_id, file_name, display_title in docs:
        # Check if already has full_text
        if not args.force:
            cur.execute("SELECT LENGTH(full_text) FROM documents WHERE id = %s AND full_text IS NOT NULL AND full_text != ''", (doc_id,))
            row = cur.fetchone()
            if row and row[0] and row[0] > 0:
                skipped += 1
                print(f"  SKIP: Doc {doc_id} — {display_title} (already has text)")
                continue

        # Find matching PDF
        matched_pdf = None
        for pdf_name, pdf_path in pdf_files.items():
            # Match by checking if the PDF name starts similarly to the file_name
            if pdf_name == file_name:
                matched_pdf = pdf_path
                break

        # Try fuzzy matching if exact match failed
        if not matched_pdf:
            # The loader converts filenames: spaces→underscores, semicolons→underscores
            # Try to reverse that
            for pdf_name, pdf_path in pdf_files.items():
                pdf_base = os.path.splitext(pdf_name)[0]
                # Normalize both for comparison
                norm_pdf = pdf_base.lower().replace(";", "").replace(",", "").replace(":", "").replace("  ", " ").strip()
                norm_doc = display_title.lower().replace(";", "").replace(",", "").replace(":", "").replace("  ", " ").strip()
                if norm_pdf == norm_doc:
                    matched_pdf = pdf_path
                    break

        if not matched_pdf:
            not_found += 1
            print(f"  MISS: Doc {doc_id} — {display_title} (no matching PDF)")
            continue

        # Extract text and update
        print(f"  [{updated + 1}] Doc {doc_id}: {display_title}...", end=" ", flush=True)
        text, page_count, file_size = extract_full_text(matched_pdf)
        cur.execute("""
            UPDATE documents SET full_text = %s, page_count = %s, file_size = %s
            WHERE id = %s
        """, (text, page_count, file_size, doc_id))
        conn.commit()
        updated += 1
        print(f"{len(text):,} chars, {page_count} pages")

    cur.close()
    conn.close()

    print(f"\nDone. Updated: {updated}, Skipped: {skipped}, No PDF found: {not_found}")


if __name__ == "__main__":
    main()
