#!/usr/bin/env python3
"""
Load Survey of Conditions v4 extractions into PostgreSQL.

Creates the database if it doesn't exist, applies the v4 schema,
then loads all completed extraction JSONs from survey_of_conditions_extractions/.

Usage:
    python3 load_survey_extractions.py                          # load all
    python3 load_survey_extractions.py --db survey_test         # different db name
    python3 load_survey_extractions.py --dir /path/to/jsons     # different input dir
    python3 load_survey_extractions.py --force                  # reload all (delete existing)
"""

import argparse
import glob
import json
import os
import subprocess
import sys

import psycopg2

DB_NAME = "survey_of_conditions"
EXTRACTION_DIR = "survey_of_conditions_extractions"
SCHEMA_FILE = "schema_v4.sql"


def create_database(db_name):
    """Create the database if it doesn't exist."""
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
    """Apply the v4 schema to the database."""
    conn = psycopg2.connect(dbname=db_name, host="localhost")
    cur = conn.cursor()
    with open(schema_file) as f:
        cur.execute(f.read())
    conn.commit()
    cur.close()
    conn.close()
    print(f"Schema applied: {schema_file}")


def load_one_document(json_path, db_name, force=False):
    """Load a single extraction JSON into the database."""
    conn = psycopg2.connect(dbname=db_name, host="localhost")
    cur = conn.cursor()

    with open(json_path) as f:
        data = json.load(f)

    # Derive document name from directory
    doc_dir = os.path.basename(os.path.dirname(json_path))
    # Convert back from safe name: underscores to original chars
    file_name = doc_dir.replace("__", "; ").replace("_", " ") + ".pdf"

    # Check if already loaded
    cur.execute("SELECT id FROM documents WHERE file_path = %s", (json_path,))
    existing = cur.fetchone()
    if existing and not force:
        cur.close()
        conn.close()
        return None, "already loaded"
    if existing and force:
        cur.execute("DELETE FROM documents WHERE id = %s", (existing[0],))

    # Count items for display title
    total = sum(len(v) for v in data.values() if isinstance(v, list))

    # Insert document
    cur.execute("""
        INSERT INTO documents (file_name, display_title, file_path,
                               collection, extraction_model, pipeline_version)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (file_name, doc_dir.replace("__", "; ").replace("_", " "),
          json_path, "Survey of Conditions", "kimi-k2.5", "v4"))
    doc_id = cur.fetchone()[0]

    counts = {}

    # Entities + mentions
    count = 0
    new_ents = 0
    for ent in data.get("entities", []):
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
            new_ents += 1
        cur.execute("""INSERT INTO mentions (entity_id, document_id, context)
                       VALUES (%s, %s, %s) ON CONFLICT (entity_id, document_id) DO NOTHING""",
                    (ent_id, doc_id, context))
        count += 1
    counts["entities"] = count

    # Events
    count = 0
    for evt in data.get("events", []):
        cur.execute("INSERT INTO events (document_id, type, date, location, description) VALUES (%s,%s,%s,%s,%s)",
                    (doc_id, evt.get("type",""), evt.get("date",""), evt.get("location",""), evt.get("description","")))
        count += 1
    counts["events"] = count

    # Financial transactions
    count = 0
    for fin in data.get("financial_transactions", []):
        cur.execute("""INSERT INTO financial_transactions (document_id, type, amount, payer, payee, date, context)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, fin.get("type",""), fin.get("amount",""), fin.get("payer",""),
                     fin.get("payee",""), fin.get("date",""), fin.get("description", fin.get("context",""))))
        count += 1
    counts["financial_transactions"] = count

    # Relationships
    count = 0
    for rel in data.get("relationships", []):
        cur.execute("INSERT INTO relationships (document_id, type, subject, object, context) VALUES (%s,%s,%s,%s,%s)",
                    (doc_id, rel.get("type",""), rel.get("subject",""), rel.get("object",""), rel.get("context","")))
        count += 1
    counts["relationships"] = count

    # Fee patents
    count = 0
    for fp in data.get("fee_patents", []):
        allottee = fp.get("allottee_name", fp.get("allottee", "")) or "unknown"
        cur.execute("""INSERT INTO fee_patents (document_id, allottee, allotment_number, acreage,
                       patent_date, patent_number, trust_to_fee_mechanism, subsequent_buyer,
                       sale_price, attorney, mortgage_amount, context)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, allottee, fp.get("allotment_number",""), fp.get("acreage",""),
                     fp.get("patent_date",""), fp.get("patent_number",""), fp.get("mechanism",""),
                     fp.get("buyer",""), fp.get("sale_price",""), fp.get("attorney",""),
                     fp.get("mortgage",""), fp.get("context", fp.get("description",""))))
        count += 1
    counts["fee_patents"] = count

    # Correspondence
    count = 0
    for corr in data.get("correspondence", []):
        sender = corr.get("sender","") or "unknown"
        recipient = corr.get("recipient","") or "unknown"
        cur.execute("""INSERT INTO correspondence (document_id, sender, sender_title, recipient,
                       recipient_title, date, subject, action_requested, outcome)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, sender, corr.get("sender_title",""), recipient,
                     corr.get("recipient_title",""), corr.get("date",""), corr.get("subject",""),
                     corr.get("action_requested",""), corr.get("outcome","")))
        count += 1
    counts["correspondence"] = count

    # Legislative actions
    count = 0
    for leg in data.get("legislative_actions", []):
        bill = leg.get("bill_number","") or "unknown"
        action_type = leg.get("action_type","") or "unknown"
        cur.execute("""INSERT INTO legislative_actions (document_id, bill_number, sponsor,
                       action_type, action_date, vote_count, committee, outcome)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, bill, leg.get("sponsor",""), action_type,
                     leg.get("date",""), leg.get("vote_count",""),
                     leg.get("committee",""), leg.get("outcome","")))
        count += 1
    counts["legislative_actions"] = count

    # Testimony (v4)
    count = 0
    for test in data.get("testimony", []):
        witness = test.get("witness","") or "unknown"
        cur.execute("""INSERT INTO testimony (document_id, witness, witness_title, hearing,
                       committee, location, date, subject, key_claims, questioner)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, witness, test.get("witness_title",""), test.get("hearing",""),
                     test.get("committee",""), test.get("location",""), test.get("date",""),
                     test.get("subject",""), test.get("key_claims",""), test.get("questioner","")))
        count += 1
    counts["testimony"] = count

    # Taxes (v4)
    count = 0
    for tax in data.get("taxes", []):
        cur.execute("""INSERT INTO taxes (document_id, taxpayer, land_description, tax_type,
                       amount, year, status, county, context)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, tax.get("taxpayer",""), tax.get("land_description",""),
                     tax.get("tax_type",""), tax.get("amount",""), tax.get("year",""),
                     tax.get("status",""), tax.get("county",""), tax.get("context","")))
        count += 1
    counts["taxes"] = count

    # Mortgages (v4)
    count = 0
    for mtg in data.get("mortgages", []):
        cur.execute("""INSERT INTO mortgages (document_id, borrower, lender, amount,
                       land_description, acreage, date, interest_rate, status, context)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc_id, mtg.get("borrower",""), mtg.get("lender",""), mtg.get("amount",""),
                     mtg.get("land_description",""), mtg.get("acreage",""), mtg.get("date",""),
                     mtg.get("interest_rate",""), mtg.get("status",""), mtg.get("context","")))
        count += 1
    counts["mortgages"] = count

    conn.commit()
    cur.close()
    conn.close()

    return doc_id, counts


