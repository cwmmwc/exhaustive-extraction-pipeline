#!/usr/bin/env python3
"""
Append Shawnee Indian Agency master list workstream completion to OPERATIONS.md.
"""
from pathlib import Path

OPERATIONS_PATH = Path(
    "/Users/cwm6W/projects/exhaustive-extraction-pipeline/OPERATIONS.md"
)

ADDITIONS = """

---

## Shawnee Indian Agency master list — workstream complete (2026-05-04)

The 36 rows in `circular_2464_extractions/extractions/sonnet/part10_shawnee_*.json` represent the Shawnee Indian Agency master list of allottees flagged for Circular 2464 investigation (transmitted by Supt. A.W. Leech, March 20, 1929). All 36 rows have explicit data state.

**Schema decision (option A):** The `Tribe/Reservation` field carries the actual tribe (e.g., 'Citizen Potawatomie'), not the agency name. Agency context ('Shawnee Indian Agency') is recoverable from the filename pattern (`part10_shawnee_*`) and preserved in NOTES. This treats the agency administrative structure and the actual tribal affiliation as separate analytical facts.

**Workstream results:**

- **30 rows resolved** with allotment + actual tribe:
  - 12 rows backfilled from matched affidavit/questionnaire records elsewhere in the corpus (10 via automated triage, 2 via manual triage for married-name and deceased-filing variants)
  - 18 rows backfilled from Christian's federal-register-app patents database (https://federal-register-app-996830241007.us-east1.run.app/patents)
  - All 30 confirmed allottees are **Citizen Potawatomie**

- **6 rows marked unresolved** with `Allotment number = "(not in patents database)"` and `Tribe/Reservation = "Shawnee Indian Agency (actual tribe unknown)"`:
  - Julia Bourasa Riley (row 04)
  - Nellie Bourasa (row 07)
  - R. DeGraff (row 10)
  - Josephine DeGraff (row 11)
  - Mrs. Jos. Nedeau (row 26)
  - Julia C. Pierson (row 29)

**Analytically significant findings:**

1. **"Shawnee" is agency, not tribe.** Every resolvable row on this master list turned out to be Citizen Potawatomie. The Shawnee Indian Agency administered Citizen Potawatomie, Iowa, Sac & Fox, and Eastern Shawnee allottees, but the master list itself happens to be entirely Citizen Potawatomie. The misclassification of `Tribe/Reservation = "Shawnee"` in the original Sonnet extraction reflects literal transcription of the master list header, not the actual tribal affiliations.

2. **Name variants between 1929 master list and modern patents database are routine.** Documented variants include:
   - Bourbonais (master list) vs Bourbonnais (database, double-n)
   - Joseph C. Cummings (master list) vs Joseph H. Cummings (database, middle initial)
   - Sophie Johnson (master list) vs Sophia Johnson (database)
   - Benis A. Mars (master list) vs Dennis A. Mars (database — master list misread 'D' as 'B')

3. **Married-name and deceased-filing variants required manual triage.** The automated normalize-name triage missed:
   - Lizzie Hartman (master list maiden name) ↔ Lizzie Lyons née Hartman (part10_questionnaire_011, married name in corpus)
   - James J. Sweeney 'for his deceased wife' (master list petitioner) ↔ Laura Dean (part10_questionnaire_017, the actual deceased allottee)
   Future master-list backfills should manually verify residual rows against the corpus, looking for these patterns.

4. **Absence from patents database is itself data.** The 6 unresolved rows may indicate cases where Circular 2464 investigation began but no forced fee patent was consummated, or patent records under different names not indexed in the current database. Marking these rows as explicitly unresolved (rather than leaving them indistinguishable from unprocessed rows) preserves the analytical signal.

**Patches and audit trail:**

- `backfill_shawnee_master_list.py` — 10 corpus cross-references
- `backfill_shawnee_master_list_manual_triage.py` — 2 manual matches (Hartman, Sweeney)
- `backfill_shawnee_final.py` — 18 patents-database confirmations + 6 not-in-database
- Each patched record's `recovery_notes` documents: source (patents database URL or corpus cross-reference), name variant if any, schema rationale, agency context, user confirmation

Total of 36 master list rows now have complete data state. The 6 unresolved rows remain candidates for future research (different databases, family history sources, NARA records).
"""

MARKER = "## Shawnee Indian Agency master list — workstream complete"


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
    print("New section: Shawnee Indian Agency master list — workstream complete")


if __name__ == "__main__":
    main()
