#!/usr/bin/env python3
"""
Append final 2026-05-04 observations to OPERATIONS.md.

Three additions not yet in the doc:
  1. Integrity-pass methodology (the verification pattern)
  2. Buyer-network names surfaced by the vision retrofit
  3. The George Menard pattern (multi-document allottees that are
     NOT duplicates)
"""
from pathlib import Path

OPERATIONS_PATH = Path(
    "/Users/cwm6W/projects/exhaustive-extraction-pipeline/OPERATIONS.md"
)

ADDITIONS = """

---

## Integrity-pass methodology (reusable verification pattern)

After a long writing session, the corpus needs an integrity check.
`integrity_pass_20260504.py` is the template: it walks every record
patched on a given date (identified by a date string in recovery_notes)
and verifies four things:

1. **Structural integrity** — extraction is a dict, not a list or
   missing; NOTES is non-empty and contains a marker matching the
   session date (catches NOTES clobbering, the failure mode where a
   later patch overwrites instead of appending).
2. **Double-patch detection** — flags any record with two or more
   recovery_notes of the SAME type on the same date. Type-aware, not
   just date-aware: a correction following an initial patch is
   legitimate (different types), but two patches of the same type
   indicate a bug or accidental re-run.
3. **Special-value checks** — the fractional ('.5') allotments
   (Louise Anderson Ernst 12.5, Josephine Collins 2862.5, Jennie
   Wright 1504.5) and the same-person cross-reference groups (matching
   allotments within group; differing allotments preserved across
   sibling-but-distinct groups like the Charbonneau cluster) are
   intact.
4. **Spot-check vision_extraction_v5** — dump structured fee_patents
   and financial_transactions for known-good clusters (Charbonneau,
   DuBray) to confirm the retrofit preserved real data, not just
   placeholders.

Run after any large patching session. Cheap insurance.

---

## Buyer-network names surfaced by the vision retrofit

The vision_extraction_v5 retrofit (38 records) yields structured buyer
and transaction data that the original Sonnet text extraction had
captured only as NOTES prose. The 2026-05-04 spot-check surfaced
the following named non-allottee actors in the DuBray cluster alone:

- Charles Burtz (bought from John DuBray Boyd, allotment 2338, $2000)
- Charles W. Marley (bought from Lucy DuBray Sturdevant, allotment
  2341, '$1.00 and other valuable consideration')
- R. L. Hinn (Lucy DuBray Sturdevant paid $800)
- Ray C. Wynn (Lucy DuBray Sturdevant and husband paid $800)
- H. D. Haskell (Lily Rice DuBray paid $75)

The phrase '$1.00 and other valuable consideration' is the classic
nominal-consideration language that masks real-value transfers — the
kind of phrasing that's evidentially important and that the structured
fields now make queryable across the corpus.

These are real data points already sitting in the corpus, waiting for
the eventual database loader to aggregate them across all 38 retrofit
records (and eventually merge with Kimi v5's per-part buyer data).
This is exactly the Role 4 (network analysis) layer the corpus was
designed to support — Valandra-style queries on recurring buyers,
lessors, lenders, and witnesses across the forced-fee patent cases.

---

## Multi-document allottees are common — and they are NOT duplicates

Several allottees appear in MULTIPLE legitimate corpus records that
document different stages of the same fee-patent case. The
2026-05-04 George Menard verification confirmed the pattern:

- `part2_questionnaire_016` (pages 48-51) — George Menard's Form 5-105
  Application for Patent in Fee (the formal application document, ca.
  1918-1920)
- `part2_questionnaire_017` (page 52) — George Menard's Circular 2464
  questionnaire response (the 1928 follow-up survey), containing his
  statement that he 'asked for patent on one quarter only' but the
  patent was issued for the whole half section.

Same person, same allotment 548, consecutive but non-overlapping
pages, different document types serving different evidentiary
purposes. NOT a duplicate.

**Decision rule** (already in use through 2026-05-04):

- **Duplicate** — same source pages split into two corpus records, OR
  one record's content is wholly contained in the other (Anna Shuck
  q015/q016, Tay Sander as garbled twin of Nora Tway Sandery).
  → DELETE one record, archive its content in the canonical record's
  recovery_notes.

- **Continuation page** — different pages of the same form
  (Louise Drapeau q020/q021, Margaret DeCory q013/q022).
  → KEEP BOTH, cross-reference in NOTES.

- **Multi-document allottee** — different document types about the
  same allottee, often at different points in the timeline
  (application + later questionnaire; agency narrative + questionnaire;
  affidavit + agency narrative). George Menard q016/q017,
  Joe/Joseph St John part11_an005/q012, the DuBray bundle cases
  (agency narrative + questionnaire for John DuBray Boyd and Lucy
  DuBray Sturdevant), the Helena Larvie pair (page 30 agency
  narrative + pages 31-32 questionnaire after the 'Hazel' correction).
  → KEEP BOTH, cross-reference, often with the same allotment.

The default assumption when finding two records that share an
allottee should be 'multi-document allottee' (legitimate, keep both),
not 'duplicate' (delete one). The Anna Shuck / Tay Sander cases
were the exceptions, identified by content comparison of the source
pages themselves.
"""

MARKER = "## Integrity-pass methodology (reusable verification pattern)"


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
    print("New sections:")
    print("  - Integrity-pass methodology")
    print("  - Buyer-network names surfaced by the vision retrofit")
    print("  - Multi-document allottees are NOT duplicates")


if __name__ == "__main__":
    main()
