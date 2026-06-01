#!/usr/bin/env python3
"""
Split 6 multi-allottee bundle records using Sonnet vision extractions.

Pattern: each bundle PDF contains two distinct allottees. The original
Sonnet text extraction collapsed them into one list-shaped record. We
split each into _NNNa.json (allottee 1) and _NNNb.json (allottee 2),
populating each with content from the Sonnet vision extraction
(validation_samples/<bundle>_vision/vision_merged.json).

Bundles processed (all confirmed as genuine 2-allottee bundles via
user source-page review on 2026-05-03):
  1. part1_agency_narrative_003 — Benjamin Decory (8) + David B. Whiting (9)
  2. part12_questionnaire_005 — Warren Real Rider (226) + Jesse Peters (728)
  3. part2_agency_narrative_034 — Harry Moran (812) + Narcisse Moran (813)
  4. part3_agency_narrative_007 — Luther Arcoran (1196) + Frank Arcoran (1197)
  5. part7_agency_narrative_005 — William Grant (2181) + Peter Bordeaux (2266)
  6. part7_agency_narrative_025 — John DuBray (Boyd) (2338) + Lucy DuBray (Sturdevant) (2341)

NOTE: William Grant's allotment shows as 2181 in vision extraction but
2101 was previously cited. The vision number (2181) is preferred since
Sonnet vision rendered the actual handwriting; 2101 may have been a
text-extraction artifact. Worth source-page verification.

Each new record:
  - extraction.Name = allottee's name
  - extraction.Allotment number = their allotment
  - extraction.Tribe/Reservation = inferred from part context
  - extraction.NOTES = full content from vision extraction
  - pre_split_sonnet_extraction = archive of original text-only extraction
  - recovery_notes entry with split_origin pointing to source PDF + sibling
"""
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
SPLIT_DOCS = PROJECT_ROOT / "circular_2464_extractions" / "split_documents"

