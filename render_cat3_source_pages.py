#!/usr/bin/env python3
"""
Render source pages for the 2 pending CAT_3 records that need review.

  - Hazel (part9_questionnaire_010): part 9, pages 31-32
  - Thomas Wright (part7_questionnaire_022): part 7, page 59

Source PDFs from /Users/cwm6W/Desktop/KEY FILES/RG 75 1929 Circular 2464/.
Renders at 300 DPI for legibility of handwritten names.

Note on page numbering: source_pages in the corpus records are
1-indexed (page 31 = the 31st page). PyMuPDF page indices are
0-indexed, so we subtract 1.
"""
import fitz  # PyMuPDF
from pathlib import Path

KEY_FILES = Path("/Users/cwm6W/Desktop/KEY FILES/RG 75 1929 Circular 2464")
OUTPUT_DIR = Path(
    "/Users/cwm6W/projects/exhaustive-extraction-pipeline"
    "/validation_samples/cat3_source_review"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DPI = 300
ZOOM = DPI / 72.0  # PyMuPDF default is 72 DPI

RENDER_JOBS = [
    {
        "label": "hazel",
        "pdf": "RG 75 1929 circular 2464 part 9.pdf",
        "pages_1indexed": [31, 32],
        "record": "part9_questionnaire_010",
    },
    {
        "label": "thomas_wright",
        "pdf": "RG 75 1929 circular 2464 part 7.pdf",
        "pages_1indexed": [59],
        "record": "part7_questionnaire_022",
    },
]


def main():
    mat = fitz.Matrix(ZOOM, ZOOM)

    for job in RENDER_JOBS:
        pdf_path = KEY_FILES / job["pdf"]
        if not pdf_path.exists():
            print(f"ERROR: PDF not found: {pdf_path}")
            continue

        doc = fitz.open(pdf_path)
        n_pages = len(doc)
        print(f"{job['record']} ({job['label']}): {job['pdf']} has {n_pages} pages")

        for page_1idx in job["pages_1indexed"]:
            page_0idx = page_1idx - 1
            if page_0idx < 0 or page_0idx >= n_pages:
                print(f"  WARNING: page {page_1idx} out of range (1-{n_pages})")
                continue
            page = doc[page_0idx]
            pix = page.get_pixmap(matrix=mat)
            out_path = OUTPUT_DIR / f"{job['label']}_{job['record']}_p{page_1idx}.png"
            pix.save(out_path)
            print(f"  rendered page {page_1idx} -> {out_path.name}")

        doc.close()

    print()
    print(f"PNGs written to: {OUTPUT_DIR}")
    print(f"Open them with:")
    print(f"  open '{OUTPUT_DIR}'")


if __name__ == "__main__":
    main()
