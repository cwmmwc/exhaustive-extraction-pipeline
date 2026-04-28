#!/usr/bin/env python3
"""
Load index card (DOJ record slip) extractions into PostgreSQL.

Handles the record_slips, legal_cases, and persons types from --index-cards extraction.

Usage:
    python3 load_index_card_extractions.py vision_index_cards_full/
    python3 load_index_card_extractions.py vision_index_cards_full/ --db index_cards_db
    python3 load_index_card_extractions.py vision_index_cards_full/ --force
"""

import argparse
import glob
import json
import os
import sys

import psycopg2

DB_NAME = "index_cards"
SCHEMA_FILE = "schema_v4.sql"


def create_database(db_name):
    conn = psycopg2.connect(dbname="postgres", host="localhost")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{db_name}"')
        print(f"Created database: {db_name}")
    else:
        print(f"Database exists: {db_name}")
    cur.close()
    conn.close()


def apply_schema(db_name, schema_file):
    conn = psycopg2.connect(dbname=db_name, host="localhost")
    cur = conn.cursor()
    with open(schema_file) as f:
        cur.execute(f.read())
    conn.commit()
    cur.close()
    conn.close()
    print(f"Schema applied: {schema_file}")


def find_json_files(directory):
    merged = os.path.join(directory, "vision_merged.json")
    if os.path.exists(merged):
        return [merged]
    return sorted(glob.glob(os.path.join(directory, "vision_batch_*.json")))


