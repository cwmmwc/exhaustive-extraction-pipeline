#!/usr/bin/env python3
"""
Entity Deduplication — Phase 1: Case Normalization + Title Stripping

WHAT THIS DOES:
  Merges entity records that differ only by:
    1. Letter case ("Frank Yarlott" vs "FRANK YARLOTT")
    2. Honorific/title prefix ("Mr. FRANK YARLOTT" vs "Frank Yarlott")
    3. Leading/trailing whitespace

  These are safe, mechanical merges — no fuzzy matching, no judgment calls.

HOW IT WORKS:
  1. For each entity type, compute a canonical name:
     - Strip whitespace
     - Lowercase
     - Remove leading titles (Mr., Mrs., Miss, Dr., Rev., Senator, Chairman,
       Chief, Hon., Col., Gen., Capt., Rep., Congressman, Commissioner)
  2. Group entities by (type, canonical_name)
  3. For groups with >1 entity, pick the "best" name as canonical:
     - Prefer the variant with the most document mentions
     - On ties, prefer mixed case over ALL CAPS, longer over shorter
  4. Merge mentions: reassign all mentions from duplicate entities to the
     canonical entity. If a mention already exists for that (entity, document)
     pair, concatenate the contexts.
  5. Delete the now-empty duplicate entity records.
  6. Log every merge to a JSON file for audit trail.

USAGE:
  python3 dedup_entities_phase1.py                    # dry run (default)
  python3 dedup_entities_phase1.py --execute          # actually merge
  python3 dedup_entities_phase1.py --db other_db      # different database
  python3 dedup_entities_phase1.py --types person org  # specific types only

OUTPUT:
  - Console summary of proposed/executed merges
  - dedup_phase1_log_YYYYMMDD_HHMMSS.json with full audit trail
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

# ─────────────────────────────────────────────────
# Title prefixes to strip (order matters: longer first)
# ─────────────────────────────────────────────────
TITLE_PATTERN = re.compile(
    r"^(commissioner|congressman|chairman|senator|general|colonel|captain|chief|miss|mrs?|dr|rev|hon|col|gen|capt|rep)\.?\s+",
    re.IGNORECASE,
)


def canonical_name(name: str) -> str:
    """Normalize a name for grouping: strip whitespace, lowercase, remove titles."""
    s = name.strip()
    s = s.lower()
    s = TITLE_PATTERN.sub("", s)
    s = s.strip()
    return s


def pick_best_variant(variants: list[dict]) -> dict:
    """
    Choose the best display name from a group of duplicates.

    Priority:
      1. Most document mentions (broadest coverage)
      2. Mixed case over ALL CAPS (more readable)
      3. Longer name over shorter (more specific)
    """
    def sort_key(v):
        name = v["name"]
        is_mixed_case = not name.isupper() and not name.islower()
        return (v["doc_count"], is_mixed_case, len(name))

    return max(variants, key=sort_key)


def get_connection(db_name: str):
    """Connect to local PostgreSQL or Cloud SQL."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        dbname=db_name,
        user=os.environ.get("USER", "cwm6W"),
        host="localhost",
    )


