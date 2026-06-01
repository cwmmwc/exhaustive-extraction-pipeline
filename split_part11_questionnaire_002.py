#!/usr/bin/env python3
"""
Split part11_questionnaire_002 into two separate records.

Background: This record's source PDF contains two distinct allottees on
sequential pages, but Sonnet's text-extraction failed completely (NOTES
described it as 'Document is largely illegible due to poor scan quality
and handwritten text that cannot be reliably transcribed. Two overlapping
questionnaire pages (Circular No. 2464 and Circular No. 3464) are
present.'). Kimi v3/v4/v5 also extracted nothing useful for these two
allottees from this PDF.

User source-page review on 2026-04-29 identified both allottees on the
rendered PNGs:

  Page 1 — Rosa Vanderbloom (page 1):
    - Q1: 'Number of allotment and date of fee patent' answered with
      '313  10/30/1919' in handwritten ink
    - Q2: Patent delivered March 1920 by rural delivery
    - Q10: 41 years old, in good health
    - Q12: Aged mother dependent
    - Description (top of form): SE/2 SW/4 - 2-8-1
    - Also row 34 on Shawnee master list (part10_page_036):
      'Rosa Vanderbloom — ditto' (Report in detail attached)

  Page 2 — Viola Wallace:
    - Patent No. 715,737 issued Oct. 30, 1919
    - Allotment 15609 (per her own testimony: 'I fail to find an
      allotment No., but on the back is (allot 15609) written by someone
      with pen & ink')
    - Received patent by mail May 1925 from A. W. Leech of Shawnee, Okla
    - Patent accepted under protest; recorded June 5, 1926
    - Pottawatomie County treasurer sold land before patent received;
      taxes demanded again with high interest
    - 48 years old, bronchial asthma trouble
    - Description: SW NW & NW NW - 12-8-5
    - Also row 35 on Shawnee master list: 'Viola Wallace — ditto'

User BLM search confirmed both are Citizen Potawatomie tribe.

This patch:
  1. Replaces part11_questionnaire_002.json with the original Sonnet
     extraction PRESERVED in a new field 'pre_split_extraction' for
     audit purposes, and a new flat dict for Rosa Vanderbloom (filename
     becomes _002a)
  2. Creates new file part11_questionnaire_002b.json for Viola Wallace
  3. Adds full audit trail to both records explaining the split

NOTE: This patch creates a record with Allotment 15609 — that's a 5-digit
number which is unusual for the Pine Ridge typewritten affidavits we've
been working with (most are 4-digit). For Citizen Potawatomie allotments
the numbering scheme appears to differ — Sam Charbonneau (part1_q_006)
has allotment 22171 and Lizzie Colomb (part7_q_011) has 22991, both
plausibly in the same series.
"""
import json
from pathlib import Path
import shutil

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

ORIGINAL_PATH = EXTRACTIONS / "part11_questionnaire_002.json"
VANDERBLOOM_PATH = EXTRACTIONS / "part11_questionnaire_002a.json"
WALLACE_PATH = EXTRACTIONS / "part11_questionnaire_002b.json"

# Vanderbloom record (page 1)
VANDERBLOOM_DATA = {
    "Name": "Rosa Vanderbloom",
    "Allotment number": "313",
    "Tribe/Reservation": "Citizen Potawatomie",
    "Post Office Address": "not stated",
    "Document type": "questionnaire",
    "Date": "not stated",
    "NOTES": (
        "Circular 2464 questionnaire response, page 1 of bundled source PDF "
        "part11_questionnaire_002.pdf (page 2 contains a separate allottee, "
        "Viola Wallace, now in part11_questionnaire_002b.json). "
        "Q1 (allotment and patent date): handwritten '313  10/30/1919'. "
        "Q2 (patent delivery): March 1920 by rural delivery. "
        "Q10 (age, condition): 41 years old, in good health. "
        "Q12 (dependents): aged mother. "
        "Description (top of form): SE/2 SW/4 - 2-8-1. "
        "Cross-reference: Rosa Vanderbloom is also row 34 on the Shawnee "
        "Indian Agency master list (part10_page_036.pdf, transmitted by "
        "Supt. A. W. Leech, March 20, 1929) where her status is "
        "'Report in detail attached' — this record IS her detail report. "
        "RECORD ORIGIN 2026-04-30: Created via split of original "
        "part11_questionnaire_002.json which Sonnet text-extracted as "
        "'largely illegible' with 'two overlapping questionnaire pages' "
        "and Kimi v3/v4/v5 also failed on. Allotment number captured by "
        "user source-page review on 2026-04-29; tribe confirmed via user "
        "BLM search."
    ),
}