def main():
    parser = argparse.ArgumentParser(description="Load Survey of Conditions extractions into PostgreSQL")
    parser.add_argument("--db", default=DB_NAME, help=f"Database name (default: {DB_NAME})")
    parser.add_argument("--dir", default=EXTRACTION_DIR, help=f"Extraction directory (default: {EXTRACTION_DIR})")
    parser.add_argument("--force", action="store_true", help="Reload all documents (delete and re-insert)")
    args = parser.parse_args()

    # Create database and apply schema
    create_database(args.db)
    apply_schema(args.db, SCHEMA_FILE)

    # Find all completed extractions
    json_files = sorted(glob.glob(os.path.join(args.dir, "*/kimi-k2.5.json")))
    if not json_files:
        print(f"No extraction files found in {args.dir}/*/kimi-k2.5.json")
        sys.exit(1)

    print(f"\nLoading {len(json_files)} documents into {args.db}...")
    print("=" * 60)

    loaded = 0
    skipped = 0
    total_counts = {}

    for json_path in json_files:
        doc_dir = os.path.basename(os.path.dirname(json_path))
        doc_name = doc_dir.replace("__", "; ").replace("_", " ")

        doc_id, result = load_one_document(json_path, args.db, force=args.force)

        if doc_id is None:
            skipped += 1
            print(f"  SKIP: {doc_name} ({result})")
            continue

        loaded += 1
        total = sum(result.values())
        print(f"  [{loaded}] Doc {doc_id}: {doc_name}")
        print(f"       {total} items: {result}")

        for k, v in result.items():
            total_counts[k] = total_counts.get(k, 0) + v

    print("\n" + "=" * 60)
    print(f"Loaded:  {loaded} documents")
    print(f"Skipped: {skipped} documents (already loaded)")
    print(f"\nTotals across all loaded documents:")
    grand_total = 0
    for k, v in sorted(total_counts.items()):
        print(f"  {k:<25} {v:>8}")
        grand_total += v
    print(f"  {'TOTAL':<25} {grand_total:>8}")
    print(f"\nDatabase: {args.db}")


if __name__ == "__main__":
    main()
