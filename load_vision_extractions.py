#!/usr/bin/env python3
"""
Load vision-mode extractions (tables + standard types) into PostgreSQL.

Handles the 'tables' type from vision extraction by loading into
document_tables and table_rows, plus all standard v4 types.

Usage:
    python3 load_vision_extractions.py vision_taylor_tables/ vision_taylor_section5/ --collection "AIPRC Taylor Report"
    python3 load_vision_extractions.py vision_taylor_tables/ --db survey_of_conditions
    python3 load_vision_extractions.py vision_taylor_section5/ --force
"""

import argparse
import json
import os
import sys

import psycopg2

DB_NAME = "survey_of_conditions"
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
    """Find vision_merged.json or vision_batch_*.json in a directory."""
    merged = os.path.join(directory, "vision_merged.json")
    if os.path.exists(merged):
        return [merged]
    # Fall back to individual batch files
    import glob
    batches = sorted(glob.glob(os.path.join(directory, "vision_batch_*.json")))
    return batches


def load_vision_extraction(directory, db_name, collection, force=False):
    """Load a vision extraction directory into the database."""
    json_files = find_json_files(directory)
    if not json_files:
        print(f"  No JSON files found in {directory}")
        return None, "no files"

    # Merge all JSON files
    merged = {}
    for jf in json_files:
        with open(jf) as f:
            data = json.load(f)
        for key, val in data.items():
            if isinstance(val, list):
                merged.setdefault(key, []).extend(val)

    # Also load appendix if present
    appendix_dir = directory.rstrip("/") + "_appendix"
    if os.path.isdir(appendix_dir):
        appendix_files = find_json_files(appendix_dir)
        for jf in appendix_files:
            with open(jf) as f:
                data = json.load(f)
            for key, val in data.items():
                if isinstance(val, list):
                    merged.setdefault(key, []).extend(val)
        print(f"  (merged appendix from {appendix_dir})")

    # Derive document name from directory
    dir_name = os.path.basename(directory.rstrip("/"))
    # Strip "vision_" prefix for display
    display_name = dir_name.replace("vision_", "").replace("_", " ").title()

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
    """, (dir_name, display_name, directory, collection, "claude-sonnet-vision", "v4-vision"))
    doc_id = cur.fetchone()[0]

    counts = {}

    # --- Standard v4 types ---

    # Entities + mentions
    count = 0
    for ent in merged.get("entities", []):
        name = ent.get("name", "")
        etype = ent.get("type", "")
        context = ent.get("context", "")
        if not name:
            continue
        cur.execute("SELECT id FROM entities WHERE name = %s AND type = %s", (name, etype))
        row = cur.fetchone()
        if row:
            ent_id = row[0]
        else:
            cur.execute("INSERT INTO entities (name, type, context) VALUES (%s, %s, %s) RETURNING id",
                        (name, etype, context))
            ent_id = cur.fetchone()[0]
        cur.execute("""INSERT INTO mentions (entity_id, document_id, context)
                       VALUES (%s, %s, %s) ON CONFLICT (entity_id, document_id) DO NOTHING""",
                    (ent_id, doc_id, context))
        count += 1
    counts["entities"] = count

    # Events
    count = 0
    for evt in merged.get("events", []):
        cur.execute("INSERT INTO events (document_id, type, date, location, description) VALUES (%s,%s,%s,%s,%s)",
                    (doc_id, evt.get("type", ""), evt.get("date", ""), evt.get("location", ""), evt.get("description", "")))
        count += 1
    counts["events"] = count

    # Financial transactions
    count = 0
    for fin in merged.get("financial_transactions", []):
        cur.execute("""INSERT INTO financial_transactions (document_id, type, amount, payer, payee, date, context)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, fin.get("type", ""), fin.get("amount", ""), fin.get("payer", ""),
                     fin.get("payee", ""), fin.get("date", ""), fin.get("description", fin.get("context", ""))))
        count += 1
    counts["financial_transactions"] = count

    # Relationships
    count = 0
    for rel in merged.get("relationships", []):
        cur.execute("INSERT INTO relationships (document_id, type, subject, object, context) VALUES (%s,%s,%s,%s,%s)",
                    (doc_id, rel.get("type", ""), rel.get("subject", ""), rel.get("object", ""), rel.get("context", "")))
        count += 1
    counts["relationships"] = count

    # Fee patents
    count = 0
    for fp in merged.get("fee_patents", []):
        allottee = fp.get("allottee_name", fp.get("allottee", "")) or "unknown"
        cur.execute("""INSERT INTO fee_patents (document_id, allottee, allotment_number, acreage,
                       patent_date, patent_number, trust_to_fee_mechanism, subsequent_buyer,
                       sale_price, attorney, mortgage_amount, context)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, allottee, fp.get("allotment_number", ""), fp.get("acreage", ""),
                     fp.get("patent_date", ""), fp.get("patent_number", ""), fp.get("mechanism", ""),
                     fp.get("buyer", ""), fp.get("sale_price", ""), fp.get("attorney", ""),
                     fp.get("mortgage", ""), fp.get("context", fp.get("description", ""))))
        count += 1
    counts["fee_patents"] = count

    # Correspondence
    count = 0
    for corr in merged.get("correspondence", []):
        sender = corr.get("sender", "") or "unknown"
        recipient = corr.get("recipient", "") or "unknown"
        cur.execute("""INSERT INTO correspondence (document_id, sender, sender_title, recipient,
                       recipient_title, date, subject, action_requested, outcome)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, sender, corr.get("sender_title", ""), recipient,
                     corr.get("recipient_title", ""), corr.get("date", ""), corr.get("subject", ""),
                     corr.get("action_requested", ""), corr.get("outcome", "")))
        count += 1
    counts["correspondence"] = count

    # Legislative actions
    count = 0
    for leg in merged.get("legislative_actions", []):
        bill = leg.get("bill_number", "") or "unknown"
        action_type = leg.get("action_type", "") or "unknown"
        cur.execute("""INSERT INTO legislative_actions (document_id, bill_number, sponsor,
                       action_type, action_date, vote_count, committee, outcome)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, bill, leg.get("sponsor", ""), action_type,
                     leg.get("date", ""), leg.get("vote_count", ""),
                     leg.get("committee", ""), leg.get("outcome", "")))
        count += 1
    counts["legislative_actions"] = count

    # Testimony
    count = 0
    for test in merged.get("testimony", []):
        witness = test.get("witness", "") or "unknown"
        cur.execute("""INSERT INTO testimony (document_id, witness, witness_title, hearing,
                       committee, location, date, subject, key_claims, questioner)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, witness, test.get("witness_title", ""), test.get("hearing", ""),
                     test.get("committee", ""), test.get("location", ""), test.get("date", ""),
                     test.get("subject", ""), test.get("key_claims", ""), test.get("questioner", "")))
        count += 1
    counts["testimony"] = count

    # Taxes
    count = 0
    for tax in merged.get("taxes", []):
        cur.execute("""INSERT INTO taxes (document_id, taxpayer, land_description, tax_type,
                       amount, year, status, county, context)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, tax.get("taxpayer", ""), tax.get("land_description", ""),
                     tax.get("tax_type", ""), tax.get("amount", ""), tax.get("year", ""),
                     tax.get("status", ""), tax.get("county", ""), tax.get("context", "")))
        count += 1
    counts["taxes"] = count

    # Mortgages
    count = 0
    for mtg in merged.get("mortgages", []):
        cur.execute("""INSERT INTO mortgages (document_id, borrower, lender, amount,
                       land_description, acreage, date, interest_rate, status, context)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, mtg.get("borrower", ""), mtg.get("lender", ""), mtg.get("amount", ""),
                     mtg.get("land_description", ""), mtg.get("acreage", ""), mtg.get("date", ""),
                     mtg.get("interest_rate", ""), mtg.get("status", ""), mtg.get("context", "")))
        count += 1
    counts["mortgages"] = count

    # --- Tables (vision-specific) ---
    table_count = 0
    row_count = 0
    for tbl in merged.get("tables", []):
        title = tbl.get("title", "")
        columns = tbl.get("columns", [])
        rows = tbl.get("rows", [])

        cur.execute("""INSERT INTO document_tables (document_id, title, columns, row_data, row_count)
                       VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                    (doc_id, title, json.dumps(columns), json.dumps(rows), len(rows)))
        table_id = cur.fetchone()[0]
        table_count += 1

        # Flatten rows into table_rows for direct SQL querying
        for row in rows:
            # Try to extract common fields regardless of column naming
            area = (row.get("Area/Reservation or Tribe") or row.get("AREA/Reservation or Tribe")
                    or row.get("State & Tribe") or row.get("State") or "")
            acreage = (row.get("Acres") or row.get("Acreage") or row.get("Acreage*")
                       or row.get("Taken for public purposes (acres)") or "")
            cost = row.get("Cost", "")
            date = row.get("Date", "")
            project = row.get("Project", row.get("Project or Purpose", ""))
            citation = row.get("Citation", "")
            remarks = row.get("Remarks", row.get("Remarks (use of other, etc.)", ""))

            cur.execute("""INSERT INTO table_rows (document_id, table_id, table_title, row_data,
                           area_or_tribe, acreage, cost, date, project_or_purpose, citation, remarks)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (doc_id, table_id, title, json.dumps(row),
                         area, acreage, cost, date, project, citation, remarks))
            row_count += 1

    counts["tables"] = table_count
    counts["table_rows"] = row_count

    conn.commit()
    cur.close()
    conn.close()

    return doc_id, counts