# Wallace record (page 2)
WALLACE_DATA = {
    "Name": "Viola Wallace",
    "Allotment number": "15609",
    "Tribe/Reservation": "Citizen Potawatomie",
    "Post Office Address": "not stated",
    "Document type": "questionnaire",
    "Date": "not stated",
    "NOTES": (
        "Circular 2464 questionnaire response, page 2 of bundled source PDF "
        "part11_questionnaire_002.pdf (page 1 contains a separate allottee, "
        "Rosa Vanderbloom, now in part11_questionnaire_002a.json). "
        "Q1 (allotment and patent date): per her testimony, 'I fail to find "
        "an allotment No., but on the back is (allot 15609) written by "
        "someone with pen & ink. My Patent No. is 715,737 was issued "
        "Oct. 30, 1919.' "
        "Q2 (patent delivery): received by mail in May 1925 from "
        "Mr. A. W. Leech of Shawnee, Okla. "
        "Q3: patent accepted under protest; Roy Z. Youngblood, an abstractor "
        "of Tecumseh, Okla., took it to record and kept it for several "
        "months against her demands; later F. A. Johnson of Tulsa, Okla. "
        "took it to have recorded; finally recorded June 5, 1926. "
        "Q4-5: land never mortgaged. "
        "Q6: land never sold. "
        "Q7: Yes — Pottawatomie County treasurer sold for back taxes "
        "before she received her patent. She paid those taxes and the "
        "county treasurer returned the check and cancelled all back "
        "taxes. Now demands these taxes again with high interest. "
        "Q10: 48 years of age; physical condition is poorly, having "
        "bronchial asthma trouble; financial condition depends solely on "
        "this 80 acres of land. "
        "Q11: has worked in stores and offices; has received no "
        "contributions of any kind. "
        "Description: SW NW & NW NW - 12-8-5. "
        "Cross-reference: Viola Wallace is also row 35 on the Shawnee "
        "Indian Agency master list (part10_page_036.pdf, transmitted by "
        "Supt. A. W. Leech, March 20, 1929) where her status is "
        "'Report in detail attached' — this record IS her detail report. "
        "RECORD ORIGIN 2026-04-30: Created via split of original "
        "part11_questionnaire_002.json which Sonnet text-extracted as "
        "'largely illegible' with 'two overlapping questionnaire pages' "
        "and Kimi v3/v4/v5 also failed on. All content from user source-"
        "page review on 2026-04-29; tribe confirmed via user BLM search."
    ),
}


