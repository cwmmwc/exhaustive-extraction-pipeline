#!/usr/bin/env python3
"""
Patch 5 records in pine_ridge_* directory where original Sonnet text-extraction
captured non-Pine-Ridge values in the Tribe/Reservation field.

Background: A corpus diagnostic on 2026-04-28 surfaced 5 records under
pine_ridge_*/extractions/ with Tribe values that didn't match the directory
implication (Crow Agency, Osage, Turtle Mountain, Beltrami County MN, Flandreau).

Source-page review and BLM cross-reference confirmed all 5 are actually Pine
Ridge allottees who were either living elsewhere when they gave testimony, or
whose affidavits were sworn off-reservation. The Tribe field captured the
RESIDENCE/SWORN-AT location rather than the allotment's tribal origin.

This is a systematic extraction-failure mode worth flagging:
    - Sonnet text-extraction conflated "where the affidavit was sworn" with
      "tribal affiliation of the allottee"
    - A larger-scale audit could surface more such records by checking whether
      Tribe field matches geographic implication of directory

Two records also have NAME corrections:
    - vol1_questionnaire_001: original "Greyearth, Mrs. Isaac" was the
      interpreter's name (Mr. Isaac Greyearth, Interpreter). Actual allottee
      is Millie Richards (signed at bottom of source page).
    - vol1_affidavit_057: original "Nora Parkhurst" is correct as her current/
      married name, but BLM patent record (accession 709441) has her as
      "Nora Martinez" (likely her name at time of allotment).

Sources confirmed via user source-page review and BLM cross-references:
    - Frank Carlow (allot 1071): BLM accession 625232, Pine Ridge
    - Cecilia Armstrong Ross (allot 2107): BLM confirms Pine Ridge
    - Clara Peck (allot 2256): BLM confirms Pine Ridge
    - Millie Richards (allot 694): BLM accession 0643-139 (class MV), Pine Ridge
    - Nora Martinez/Parkhurst (allot 834): BLM accession 709441, Pine Ridge

Note: BLM URLs (glorecords.blm.gov) cannot be programmatically fetched because
the site disallows it via robots.txt. Confirmation is via user source review
and external lookup; URLs preserved in audit trail for human follow-up.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {
        "filename": "pine_ridge_vol1_affidavit_077.json",
        "expected_current_name": "Frank Carlow",
        "expected_current_tribe": "Crow Agency",
        "new_name": "Frank Carlow",  # unchanged
        "new_tribe": "Pine Ridge (Oglala Sioux)",
        "residence_at_swearing": "Crow Agency, Montana",
        "blm_accession": "625232",
        "blm_class": "SER",
        "blm_url": "https://glorecords.blm.gov/details/patent/default.aspx?accession=625232&docClass=SER",
        "source_page_evidence": (
            "Affidavit sworn at Crow Agency, Montana, 3 Jan 1929. "
            "Document received at Pine Ridge Agency Jan 7, 1929 (stamp visible). "
            "Patent recorded by Superintendent at Martin, S. Dak. (Pine Ridge area). "
            "Land sold to Mr. Schulz of Martin, S. Dak. "
            "Allottee was at Camp Kearney, California in 1918 (likely WWI service)."
        ),
    },
    {
        "filename": "pine_ridge_vol2_affidavit_128.json",
        "expected_current_name": "Cecilia Armstrong Ross",
        "expected_current_tribe": "Turtle Mountain Indian Reservation",
        "new_name": "Cecilia Armstrong Ross",
        "new_tribe": "Pine Ridge (Oglala Sioux)",
        "residence_at_swearing": "Belcourt, Rolette County, North Dakota (Turtle Mountain)",
        "blm_accession": "(confirmed via user BLM lookup; accession not captured)",
        "blm_class": "SER",
        "blm_url": None,
        "source_page_evidence": (
            "User confirmed Pine Ridge via BLM patent search. Allottee residing "
            "at Belcourt (Turtle Mountain) when affidavit given."
        ),
    },
    {
        "filename": "pine_ridge_vol2_affidavit_022.json",
        "expected_current_name": "Clara Peck",
        "expected_current_tribe": "Osage",
        "new_name": "Clara Peck",
        "new_tribe": "Pine Ridge (Oglala Sioux)",
        "residence_at_swearing": "Wynona, Oklahoma (Osage country)",
        "blm_accession": "(confirmed via user BLM lookup; accession not captured)",
        "blm_class": "SER",
        "blm_url": None,
        "source_page_evidence": (
            "User confirmed Pine Ridge via BLM patent search. Allottee residing "
            "at Wynona, Oklahoma when affidavit given."
        ),
    },
    {
        "filename": "pine_ridge_vol1_questionnaire_001.json",
        "expected_current_name": "Greyearth, Mrs. Isaac",
        "expected_current_tribe": "Flandreau, South Dakota",
        "new_name": "Millie Richards",
        "new_tribe": "Pine Ridge (Oglala Sioux)",
        "residence_at_swearing": "Flandreau, South Dakota",
        "blm_accession": "0643-139",
        "blm_class": "MV",
        "blm_url": "https://glorecords.blm.gov/details/patent/default.aspx?accession=0643-139&docClass=MV",
        "source_page_evidence": (
            "SUBSTANTIVE NAME CORRECTION: Original extraction captured the "
            "INTERPRETER'S name ('Mr. Isaac Greyearth, Interpreter') rather "
            "than the allottee's. Actual allottee signature at bottom of source "
            "page reads 'Millie Richards.' This is a systematic extraction-failure "
            "mode worth flagging. "
            "Document signed by James H. McGregor, District Superintendent (a "
            "known Pine Ridge BIA Superintendent). Land mortgaged to J. D. "
            "Cordier of Pine Ridge. Sworn at Flandreau 20 May 1929. Fee patent "
            "date Dec 9, 1907 (early Burke Act period)."
        ),
    },
    {
        "filename": "pine_ridge_vol1_affidavit_057.json",
        "expected_current_name": "Nora Parkhurst",
        "expected_current_tribe": "Beltrami County, Minnesota (likely Red Lake or Leech Lake area)",
        "new_name": "Nora Parkhurst",  # current name; patent name was Martinez
        "new_tribe": "Pine Ridge (Oglala Sioux)",
        "residence_at_swearing": "Ponemah, Beltrami County, Minnesota (Red Lake area)",
        "blm_accession": "709441",
        "blm_class": "SER",
        "blm_url": "https://glorecords.blm.gov/details/patent/default.aspx?accession=709441&docClass=SER",
        "source_page_evidence": (
            "Patent issued under name 'Nora Martinez' (BLM accession 709441); "
            "current name at time of affidavit is 'Nora Parkhurst' (likely "
            "married name). Patent recorded in Pennington County, SD (1920). "
            "Note: Red Lake (where Ponemah is located) never participated in "
            "allotment — confirms her allotment is from Pine Ridge, not Red Lake. "
            "Sworn at Beltrami County 9 May 1929."
        ),
        "additional_note": (
            "Patent name 'Nora Martinez' may be a useful additional search "
            "key for cross-reference work; current/married name 'Nora "
            "Parkhurst' preserved as primary."
        ),
    },
]

CORPUS_PATTERN_NOTE = (
    " | CROSS-ROUTING PATTERN 2026-04-28: This record is one of 5 in the "
    "pine_ridge_* directory where the original Sonnet text-extraction captured "
    "a non-Pine-Ridge value in Tribe/Reservation. Source review and BLM "
    "cross-reference confirmed all 5 are Pine Ridge allottees who were living "
    "OFF-RESERVATION when they gave their affidavit/questionnaire testimony. "
    "The Tribe field had captured residence/sworn-at location rather than the "
    "allotment's tribal origin. Pattern documented as a systematic "
    "extraction-failure mode to be aware of in the rest of the corpus. "
    "Other affected records: Frank Carlow (vol1_aff_077, sworn at Crow Agency "
    "MT), Cecilia Armstrong Ross (vol2_aff_128, sworn at Turtle Mountain ND), "
    "Clara Peck (vol2_aff_022, sworn at Osage country OK), Millie Richards "
    "(vol1_q_001, sworn at Flandreau SD; original name extraction also "
    "captured the interpreter's name, not the allottee's), Nora Parkhurst "
    "née Martinez (vol1_aff_057, sworn at Red Lake area MN)."
)


def patch_one(spec):
    """Apply a single patch from the spec. Returns (success, message)."""
    path = EXTRACTIONS / spec["filename"]
    if not path.exists():
        return False, f"NOT FOUND: {path}"

    with open(path) as f:
        record = json.load(f)

    current = record["extraction"]

    # Verify
    if current.get("Name") != spec["expected_current_name"]:
        return False, (
            f"Name mismatch: expected '{spec['expected_current_name']}', "
            f"got '{current.get('Name')}'. Aborting this record."
        )
    if current.get("Tribe/Reservation") != spec["expected_current_tribe"]:
        return False, (
            f"Tribe mismatch: expected '{spec['expected_current_tribe']}', "
            f"got '{current.get('Tribe/Reservation')}'. Aborting this record."
        )

    # Apply patch
    name_corrected = spec["new_name"] != spec["expected_current_name"]
    if name_corrected:
        current["Name"] = spec["new_name"]
    current["Tribe/Reservation"] = spec["new_tribe"]
    current["NOTES"] = (current.get("NOTES") or "") + CORPUS_PATTERN_NOTE

    # Audit entry
    audit = {
        "date": "2026-04-28",
        "type": "cross_routing_correction",
        "method": "user_source_review_with_blm_cross_reference",
        "fields_corrected": (
            (["Name"] if name_corrected else [])
            + ["Tribe/Reservation", "NOTES"]
        ),
        "previous_values": {
            "Name": spec["expected_current_name"],
            "Tribe/Reservation": spec["expected_current_tribe"],
        },
        "corrected_values": {
            "Name": spec["new_name"],
            "Tribe/Reservation": spec["new_tribe"],
        },
        "residence_at_swearing": spec["residence_at_swearing"],
        "external_refs": {
            "BLM_accession": spec["blm_accession"],
            "BLM_class": spec["blm_class"],
            "BLM_url": spec["blm_url"],
        },
        "source_page_evidence": spec["source_page_evidence"],
        "user_confirmed": True,
        "corpus_pattern": (
            "One of 5 cross-routed pine_ridge_* records identified 2026-04-28 "
            "where Tribe field captured residence/sworn-at location rather "
            "than allotment origin."
        ),
    }
    if "additional_note" in spec:
        audit["additional_note"] = spec["additional_note"]

    record.setdefault("recovery_notes", []).append(audit)

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    msg = (
        f"  Tribe: '{spec['expected_current_tribe']}' -> '{spec['new_tribe']}'"
    )
    if name_corrected:
        msg += f"\n  Name (CORRECTED): '{spec['expected_current_name']}' -> '{spec['new_name']}'"
    return True, msg


def main():
    print("Cross-routing correction: 5 records in pine_ridge_*")
    print("=" * 60)

    successes = 0
    for spec in PATCHES:
        print(f"\n[{spec['filename']}]")
        ok, msg = patch_one(spec)
        print(msg)
        if ok:
            successes += 1
        else:
            print(f"  STATUS: FAILED ({msg})")

    print()
    print("=" * 60)
    print(f"Patches applied: {successes}/{len(PATCHES)}")
    print()
    print("Manifest unchanged (in-place patches only).")


if __name__ == "__main__":
    main()
