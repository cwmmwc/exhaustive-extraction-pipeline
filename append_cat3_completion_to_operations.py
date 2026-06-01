#!/usr/bin/env python3
"""
Append Task 5 CAT_2/CAT_3 campaign completion to OPERATIONS.md.
"""
from pathlib import Path

OPERATIONS_PATH = Path(
    "/Users/cwm6W/projects/exhaustive-extraction-pipeline/OPERATIONS.md"
)

ADDITIONS = """

---

## Task 5 CAT_2 / CAT_3 campaign — complete (2026-05-04)

The Task 5 candidate campaign (records where Sonnet text extraction
failed to capture identifying fields) is complete. Final enumeration:
CAT_1 = 0, CAT_2 = 0, CAT_3 = 0. Two records are deliberately left
unpatched (Hannah Hardin signature page part10_affidavit_004; blank
Circular 2464 instruction template part3_questionnaire_022).

**Category definitions** (from enumerate_task5_candidates.py):
- CAT_1: both Name and Allotment missing (hardest — no anchor)
- CAT_2: Name missing, Allotment captured (anchor by allotment)
- CAT_3: Name captured, Allotment missing (anchor by name + lookup)

**CAT_3 resolution — 76 records, worked by tribe:**

The CAT_3 records were grouped by tribe and resolved primarily through
Christian's federal-register-app patents database
(https://federal-register-app-996830241007.us-east1.run.app/patents),
which is keyed by allottee name and returns allotment + tribe.

- Rosebud-area: 22 records (21 patents-database backfills + 1 name
  correction — see Helena Larvie below)
- Pine Ridge / Oglala Lakota: 6 patents-database backfills + 1
  duplicate removed (Tay Sander = garbled duplicate of Nora Tway
  Sandery)
- Crow Creek / Big Bend District: 6 records (Joe and Peter St John,
  Cleveland Fallis — who is Lower Brule not Crow Creek despite the
  district label — and three William Walker records that are one
  person across pages 2-5 of part 12)
- Scattered single-tribe: 5 records (Crow Creek, Pawnee, Ponca,
  Sioux→Rosebud Sioux, Shannon-County→Oglala Lakota)
- Tribe-not-stated: 36 records (29 allotment backfills, 1
  not-in-database, 1 non-allottee witness, 2 non-allottee
  reclassifications, plus same-person cross-reference cases)

**CAT_2 resolution — 2 records:**

Both were E. W. Jermark cover letters from Pine Ridge Agency
acknowledging Circular 2464, misclassified as CAT_2 because a stray
'112' was read as an allotment number. Reclassified as
agency_correspondence; the spurious allotment cleared. page060's
aggregate patent counts (333 issued 1918-04-13, 344 issued 1919-09-29)
preserved in NOTES for the 'floor not ceiling' framing.

**New document type: non_allottee_record**

Established for records whose named individuals are neither allottees
nor land buyers:
- part6_affidavit_002 (T. C. Montgomery, J. D. Keller — affiants,
  not allottees)
- part7_agency_narrative_page056 (Eugene Sturdevant — white, no
  allotment; note Sturdevant is also the married name of allottee
  Lucy DuBray Sturdevant, a different person)

Distinct from agency_buyer_report (specifically about land buyers/
lessors) and agency_correspondence (transmittal letters). The
non_allottee_record type is the general bucket for documents retained
for evidentiary value whose subjects are not allottees.

William J. Bordeaux (part6_questionnaire_021) was marked
'(non-allottee record — witness)' in the allotment field rather than
reclassified, because he appears as a recurring witness on others'
affidavits — worth keeping discoverable as a witness-network actor.

**Methodologically significant findings:**

1. **Helena Larvie name correction (Hazel -> Helena).** Sonnet text
   extraction read degraded handwriting on part9_questionnaire_010 as
   'Hazel (last name not fully legible)'. The correct name is Helena
   Larvie. This was caught NOT by model comparison but by page-sequence
   reasoning: every allottee in part 9 has both an agency_narrative and
   a questionnaire on consecutive pages; pages 31-32 (the 'Hazel'
   questionnaire) fall exactly between Helena Larvie's agency narrative
   (page 30) and Peter Larvie's (page 33), so the 'Hazel' questionnaire
   is Helena Larvie's. User source-page review confirmed. The part 9
   narrative+questionnaire pairing pattern is itself a verification
   tool. Allotment 3432 from BLM General Land Office records
   (accession SD2610__.247) — Helena Larvie was not in the patents
   database.

2. **Jesse / Jasper Ellston — conservative separation.** Jesse
   Ellston's affidavit (part2_questionnaire_001) contains his own
   statement: 'My name is known also as Jasper J. Ellston, and I am
   sometimes called Jay Ellston.' The patents database has a Jesse
   Ellston (allotment 241) and a separate Jasper Ellston (allotment
   243, own record part2_agency_narrative_004). DECISION: treat them
   as two separate people — two names, two allotment numbers. Why
   Jesse stated he is 'also known as Jasper' is unresolved and
   deliberately not collapsed. The affidavit statement is preserved
   verbatim in NOTES as data, not resolved into an identity claim.
   This is the conservative, evidence-respecting treatment.

3. **Same-person cross-reference cases.** Several allottees have
   multiple corpus records, cross-referenced rather than merged:
   - Josephine Collins: 3 records, allotment 2862.5
     (part2_agency_narrative_page059, part6_agency_narrative_page046,
     part2_questionnaire_020)
   - Mary Dillon: 2 records, allotment 481 (part7_affidavit_005,
     part7_questionnaire_016)
   - George Menard: 2 records, allotment 548 (part2_questionnaire_016,
     part2_questionnaire_017)
   - Joseph/Joe St John: questionnaire + agency narrative, allotment
     547 (part11_questionnaire_012, part11_agency_narrative_005)

4. **Tribe-label normalization.** 'Rosebud' normalized to 'Rosebud
   Sioux'; generic 'Sioux' and the county label 'Shannon County (South
   Dakota)' replaced with actual tribes; 'Big Bond District' (OCR
   error) corrected to Big Bend / Crow Creek Sioux; 'Ponca' on Jesse
   Ellston (derived from a 'Ponca station' mention) corrected to
   Rosebud Sioux. Tribe field carries the actual tribe; agency/district
   context goes in NOTES.

5. **Name variants between 1929 records and the modern database** are
   routine and were documented per-record (e.g., Annie Desersa /
   Annie Deserea; Nora Tway / Nora Sanders / 'Nora Tway Sandery').

6. **Not-in-database records.** Hattie Whiting Whitcher could not be
   located in the patents database; marked '(not in patents database)'
   / '(actual tribe unknown)' per the option-3 convention. Absence is
   recorded as data.

**Provenance recorded per record.** Each patched record's
recovery_notes captures the source (patents database URL, BLM GLO
accession, corpus cross-reference, or source-page review), any name
variant, the tribe-normalization rationale, and user confirmation.

**Reusable scripts from this campaign** (in project root):
- enumerate_task5_candidates_v4.py (current categorization filter)
- triage_shawnee_master_list.py (corpus surname-match triage)
- presort_tribe_not_stated.py (surname -> likely tribe pre-sort)
- the various patch_*.py and backfill_*.py batch patchers
"""

MARKER = "## Task 5 CAT_2 / CAT_3 campaign — complete"


def main():
    if not OPERATIONS_PATH.exists():
        print(f"ERROR: {OPERATIONS_PATH} does not exist.")
        return

    with open(OPERATIONS_PATH) as f:
        existing = f.read()

    if MARKER in existing:
        print(f"Marker '{MARKER}' already present. Refusing to duplicate.")
        return

    with open(OPERATIONS_PATH, "a") as f:
        f.write(ADDITIONS)

    print(f"Appended {len(ADDITIONS.splitlines())} lines to OPERATIONS.md")
    print()
    print("New section: Task 5 CAT_2 / CAT_3 campaign — complete")


if __name__ == "__main__":
    main()
