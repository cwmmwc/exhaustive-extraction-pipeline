#!/usr/bin/env python3
"""
Integrity pass over the 2026-05-04 Circular 2464 cleanup.

Part 1 — Campaign verification:
  For every record patched today (identified by 2026-05-04 recovery_notes),
  check:
    - valid JSON, dict-shaped extraction
    - NOTES is non-empty and contains today's marker (not clobbered)
    - recovery_notes present
    - flag any record with MORE THAN ONE recovery_note of the same type
      on the same date (possible double-patch)
  Report each record's current Name / Allotment / Tribe.

Part 2 — Special-value checks:
    - the '.5' allotments (Louise Anderson Ernst 12.5, Josephine Collins
      2862.5, Jennie Wright 1504.5) are intact
    - the same-person cross-reference groups carry the same allotment

Part 3 — Vision retrofit spot-check:
    - dump vision_extraction_v5 structured fields for the Charbonneau
      and DuBray cluster records
"""
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

TODAY = "2026-05-04"


def load(stem):
    path = EXTRACTIONS / f"{stem}.json"
    if not path.exists():
        return None
    try:
        return json.load(open(path))
    except json.JSONDecodeError:
        return "PARSE_ERROR"


def get_e(record):
    e = record.get("extraction", {})
    if isinstance(e, list):
        return e[0] if e else {}
    return e


def part1_campaign_verification():
    print("=" * 74)
    print("PART 1 — Campaign verification (records patched 2026-05-04)")
    print("=" * 74)

    problems = []
    checked = 0
    double_patch_flags = []

    for path in sorted(EXTRACTIONS.glob("*.json")):
        try:
            record = json.load(open(path))
        except json.JSONDecodeError:
            problems.append(f"{path.stem}: JSON PARSE ERROR")
            continue

        rnotes = record.get("recovery_notes", [])
        today_notes = [n for n in rnotes if n.get("date") == TODAY]
        if not today_notes:
            continue  # not patched today

        checked += 1
        stem = path.stem

        # Check extraction shape
        e = record.get("extraction")
        if isinstance(e, list):
            problems.append(f"{stem}: extraction is list-shaped")
            continue
        if not isinstance(e, dict):
            problems.append(f"{stem}: extraction missing or wrong type")
            continue

        # Check NOTES not clobbered (should contain a TASK 5 or 2026-05-04 marker)
        notes = e.get("NOTES") or ""
        if not notes.strip():
            problems.append(f"{stem}: NOTES is empty")
        elif "2026-05-04" not in notes and "TASK 5" not in notes and "TASK5" not in notes:
            problems.append(f"{stem}: NOTES present but no 2026-05-04 marker (possible clobber)")

        # Double-patch detection: same recovery_note type appearing 2+ times today
        type_counts = Counter(n.get("type") for n in today_notes)
        for ntype, count in type_counts.items():
            if count > 1:
                double_patch_flags.append(f"{stem}: type '{ntype}' appears {count}x today")

    print(f"Records patched today: {checked}")
    print()

    if problems:
        print(f"PROBLEMS ({len(problems)}):")
        for p in problems:
            print(f"  ! {p}")
    else:
        print("No structural problems found. All today's records have")
        print("dict-shaped extractions, non-empty NOTES with date markers,")
        print("and recovery_notes.")
    print()

    if double_patch_flags:
        print(f"DOUBLE-PATCH FLAGS ({len(double_patch_flags)}):")
        for f in double_patch_flags:
            print(f"  ! {f}")
        print("  (Note: multiple notes of the SAME type on one record may be")
        print("   legitimate if the record was intentionally patched twice,")
        print("   e.g. a correction following an initial patch. Review each.)")
    else:
        print("No double-patch flags (no record has 2+ recovery_notes of the")
        print("same type dated today).")
    print()