def find_duplicate_groups(conn, entity_types: list[str] | None = None) -> list[dict]:
    """
    Find all groups of entities that share the same (type, canonical_name).

    Returns a list of groups, each containing:
      - canonical: the normalized name
      - type: entity type
      - entities: list of {id, name, doc_count, context}
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    type_filter = ""
    params: list = []
    if entity_types:
        type_filter = "WHERE e.type = ANY(%s)"
        params = [entity_types]

    cur.execute(
        f"""
        SELECT e.id, e.name, e.type, e.context, e.acres, e.land_type,
               COUNT(DISTINCT m.document_id) AS doc_count
        FROM entities e
        LEFT JOIN mentions m ON m.entity_id = e.id
        {type_filter}
        GROUP BY e.id, e.name, e.type, e.context, e.acres, e.land_type
        ORDER BY e.type, e.name
        """,
        params or None,
    )

    # Group by (type, canonical)
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in cur:
        canon = canonical_name(row["name"])
        key = (row["type"], canon)
        entry = {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "context": row["context"],
            "acres": row["acres"],
            "land_type": row["land_type"],
            "doc_count": row["doc_count"],
        }
        groups.setdefault(key, []).append(entry)

    cur.close()

    # Only return groups with duplicates
    result = []
    for (etype, canon), entities in groups.items():
        if len(entities) > 1:
            result.append(
                {
                    "canonical": canon,
                    "type": etype,
                    "entities": entities,
                }
            )

    # Sort by total doc_count descending (most impactful merges first)
    result.sort(key=lambda g: sum(e["doc_count"] for e in g["entities"]), reverse=True)
    return result


def execute_merge(conn, group: dict, dry_run: bool) -> dict:
    """
    Merge a group of duplicate entities into one canonical entity.

    Returns a log entry documenting the merge.
    """
    best = pick_best_variant(group["entities"])
    canonical_id = best["id"]
    canonical_display = best["name"]
    duplicates = [e for e in group["entities"] if e["id"] != canonical_id]

    log_entry = {
        "canonical_name": canonical_display,
        "canonical_id": canonical_id,
        "canonical_doc_count": best["doc_count"],
        "type": group["type"],
        "normalized": group["canonical"],
        "merged_variants": [],
        "mentions_reassigned": 0,
        "mentions_consolidated": 0,
        "entities_deleted": 0,
    }

    if not duplicates:
        return log_entry

    cur = conn.cursor()

    for dup in duplicates:
        variant_log = {
            "id": dup["id"],
            "name": dup["name"],
            "doc_count": dup["doc_count"],
        }

        if not dry_run:
            # Get all mentions for this duplicate entity
            cur.execute(
                "SELECT id, document_id, context FROM mentions WHERE entity_id = %s",
                (dup["id"],),
            )
            dup_mentions = cur.fetchall()

            reassigned = 0
            consolidated = 0

            for mention_id, doc_id, mention_context in dup_mentions:
                # Check if canonical entity already has a mention for this document
                cur.execute(
                    "SELECT id, context FROM mentions WHERE entity_id = %s AND document_id = %s",
                    (canonical_id, doc_id),
                )
                existing = cur.fetchone()

                if existing:
                    # Consolidate: append context to existing mention
                    existing_id, existing_context = existing
                    if mention_context and mention_context.strip():
                        new_context = existing_context or ""
                        if new_context:
                            new_context += "; "
                        new_context += mention_context
                        cur.execute(
                            "UPDATE mentions SET context = %s WHERE id = %s",
                            (new_context, existing_id),
                        )
                    # Delete the duplicate mention
                    cur.execute("DELETE FROM mentions WHERE id = %s", (mention_id,))
                    consolidated += 1
                else:
                    # Reassign: point mention to canonical entity
                    cur.execute(
                        "UPDATE mentions SET entity_id = %s WHERE id = %s",
                        (canonical_id, mention_id),
                    )
                    reassigned += 1

            variant_log["mentions_reassigned"] = reassigned
            variant_log["mentions_consolidated"] = consolidated
            log_entry["mentions_reassigned"] += reassigned
            log_entry["mentions_consolidated"] += consolidated

            # Merge context from duplicate entity into canonical if useful
            if dup["context"] and dup["context"].strip():
                cur.execute("SELECT context FROM entities WHERE id = %s", (canonical_id,))
                canon_context = cur.fetchone()[0] or ""
                if dup["context"] not in canon_context:
                    updated = canon_context + ("; " if canon_context else "") + dup["context"]
                    cur.execute(
                        "UPDATE entities SET context = %s WHERE id = %s",
                        (updated, canonical_id),
                    )

            # Merge acres/land_type if canonical is missing them
            if dup["acres"] and not best.get("acres"):
                cur.execute(
                    "UPDATE entities SET acres = %s WHERE id = %s",
                    (dup["acres"], canonical_id),
                )
            if dup["land_type"] and not best.get("land_type"):
                cur.execute(
                    "UPDATE entities SET land_type = %s WHERE id = %s",
                    (dup["land_type"], canonical_id),
                )

            # Delete the duplicate entity (mentions already handled)
            cur.execute("DELETE FROM entities WHERE id = %s", (dup["id"],))
            log_entry["entities_deleted"] += 1

        log_entry["merged_variants"].append(variant_log)

    cur.close()
    return log_entry


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1 entity deduplication: case + title normalization"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform merges (default is dry run)",
    )
    parser.add_argument(
        "--db",
        default="crow_historical_docs",
        help="Database name (default: crow_historical_docs)",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        help="Entity types to dedup (default: all types)",
    )
    args = parser.parse_args()

    dry_run = not args.execute
    mode_label = "DRY RUN" if dry_run else "EXECUTING"

    print(f"{'=' * 60}")
    print(f"Entity Deduplication — Phase 1 ({mode_label})")
    print(f"Database: {args.db}")
    print(f"Types: {args.types or 'all'}")
    print(f"{'=' * 60}\n")

    conn = get_connection(args.db)

    # Find duplicate groups
    groups = find_duplicate_groups(conn, args.types)

    if not groups:
        print("No duplicates found. Nothing to do.")
        conn.close()
        return

    # Summary
    total_dupes = sum(len(g["entities"]) - 1 for g in groups)
    total_groups = len(groups)
    by_type: dict[str, int] = {}
    for g in groups:
        by_type[g["type"]] = by_type.get(g["type"], 0) + len(g["entities"]) - 1

    print(f"Found {total_groups} duplicate groups ({total_dupes} entities to merge):\n")
    for etype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {etype}: {count} duplicates")
    print()

    # Show top examples
    print("Top 10 groups by document coverage:\n")
    for g in groups[:10]:
        total_docs = sum(e["doc_count"] for e in g["entities"])
        best = pick_best_variant(g["entities"])
        others = [e["name"] for e in g["entities"] if e["id"] != best["id"]]
        print(f"  [{g['type']}] {best['name']} ({best['doc_count']} docs)")
        print(f"    merging: {', '.join(others)}")
        print()

    # Execute or report
    log_entries = []
    if not dry_run:
        print(f"Merging {total_dupes} duplicate entities...\n")

    for i, group in enumerate(groups):
        entry = execute_merge(conn, group, dry_run)
        log_entries.append(entry)

        if not dry_run and (i + 1) % 50 == 0:
            print(f"  ...processed {i + 1}/{total_groups} groups")

    if not dry_run:
        conn.commit()
        total_reassigned = sum(e["mentions_reassigned"] for e in log_entries)
        total_consolidated = sum(e["mentions_consolidated"] for e in log_entries)
        total_deleted = sum(e["entities_deleted"] for e in log_entries)
        print(f"\nDone.")
        print(f"  Entities deleted: {total_deleted}")
        print(f"  Mentions reassigned: {total_reassigned}")
        print(f"  Mentions consolidated (same doc): {total_consolidated}")

    conn.close()

    # Write audit log
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_filename = f"dedup_phase1_log_{timestamp}.json"
    log_path = os.path.join(os.path.dirname(__file__), log_filename)
    log_data = {
        "phase": 1,
        "description": "Case normalization + title stripping",
        "mode": "dry_run" if dry_run else "executed",
        "database": args.db,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "types_processed": args.types or "all",
        "summary": {
            "duplicate_groups": total_groups,
            "entities_merged": total_dupes,
            "by_type": by_type,
        },
        "merges": log_entries,
    }
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2, default=str)

    print(f"\nAudit log written to: {log_filename}")
    if dry_run:
        print(f"\nThis was a DRY RUN. To execute, run:")
        print(f"  python3 dedup_entities_phase1.py --execute")


if __name__ == "__main__":
    main()
