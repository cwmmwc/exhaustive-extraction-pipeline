#!/usr/bin/env python3
"""
Add part 4 to split_corpus.py's hardcoded label dicts.

Inserts the part 4 entry after the part 3 entry in both LABEL_TO_PDF and
LABEL_SHORT. Uses the local copy of the part 4 PDF (not OneDrive) since it
hasn't been moved into the OneDrive Circular 2464 folder.
"""
import re
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
SPLIT_CORPUS = PROJECT_ROOT / "split_corpus.py"

NEW_LABEL_TO_PDF_LINE = (
    '    "RG_75_1929_circular_2464_part_4": '
    '"/Users/cwm6W/projects/exhaustive-extraction-pipeline/RG 75 1929 circular 2464 part 4.pdf",'
)

NEW_LABEL_SHORT_LINE = (
    '    "RG_75_1929_circular_2464_part_4": "part4",'
)


def main():
    with open(SPLIT_CORPUS) as f:
        text = f.read()

    if "RG_75_1929_circular_2464_part_4" in text:
        print("part 4 entries already present — refusing to add duplicates")
        return

    # Insert NEW_LABEL_TO_PDF_LINE after the part_3 entry in LABEL_TO_PDF
    pattern_3_in_pdf = (
        '    "RG_75_1929_circular_2464_part_3": '
        'f"{PDF_BASE}/Replies to Circular 2464/RG 75 1929 circular 2464 part 3.pdf",'
    )
    if pattern_3_in_pdf not in text:
        print(f"ERROR: could not find part 3 line in LABEL_TO_PDF dict.")
        print(f"Looked for: {pattern_3_in_pdf}")
        return
    text = text.replace(
        pattern_3_in_pdf,
        pattern_3_in_pdf + "\n" + NEW_LABEL_TO_PDF_LINE,
    )

    # Insert NEW_LABEL_SHORT_LINE after the part_3 entry in LABEL_SHORT
    pattern_3_in_short = '    "RG_75_1929_circular_2464_part_3": "part3",'
    if pattern_3_in_short not in text:
        print(f"ERROR: could not find part 3 line in LABEL_SHORT dict.")
        return
    text = text.replace(
        pattern_3_in_short,
        pattern_3_in_short + "\n" + NEW_LABEL_SHORT_LINE,
    )

    # Backup and write
    backup = SPLIT_CORPUS.with_suffix(".py.bak")
    with open(backup, "w") as f:
        with open(SPLIT_CORPUS) as src:
            f.write(src.read())
    print(f"Backup saved: {backup}")

    with open(SPLIT_CORPUS, "w") as f:
        f.write(text)
    print(f"Updated: {SPLIT_CORPUS}")
    print()
    print("Added entries:")
    print(f"  LABEL_TO_PDF: {NEW_LABEL_TO_PDF_LINE.strip()}")
    print(f"  LABEL_SHORT:  {NEW_LABEL_SHORT_LINE.strip()}")


if __name__ == "__main__":
    main()