def make_record(extraction_data, source_filename, page_number, sibling_filename):
    """Build a full record (with extraction + recovery_notes)."""
    return {
        "extraction": extraction_data,
        "recovery_notes": [
            {
                "date": "2026-04-30",
                "type": "task5_record_split_from_multi_allottee_bundle",
                "method": "user_source_page_review_with_blm_tribe_confirmation",
                "fields_corrected": [
                    "Name", "Allotment number", "Tribe/Reservation",
                    "NOTES", "Document type", "(record creation)",
                ],
                "previous_state": (
                    "Original part11_questionnaire_002.json had Name='not stated' "
                    "and Allotment='not stated' because Sonnet text-extraction "
                    "failed on the bundled multi-allottee PDF (NOTES described "
                    "it as 'largely illegible' with 'two overlapping questionnaire "
                    "pages'). Kimi v3/v4/v5 also failed to extract these allottees "
                    "from this source."
                ),
                "split_origin": {
                    "source_pdf": source_filename,
                    "page_number": page_number,
                    "sibling_record": sibling_filename,
                },
                "user_confirmed": True,
                "rationale": (
                    "Source PDF contains two distinct allottees (Rosa Vanderbloom "
                    "on page 1, Viola Wallace on page 2). Both have detail records "
                    "on these pages corresponding to their 'Report in detail "
                    "attached' notations on the Shawnee Indian Agency master list "
                    "(rows 34 and 35 respectively). Each allottee's detail report "
                    "is the rich source of information about her case; preserving "
                    "them as a single bundled record loses individual identity "
                    "resolution. Split into two separate records, one per "
                    "allottee, matching the rest of the corpus's one-record-"
                    "per-allottee convention."
                ),
                "extraction_failure_modes": [
                    "Sonnet hallucinated 'Circular No. 3464' alongside the real "
                    "Circular No. 2464 (only 2464 actually appears on source pages)",
                    "Sonnet did not separate the two allottees on the bundled pages",
                    "Sonnet extracted no Name, no Allotment, no substantive "
                    "content — claimed 'most answers indecipherable'",
                    "Kimi v3/v4/v5 extractions of part 11 captured no entries for "
                    "Vanderbloom or Wallace despite capturing other part 11 content",
                ],
            }
        ],
    }


def main():
    if not ORIGINAL_PATH.exists():
        print(f"ERROR: original file not found: {ORIGINAL_PATH}")
        return

    # Read original for archival
    with open(ORIGINAL_PATH) as f:
        original = json.load(f)

    print("Splitting part11_questionnaire_002 into two records:")
    print()

    # Check for safety: refuse if either target already exists
    for target in (VANDERBLOOM_PATH, WALLACE_PATH):
        if target.exists():
            print(f"ERROR: target already exists, refusing to overwrite: {target.name}")
            return

    # Create Vanderbloom record (002a)
    vanderbloom = make_record(
        VANDERBLOOM_DATA,
        source_filename="part11_questionnaire_002.pdf",
        page_number=1,
        sibling_filename="part11_questionnaire_002b.json",
    )
    # Preserve original Sonnet extraction for audit
    vanderbloom["pre_split_sonnet_extraction"] = original.get("extraction")

    with open(VANDERBLOOM_PATH, "w") as f:
        json.dump(vanderbloom, f, indent=2, ensure_ascii=False)
    print(f"  Created: {VANDERBLOOM_PATH.name}")
    print(f"    Name: Rosa Vanderbloom")
    print(f"    Allotment: 313")
    print(f"    Tribe: Citizen Potawatomie")
    print()

    # Create Wallace record (002b)
    wallace = make_record(
        WALLACE_DATA,
        source_filename="part11_questionnaire_002.pdf",
        page_number=2,
        sibling_filename="part11_questionnaire_002a.json",
    )
    # No need to duplicate original Sonnet extraction in both files; pointer is enough
    wallace["pre_split_sonnet_extraction"] = (
        "See part11_questionnaire_002a.json field "
        "'pre_split_sonnet_extraction' for archived original"
    )

    with open(WALLACE_PATH, "w") as f:
        json.dump(wallace, f, indent=2, ensure_ascii=False)
    print(f"  Created: {WALLACE_PATH.name}")
    print(f"    Name: Viola Wallace")
    print(f"    Allotment: 15609")
    print(f"    Tribe: Citizen Potawatomie")
    print()

    # Remove the original record (its content is preserved in 002a's audit)
    ORIGINAL_PATH.unlink()
    print(f"  Removed: part11_questionnaire_002.json (content archived in 002a)")
    print()

    print("Split complete. Both new records have full audit trails.")


if __name__ == "__main__":
    main()