def main():
    parser = argparse.ArgumentParser(description="Load vision extractions into PostgreSQL")
    parser.add_argument("directories", nargs="+", help="Vision extraction directories to load")
    parser.add_argument("--db", default=DB_NAME, help=f"Database name (default: {DB_NAME})")
    parser.add_argument("--collection", default="AIPRC Taylor Report",
                        help="Collection name for these documents")
    parser.add_argument("--force", action="store_true", help="Reload (delete and re-insert)")
    args = parser.parse_args()

    create_database(args.db)
    apply_schema(args.db, SCHEMA_FILE)

    print(f"\nLoading {len(args.directories)} extraction(s) into {args.db}...")
    print("=" * 60)

    loaded = 0
    skipped = 0
    total_counts = {}

    for directory in args.directories:
        directory = directory.rstrip("/")
        print(f"\n  {os.path.basename(directory)}:")

        doc_id, result = load_vision_extraction(directory, args.db, args.collection, force=args.force)

        if doc_id is None:
            skipped += 1
            print(f"    SKIP ({result})")
            continue

        loaded += 1
        total = sum(result.values())
        print(f"    Doc {doc_id}: {total} items loaded")
        for k, v in sorted(result.items()):
            if v > 0:
                print(f"      {k:<25} {v:>6}")

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
                print(f"  {k:<25} {v:>8}")
                grand_total += v
        print(f"  {'TOTAL':<25} {grand_total:>8}")
    print(f"\nDatabase: {args.db}")

    # Auto-generate summaries for newly loaded documents
    if loaded > 0:
        print(f"\nGenerating summaries for {loaded} document(s)...")
        import subprocess
        result = subprocess.run(
            ["python3", "enrich_summaries.py",
             "--db", args.db, "--from-extraction", "--model", "sonnet"],
            capture_output=False)
        if result.returncode != 0:
            print("Warning: summary generation had errors (summaries can be generated later)")


if __name__ == "__main__":
    main()
