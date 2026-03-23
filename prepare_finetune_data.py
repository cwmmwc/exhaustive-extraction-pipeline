#!/usr/bin/env python3
"""
Prepare fine-tuning data for Llama 3.3 70B extraction model.

Exports (document_text → extraction_json) pairs from the PostgreSQL database,
using Claude's existing extractions as training data.

Usage:
    # Export from Crow corpus (default)
    python3 prepare_finetune_data.py

    # Export from Kiowa corpus too
    python3 prepare_finetune_data.py --db historical_docs --output finetune_kiowa.jsonl

    # Limit to best examples (documents with most extractions)
    python3 prepare_finetune_data.py --min-items 20

    # Preview without writing
    python3 prepare_finetune_data.py --dry-run

    # Export and split into train/val
    python3 prepare_finetune_data.py --split 0.1
"""

import argparse
import json
import os
import random
import sys
from typing import Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras


def get_db_connection(db_name: str = "crow_historical_docs"):
    """Connect to the PostgreSQL database."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(dbname=db_name)


def build_extraction_prompt(chunk: str) -> str:
    """Build the base extraction prompt (no few-shot examples).
    This is what the fine-tuned model will receive at inference time."""
    return f"""Extract ALL structured information from this historical document text.
Return a single JSON object with these keys:

{{
  "entities": [
    {{"name": "...", "type": "person|organization|location|land_parcel|legal_case|legislation|acreage_holding", "context": "brief description"}}
  ],
  "events": [
    {{"type": "...", "date": "YYYY-MM-DD or partial", "location": "...", "description": "..."}}
  ],
  "financial_transactions": [
    {{"type": "sale|lease|payment|fee|other", "amount": "...", "payer": "...", "payee": "...", "date": "...", "description": "..."}}
  ],
  "relationships": [
    {{"subject": "...", "type": "represented|employed_by|sold_to|bought_from|related_to|...", "object": "...", "context": "..."}}
  ],
  "fee_patents": [
    {{"allottee_name": "...", "allotment_number": "...", "acreage": "...", "patent_date": "...", "patent_number": "...", "mechanism": "private_bill|administrative|application", "buyer": "...", "sale_price": "...", "attorney": "...", "mortgage": "..."}}
  ],
  "correspondence": [
    {{"sender": "...", "sender_title": "...", "recipient": "...", "recipient_title": "...", "date": "...", "subject": "...", "action_requested": "...", "outcome": "..."}}
  ],
  "legislative_actions": [
    {{"bill_number": "...", "sponsor": "...", "action_type": "introduced|reported|amended|passed|vetoed|enacted", "date": "...", "vote_count": "...", "committee": "...", "outcome": "..."}}
  ]
}}

Extract EVERY entity, event, transaction, relationship, fee patent, correspondence record, and legislative action mentioned. Be thorough — missing data is worse than extra data.

DOCUMENT TEXT:
{chunk}

