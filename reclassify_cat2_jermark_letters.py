#!/usr/bin/env python3
"""
Reclassify the 2 remaining CAT_2 records as agency_correspondence.

part3_agency_narrative_page059 and part3_agency_narrative_page060 are
both administrative cover letters from Superintendent E. W. Jermark
(Pine Ridge Agency) to the Commissioner of Indian Affairs,
acknowledging receipt of Circular No. 2464. They are NOT allottee
records.

The "allotment 112" that placed them in CAT_2 (name missing, allotment
captured) is a misextraction — a stray reference number or count that
Sonnet read as an allotment number. It is cleared.

This matches the 6 earlier agency_correspondence reclassifications
(Page, Buntin, and 4 Jermark letters) done 2026-05-03.

Analytical note: page060 records aggregate patent counts (333 patents
issued April 13, 1918; 344 issued September 29, 1919). These figures
are preserved in NOTES — they bear on the "floor not ceiling" framing
of the forced-fee patent research (agency-level totals of patents
issued).
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

RECORDS = [
    {
        "stem": "part3_agency_narrative_page059",
        "note": (
            "Administrative cover letter from E. W. Jermark, Pine Ridge "
            "Agency, to the Commissioner of Indian Affairs, dated "
            "November 3, 1928, acknowledging receipt of Circular No. "
            "2464. Not an allottee record."
        ),
    },
    {
        "stem": "part3_agency_narrative_page060",
        "note": (
            "Cover letter from E. W. Jermark, Superintendent, Pine Ridge, "
            "dated September 22, 1928, acknowledging receipt of Circular "
            "No. 2464 Fee Patent Data. ANALYTICAL: the letter records "
            "aggregate patent counts — 333 patents issued April 13, 1918 "
            "and 344 issued September 29, 1919. These agency-level totals "
            "are preserved here for their relevance to the 'floor not "
            "ceiling' framing of the forced-fee research. Not an allottee "
            "record."
        ),
    },
]


def main():
    print("=" * 70)
    print(f"CAT_2 reclassification: {len(RECORDS)} records")
    print("=" * 70)

    ok = 0
    for spec in RECORDS:
        path = EXTRACTIONS / f"{spec['stem']}.json"
        if not path.exists():
            print(f"  ! {spec['stem']}: NOT FOUND")
            continue
        with open(path) as f:
            record = json.load(f)
        e = record["extraction"]
        if isinstance(e, list):
            print(f"  ! {spec['stem']}: list-shaped extraction")
            continue

        previous = {
            "Allotment number": e.get("Allotment number", ""),
            "Document type": e.get("Document type", ""),
        }

        e["Allotment number"] = "(not applicable — agency correspondence)"
        e["Document type"] = "agency_correspondence"
        e["NOTES"] = (e.get("NOTES") or "") + (
            f" | TASK 5 CAT_2 RECLASSIFICATION 2026-05-04: {spec['note']} "
            f"Reclassified as agency_correspondence (matching the 6 earlier "
            f"agency cover-letter reclassifications 2026-05-03). The "
            f"'allotment 112' that originally placed this record in CAT_2 "
            f"was a misextraction (a stray reference number or count read "
            f"as an allotment); it has been cleared."
        )

        record.setdefault("recovery_notes", []).append({
            "date": "2026-05-04",
            "type": "task5_reclassification_administrative_correspondence",
            "method": "user_confirmed_agency_cover_letter",
            "fields_corrected": ["Allotment number", "Document type", "NOTES"],
            "previous_values": previous,
            "corrected_values": {
                "Allotment number": "(not applicable — agency correspondence)",
                "Document type": "agency_correspondence",
            },
            "rationale": (
                "E. W. Jermark cover letter acknowledging Circular 2464. "
                "Not an allottee record. The 'allotment 112' was a "
                "misextraction and has been cleared."
            ),
            "user_confirmed": True,
        })

        with open(path, "w") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        print(f"  {spec['stem']:38s} -> agency_correspondence (allotment cleared)")
        ok += 1

    print()
    print(f"Reclassified: {ok}/{len(RECORDS)}")


if __name__ == "__main__":
    main()