# For each bundle, define the two allottees with their content from vision
BUNDLES = [
    {
        "bundle_filename": "part1_agency_narrative_003.json",
        "source_pdf": "agency_narratives/part1_agency_narrative_003.pdf",
        "vision_dir": "validation_samples/part1_an003_vision",
        "tribe": "Rosebud Sioux",
        "po_address": "Rosebud, South Dakota",
        "doc_type": "agency_narrative",
        "allottees": [
            {
                "suffix": "a",
                "name": "Benjamin Decory",
                "allotment": "8",
                "patent_date": "1920-03-12",
                "patent_number": "739603",
                "mechanism": "administrative",
                "buyer": "W. H. Whitcher",
                "sale_price": "$3400.00",
                "page_in_bundle": 1,
                "additional_notes": (
                    "Sold land to W. H. Whitcher for $3,400. Patent issued "
                    "March 12, 1920."
                ),
            },
            {
                "suffix": "b",
                "name": "David B. Whiting",
                "allotment": "9",
                "patent_date": "1917-12-29",
                "patent_number": "612742",
                "mechanism": "administrative",
                "buyer": "William J. Whitcher",
                "sale_price": "$10,000.00",
                "page_in_bundle": 2,
                "additional_notes": (
                    "Sold land to William J. Whitcher for $10,000. Patent "
                    "issued December 29, 1917. Buyer surname matches "
                    "Decory's buyer; Whitcher family appears as recurring "
                    "purchaser of adjacent allotments."
                ),
            },
        ],
    },
    {
        "bundle_filename": "part12_questionnaire_005.json",
        "source_pdf": "questionnaires/part12_questionnaire_005.pdf",
        "vision_dir": "validation_samples/part12_questionnaire_005_vision",
        "tribe": "Pawnee",
        "po_address": "Pawnee Agency, Oklahoma",
        "doc_type": "questionnaire",
        "allottees": [
            {
                "suffix": "a",
                "name": "Warren Real Rider",
                "allotment": "226",
                "patent_date": "1917-11-13",
                "patent_number": "(unknown — not captured in vision extraction)",
                "mechanism": "administrative",
                "buyer": "C. E. Vandervoort",
                "sale_price": "$2000",
                "page_in_bundle": 1,
                "additional_notes": (
                    "Pawnee Nation member. Sold land to C. E. Vandervoort "
                    "for $2,000. Patent received at Pawnee Agency Office "
                    "1917-1918."
                ),
            },
            {
                "suffix": "b",
                "name": "Jesse Peters (Peter George)",
                "allotment": "728",
                "patent_date": "1917-12-24",
                "patent_number": "(unknown — not captured in vision extraction)",
                "mechanism": "administrative",
                "buyer": "(unknown buyer; mortgagee R. C. Spinning, mortgage $1700)",
                "sale_price": "$2000",
                "page_in_bundle": 2,
                "additional_notes": (
                    "Pawnee Nation member, also known as Peter George/Georges. "
                    "Land subject to a $1,700 mortgage held by R. C. Spinning. "
                    "Sale price $2,000. Patent received at Pawnee Agency "
                    "Office 1917-1918."
                ),
            },
        ],
    },
    {
        "bundle_filename": "part2_agency_narrative_034.json",
        "source_pdf": "agency_narratives/part2_agency_narrative_034.pdf",
        "vision_dir": "validation_samples/part2_agency_narrative_034_vision",
        "tribe": "Rosebud Sioux",
        "po_address": "Rosebud, South Dakota",
        "doc_type": "agency_narrative",
        "allottees": [
            {
                "suffix": "a",
                "name": "Harry Moran",
                "allotment": "812",
                "patent_date": "1920-03-12",
                "patent_number": "739641",
                "mechanism": "administrative",
                "buyer": "Thomas R. Reynolds",
                "sale_price": "$1.00 and other valuable consideration",
                "page_in_bundle": 1,
                "additional_notes": (
                    "Land: southwest quarter of section 24, township 43, "
                    "range 27. Sold to Thomas R. Reynolds for nominal "
                    "consideration ($1 and other). Patent issued same day "
                    "as sibling allotment 813 (Narcisse Moran), suggesting "
                    "coordinated processing."
                ),
            },
            {
                "suffix": "b",
                "name": "Narcisse Moran",
                "allotment": "813",
                "patent_date": "1920-03-12",
                "patent_number": "739643",
                "mechanism": "administrative",
                "buyer": "Ed Haisch",
                "sale_price": "$1.00 and other valuable consideration",
                "page_in_bundle": 2,
                "additional_notes": (
                    "Land: northwest quarter of section 24, township 43, "
                    "range 27 (adjacent to Harry Moran's allotment 812). "
                    "Sold to Ed Haisch for nominal consideration. Patent "
                    "issued same day as sibling allotment 812. Likely "
                    "family relationship between Harry and Narcisse Moran "
                    "given adjacent allotments and shared surname."
                ),
            },
        ],
    },
    {
        "bundle_filename": "part3_agency_narrative_007.json",
        "source_pdf": "agency_narratives/part3_agency_narrative_007.pdf",
        "vision_dir": "validation_samples/part3_agency_narrative_007_vision",
        "tribe": "Rosebud Sioux",
        "po_address": "Rosebud, South Dakota",
        "doc_type": "agency_narrative",
        "allottees": [
            {
                "suffix": "a",
                "name": "Luther Arcoran",
                "allotment": "1196",
                "patent_date": "1920-03-12",
                "patent_number": "739691",
                "mechanism": "administrative",
                "buyer": "Edward L. McHenry",
                "sale_price": "$12,000",
                "page_in_bundle": 1,
                "additional_notes": (
                    "Land conveyed to Edward L. McHenry for $12,000 — same "
                    "buyer named in part 4 records (McHenry as recurring "
                    "Rosebud allotment purchaser). Tripp County sheriff "
                    "levied on this allotment. Note: this record duplicates "
                    "content also captured at part4_agency_narrative_008 "
                    "(also Luther Arcoran 1196). Cross-reference both "
                    "records for full case detail."
                ),
            },
            {
                "suffix": "b",
                "name": "Frank Arcoran",
                "allotment": "1197",
                "patent_date": "1920-03-12",
                "patent_number": "739690",
                "mechanism": "administrative",
                "buyer": "William Lynass",
                "sale_price": "$9,000",
                "page_in_bundle": 2,
                "additional_notes": (
                    "Died June 19, 1920 (shortly after patent issuance "
                    "March 12, 1920). Sold to William Lynass for $9,000. "
                    "Note: this record duplicates content also captured at "
                    "part4_agency_narrative_009 (also Frank Arcoran 1197) "
                    "and part4_questionnaire_006 (where Josephine Arcoran "
                    "as mother gave testimony for the deceased). Cross-"
                    "reference all three records for full case detail."
                ),
            },
        ],
    },
    {
        "bundle_filename": "part7_agency_narrative_005.json",
        "source_pdf": "agency_narratives/part7_agency_narrative_005.pdf",
        "vision_dir": "validation_samples/part7_agency_narrative_005_vision",
        "tribe": "Rosebud Sioux",
        "po_address": "Rosebud, South Dakota",
        "doc_type": "agency_narrative",
        "allottees": [
            {
                "suffix": "a",
                "name": "William Grant",
                "allotment": "2181",
                "patent_date": "1920-03-12",
                "patent_number": "739610",
                "mechanism": "administrative",
                "buyer": "K. L. Smith",
                "sale_price": "$1.00 and other valuable consideration",
                "page_in_bundle": 1,
                "additional_notes": (
                    "Note: previous text extraction had allotment '2101' "
                    "but Sonnet vision shows '2181'. Vision number is "
                    "preferred since it rendered the actual handwriting; "
                    "worth source-page verification. Sold to K. L. Smith "
                    "for nominal consideration."
                ),
            },
            {
                "suffix": "b",
                "name": "Peter Bordeaux",
                "allotment": "2266",
                "patent_date": "1920-03-12",
                "patent_number": "739598",
                "mechanism": "administrative",
                "buyer": "W. H. Tackett",
                "sale_price": "$2000.00",
                "page_in_bundle": 2,
                "additional_notes": (
                    "Sold to W. H. Tackett for $2,000. Patent issued same "
                    "day as sibling allotment 2181 (William Grant)."
                ),
            },
        ],
    },
    {
        "bundle_filename": "part7_agency_narrative_025.json",
        "source_pdf": "agency_narratives/part7_agency_narrative_025.pdf",
        "vision_dir": "validation_samples/part7_agency_narrative_025_vision",
        "tribe": "Rosebud Sioux",
        "po_address": "Rosebud, South Dakota",
        "doc_type": "agency_narrative",
        "allottees": [
            {
                "suffix": "a",
                "name": "John DuBray (Boyd)",
                "allotment": "2338",
                "patent_date": "1917-12-21",
                "patent_number": "612453",
                "mechanism": "administrative",
                "buyer": "Charles Burtz",
                "sale_price": "$2000",
                "page_in_bundle": 1,
                "additional_notes": (
                    "Land: Section 6, Township 102, north of Range 77. "
                    "Also known as John Boyd. Sold to Charles Burtz for "
                    "$2,000. Likely sibling relationship with Lucy DuBray "
                    "Sturdevant (allotment 2341, adjacent processing)."
                ),
            },
            {
                "suffix": "b",
                "name": "Lucy DuBray (Sturdevant)",
                "allotment": "2341",
                "patent_date": "1917-12-29",
                "patent_number": "512761",
                "mechanism": "administrative",
                "buyer": "Charles W. Marley",
                "sale_price": "$1.00 and other valuable consideration",
                "page_in_bundle": 2,
                "additional_notes": (
                    "Land: Section 30, Township 100, north of Range 76. "
                    "Also known as Lucy Sturdevant (married name). Sold to "
                    "Charles W. Marley for nominal consideration. Likely "
                    "sibling relationship with John DuBray (Boyd), "
                    "allotment 2338."
                ),
            },
        ],
    },
]


