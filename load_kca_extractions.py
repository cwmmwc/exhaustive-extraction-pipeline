#!/usr/bin/env python3
"""
Load KCA/Kiowa Kimi K2.5 v4 re-extractions into the historical_docs database,
replacing the old Claude Sonnet v3 extraction data.

Adds the v4 tables (testimony, taxes, mortgages) if they don't exist.
For each document, deletes old extraction data and loads the new v4 data.
Matches extraction directories to existing documents by file_name.

Usage:
    python3 load_kca_extractions.py                    # load all
    python3 load_kca_extractions.py --dry-run          # preview without changes
    python3 load_kca_extractions.py --dir /other/path  # different input dir
"""

import argparse
import glob
import json
import os
import sys

import psycopg2

DB_NAME = "historical_docs"
EXTRACTION_DIR = "kca_reextraction"

# Tables that have document_id and need to be cleared on re-extraction.
# Order matters: mentions first (FK to entities), then the rest.
TABLES_WITH_DOC_ID = [
    "mentions", "events", "financial_transactions", "financial_data",
    "relationships", "fee_patents", "correspondence", "legislative_actions",
    "testimony", "taxes", "mortgages",
]


def add_v4_tables(db_name):
    """Add testimony, taxes, mortgages tables if they don't exist."""
    conn = psycopg2.connect(dbname=db_name, host="localhost")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS testimony (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id),
            witness TEXT,
            witness_title TEXT,
            hearing TEXT,
            committee TEXT,
            location TEXT,
            date TEXT,
            subject TEXT,
            key_claims TEXT,
            questioner TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS taxes (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id),
            taxpayer TEXT,
            land_description TEXT,
            tax_type TEXT,
            amount TEXT,
            year TEXT,
            status TEXT,
            county TEXT,
            context TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS mortgages (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id),
            borrower TEXT,
            lender TEXT,
            amount TEXT,
            land_description TEXT,
            acreage TEXT,
            date TEXT,
            interest_rate TEXT,
            status TEXT,
            context TEXT
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("v4 tables ensured (testimony, taxes, mortgages)")


def clear_old_extraction(cur, conn, doc_id):
    """Delete all extraction data for a document."""
    total_deleted = 0
    for table in TABLES_WITH_DOC_ID:
        try:
            cur.execute(f"DELETE FROM {table} WHERE document_id = %s", [doc_id])
            n = cur.rowcount
            if n > 0:
                total_deleted += n
        except Exception:
            conn.rollback()
    return total_deleted


def load_one_document(json_path, db_name, dry_run=False):
    """Load a single extraction JSON, replacing old data for the matching document."""
    conn = psycopg2.connect(dbname=db_name, host="localhost")
    cur = conn.cursor()

    with open(json_path) as f:
        data = json.load(f)

    # Derive file_name from directory name
    doc_dir = os.path.basename(os.path.dirname(json_path))
    # The HPC extraction used the PDF basename (without .pdf) as directory name.
    # The database stores file_name with .pdf extension.
    file_name = doc_dir + ".pdf"

    # Find matching document in database
    cur.execute("SELECT id, file_name FROM documents WHERE file_name = %s", (file_name,))
    row = cur.fetchone()
    if not row:
        # Try without .pdf in case of mismatch
        cur.execute("SELECT id, file_name FROM documents WHERE file_name = %s", (doc_dir,))
        row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return None, f"no matching document for '{file_name}'"

    doc_id = row[0]

    if dry_run:
        total = sum(len(v) for v in data.values() if isinstance(v, list))
        cur.close()
        conn.close()
        return doc_id, f"would load {total} items (dry run)"

    # Clear old extraction data
    cleared = clear_old_extraction(cur, conn, doc_id)

    # Update document metadata
    cur.execute("""UPDATE documents SET extraction_model = 'kimi-k2.5', pipeline_version = 'v4'
                   WHERE id = %s""", [doc_id])

    counts = {}

    # Entities + mentions (this schema uses entities table + mentions junction)
    count = 0
    for ent in data.get("entities", []):
        name = ent.get("name", "")
        etype = ent.get("type", "")
        context = ent.get("context", "")
        if not name:
            continue
        cur.execute("SELECT id FROM entities WHERE name = %s AND type = %s", (name, etype))
        existing = cur.fetchone()
        if existing:
            ent_id = existing[0]
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

    # Testimony (v4 — new)
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

    # Taxes (v4 — new)
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

    # Mortgages (v4 — new)
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
    parser = argparse.ArgumentParser(description="Load KCA Kimi K2.5 v4 re-extractions into historical_docs")
    parser.add_argument("--db", default=DB_NAME, help=f"Database name (default: {DB_NAME})")
    parser.add_argument("--dir", default=EXTRACTION_DIR, help=f"Extraction directory (default: {EXTRACTION_DIR})")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be loaded without making changes")
    args = parser.parse_args()

    # Add v4 tables if needed
    if not args.dry_run:
        add_v4_tables(args.db)

    # Find all completed extractions
    candidates = (
        glob.glob(os.path.join(args.dir, "*/kimi-k2.5.json"))
        + glob.glob(os.path.join(args.dir, "*/Kimi K2.5.json"))
    )
    json_files = sorted(p for p in candidates if os.path.getsize(p) > 0)
    if not json_files:
        print(f"No extraction files found in {args.dir}/*/(kimi-k2.5.json | Kimi K2.5.json)")
        sys.exit(1)

    mode = "DRY RUN" if args.dry_run else "LOADING"
    print(f"\n{mode}: {len(json_files)} extractions into {args.db}")
    print("=" * 60)

    loaded = 0
    skipped = 0
    not_found = 0
    total_counts = {}

    for json_path in json_files:
        doc_dir = os.path.basename(os.path.dirname(json_path))

        doc_id, result = load_one_document(json_path, args.db, dry_run=args.dry_run)

        if doc_id is None:
            not_found += 1
            print(f"  SKIP: {doc_dir} ({result})")
            continue

        if args.dry_run:
            print(f"  Doc {doc_id}: {doc_dir} — {result}")
            loaded += 1
            continue

        loaded += 1
        total = sum(result.values())
        print(f"  [{loaded}] Doc {doc_id}: {doc_dir}")
        print(f"       {total} items: {result}")

        for k, v in result.items():
            total_counts[k] = total_counts.get(k, 0) + v

    print("\n" + "=" * 60)
    print(f"Loaded:    {loaded} documents")
    print(f"Not found: {not_found} documents (no matching doc in database)")
    if total_counts:
        print(f"\nTotals across all loaded documents:")
        grand_total = 0
        for k, v in sorted(total_counts.items()):
            print(f"  {k:<25} {v:>8}")
            grand_total += v
        print(f"  {'TOTAL':<25} {grand_total:>8}")


if __name__ == "__main__":
    main()
