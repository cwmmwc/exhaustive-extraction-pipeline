#!/usr/bin/env python3
"""
Load Kimi K2.5 extraction JSON into the full_corpus_docs database
alongside Claude's extraction of the same document.

Creates a new document row with extraction_model='kimi-k2.5' and loads
all extracted entities, events, fee_patents, etc. linked to that document.

Usage:
    python3 load_kimi_extraction.py comparisons/single_20260325_090708_1921\ CCF\ 56074-21-312\ GS_chunked/kimi-k2.5.json
"""

import argparse
import json
import sys

import psycopg2


DB_NAME = "full_corpus_docs"

# Reference document (Claude's extraction) to copy metadata from
REFERENCE_DOC_ID = 2


def load_extraction(json_path: str, db_name: str = DB_NAME):
    conn = psycopg2.connect(dbname=db_name)
    cur = conn.cursor()

    # Load JSON
    with open(json_path) as f:
        data = json.load(f)

    # Get reference document metadata
    cur.execute("""
        SELECT file_name, display_title, summary, page_count, file_size,
               full_text, collection, subcollection, location, extracted_dates
        FROM documents WHERE id = %s
    """, (REFERENCE_DOC_ID,))
    ref = cur.fetchone()
    if not ref:
        print(f"Reference document {REFERENCE_DOC_ID} not found")
        sys.exit(1)

    (file_name, display_title, summary, page_count, file_size,
     full_text, collection, subcollection, location, extracted_dates) = ref

    # Create new document row for Kimi extraction
    # Use a distinct file_path to satisfy UNIQUE constraint
    kimi_file_path = f"kimi-k2.5/{file_name}"
    kimi_title = f"{display_title} [Kimi K2.5 extraction]"

    cur.execute("""
        INSERT INTO documents (file_name, display_title, summary, page_count, file_size,
                               full_text, collection, subcollection, location, extracted_dates,
                               extraction_model, pipeline_version, file_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (file_name, kimi_title, summary, page_count, file_size,
          full_text, collection, subcollection, location, extracted_dates,
          'kimi-k2.5', 'v3', kimi_file_path))
    doc_id = cur.fetchone()[0]
    print(f"Created document id={doc_id} (extraction_model=kimi-k2.5)")

    # Load entities + mentions (find-or-create to respect unique constraint)
    entity_count = 0
    new_entities = 0
    for ent in data.get("entities", []):
        name = ent.get("name", "")
        etype = ent.get("type", "")
        context = ent.get("context", "")
        if not name:
            continue
        # Try to find existing entity
        cur.execute("SELECT id FROM entities WHERE name = %s AND type = %s", (name, etype))
        row = cur.fetchone()
        if row:
            ent_id = row[0]
        else:
            cur.execute("""
                INSERT INTO entities (name, type, context)
                VALUES (%s, %s, %s) RETURNING id
            """, (name, etype, context))
            ent_id = cur.fetchone()[0]
            new_entities += 1
        cur.execute("""
            INSERT INTO mentions (entity_id, document_id, context)
            VALUES (%s, %s, %s)
            ON CONFLICT (entity_id, document_id) DO NOTHING
        """, (ent_id, doc_id, context))
        entity_count += 1

    # Load events
    event_count = 0
    for evt in data.get("events", []):
        cur.execute("""
            INSERT INTO events (document_id, type, date, location, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (doc_id, evt.get("type", ""), evt.get("date", ""),
              evt.get("location", ""), evt.get("description", "")))
        event_count += 1

    # Load financial transactions
    fin_count = 0
    for fin in data.get("financial_transactions", []):
        cur.execute("""
            INSERT INTO financial_transactions (document_id, type, amount, payer, payee, date, context)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (doc_id, fin.get("type", ""), fin.get("amount", ""),
              fin.get("payer", ""), fin.get("payee", ""),
              fin.get("date", ""), fin.get("description", "")))
        fin_count += 1

    # Load relationships
    rel_count = 0
    for rel in data.get("relationships", []):
        cur.execute("""
            INSERT INTO relationships (document_id, type, subject, object, context)
            VALUES (%s, %s, %s, %s, %s)
        """, (doc_id, rel.get("type", ""), rel.get("subject", ""),
              rel.get("object", ""), rel.get("context", "")))
        rel_count += 1

    # Load fee patents
    fp_count = 0
    for fp in data.get("fee_patents", []):
        allottee = fp.get("allottee_name", "") or "unknown"
        cur.execute("""
            INSERT INTO fee_patents (document_id, allottee, allotment_number, acreage,
                                     patent_date, patent_number, trust_to_fee_mechanism,
                                     subsequent_buyer, sale_price, attorney,
                                     mortgage_amount, context)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (doc_id, allottee, fp.get("allotment_number", ""),
              fp.get("acreage", ""), fp.get("patent_date", ""),
              fp.get("patent_number", ""), fp.get("mechanism", ""),
              fp.get("buyer", ""), fp.get("sale_price", ""),
              fp.get("attorney", ""), fp.get("mortgage", ""),
              fp.get("context", fp.get("description", ""))))
        fp_count += 1

    # Load correspondence
    corr_count = 0
    for corr in data.get("correspondence", []):
        sender = corr.get("sender", "") or "unknown"
        recipient = corr.get("recipient", "") or "unknown"
        cur.execute("""
            INSERT INTO correspondence (document_id, sender, sender_title, recipient,
                                        recipient_title, date, subject, action_requested, outcome)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (doc_id, sender, corr.get("sender_title", ""),
              recipient, corr.get("recipient_title", ""),
              corr.get("date", ""), corr.get("subject", ""),
              corr.get("action_requested", ""), corr.get("outcome", "")))
        corr_count += 1

    # Load legislative actions
    leg_count = 0
    for leg in data.get("legislative_actions", []):
        bill_number = leg.get("bill_number", "") or "unknown"
        cur.execute("""
            INSERT INTO legislative_actions (document_id, bill_number, sponsor,
                                             action_type, action_date, vote_count,
                                             committee, outcome)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (doc_id, bill_number, leg.get("sponsor", ""),
              leg.get("action_type", ""), leg.get("date", ""),
              leg.get("vote_count", ""), leg.get("committee", ""),
              leg.get("outcome", "")))
        leg_count += 1

    conn.commit()

    print(f"\nLoaded into document {doc_id}:")
    print(f"  Entities:               {entity_count}")
    print(f"  Events:                 {event_count}")
    print(f"  Financial transactions: {fin_count}")
    print(f"  Relationships:          {rel_count}")
    print(f"  Fee patents:            {fp_count}")
    print(f"  Correspondence:         {corr_count}")
    print(f"  Legislative actions:    {leg_count}")
    print(f"  Total:                  {entity_count + event_count + fin_count + rel_count + fp_count + corr_count + leg_count}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Kimi extraction into database")
    parser.add_argument("json_file", help="Path to Kimi K2.5 merged JSON")
    parser.add_argument("--db", default=DB_NAME, help=f"Database name (default: {DB_NAME})")
    args = parser.parse_args()
    load_extraction(args.json_file, args.db)