def build_record(bundle, allottee, sibling_filename, original_extraction_archive):
    """Build a full split record for one allottee."""
    notes_content = (
        f"Source: split from multi-allottee bundle "
        f"({bundle['bundle_filename']}) on 2026-05-03 using Sonnet vision "
        f"extraction. "
        f"Allotment {allottee['allotment']}. "
        f"Patent date: {allottee['patent_date']}. "
        f"Patent number: {allottee['patent_number']}. "
        f"Mechanism: {allottee['mechanism']}. "
        f"Buyer: {allottee['buyer']}. "
        f"Sale price: {allottee['sale_price']}. "
        f"{allottee['additional_notes']} "
        f"Sibling record (other allottee in original bundle): {sibling_filename}. "
        f"Vision extraction archived at: {bundle['vision_dir']}/vision_merged.json."
    )

    return {
        "extraction": {
            "Name": allottee["name"],
            "Allotment number": allottee["allotment"],
            "Tribe/Reservation": bundle["tribe"],
            "Post Office Address": bundle["po_address"],
            "Date": allottee["patent_date"],
            "Document type": bundle["doc_type"],
            "NOTES": notes_content,
        },
        "pre_split_sonnet_extraction": original_extraction_archive,
        "recovery_notes": [
            {
                "date": "2026-05-03",
                "type": "task5_record_split_from_multi_allottee_bundle",
                "method": "sonnet_vision_extraction_with_user_source_page_confirmation",
                "fields_corrected": [
                    "Name", "Allotment number", "Tribe/Reservation",
                    "Post Office Address", "Date", "Document type",
                    "NOTES", "(record creation)",
                ],
                "previous_state": (
                    f"Original {bundle['bundle_filename']} had list-shaped "
                    f"extraction collapsing two distinct allottees on "
                    f"sequential pages into a single record."
                ),
                "split_origin": {
                    "source_pdf": bundle["source_pdf"],
                    "page_number": allottee["page_in_bundle"],
                    "sibling_record": sibling_filename,
                    "vision_extraction_path": (
                        f"{bundle['vision_dir']}/vision_merged.json"
                    ),
                },
                "user_confirmed": True,
                "rationale": (
                    "User source-page review confirmed two distinct "
                    "allottees on sequential pages. Vision extraction "
                    "captured per-allottee fee patent details (name, "
                    "allotment, patent date, patent number, buyer, sale "
                    "price). Split into two records preserving all "
                    "captured content."
                ),
            }
        ],
    }