Return ONLY valid JSON, no markdown fencing, no commentary:"""


def gather_extraction(cur, doc_id: int) -> Dict:
    """Reconstruct the extraction JSON from database tables for a given document."""
    extraction = {
        "entities": [],
        "events": [],
        "financial_transactions": [],
        "relationships": [],
        "fee_patents": [],
        "correspondence": [],
        "legislative_actions": [],
    }

    # Entities (via mentions junction table)
    cur.execute("""
        SELECT e.name, e.type, e.context
        FROM entities e
        JOIN mentions m ON e.id = m.entity_id
        WHERE m.document_id = %s
        ORDER BY e.name
    """, [doc_id])
    for name, etype, context in cur.fetchall():
        extraction["entities"].append({
            "name": name or "",
            "type": etype or "",
            "context": context or "",
        })

    # Events
    cur.execute("""
        SELECT type, date, location, description
        FROM events WHERE document_id = %s
        ORDER BY date, id
    """, [doc_id])
    for etype, date, location, desc in cur.fetchall():
        extraction["events"].append({
            "type": etype or "",
            "date": date or "",
            "location": location or "",
            "description": desc or "",
        })

    # Financial transactions
    # DB columns: amount, type, payer, payee, for_what, date, context
    # JSON keys: type, amount, payer, payee, date, description
    cur.execute("""
        SELECT type, amount, payer, payee, date,
               COALESCE(for_what, context, '') as description
        FROM financial_transactions WHERE document_id = %s
        ORDER BY date, id
    """, [doc_id])
    for ftype, amount, payer, payee, date, desc in cur.fetchall():
        extraction["financial_transactions"].append({
            "type": ftype or "",
            "amount": amount or "",
            "payer": payer or "",
            "payee": payee or "",
            "date": date or "",
            "description": desc or "",
        })

    # Relationships
    cur.execute("""
        SELECT subject, type, object, context
        FROM relationships WHERE document_id = %s
        ORDER BY subject, id
    """, [doc_id])
    for subj, rtype, obj, context in cur.fetchall():
        extraction["relationships"].append({
            "subject": subj or "",
            "type": rtype or "",
            "object": obj or "",
            "context": context or "",
        })

    # Fee patents
    # DB columns: allottee, allotment_number, acreage, patent_date, patent_number,
    #             trust_to_fee_mechanism, subsequent_buyer, sale_price, attorney,
    #             mortgage_amount
    # JSON keys: allottee_name, allotment_number, acreage, patent_date, patent_number,
    #            mechanism, buyer, sale_price, attorney, mortgage
    cur.execute("""
        SELECT allottee, allotment_number, acreage, patent_date, patent_number,
               trust_to_fee_mechanism, subsequent_buyer, sale_price, attorney,
               COALESCE(mortgage_amount, '') as mortgage
        FROM fee_patents WHERE document_id = %s
        ORDER BY allottee, id
    """, [doc_id])
    for row in cur.fetchall():
        extraction["fee_patents"].append({
            "allottee_name": row[0] or "",
            "allotment_number": row[1] or "",
            "acreage": row[2] or "",
            "patent_date": row[3] or "",
            "patent_number": row[4] or "",
            "mechanism": row[5] or "",
            "buyer": row[6] or "",
            "sale_price": row[7] or "",
            "attorney": row[8] or "",
            "mortgage": row[9] or "",
        })

    # Correspondence
    cur.execute("""
        SELECT sender, sender_title, recipient, recipient_title,
               date, subject, action_requested, outcome
        FROM correspondence WHERE document_id = %s
        ORDER BY date, id
    """, [doc_id])
    for row in cur.fetchall():
        extraction["correspondence"].append({
            "sender": row[0] or "",
            "sender_title": row[1] or "",
            "recipient": row[2] or "",
            "recipient_title": row[3] or "",
            "date": row[4] or "",
            "subject": row[5] or "",
            "action_requested": row[6] or "",
            "outcome": row[7] or "",
        })

    # Legislative actions
    # DB columns: bill_number, sponsor, action_type, action_date, vote_count, committee, outcome
    # JSON keys: bill_number, sponsor, action_type, date, vote_count, committee, outcome
    cur.execute("""
        SELECT bill_number, sponsor, action_type, action_date,
               vote_count, committee, outcome
        FROM legislative_actions WHERE document_id = %s
        ORDER BY action_date, id
    """, [doc_id])
    for row in cur.fetchall():
        extraction["legislative_actions"].append({
            "bill_number": row[0] or "",
            "sponsor": row[1] or "",
            "action_type": row[2] or "",
            "date": row[3] or "",
            "vote_count": row[4] or "",
            "committee": row[5] or "",
            "outcome": row[6] or "",
        })

    return extraction


def count_items(extraction: Dict) -> int:
    """Count total extracted items across all categories."""
    return sum(len(v) for v in extraction.values())


def export_training_pairs(
    db_name: str = "crow_historical_docs",
    min_items: int = 5,
    min_text_length: int = 5000,
    max_text_length: int = 40000,
) -> List[Dict]:
    """Export (document_chunk, extraction_json) training pairs from the database."""
    conn = get_db_connection(db_name)
    cur = conn.cursor()

    # Get all documents with sufficient text
    cur.execute("""
        SELECT id, display_title, file_name,
               SUBSTRING(full_text FROM 1 FOR %s) as chunk,
               LENGTH(full_text) as text_length
        FROM documents
        WHERE full_text IS NOT NULL
          AND LENGTH(full_text) > %s
        ORDER BY id
    """, [max_text_length, min_text_length])

    rows = cur.fetchall()
    print(f"Found {len(rows)} documents with >{min_text_length} chars in {db_name}")

    pairs = []
    skipped_empty = 0
    skipped_few = 0

    for doc_id, display_title, file_name, chunk, text_length in rows:
        title = display_title or file_name or f"doc_{doc_id}"
        extraction = gather_extraction(cur, doc_id)
        item_count = count_items(extraction)

        if item_count == 0:
            skipped_empty += 1
            continue
        if item_count < min_items:
            skipped_few += 1
            continue

        # Build the prompt (same prompt the model will see at inference)
        prompt = build_extraction_prompt(chunk)
        completion = json.dumps(extraction)

        # Validate the completion is valid JSON
        try:
            json.loads(completion)
        except json.JSONDecodeError:
            print(f"  WARNING: Invalid JSON for doc {doc_id} ({title}), skipping")
            continue

        pairs.append({
            "doc_id": doc_id,
            "title": title,
            "text_length": text_length,
            "item_count": item_count,
            "prompt": prompt,
            "completion": completion,
        })

    cur.close()
    conn.close()

    print(f"  Exported: {len(pairs)} training pairs")
    print(f"  Skipped (no extractions): {skipped_empty}")
    print(f"  Skipped (<{min_items} items): {skipped_few}")

    return pairs


def write_jsonl(pairs: List[Dict], output_file: str):
    """Write training pairs in OpenAI/Together AI chat JSONL format."""
    with open(output_file, 'w') as f:
        for pair in pairs:
            entry = {
                "messages": [
                    {"role": "user", "content": pair["prompt"]},
                    {"role": "assistant", "content": pair["completion"]},
                ]
            }
            f.write(json.dumps(entry) + '\n')
    print(f"Wrote {len(pairs)} examples to {output_file}")


def print_stats(pairs: List[Dict]):
    """Print statistics about the training data."""
    if not pairs:
        print("No training pairs to report on.")
        return

    item_counts = [p["item_count"] for p in pairs]
    text_lengths = [p["text_length"] for p in pairs]
    completion_lengths = [len(p["completion"]) for p in pairs]

    print(f"\n{'='*60}")
    print(f"Training Data Statistics")
    print(f"{'='*60}")
    print(f"  Total examples:     {len(pairs)}")
    print(f"  Item counts:        min={min(item_counts)}, "
          f"median={sorted(item_counts)[len(item_counts)//2]}, "
          f"max={max(item_counts)}, "
          f"mean={sum(item_counts)/len(item_counts):.0f}")
    print(f"  Document lengths:   min={min(text_lengths):,}, "
          f"median={sorted(text_lengths)[len(text_lengths)//2]:,}, "
          f"max={max(text_lengths):,}")
    print(f"  Completion chars:   min={min(completion_lengths):,}, "
          f"median={sorted(completion_lengths)[len(completion_lengths)//2]:,}, "
          f"max={max(completion_lengths):,}")

    # Estimate token counts (rough: 1 token ≈ 4 chars)
    total_prompt_chars = sum(len(p["prompt"]) for p in pairs)
    total_completion_chars = sum(completion_lengths)
    total_tokens_est = (total_prompt_chars + total_completion_chars) / 4
    print(f"  Estimated total tokens: ~{int(total_tokens_est):,}")
    print(f"  Estimated training cost (Together AI, 3 epochs): "
          f"~${total_tokens_est * 3 / 1_000_000 * 5:.2f}")

    # Category breakdown
    categories = ["entities", "events", "financial_transactions",
                   "relationships", "fee_patents", "correspondence",
                   "legislative_actions"]
    print(f"\n  Category totals across all examples:")
    for cat in categories:
        total = sum(len(json.loads(p["completion"]).get(cat, [])) for p in pairs)
        print(f"    {cat:30s} {total:,}")


def main():
    parser = argparse.ArgumentParser(
        description="Export fine-tuning data from extraction database"
    )
    parser.add_argument("--db", default="crow_historical_docs",
                        help="Database name (default: crow_historical_docs)")
    parser.add_argument("--output", default="finetune_data.jsonl",
                        help="Output JSONL file (default: finetune_data.jsonl)")
    parser.add_argument("--min-items", type=int, default=5,
                        help="Minimum extracted items per document (default: 5)")
    parser.add_argument("--min-text", type=int, default=5000,
                        help="Minimum document text length in chars (default: 5000)")
    parser.add_argument("--split", type=float, default=None,
                        help="Validation split ratio (e.g., 0.1 for 90/10 train/val)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for split (default: 42)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print statistics without writing files")
    parser.add_argument("--top-n", type=int, default=None,
                        help="Only use the top N documents by extraction count")
    args = parser.parse_args()

    print(f"Exporting training data from {args.db}...")
    pairs = export_training_pairs(
        db_name=args.db,
        min_items=args.min_items,
        min_text_length=args.min_text,
    )

    if not pairs:
        print("No training pairs found. Check database and filters.")
        sys.exit(1)

    # Sort by item count descending (richest examples first)
    pairs.sort(key=lambda p: p["item_count"], reverse=True)

    # Filter out documents where completions are too large for training
    # (these are multi-chunk documents where DB has extractions from all chunks)
    max_completion_chars = 100_000  # ~25K tokens — reasonable training completion
    before = len(pairs)
    pairs = [p for p in pairs if len(p["completion"]) <= max_completion_chars]
    if len(pairs) < before:
        print(f"  Filtered out {before - len(pairs)} documents with oversized completions "
              f"(>{max_completion_chars:,} chars)")

    if args.top_n:
        pairs = pairs[:args.top_n]
        print(f"  Using top {args.top_n} documents by extraction count")

    print_stats(pairs)

    if args.dry_run:
        print("\nDry run — no files written.")
        # Show top 10 examples
        print(f"\nTop 10 documents by extraction count:")
        for p in pairs[:10]:
            print(f"  [{p['doc_id']:>4d}] {p['item_count']:>4d} items  "
                  f"{p['text_length']:>6,} chars  {p['title'][:60]}")
        return

    # Shuffle before splitting (but after top-n selection)
    random.seed(args.seed)
    random.shuffle(pairs)

    if args.split:
        split_point = int(len(pairs) * (1 - args.split))
        train_pairs = pairs[:split_point]
        val_pairs = pairs[split_point:]

        train_file = args.output.replace('.jsonl', '_train.jsonl')
        val_file = args.output.replace('.jsonl', '_val.jsonl')

        write_jsonl(train_pairs, train_file)
        write_jsonl(val_pairs, val_file)
        print(f"\nSplit: {len(train_pairs)} train, {len(val_pairs)} validation")
    else:
        write_jsonl(pairs, args.output)

    print("\nNext steps:")
    print("  1. Review a few examples:  head -1 finetune_data.jsonl | python3 -m json.tool")
    print("  2. Upload to Together AI:  together files upload finetune_data.jsonl")
    print("  3. Start fine-tuning:      together fine-tuning create \\")
    print("       --training-file <file-id> \\")
    print("       --model meta-llama/Llama-3.3-70B-Instruct-Turbo \\")
    print("       --n-epochs 3 --suffix crow-extraction-v1")


if __name__ == "__main__":
    main()
