#!/usr/bin/env python3
"""
Run Sonnet vision on the 26 CAT_1 candidate sub-PDFs.

Reads the CAT_1 batch manifest (built by prep_cat1_vision_batch.py),
deduplicates to one row per record (manifest has one row per page),
finds each record's sub-PDF, and runs:
  python3 extract_single_pdf.py <pdf> --claude-only --vision --output ...

Output goes to validation_samples/cat1_sonnet_vision/<record_id>/
which mirrors the per-record naming used for tonight's bundle vision runs.

Skips records where validation_samples/cat1_sonnet_vision/<record_id>/vision_merged.json
already exists, so this is idempotent.

Run in parallel with the HPC Qwen batch — Sonnet runs locally, Qwen runs
on HPC. When both complete, compare side by side per record.
"""
import csv
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
MANIFEST = PROJECT_ROOT / "circular_2464_extractions" / "vision_recovery_cat1" / "manifest.csv"
SPLIT_DOCS = PROJECT_ROOT / "circular_2464_extractions" / "split_documents"
OUTPUT_BASE = PROJECT_ROOT / "validation_samples" / "cat1_sonnet_vision"
EXTRACT_SCRIPT = PROJECT_ROOT / "extract_single_pdf.py"


def derive_subdir(record_id):
    if "_affidavit_" in record_id:
        return "affidavits"
    if "_questionnaire_" in record_id:
        return "questionnaires"
    if "_agency_narrative_" in record_id:
        return "agency_narratives"
    return None


def main():
    if not MANIFEST.exists():
        print(f"ERROR: manifest not found at {MANIFEST}")
        print("Run prep_cat1_vision_batch.py first.")
        sys.exit(1)

    if not EXTRACT_SCRIPT.exists():
        print(f"ERROR: extract_single_pdf.py not found at {EXTRACT_SCRIPT}")
        sys.exit(1)

    # Read manifest, deduplicate to one row per record
    seen = set()
    records = []
    with open(MANIFEST) as f:
        for row in csv.DictReader(f):
            rid = row["record_id"]
            if rid in seen:
                continue
            seen.add(rid)
            records.append(rid)

    print(f"Records to process: {len(records)}")
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    n_done_already = 0
    n_processed = 0
    n_failed = 0
    n_pdf_missing = 0

    for i, rid in enumerate(records, 1):
        out_dir = OUTPUT_BASE / rid
        out_file = out_dir / "vision_merged.json"

        if out_file.exists():
            print(f"[{i:2d}/{len(records)}] SKIP {rid} (already done)")
            n_done_already += 1
            continue

        subdir = derive_subdir(rid)
        if not subdir:
            print(f"[{i:2d}/{len(records)}] SKIP {rid} (cannot derive subdir)")
            continue

        pdf_path = SPLIT_DOCS / subdir / f"{rid}.pdf"
        if not pdf_path.exists():
            print(f"[{i:2d}/{len(records)}] PDF NOT FOUND: {pdf_path}")
            n_pdf_missing += 1
            continue

        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"[{i:2d}/{len(records)}] Sonnet vision: {rid}")

        cmd = [
            "python3",
            str(EXTRACT_SCRIPT),
            str(pdf_path),
            "--claude-only",
            "--vision",
            "--output",
            f"{out_dir}/",
        ]
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"   FAILED: returncode {result.returncode}")
            n_failed += 1
        else:
            n_processed += 1

    print()
    print("=" * 70)
    print("Sonnet vision recovery — CAT_1 batch")
    print("=" * 70)
    print(f"Records processed:        {n_processed}")
    print(f"Records skipped (done):   {n_done_already}")
    print(f"Records failed:           {n_failed}")
    print(f"PDFs missing:             {n_pdf_missing}")
    print()
    print(f"Output: {OUTPUT_BASE}")


if __name__ == "__main__":
    main()