def split_one_bundle(bundle):
    bundle_path = EXTRACTIONS / bundle["bundle_filename"]
    if not bundle_path.exists():
        return False, f"NOT FOUND: {bundle_path}"

    # Read and archive original
    with open(bundle_path) as f:
        original = json.load(f)

    base_stem = bundle_path.stem  # e.g., 'part1_agency_narrative_003'
    new_paths = []

    # Refuse to overwrite existing _NNNa or _NNNb
    for allottee in bundle["allottees"]:
        target = EXTRACTIONS / f"{base_stem}{allottee['suffix']}.json"
        if target.exists():
            return False, f"refusing to overwrite existing: {target.name}"
        new_paths.append((target, allottee))

    # Build records
    siblings = {
        "a": f"{base_stem}b.json",
        "b": f"{base_stem}a.json",
    }

    for i, (target, allottee) in enumerate(new_paths):
        if i == 0:
            # First sibling archives the original full extraction
            archive = original.get("extraction")
        else:
            # Second sibling references the first
            archive = (
                f"See {base_stem}a.json field 'pre_split_sonnet_extraction' "
                f"for archived original"
            )

        record = build_record(
            bundle=bundle,
            allottee=allottee,
            sibling_filename=siblings[allottee["suffix"]],
            original_extraction_archive=archive,
        )

        with open(target, "w") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

    # Remove original
    bundle_path.unlink()

    return True, f"Split into {base_stem}a.json + {base_stem}b.json (original removed)"


def main():
    print("=" * 70)
    print(f"Multi-allottee bundle split: {len(BUNDLES)} bundles")
    print("=" * 70)
    print()

    ok = 0
    for bundle in BUNDLES:
        print(f"Processing: {bundle['bundle_filename']}")
        success, msg = split_one_bundle(bundle)
        marker = "  " if success else "  ! "
        print(f"{marker}{msg}")
        for allottee in bundle["allottees"]:
            print(
                f"    {allottee['suffix']}: {allottee['name']:35s}  "
                f"allot={allottee['allotment']}"
            )
        print()
        if success:
            ok += 1

    print("=" * 70)
    print(f"Bundles split: {ok}/{len(BUNDLES)}")
    print(f"New records created: {ok * 2} (one pair per bundle)")
    print("=" * 70)


if __name__ == "__main__":
    main()
