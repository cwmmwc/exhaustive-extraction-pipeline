#!/usr/bin/env python3
"""
Render part 9 pages 30-40 to locate Hazel's questionnaire.

The corpus source_pages reference for part9_questionnaire_010 (Hazel)
says pages 31-32, but rendering those showed Helena Larvie's material
instead. Larvie's own record claims page 30. There is a page-numbering
offset between the corpus source_pages field and the actual PDF.

This renders a wider window (PDF pages 30-40, 1-indexed) so the actual
Hazel questionnaire can be found by eye.
"""
import fitz
from pathlib import Path

KEY_FILES = Path("/Users/cwm6W/Desktop/KEY FILES/RG 75 1929 Circular 2464")
OUTPUT_DIR = Path(
    "/Users/cwm6W/projects/exhaustive-extraction-pipeline"
    "/validation_samples/cat3_source_review/part9_window"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PDF_NAME = "RG 75 1929 circular 2464 part 9.pdf"
PAGE_START_1IDX = 30
PAGE_END_1IDX = 40
DPI = 200  # slightly lower DPI since this is a scan-to-locate pass
ZOOM = DPI / 72.0


def main():
    pdf_path = KEY_FILES / PDF_NAME
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return

    doc = fitz.open(pdf_path)
    n_pages = len(doc)
    print(f"{PDF_NAME}: {n_pages} pages")
    print(f"Rendering pages {PAGE_START_1IDX}-{PAGE_END_1IDX} (1-indexed)")
    print()

    mat = fitz.Matrix(ZOOM, ZOOM)
    for page_1idx in range(PAGE_START_1IDX, PAGE_END_1IDX + 1):
        page_0idx = page_1idx - 1
        if page_0idx < 0 or page_0idx >= n_pages:
            print(f"  page {page_1idx}: out of range")
            continue
        page = doc[page_0idx]
        pix = page.get_pixmap(matrix=mat)
        out_path = OUTPUT_DIR / f"part9_page{page_1idx:02d}.png"
        pix.save(out_path)
        print(f"  rendered PDF page {page_1idx} -> {out_path.name}")

    doc.close()
    print()
    print(f"Open the folder and scan for Hazel's questionnaire:")
    print(f"  open '{OUTPUT_DIR}'")


if __name__ == "__main__":
    main()
