#!/usr/bin/env python3
"""
Dedup the survey_of_conditions database.

Handles three kinds of cleanup:

  1. Cross-collection orphans — documents that ended up in
     survey_of_conditions but actually belong elsewhere. Currently:
     Doc 56 (1921 CCF 56074-21-312 GS — already in full_corpus_docs).
     Doc 55 (Taylor Full) is intentionally NOT touched: its only home
     is this database, and it's actively used by the analysis tool.

  2. Exact-filename duplicates — discovered dynamically by querying
     for any file_name appearing on more than one row. These come from
     loading the same volume twice (e.g., once via Together AI and
     once via the HPC Kimi reload). Each duplicate group is run
     through pick_winner() and the loser(s) deleted.

  3. Near-duplicate Survey volumes — same hearing loaded twice under
     variant filenames. For each pair, the row with the most
     extraction items + has full_text wins. The other is deleted.

Foreign keys cascade, so deleting a documents row cleans up
mentions, events, fee_patents, taxes, mortgages, etc. automatically.

Default mode is dry-run. Pass --apply to actually execute deletes.

Usage:
    python3 dedup_survey.py            # dry run (default)
    python3 dedup_survey.py --apply    # actually delete
"""

import argparse
import sys
import psycopg2
import psycopg2.extras


DB_NAME = "survey_of_conditions"


# ─────────────────────────────────────────────────────────────────
# Cleanup actions
# ─────────────────────────────────────────────────────────────────

# Cross-collection orphans: delete unconditionally.
# Each entry is (delete_id, reason)
ORPHAN_DELETES = [
    (
        56,
        "1921 CCF 56074-21-312 GS — Board of Indian Commissioners report; "
        "wrong collection (Survey of Conditions). Canonical copy lives in "
        "full_corpus_docs as Doc 2 + Doc 5 (Doc 5 has 293 fee patents from "
        "the Kimi K2.5 extraction; this Survey copy only has 67).",
    ),
]

# Near-duplicate Survey volume pairs.
# Each entry is (id_a, id_b, description). The script will fetch
# extraction counts + full_text presence for both and pick the winner
# automatically (most data + has full_text). The "loser" is deleted.
DEDUP_PAIRS = [
    (
        58, 59,
        "1928–1929 General Hearing Part 3: '...part 3 duplicate' vs '...part 3'",
    ),
    (
        62, 63,
        "1928 SF/Riverside/SLC Part 2: '...part 2' vs '...part 2 duplicate'",
    ),
    (
        64, 65,
        "1928 Yakima Part 1: '...Yakima, WA; Klamath Falls, OR; part 1' vs "
        "'...Yakima, Washington; Part 1' (variant filename)",
    ),
    (
        70, 71,
        "1929 Madison Part 5: byte-identical 1,232,215 chars / 336 pages "
        "(both: '1929; Madison, WI; Lac du Flambeau, WI; Hayward, WI; "
        "Winnebago, NE; Pierre, SD; part 5')",
    ),
]


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

EXTRACTION_TABLES = [
    "mentions", "events", "financial_transactions", "relationships",
    "fee_patents", "correspondence", "legislative_actions",
    "testimony", "taxes", "mortgages",
]


def get_doc_stats(cur, doc_id):
    """Return a dict of stats for a single document row."""
    cur.execute("""
        SELECT id, file_name, display_title, page_count,
               full_text IS NOT NULL AND length(full_text) > 0 AS has_text,
               coalesce(length(full_text), 0) AS text_chars,
               summary IS NOT NULL AND length(summary) > 0 AS has_summary
        FROM documents
        WHERE id = %s
    """, (doc_id,))
    row = cur.fetchone()
    if row is None:
        return None
    stats = dict(row)
    counts = {}
    for tbl in EXTRACTION_TABLES:
        cur.execute(f"SELECT COUNT(*) AS n FROM {tbl} WHERE document_id = %s", (doc_id,))
        counts[tbl] = cur.fetchone()["n"]
    stats["counts"] = counts
    stats["total_items"] = sum(counts.values())
    return stats


def format_stats_line(s):
    """Compact one-line summary of a doc's stats."""
    return (
        f"Doc {s['id']:<3} | {s['total_items']:>6} items | "
        f"text={'yes' if s['has_text'] else 'no'} ({s['text_chars']:>9,} ch) | "
        f"summary={'yes' if s['has_summary'] else 'no'} | "
        f"{s['file_name'][:80]}"
    )


def pick_winner(stats_a, stats_b):
    """Decide which of the two rows to keep. Returns (keep, drop, reason)."""
    # Rule 1: row with full_text wins (full_text was loaded from PDF;
    # it's a strong signal that the file_path / filename matched the PDF
    # in Box, which means it's the canonical version)
    if stats_a["has_text"] and not stats_b["has_text"]:
        return stats_a, stats_b, "A has full_text, B does not"
    if stats_b["has_text"] and not stats_a["has_text"]:
        return stats_b, stats_a, "B has full_text, A does not"

    # Rule 2: row with more extraction items wins
    if stats_a["total_items"] > stats_b["total_items"]:
        return stats_a, stats_b, f"A has more items ({stats_a['total_items']} vs {stats_b['total_items']})"
    if stats_b["total_items"] > stats_a["total_items"]:
        return stats_b, stats_a, f"B has more items ({stats_b['total_items']} vs {stats_a['total_items']})"

    # Rule 3: row with summary wins
    if stats_a["has_summary"] and not stats_b["has_summary"]:
        return stats_a, stats_b, "A has summary, B does not"
    if stats_b["has_summary"] and not stats_a["has_summary"]:
        return stats_b, stats_a, "B has summary, A does not"

    # Rule 4: lower id wins (older row, presumably the original)
    if stats_a["id"] < stats_b["id"]:
        return stats_a, stats_b, f"tie on data; lower id wins ({stats_a['id']} < {stats_b['id']})"
    return stats_b, stats_a, f"tie on data; lower id wins ({stats_b['id']} < {stats_a['id']})"