def part2_special_values():
    print("=" * 74)
    print("PART 2 — Special-value checks")
    print("=" * 74)

    # .5 allotments
    print("Fractional ('.5') allotments:")
    half_allots = [
        ("part1_questionnaire_009", "Louise Anderson Ernst", "12.5"),
        ("part2_agency_narrative_page059", "Josephine Collins", "2862.5"),
        ("part6_agency_narrative_page046", "Josephine Collins", "2862.5"),
        ("part2_questionnaire_020", "Josephine Collins", "2862.5"),
        ("part3_questionnaire_017", "Jennie Wright", "1504.5"),
    ]
    for stem, name, expected in half_allots:
        record = load(stem)
        if not record or record == "PARSE_ERROR":
            print(f"  ! {stem}: missing or parse error")
            continue
        actual = get_e(record).get("Allotment number", "")
        status = "OK" if actual == expected else "MISMATCH"
        marker = "  " if status == "OK" else "  ! "
        print(f"{marker}{stem:38s} {name:24s} expected={expected:8s} actual={actual} [{status}]")
    print()

    # Cross-reference groups — same allotment across the group
    print("Same-person cross-reference groups (allotment should match within group):")
    groups = [
        ("Josephine Collins", "2862.5", [
            "part2_agency_narrative_page059",
            "part6_agency_narrative_page046",
            "part2_questionnaire_020",
        ]),
        ("Mary Dillon", "481", [
            "part7_affidavit_005",
            "part7_questionnaire_016",
        ]),
        ("George Menard", "548", [
            "part2_questionnaire_016",
            "part2_questionnaire_017",
        ]),
        ("St John (Joe/Joseph)", "547", [
            "part11_agency_narrative_005",
            "part11_questionnaire_012",
        ]),
        ("Charbonneau cluster (different allotments expected)", None, [
            "part3_questionnaire_012",  # Alphonse 1466
            "part3_questionnaire_013",  # Della 1467
            "part4_questionnaire_012",  # Alphonse 1466
        ]),
    ]
    for label, expected, stems in groups:
        print(f"  {label}:")
        for stem in stems:
            record = load(stem)
            if not record or record == "PARSE_ERROR":
                print(f"    ! {stem}: missing or parse error")
                continue
            e = get_e(record)
            allot = e.get("Allotment number", "")
            name = e.get("Name", "")
            if expected is not None:
                status = "OK" if allot == expected else "MISMATCH"
                marker = "    " if status == "OK" else "    ! "
                print(f"{marker}{stem:38s} {name[:28]:28s} allot={allot} [{status}]")
            else:
                print(f"      {stem:38s} {name[:28]:28s} allot={allot}")
        print()


def part3_vision_retrofit_spotcheck():
    print("=" * 74)
    print("PART 3 — vision_extraction_v5 retrofit spot-check")
    print("=" * 74)

    spotcheck = [
        "part3_questionnaire_012",       # Alphonse Charbonneau
        "part3_questionnaire_013",       # Della Charbonneau
        "part4_questionnaire_012",       # Alphonse Charbonneau (part 4)
        "part7_questionnaire_020",       # Lucy DuBray Sturdevant
        "part7_questionnaire_023",       # Lily Rice DuBray
        "part7_agency_narrative_025a",   # John DuBray Boyd (bundle)
        "part7_agency_narrative_025b",   # Lucy DuBray Sturdevant (bundle)
    ]

    for stem in spotcheck:
        record = load(stem)
        if not record or record == "PARSE_ERROR":
            print(f"  ! {stem}: missing or parse error")
            continue
        v5 = record.get("vision_extraction_v5")
        e = get_e(record)
        name = e.get("Name", "")
        print(f"  {stem} ({name}):")
        if not v5:
            print(f"    (no vision_extraction_v5)")
            print()
            continue
        if v5.get("_retrofit_filter_note"):
            print(f"    filter: {v5['_retrofit_filter_note'][:90]}")
        fps = v5.get("fee_patents") or []
        print(f"    fee_patents: {len(fps)}")
        for fp in fps:
            print(f"      allottee={fp.get('allottee_name')} allot={fp.get('allotment_number')} "
                  f"buyer={fp.get('buyer')} price={fp.get('sale_price')}")
        fts = v5.get("financial_transactions") or []
        print(f"    financial_transactions: {len(fts)}")
        for ft in fts:
            print(f"      type={ft.get('type')} amount={ft.get('amount')} "
                  f"payer={ft.get('payer')} payee={ft.get('payee')}")
        print()


def main():
    part1_campaign_verification()
    part2_special_values()
    part3_vision_retrofit_spotcheck()
    print("=" * 74)
    print("Integrity pass complete.")
    print("=" * 74)


if __name__ == "__main__":
    main()
