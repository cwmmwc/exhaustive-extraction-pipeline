#!/usr/bin/env python3
"""
Prepare the CAT_1 vision recovery batch directory.

For each current CAT_1 record (Sonnet missed both Name and Allotment):
  1. Find the corresponding sub-PDF in split_documents/<type>/
  2. Render each page to PNG at 200 DPI
  3. Add an entry to manifest.csv with the format the Qwen slurm expects

Excludes records already resolved earlier in this session:
  - part10_questionnaire_015 (Addie Easton Payne — patched 2026-05-03)
  - part10_affidavit_004 (likely Hannah Hardin signature page; see part10_questionnaire_012)

Output structure:
  circular_2464_extractions/vision_recovery_cat1/
    manifest.csv
    images/
      part1_questionnaire_003_page-1.png
      part1_questionnaire_003_page-2.png
      ...
"""
import csv
import json
import re
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
SPLIT_DOCS = PROJECT_ROOT / "circular_2464_extractions" / "split_documents"
OUTPUT_DIR = PROJECT_ROOT / "circular_2464_extractions" / "vision_recovery_cat1"
IMAGES_DIR = OUTPUT_DIR / "images"
MANIFEST_PATH = OUTPUT_DIR / "manifest.csv"

EXCLUDE = {
    "part10_questionnaire_015",  # Addie Easton Payne — patched
    "part10_affidavit_004",      # likely Hannah Hardin signature page
}

TYPE_TO_SUBDIR = {
    "affidavit": "affidavits",
    "questionnaire": "questionnaires",
    "agency_narrative": "agency_narratives",
    "Form 5-105 Application for Patent in Fee": "questionnaires",
}


def derive_subdir_from_filename(filename):
    """Get the split_documents subdir from the filename."""
    if "_affidavit_" in filename:
        return "affidavits"
    if "_questionnaire_" in filename:
        return "questionnaires"
    if "_agency_narrative_" in filename:
        return "agency_narratives"
    if "_ledger_" in filename:
        return "ledgers"
    return None


def find_cat1_records():
    """Walk extractions/sonnet/ and find records where Name and Allotment are both 'not stated'."""
    records = []
    for path in sorted(EXTRACTIONS.glob("*.json")):
        try:
            with open(path) as f:
                d = json.load(f)
        except json.JSONDecodeError:
            continue
        e = d.get("extraction", {})
        if isinstance(e, list):
            continue  # skip list-shaped (we handled bundles separately)
        if not isinstance(e, dict):
            continue

        name = (e.get("Name") or "").strip().lower()
        allot = (e.get("Allotment number") or "").strip().lower()

        if name in ("not stated", "") and allot in ("not stated", ""):
            stem = path.stem
            if stem in EXCLUDE:
                continue
            records.append({
                "record_id": stem,
                "filename": path.name,
                "po_address": e.get("Post Office Address", ""),
                "doc_type": e.get("Document type", ""),
            })
    return records


def get_pdf_count_pages(pdf_path):
    """Return number of pages in a PDF using pdfinfo."""
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None


def render_pages(pdf_path, output_prefix, dpi=200):
    """Render PDF pages to PNG using pdftoppm. Returns list of generated files."""
    cmd = [
        "pdftoppm",
        "-r", str(dpi),
        str(pdf_path),
        str(output_prefix),
        "-png",
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    # pdftoppm names files like prefix-1.png, prefix-2.png, etc.
    parent = output_prefix.parent
    stem = output_prefix.name
    return sorted(parent.glob(f"{stem}-*.png"))


def main():
    print(f"Output directory: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    records = find_cat1_records()
    print(f"CAT_1 records found (excluding {len(EXCLUDE)}): {len(records)}")
    print()

    manifest_rows = []
    n_pdfs_found = 0
    n_pdfs_missing = 0
    n_pages_rendered = 0

    for rec in records:
        stem = rec["record_id"]
        subdir = derive_subdir_from_filename(stem + ".json")
        if not subdir:
            print(f"  SKIP {stem}: cannot derive document type subdir")
            n_pdfs_missing += 1
            continue

        pdf_path = SPLIT_DOCS / subdir / f"{stem}.pdf"
        if not pdf_path.exists():
            print(f"  PDF NOT FOUND: {pdf_path}")
            n_pdfs_missing += 1
            continue

        n_pdfs_found += 1
        n_pages = get_pdf_count_pages(pdf_path)

        # Render pages
        output_prefix = IMAGES_DIR / stem
        try:
            pngs = render_pages(pdf_path, output_prefix)
        except subprocess.CalledProcessError as e:
            print(f"  RENDER FAILED {stem}: {e}")
            continue

        for png_path in pngs:
            # Extract page number from filename: prefix-N.png
            m = re.match(rf"{re.escape(stem)}-(\d+)\.png$", png_path.name)
            if not m:
                continue
            page_num = int(m.group(1))
            n_pages_rendered += 1
            manifest_rows.append({
                "record_id": stem,
                "page": str(page_num),
                "image_path": f"images/{png_path.name}",
                "known_allotment": "",  # CAT_1 has neither name nor allotment known
                "agency_hint": rec["po_address"] or rec["doc_type"] or "",
            })

        print(f"  OK   {stem}: {len(pngs)} pages rendered")

    # Write manifest
    with open(MANIFEST_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "record_id", "page", "image_path",
            "known_allotment", "agency_hint",
        ])
        w.writeheader()
        for row in manifest_rows:
            w.writerow(row)

    print()
    print("=" * 70)
    print("CAT_1 batch preparation complete")
    print("=" * 70)
    print(f"PDFs found:           {n_pdfs_found}")
    print(f"PDFs missing:         {n_pdfs_missing}")
    print(f"Pages rendered:       {n_pages_rendered}")
    print(f"Manifest rows:        {len(manifest_rows)}")
    print()
    print(f"Output directory:     {OUTPUT_DIR}")
    print(f"Manifest:             {MANIFEST_PATH}")
    print(f"Images:               {IMAGES_DIR}")
    print()
    print("Next steps:")
    print("1. Upload to HPC:")
    print(f"   scp -r {OUTPUT_DIR} \\")
    print(f"       cwm6w@login.hpc.virginia.edu:/project/LawData/kimi-extraction/code/circular_2464_extractions/")
    print()
    print("2. Submit slurm job (from HPC):")
    print("   sbatch --export=ALL,\\")
    print("       INPUT_DIR=/project/LawData/kimi-extraction/code/circular_2464_extractions/vision_recovery_cat1,\\")
    print("       OUT_DIR=/project/LawData/kimi-extraction/outputs/vision_recovery_cat1 \\")
    print("       /project/LawData/kimi-extraction/hpc/run_qwen_vl_recovery.slurm")
    print()
    print("3. Pull results back (from laptop):")
    print("   rsync -avz \\")
    print('       "cwm6w@login.hpc.virginia.edu:'"'"'/project/LawData/kimi-extraction/outputs/vision_recovery_cat1/'"'"'" \\')
    print(f"       \"{OUTPUT_DIR}/qwen_outputs/\"")


if __name__ == "__main__":
    main()
