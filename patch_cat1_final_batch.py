#!/usr/bin/env python3
"""
Final CAT_1 batch patch — 12 records.

11 from the remaining CAT_1 list + part1_questionnaire_013 (Margaret DeCory's
main questionnaire) which gets its allotment backfilled from the user's
research (342) at the same time as her continuation page q022.

User-verified values (2026-05-04):

Single-allottee records:
  part10_affidavit_005      → Albion Ogee, 1080, Citizen Potawatomie
  part10_questionnaire_011  → Lizzie Lyons (née Hartman), 765, Citizen Potawatomie
  part10_questionnaire_016  → Olive Shepard, 862, Citizen Potawatomie
  part11_affidavit_001      → Nicholas Trombla, 484, Citizen Potawatomie
  part13_affidavit_001      → Belle Water, 61, Ponca
  part1_questionnaire_005   → Edith Emery Lague, 2996, Rosebud Sioux
  part1_questionnaire_013   → Margaret DeCory, 342, Rosebud Sioux (backfill)
  part2_questionnaire_016   → George Menard, 548, Rosebud Sioux

Continuation page records (cross-referenced to lead record):
  part1_questionnaire_021   → Louise Drapeau, 6493, Rosebud Sioux
                              (final page of her 5-105; lead at q020)
  part1_questionnaire_022   → Margaret DeCory, 342, Rosebud Sioux
                              (continuation page; lead at q013)

Buyer/network record:
  part11_agency_narrative_003 → agency_buyer_report
                                Captures buyer/lessor info on M.B. Gregg
                                (lessor, Harrold SD) and Frank Ktilienk
                                (buyer, DeGrey SD, Crow Creek). Authored
                                by Supt. H.E. Wright.

Note on continuation pages: q021 is the trailing page of Louise Drapeau's
5-page Form 5-105 application; q020 (already patched) covers pages 1-3.
q022 is the trailing biographical page of Margaret DeCory's 2464
questionnaire; q013 (now patched) covers the main content. Both
continuation pages get the same Name/Allotment/Tribe as their lead
records, with NOTES cross-referencing the lead. The continuation pages
remain in the corpus as separate records (not deleted) because their
content is genuinely different from the lead — they capture different
sections of the same form.

The captured "patent was forced on me" (Lizzie Lyons) and "did not
care for fee patent" (Olive Shepard) phrases are preserved in NOTES
because they're directly relevant to the project's argument about
forced fee patents.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"

PATCHES = [
    {
        "filename": "part10_affidavit_005.json",
        "name": "Albion Ogee",
        "allotment": "1080",
        "tribe": "Citizen Potawatomie",
        "doc_type": None,  # keep existing
        "models_summary": (
            "Sonnet vision: 'Albion Ogee' / unknown allotment. Qwen vision: "
            "'Albion Dyer' / null. User confirmed Sonnet's name reading "
            "and provided allotment 1080 (Citizen Potawatomie)."
        ),
        "extra_notes": "",
    },
    {
        "filename": "part10_questionnaire_011.json",
        "name": "Lizzie Lyons (née Hartman)",
        "allotment": "765",
        "tribe": "Citizen Potawatomie",
        "doc_type": None,
        "models_summary": (
            "Sonnet vision: 'Lizzie Lyons nee Hartman' / 'N1/2 SW1/4 S-8-5'. "
            "Qwen vision: 'Lizzie Lyons New Hartman' / 'N½ S17 T4 S=8 R5'. "
            "Sonnet's 'née' reading is correct (maiden name marker); Qwen's "
            "'New' is wrong. Both reading land descriptions instead of "
            "allotment number. User confirmed allotment 765, tribe Citizen "
            "Potawatomie."
        ),
        "extra_notes": (
            "ANALYTICAL: Source page contains allottee statement 'patent "
            "was forced on me' — directly relevant to forced-fee patent "
            "argumentation."
        ),
    },
    {
        "filename": "part10_questionnaire_016.json",
        "name": "Olive Shepard",
        "allotment": "862",
        "tribe": "Citizen Potawatomie",
        "doc_type": None,
        "models_summary": (
            "Sonnet vision: 'Olive Shepard' / 862. Qwen vision: 'Oline "
            "Shepard' / 862. Single-letter name disagreement; both correct "
            "on allotment. User confirmed Sonnet's 'Olive' spelling and "
            "tribe Citizen Potawatomie."
        ),
        "extra_notes": (
            "ANALYTICAL: Source page contains allottee statement 'did not "
            "care for fee patent' — relevant to forced-fee patent context."
        ),
    },
    {
        "filename": "part11_affidavit_001.json",
        "name": "Nicholas Trombla",
        "allotment": "484",
        "tribe": "Citizen Potawatomie",
        "doc_type": None,
        "models_summary": (
            "Both Sonnet and Qwen vision agree on name 'Nicholas Trombla'. "
            "Neither captured allotment from the source page. User "
            "confirmed allotment 484 and tribe Citizen Potawatomie. "
            "Trombla is on the Shawnee Indian Agency master list (row 33) "
            "as 'Nicholas Trombla' — affirms cross-reference."
        ),
        "extra_notes": "",
    },
    {
        "filename": "part13_affidavit_001.json",
        "name": "Belle Water",
        "allotment": "61",
        "tribe": "Ponca",
        "doc_type": None,
        "models_summary": (
            "Both Sonnet and Qwen vision agree on name 'Belle Water'. "
            "Neither captured allotment. User confirmed allotment 61 "
            "and tribe Ponca."
        ),
        "extra_notes": "",
    },
    {
        "filename": "part1_questionnaire_005.json",
        "name": "Edith Emery Lague",
        "allotment": "2996",
        "tribe": "Rosebud Sioux",
        "doc_type": None,
        "models_summary": (
            "Sonnet vision: 'Edith Emery Lague' / 2996. Qwen vision: "
            "'Edith Emery Laque' / 6931. Sonnet correct on both name "
            "spelling (Lague vs Laque) and allotment (2996). User "
            "verified."
        ),
        "extra_notes": "",
    },
    {
        "filename": "part1_questionnaire_013.json",
        "name": "Margaret DeCory",
        "allotment": "342",
        "tribe": "Rosebud Sioux",
        "doc_type": None,
        "models_summary": (
            "Backfill of allotment number from user research (342). "
            "Original Sonnet text extraction captured Margaret DeCory's "
            "name and substantive content (no receipt signed, $12,000 "
            "land sale) but not her allotment number; this patch adds it."
        ),
        "extra_notes": (
            "Continuation page of this questionnaire is at "
            "part1_questionnaire_022 (biographical/health section). "
            "Both records refer to the same source document."
        ),
    },
    {
        "filename": "part1_questionnaire_021.json",
        "name": "Louise Drapeau",
        "allotment": "6493",
        "tribe": "Rosebud Sioux",
        "doc_type": None,
        "models_summary": (
            "Sonnet vision: 'Louise Drapeau' / unknown. Qwen vision: "
            "'Louise Arapahoe' / null. User confirmed this is the "
            "trailing page of Louise Drapeau's 5-page Form 5-105 "
            "application. Lead record is part1_questionnaire_020 "
            "(allotment 6493, Rosebud Sioux). q020 was patched earlier "
            "in this session."
        ),
        "extra_notes": (
            "CONTINUATION PAGE: This record is the final page of "
            "Louise Drapeau's Form 5-105 Application for Patent in Fee. "
            "The first 3 pages are at part1_questionnaire_020. Both "
            "records refer to the same source document but capture "
            "different pages. Retained as separate corpus records "
            "rather than merged."
        ),
    },
    {
        "filename": "part1_questionnaire_022.json",
        "name": "Margaret DeCory",
        "allotment": "342",
        "tribe": "Rosebud Sioux",
        "doc_type": None,
        "models_summary": (
            "User confirmed this is the continuation page of Margaret "
            "DeCory's 2464 questionnaire. Lead record is "
            "part1_questionnaire_013 (Margaret DeCory, allotment 342, "
            "Rosebud Sioux — patched in this session)."
        ),
        "extra_notes": (
            "CONTINUATION PAGE: This record captures the trailing "
            "biographical/health section of Margaret DeCory's 2464 "
            "questionnaire (supported by husband, in good health, "
            "partially illegible). Main content is at "
            "part1_questionnaire_013. Both records refer to the same "
            "source document but capture different pages. Retained as "
            "separate corpus records rather than merged."
        ),
    },
    {
        "filename": "part2_questionnaire_016.json",
        "name": "George Menard",
        "allotment": "548",
        "tribe": "Rosebud Sioux",
        "doc_type": None,
        "models_summary": (
            "Sonnet vision: 'George Menard' / 548. Qwen vision had "
            "garbled readings across pages ('George Wuard' / '5-48' on "
            "page 1; 'Leo Minard' / null on page 3; 'George Minard' / "
            "null on page 4). Sonnet correct on both name and allotment. "
            "User confirmed tribe Rosebud Sioux."
        ),
        "extra_notes": "",
    },
    # Special case: M.B. Gregg buyer report
    {
        "filename": "part11_agency_narrative_003.json",
        "name": "(buyer report — see NOTES for named actors)",
        "allotment": "(not applicable — non-allottee record)",
        "tribe": "Crow Creek",
        "doc_type": "agency_buyer_report",
        "models_summary": (
            "Sonnet vision: 'M. B. Gregg' (fallback to entities[person]; "
            "no allotment). Qwen vision: nothing on page. The record is "
            "NOT an allottee record — it's an agency narrative report by "
            "Superintendent H.E. Wright describing two non-allottee "
            "individuals operating on Crow Creek Reservation."
        ),
        "extra_notes": (
            "BUYER/LESSOR NETWORK ACTORS: "
            "(1) M.B. Gregg — lessor at Harrold, SD; described as having "
            "'nothing in his name and is worth nothing'. "
            "(2) Frank Ktilienk — at DeGrey, SD; living on Crow Creek "
            "Reservation at time of writing; described as having "
            "'nothing at all'. "
            "Authored by H.E. Wright, Superintendent and Special "
            "Disbursing Agent (S.D.A.). "
            "Document type set to 'agency_buyer_report' (new type) to "
            "distinguish reports about land buyers/lessors from records "
            "about allottees and from administrative correspondence "
            "(agency_correspondence). This type supports future buyer-"
            "network analysis (Valandra-style queries)."
        ),
    },
]


def patch_one(spec):
    path = EXTRACTIONS / spec["filename"]
    if not path.exists():
        return False, "NOT FOUND"
    with open(path) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        return False, "list-shaped extraction"

    previous = {
        "Name": e.get("Name", ""),
        "Allotment number": e.get("Allotment number", ""),
        "Tribe/Reservation": e.get("Tribe/Reservation", ""),
        "Document type": e.get("Document type", ""),
    }

    e["Name"] = spec["name"]
    e["Allotment number"] = spec["allotment"]
    e["Tribe/Reservation"] = spec["tribe"]
    if spec["doc_type"]:
        e["Document type"] = spec["doc_type"]

    note_addition = (
        f" | TASK 5 CAT_1 PATCH 2026-05-04: {spec['models_summary']}"
    )
    if spec["extra_notes"]:
        note_addition += f" {spec['extra_notes']}"
    e["NOTES"] = (e.get("NOTES") or "") + note_addition

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-04",
        "type": "task5_cat1_dual_model_with_user_verification",
        "method": "sonnet_vision_plus_qwen_vision_with_user_verification",
        "fields_corrected": [
            k for k in ["Name", "Allotment number", "Tribe/Reservation",
                        "Document type", "NOTES"]
            if k != "Document type" or spec["doc_type"]
        ],
        "previous_values": previous,
        "corrected_values": {
            "Name": spec["name"],
            "Allotment number": spec["allotment"],
            "Tribe/Reservation": spec["tribe"],
            **({"Document type": spec["doc_type"]} if spec["doc_type"] else {}),
        },
        "models_summary": spec["models_summary"],
        "extra_notes": spec["extra_notes"],
        "user_confirmed": True,
    })

    with open(path, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    msg = f"-> {spec['name']}, {spec['allotment']}, {spec['tribe']}"
    if spec["doc_type"]:
        msg += f" [doc_type={spec['doc_type']}]"
    return True, msg


def main():
    print("=" * 70)
    print(f"CAT_1 final batch patch: {len(PATCHES)} records")
    print("=" * 70)

    ok = 0
    for spec in PATCHES:
        success, msg = patch_one(spec)
        marker = "  " if success else "  ! "
        print(f"{marker}{spec['filename']:42s} {msg}")
        if success:
            ok += 1

    print()
    print(f"Patches applied: {ok}/{len(PATCHES)}")


if __name__ == "__main__":
    main()