def load_one_extraction(directory, db_name, collection, force=False):
    """Load a single index card extraction directory into the database."""
    json_files = find_json_files(directory)
    if not json_files:
        return None, "no files"

    # Merge all JSON files
    merged = {}
    for jf in json_files:
        with open(jf) as f:
            data = json.load(f)
        for key, val in data.items():
            if isinstance(val, list):
                merged.setdefault(key, []).extend(val)

    dir_name = os.path.basename(directory.rstrip("/"))
    display_name = dir_name.replace("_", " ")

    conn = psycopg2.connect(dbname=db_name, host="localhost")
    cur = conn.cursor()

    # Check if already loaded
    cur.execute("SELECT id FROM documents WHERE file_path = %s", (directory,))
    existing = cur.fetchone()
    if existing and not force:
        cur.close()
        conn.close()
        return None, "already loaded"
    if existing and force:
        cur.execute("DELETE FROM documents WHERE id = %s", (existing[0],))

    total_items = sum(len(v) for v in merged.values() if isinstance(v, list))

    # Insert document
    cur.execute("""
        INSERT INTO documents (file_name, display_title, file_path,
                               collection, extraction_model, pipeline_version)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (dir_name, display_name, directory, collection,
          "claude-sonnet-vision", "v4-index-cards"))
    doc_id = cur.fetchone()[0]

    counts = {}

    # Record slips
    count = 0
    for slip in merged.get("record_slips", []):
        cur.execute("""INSERT INTO record_slips (document_id, file_number, jurisdiction,
                       date, correspondent, correspondent_role, case_name, case_number,
                       named_individual, allottee_number, tribe_or_reservation, subject,
                       action_type, enclosures, routing_division, routing_date,
                       clerk_initials, processed_date)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, slip.get("file_number", ""),
                     slip.get("jurisdiction", ""),
                     slip.get("date", ""),
                     slip.get("correspondent", ""),
                     slip.get("correspondent_role", ""),
                     slip.get("case_name", ""),
                     slip.get("case_number", ""),
                     slip.get("allottee_name", slip.get("named_individual", "")),
                     slip.get("allottee_number", ""),
                     slip.get("tribe_or_reservation", ""),
                     slip.get("subject", ""),
                     slip.get("action_type", ""),
                     slip.get("enclosures", ""),
                     slip.get("routing_division", ""),
                     slip.get("routing_date", ""),
                     slip.get("clerk_initials", ""),
                     slip.get("processed_date", "")))
        count += 1
    counts["record_slips"] = count

    # Legal cases
    count = 0
    for case in merged.get("legal_cases", []):
        cur.execute("""INSERT INTO legal_cases (document_id, case_name, file_number,
                       jurisdiction, case_type, named_individual, allottee_number,
                       tribe_or_reservation, county)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, case.get("case_name", ""),
                     case.get("file_number", ""),
                     case.get("jurisdiction", ""),
                     case.get("case_type", ""),
                     case.get("allottee_name", case.get("named_individual", "")),
                     case.get("allottee_number", ""),
                     case.get("tribe_or_reservation", ""),
                     case.get("county", "")))
        count += 1
    counts["legal_cases"] = count

    # Persons → entities + mentions (reuse existing entity tables)
    count = 0
    new_ents = 0
    for person in merged.get("persons", []):
        name = person.get("name", "")
        if not name:
            continue
        etype = "person"
        context = f"{person.get('role', '')} ({person.get('tribe', '')})".strip(" ()")

        cur.execute("SELECT id FROM entities WHERE name = %s AND type = %s", (name, etype))
        row = cur.fetchone()
        if row:
            ent_id = row[0]
        else:
            cur.execute("INSERT INTO entities (name, type, context) VALUES (%s, %s, %s) RETURNING id",
                        (name, etype, context))
            ent_id = cur.fetchone()[0]
            new_ents += 1
        cur.execute("""INSERT INTO mentions (entity_id, document_id, context)
                       VALUES (%s, %s, %s) ON CONFLICT (entity_id, document_id) DO NOTHING""",
                    (ent_id, doc_id, context))
        count += 1
    counts["persons"] = count

    conn.commit()
    cur.close()
    conn.close()

    return doc_id, counts


def main():
    parser = argparse.ArgumentParser(description="Load index card extractions into PostgreSQL")
    parser.add_argument("directory", help="Directory containing extraction subdirectories")
    parser.add_argument("--db", default=DB_NAME, help=f"Database name (default: {DB_NAME})")
    parser.add_argument("--collection", default="NARA RG 60 DOJ Record Slips",
                        help="Collection name")
    parser.add_argument("--force", action="store_true", help="Reload (delete and re-insert)")
    args = parser.parse_args()

    create_database(args.db)
    apply_schema(args.db, SCHEMA_FILE)

    # Find all extraction subdirectories
    base = args.directory.rstrip("/")
    subdirs = sorted([
        os.path.join(base, d) for d in os.listdir(base)
        if os.path.isdir(os.path.join(base, d))
    ])

    if not subdirs:
        # Maybe it's a single extraction directory
        if find_json_files(base):
            subdirs = [base]
        else:
            print(f"No extraction directories found in {base}")
            sys.exit(1)

    print(f"\nLoading {len(subdirs)} extraction(s) into {args.db}...")
    print("=" * 60)

    loaded = 0
    skipped = 0
    total_counts = {}

    for directory in subdirs:
        dir_name = os.path.basename(directory)
        doc_id, result = load_one_extraction(directory, args.db, args.collection, force=args.force)

        if doc_id is None:
            skipped += 1
            print(f"  SKIP: {dir_name} ({result})")
            continue

        loaded += 1
        total = sum(result.values())
        print(f"  [{loaded}] Doc {doc_id}: {dir_name} — {total} items")
        for k, v in sorted(result.items()):
            if v > 0:
                print(f"        {k:<20} {v:>6}")

        for k, v in result.items():
            total_counts[k] = total_counts.get(k, 0) + v

    print("\n" + "=" * 60)
    print(f"Loaded:  {loaded} documents")
    print(f"Skipped: {skipped} documents")
    if total_counts:
        print(f"\nTotals:")
        grand_total = 0
        for k, v in sorted(total_counts.items()):
            if v > 0:
                print(f"  {k:<20} {v:>8}")
                grand_total += v
        print(f"  {'TOTAL':<20} {grand_total:>8}")
    print(f"\nDatabase: {args.db}")


if __name__ == "__main__":
    main()
