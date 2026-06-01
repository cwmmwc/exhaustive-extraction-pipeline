#!/usr/bin/env python3
"""
Reclassify 6 administrative cover letters from CAT_1 to agency_correspondence.

These records were enumerated as CAT_1 (Sonnet missed Name + Allotment)
but they are NOT allottee records. They are cover letters from agency
superintendents (Page, Buntin, Jermark) to the Commissioner of Indian
Affairs reporting on Circular 2464 compliance. There is no allottee
Name or Allotment to recover because the documents are correspondence,
not allottee case files.

Records reclassified:
  - part11_agency_narrative_page015 — L.W. Page, Fort Berthold, 1928-12-27
  - part11_agency_narrative_page034 — J.A. Buntin, District Sup't, 1928-11-08
  - part3_agency_narrative_page062  — E.W. Jermark, Pine Ridge, 1928-11-21
  - part3_agency_narrative_page064  — Pine Ridge Agency to CIA, 1929-02-18
  - part3_agency_narrative_page066  — E.W. Jermark, Pine Ridge, 1928-12-07
  - pine_ridge_vol1_agency_narrative_page005 — E.W. Jermark, 1928-12-18

Action:
  - Sets Document type = 'agency_correspondence'
  - Adds NOTES explaining the reclassification
  - Records the rationale in recovery_notes

These records remain analytically valuable as compliance/response
correspondence — Jermark's multiple letters are useful comparative
material on Pine Ridge agency's handling of the circular.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

RECORDS = [
    {
        "stem": "part11_agency_narrative_page015",
        "sender": "L.W. Page",
        "title": "Superintendent, Fort Berthold Indian Agency",
        "date": "1928-12-27",
    },
    {
        "stem": "part11_agency_narrative_page034",
        "sender": "J.A. Buntin",
        "title": "District Superintendent in Charge",
        "date": "1928-11-08",
    },
    {
        "stem": "part3_agency_narrative_page062",
        "sender": "E.W. Jermark",
        "title": "Superintendent, Pine Ridge Agency",
        "date": "1928-11-21",
    },
    {
        "stem": "part3_agency_narrative_page064",
        "sender": "(unspecified Pine Ridge Agency author)",
        "title": "Pine Ridge Agency to Commissioner of Indian Affairs",
        "date": "1929-02-18",
    },
    {
        "stem": "part3_agency_narrative_page066",
        "sender": "E.W. Jermark",
        "title": "Superintendent, Pine Ridge Agency",
        "date": "1928-12-07",
    },
    {
        "stem": "pine_ridge_vol1_agency_narrative_page005",
        "stem_alias": "pine_ridge_vol1_agency_narrative_page005",
        "sender": "E.W. Jermark",
        "title": "Superintendent, Pine Ridge Agency",
        "date": "1928-12-18",
    },
]


def patch_one(rec):
    path = EXTRACTIONS / f"{rec['stem']}.json"
    if not path.exists():
        return False, "NOT FOUND"
    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        return False, "list-shaped extraction (unexpected)"

    previous_doc_type = e.get("Document type", "")
    if previous_doc_type == "agency_correspondence":
        return False, "already reclassified"

    e["Document type"] = "agency_correspondence"
    e["NOTES"] = (e.get("NOTES") or "") + (
        f" | TASK 5 RECLASSIFICATION 2026-05-03: This record was originally "
        f"enumerated as CAT_1 (Sonnet missed allottee Name + Allotment), but "
        f"it is NOT an allottee record — it is a cover letter from "
        f"{rec['sender']} ({rec['title']}) to the Commissioner of Indian "
        f"Affairs dated {rec['date']}, reporting on Circular 2464 compliance. "
        f"There is no allottee Name or Allotment to recover because the "
        f"document is correspondence, not an allottee case file. Document "
        f"type updated from '{previous_doc_type}' to 'agency_correspondence'. "
        f"This record is analytically valuable as compliance/response "
        f"correspondence and should remain in the corpus, but should be "
        f"excluded from CAT_1 vision recovery batches."
    )

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-03",
        "type": "task5_reclassification_administrative_correspondence",
        "method": "user_review_of_administrative_cover_letters",
        "fields_corrected": ["Document type", "NOTES"],
        "previous_doc_type": previous_doc_type,
        "corrected_doc_type": "agency_correspondence",
        "sender": rec["sender"],
        "sender_title": rec["title"],
        "letter_date": rec["date"],
        "rationale": (
            "Cover letter from agency superintendent to Commissioner of "
            "Indian Affairs. Has no allottee Name or Allotment because it "
            "is administrative correspondence, not an allottee case file. "
            "Should be excluded from CAT_1 vision recovery."
        ),
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return True, f"reclassified to agency_correspondence ({rec['sender']}, {rec['date']})"


def main():
    print("=" * 70)
    print(f"Reclassifying {len(RECORDS)} administrative cover letters")
    print("=" * 70)
    print()

    ok = 0
    for rec in RECORDS:
        success, msg = patch_one(rec)
        marker = "  " if success else "  ! "
        print(f"{marker}{rec['stem']:50s} {msg}")
        if success:
            ok += 1

    print()
    print(f"Reclassified: {ok}/{len(RECORDS)}")


if __name__ == "__main__":
    main()