def delete_doc(cur, doc_id):
    """Delete a document row. Cascades through all extraction tables."""
    cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DB_NAME, help=f"Database (default: {DB_NAME})")
    parser.add_argument("--apply", action="store_true",
                        help="Actually execute deletes (default: dry run)")
    args = parser.parse_args()

    conn = psycopg2.connect(dbname=args.db, host="localhost")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("=" * 78)
    print(f"  dedup_survey.py — {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"  Database: {args.db}")
    print("=" * 78)

    deletes_planned = []  # list of (doc_id, reason)

    # ─── Cross-collection orphans ──────────────────────────────────
    print("\n## Cross-collection orphans\n")
    for doc_id, reason in ORPHAN_DELETES:
        stats = get_doc_stats(cur, doc_id)
        if stats is None:
            print(f"  Doc {doc_id}: NOT FOUND in {args.db} — already deleted? Skipping.")
            continue
        print(f"  CANDIDATE FOR DELETE:")
        print(f"    {format_stats_line(stats)}")
        print(f"    Reason: {reason}")
        print()
        deletes_planned.append((doc_id, "orphan"))

    # ─── Exact-filename duplicates (discovered dynamically) ────────
    print("\n## Exact-filename duplicates\n")
    cur.execute("""
        SELECT file_name, array_agg(id ORDER BY id) AS ids
        FROM documents
        GROUP BY file_name
        HAVING COUNT(*) > 1
        ORDER BY file_name
    """)
    exact_groups = cur.fetchall()
    if not exact_groups:
        print("  None found.\n")
    for grp in exact_groups:
        ids = grp["ids"]
        print(f"  Group: {grp['file_name'][:80]}  ({len(ids)} rows)")
        # Fetch stats for every row in the group
        group_stats = [get_doc_stats(cur, i) for i in ids]
        for s in group_stats:
            print(f"    {format_stats_line(s)}")
        # Fold pick_winner across the group: start with first, compare to next,
        # keep winner, mark loser for delete; continue until one row stands.
        current_winner = group_stats[0]
        losers = []
        for challenger in group_stats[1:]:
            keep, drop, _reason = pick_winner(current_winner, challenger)
            current_winner = keep
            losers.append(drop)
        print(f"    KEEP   Doc {current_winner['id']}")
        for drop in losers:
            print(f"    DELETE Doc {drop['id']} ({drop['total_items']} items will cascade-delete)")
            deletes_planned.append(
                (drop['id'], f"exact-filename dup with Doc {current_winner['id']}")
            )
        print()

    # ─── Near-duplicate pairs ──────────────────────────────────────
    print("\n## Near-duplicate pairs (variant filenames)\n")
    for id_a, id_b, desc in DEDUP_PAIRS:
        print(f"  Pair: {desc}")
        stats_a = get_doc_stats(cur, id_a)
        stats_b = get_doc_stats(cur, id_b)
        if stats_a is None or stats_b is None:
            missing = id_a if stats_a is None else id_b
            print(f"    Doc {missing} NOT FOUND — already deleted? Skipping pair.")
            print()
            continue
        print(f"    A: {format_stats_line(stats_a)}")
        print(f"    B: {format_stats_line(stats_b)}")
        keep, drop, reason = pick_winner(stats_a, stats_b)
        print(f"    KEEP   Doc {keep['id']}")
        print(f"    DELETE Doc {drop['id']} ({drop['total_items']} items will cascade-delete)")
        print(f"    Reason: {reason}")
        print()
        deletes_planned.append((drop['id'], f"dedup pair with Doc {keep['id']}"))

    # ─── Summary ───────────────────────────────────────────────────
    print("=" * 78)
    print(f"\nTotal deletes planned: {len(deletes_planned)}")
    for doc_id, why in deletes_planned:
        print(f"  - Doc {doc_id} ({why})")

    if not deletes_planned:
        print("\nNothing to do. Exiting.")
        cur.close()
        conn.close()
        return

    if not args.apply:
        print("\nThis was a DRY RUN. No changes made.")
        print("Re-run with --apply to execute these deletes.")
        cur.close()
        conn.close()
        return

    # ─── Apply ─────────────────────────────────────────────────────
    print("\nExecuting deletes...")
    for doc_id, why in deletes_planned:
        delete_doc(cur, doc_id)
        print(f"  Deleted Doc {doc_id} ({why})")
    conn.commit()
    print(f"\nDone. {len(deletes_planned)} document(s) deleted (cascading "
          f"through all extraction tables).")

    # Sanity check: report the new doc count
    cur.execute("SELECT COUNT(*) AS n FROM documents")
    print(f"Remaining documents in {args.db}: {cur.fetchone()['n']}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
