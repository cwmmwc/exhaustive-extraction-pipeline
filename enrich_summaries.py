#!/usr/bin/env python3
"""
Document Summary Enrichment — Generate Analytical Summaries for Corpus-Wide Synthesis

WHAT THIS DOES:
  Sends each document's full text to Claude Opus and stores a structured analytical
  summary (~200-350 words) capturing document type, key parties, dates, claims,
  legal mechanisms, land/money specifics, and evidentiary value.

  These summaries enable the analysis interface to synthesize across the ENTIRE corpus
  in a single API call, bypassing the context window limits that restrict raw text
  approaches to ~15 documents per query.

WHY:
  345 summaries × ~300 words ≈ 100K tokens — fits in one Opus call.
  345 full documents × ~50K words each = impossible in any context window.
  Summaries are the bridge between exhaustive extraction and corpus-wide reasoning.

USAGE:
  python3 enrich_summaries.py                    # summarize all unsummarized docs
  python3 enrich_summaries.py --limit 5          # test on 5 documents first
  python3 enrich_summaries.py --force            # re-summarize all documents
  python3 enrich_summaries.py --batch            # use Batch API (50% cost savings)
  python3 enrich_summaries.py --batch --force    # re-summarize all via Batch API
  python3 enrich_summaries.py --db other_db      # different database

REQUIREMENTS:
  ANTHROPIC_API_KEY environment variable must be set.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

MODEL = "claude-opus-4-6"
MAX_INPUT_TOKENS = 180000  # leave room for prompt + response in 200K window
CHARS_PER_TOKEN = 3.2

SUMMARY_PROMPT = """You are analyzing a historical document from an archival collection about Native American land dispossession, the Crow Reservation, federal Indian policy, and Bureau of Indian Affairs records.

Document: {file_name}
Collection: {collection}

Begin with a date line in this exact format: "DATE RANGE: [earliest year]–[latest year]" (or "DATE RANGE: undated" if no dates are discernible). Then write a dense analytical summary in 150-250 words. No headers or bullet points — write in plain prose paragraphs. Cover: document type and purpose; author, recipient, date; specific claims, actions, or decisions (names, amounts, acreages); legal mechanisms invoked (statutes, policies, administrative procedures); and what it proves about land dispossession.

Prioritize specifics over generalities. Include dollar amounts, acreages, allotment numbers, and legal citations when present. If the OCR is poor or the document fragmentary, note that briefly.

DOCUMENT TEXT:
{full_text}"""

SUMMARY_PROMPT_FROM_EXTRACTION = """You are analyzing a historical document from an archival collection about Native American land dispossession, federal Indian policy, and Bureau of Indian Affairs records. Instead of the raw document text, you have the structured data extracted from it by an AI model — every entity, event, financial transaction, relationship, fee patent, correspondence record, legislative action, testimony, tax record, and mortgage that was identified.

Document: {file_name}

Begin with a date line in this exact format: "DATE RANGE: [earliest year]–[latest year]" (or "DATE RANGE: undated" if no dates are discernible). Then write a dense analytical summary in 200-350 words. No headers or bullet points — write in plain prose paragraphs. Cover: document type and purpose; key individuals and organizations; specific claims, actions, or decisions (names, amounts, acreages); legal mechanisms invoked (statutes, policies, administrative procedures); tribes and locations involved; and what it reveals about land dispossession.

Prioritize specifics over generalities. Include dollar amounts, acreages, allotment numbers, and legal citations when present. Use the testimony records to identify who testified and what they claimed. Use the fee patents to identify patterns of dispossession. Use the financial transactions and tax records to trace the economic mechanisms.

EXTRACTION SUMMARY:
{item_counts}

KEY FEE PATENTS (sample of up to 50):
{fee_patents}

KEY TESTIMONY (sample of up to 30):
{testimony}

KEY CORRESPONDENCE (sample of up to 30):
{correspondence}

KEY LEGISLATIVE ACTIONS (all):
{legislative_actions}

KEY FINANCIAL TRANSACTIONS (sample of up to 30):
{financial_transactions}

KEY TAX RECORDS (sample of up to 30):
{taxes}

KEY MORTGAGES (sample of up to 20):
{mortgages}

KEY ENTITIES — PERSONS (sample of up to 50):
{person_entities}

KEY EVENTS (sample of up to 30):
{events}"""


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


def truncate_text(text: str, max_tokens: int) -> tuple[str, bool]:
    """Truncate text to approximate token limit."""
    estimated = int(len(text) / CHARS_PER_TOKEN)
    if estimated <= max_tokens:
        return text, False
    max_chars = int(max_tokens * CHARS_PER_TOKEN)
    return text[:max_chars] + "\n\n[... DOCUMENT TRUNCATED ...]", True


def get_documents(conn, force: bool = False, limit: int | None = None,
                   from_extraction: bool = False) -> list[dict]:
    """Get documents that need summaries."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if from_extraction:
        # For extraction-based summaries, we don't need full_text
        where = "WHERE 1=1"
    else:
        where = "WHERE d.full_text IS NOT NULL AND d.full_text != ''"
    if not force:
        where += " AND d.summary IS NULL"
    query = f"""
        SELECT d.id, d.file_name, d.display_title, d.collection,
               {'d.full_text, ' if not from_extraction else ''}
               LENGTH(COALESCE(d.full_text, '')) as text_length
        FROM documents d
        {where}
        ORDER BY d.file_name
    """
    if limit:
        query += f" LIMIT {limit}"
    cur.execute(query)
    results = [dict(row) for row in cur.fetchall()]
    cur.close()
    return results


def _spread_sample(records: list[dict], n: int,
                    richness_fields: list[str] | None = None) -> list[dict]:
    """Sample n records spread evenly across the list (i.e., across the document).

    If richness_fields is provided, prioritize records that have more of those
    fields populated, while still maintaining spread. Strategy: score each record
    by how many richness_fields are non-empty, then take the top-scored records
    from evenly-spaced segments of the list.
    """
    if len(records) <= n:
        return records

    if richness_fields:
        # Score each record by how many richness fields are populated
        for r in records:
            r['_richness'] = sum(
                1 for f in richness_fields
                if r.get(f) and str(r.get(f, '')).strip()
                and str(r.get(f, '')).lower() not in ('unknown', 'n/a', 'none', 'not specified')
            )

        # Divide into n segments, pick the richest record from each
        segment_size = len(records) / n
        sampled = []
        for i in range(n):
            start = int(i * segment_size)
            end = int((i + 1) * segment_size)
            segment = records[start:end]
            if segment:
                best = max(segment, key=lambda r: r.get('_richness', 0))
                sampled.append(best)

        # Clean up the temporary scoring field
        for r in sampled:
            r.pop('_richness', None)
        for r in records:
            r.pop('_richness', None)
        return sampled
    else:
        # Simple evenly-spaced sampling
        step = len(records) / n
        return [records[int(i * step)] for i in range(n)]


def get_extraction_data(conn, doc_id: int) -> dict:
    """Pull structured extraction data for a document to use in summary generation."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    data = {}

    # Item counts
    counts = {}
    for table in ['entities', 'events', 'financial_transactions', 'relationships',
                  'fee_patents', 'correspondence', 'legislative_actions',
                  'testimony', 'taxes', 'mortgages']:
        try:
            cur.execute(f"SELECT count(*) as cnt FROM {table} WHERE document_id = %s", (doc_id,))
            counts[table] = cur.fetchone()['cnt']
        except Exception:
            counts[table] = 0
            conn.rollback()
    data['counts'] = counts

    # Fee patents — spread across document using evenly-spaced sampling
    # Prioritize records with the most populated fields
    try:
        cur.execute("""SELECT allottee_name, allotment_number, acreage, patent_date,
                              mechanism, buyer, sale_price, attorney, id
                       FROM fee_patents WHERE document_id = %s
                       ORDER BY id""", (doc_id,))
        all_fps = [dict(r) for r in cur.fetchall()]
        data['fee_patents'] = _spread_sample(all_fps, 75, richness_fields=[
            'acreage', 'sale_price', 'buyer', 'patent_date', 'mechanism'])
    except Exception:
        data['fee_patents'] = []
        conn.rollback()

    # Testimony — prioritize records with longest key_claims
    try:
        cur.execute("""SELECT witness, witness_title, hearing, location, date,
                              subject, key_claims, id
                       FROM testimony WHERE document_id = %s
                       ORDER BY LENGTH(COALESCE(key_claims, '')) DESC""", (doc_id,))
        data['testimony'] = [dict(r) for r in cur.fetchall()[:50]]
    except Exception:
        data['testimony'] = []
        conn.rollback()

    # Correspondence — spread across document
    try:
        cur.execute("""SELECT sender, sender_title, recipient, recipient_title,
                              date, subject, action_requested, outcome, id
                       FROM correspondence WHERE document_id = %s
                       ORDER BY id""", (doc_id,))
        all_corr = [dict(r) for r in cur.fetchall()]
        data['correspondence'] = _spread_sample(all_corr, 40)
    except Exception:
        data['correspondence'] = []
        conn.rollback()

    # Legislative actions (all — these are high-value and usually not too many)
    try:
        cur.execute("""SELECT bill_number, sponsor, action_type, date,
                              committee, outcome
                       FROM legislative_actions WHERE document_id = %s""", (doc_id,))
        data['legislative_actions'] = [dict(r) for r in cur.fetchall()]
    except Exception:
        data['legislative_actions'] = []
        conn.rollback()

    # Financial transactions — spread across document, prioritize ones with amounts
    try:
        cur.execute("""SELECT type, amount, payer, payee, date, description, id
                       FROM financial_transactions WHERE document_id = %s
                       ORDER BY id""", (doc_id,))
        all_ft = [dict(r) for r in cur.fetchall()]
        data['financial_transactions'] = _spread_sample(all_ft, 40, richness_fields=['amount', 'payer', 'payee'])
    except Exception:
        data['financial_transactions'] = []
        conn.rollback()

    # Taxes — spread across document
    try:
        cur.execute("""SELECT taxpayer, land_description, tax_type, amount,
                              year, status, county, context, id
                       FROM taxes WHERE document_id = %s
                       ORDER BY id""", (doc_id,))
        all_taxes = [dict(r) for r in cur.fetchall()]
        data['taxes'] = _spread_sample(all_taxes, 40)
    except Exception:
        data['taxes'] = []
        conn.rollback()

    # Mortgages (all — usually not too many)
    try:
        cur.execute("""SELECT borrower, lender, amount, land_description,
                              acreage, date, interest_rate, status, context
                       FROM mortgages WHERE document_id = %s""", (doc_id,))
        data['mortgages'] = [dict(r) for r in cur.fetchall()]
    except Exception:
        data['mortgages'] = []
        conn.rollback()

    # Person entities — get distinct names, prioritize those with longest context
    try:
        cur.execute("""SELECT DISTINCT ON (name) name, type, context
                       FROM entities WHERE document_id = %s AND type = 'person'
                       ORDER BY name, LENGTH(COALESCE(context, '')) DESC""", (doc_id,))
        all_persons = [dict(r) for r in cur.fetchall()]
        data['person_entities'] = _spread_sample(all_persons, 60)
    except Exception:
        data['person_entities'] = []
        conn.rollback()

    # Events — spread across document, prioritize ones with dates
    try:
        cur.execute("""SELECT type, date, location, description, id
                       FROM events WHERE document_id = %s
                       ORDER BY id""", (doc_id,))
        all_events = [dict(r) for r in cur.fetchall()]
        data['events'] = _spread_sample(all_events, 40, richness_fields=['date', 'location'])
    except Exception:
        data['events'] = []
        conn.rollback()

    cur.close()
    return data


def generate_summary_from_extraction(client, doc: dict,
                                      extraction: dict, use_kimi: bool = False) -> str | None:
    """Generate a summary from structured extraction data instead of raw text."""
    import json

    display_name = doc.get("display_title") or doc["file_name"]
    counts = extraction['counts']
    item_counts = "\n".join(f"  {k}: {v}" for k, v in counts.items() if v > 0)
    total = sum(counts.values())
    item_counts = f"Total items: {total}\n" + item_counts

    def fmt(records):
        if not records:
            return "(none)"
        return json.dumps(records, indent=1, default=str)[:20000]

    prompt = SUMMARY_PROMPT_FROM_EXTRACTION.format(
        file_name=display_name,
        item_counts=item_counts,
        fee_patents=fmt(extraction['fee_patents']),
        testimony=fmt(extraction['testimony']),
        correspondence=fmt(extraction['correspondence']),
        legislative_actions=fmt(extraction['legislative_actions']),
        financial_transactions=fmt(extraction['financial_transactions']),
        taxes=fmt(extraction['taxes']),
        mortgages=fmt(extraction['mortgages']),
        person_entities=fmt(extraction['person_entities']),
        events=fmt(extraction['events']),
    )

    log.info(f"  Extraction-based prompt: ~{int(len(prompt) / CHARS_PER_TOKEN):,} tokens")

    if use_kimi:
        response = client.chat.completions.create(
            model="moonshotai/Kimi-K2.5",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.2,
        )
        return response.choices[0].message.content
    else:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


def generate_summary(client: anthropic.Anthropic, doc: dict) -> str | None:
    """Generate an analytical summary for a single document."""
    full_text = doc.get("full_text", "")
    if not full_text or len(full_text.strip()) < 100:
        return None

    # Reserve tokens for the prompt template and response
    prompt_overhead = 1000  # tokens for the template text
    max_text_tokens = MAX_INPUT_TOKENS - prompt_overhead
    text, was_truncated = truncate_text(full_text, max_text_tokens)

    if was_truncated:
        log.warning(
            f"  Truncated {doc['file_name']} from "
            f"~{int(len(full_text) / CHARS_PER_TOKEN):,} to ~{max_text_tokens:,} tokens"
        )

    display_name = doc.get("display_title") or doc["file_name"]
    prompt = SUMMARY_PROMPT.format(
        file_name=display_name,
        collection=doc.get("collection") or "n/a",
        full_text=text,
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def store_summary(conn, doc_id: int, summary: str):
    """Store summary in the database."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE documents SET summary = %s, summary_date = %s WHERE id = %s",
        (summary, datetime.now(timezone.utc), doc_id),
    )
    conn.commit()
    cur.close()


def build_batch_request(doc: dict) -> Request | None:
    """Build a Batch API request for a single document."""
    full_text = doc.get("full_text", "")
    if not full_text or len(full_text.strip()) < 100:
        return None

    prompt_overhead = 1000
    max_text_tokens = MAX_INPUT_TOKENS - prompt_overhead
    text, was_truncated = truncate_text(full_text, max_text_tokens)

    if was_truncated:
        log.warning(
            f"  Truncated {doc['file_name']} from "
            f"~{int(len(full_text) / CHARS_PER_TOKEN):,} to ~{max_text_tokens:,} tokens"
        )

    display_name = doc.get("display_title") or doc["file_name"]
    prompt = SUMMARY_PROMPT.format(
        file_name=display_name,
        collection=doc.get("collection") or "n/a",
        full_text=text,
    )

    return Request(
        custom_id=f"doc-{doc['id']}",
        params=MessageCreateParamsNonStreaming(
            model=MODEL,
            max_tokens=1000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        ),
    )


def run_batch(client: anthropic.Anthropic, conn, docs: list[dict]):
    """Submit all documents as a Batch API request and poll for results."""
    # Build requests
    requests = []
    doc_map = {}  # custom_id -> doc dict
    skipped = 0

    for doc in docs:
        req = build_batch_request(doc)
        if req:
            requests.append(req)
            doc_map[f"doc-{doc['id']}"] = doc
        else:
            skipped += 1
            display_name = doc.get("display_title") or doc["file_name"]
            log.warning(f"  Skipped (too short): {display_name}")

    if not requests:
        log.info("No valid requests to batch.")
        return

    log.info(f"Submitting batch of {len(requests)} requests ({skipped} skipped)...")

    # Submit batch
    message_batch = client.messages.batches.create(requests=requests)
    batch_id = message_batch.id
    log.info(f"Batch created: {batch_id}")
    log.info(f"Status: {message_batch.processing_status}")

    # Poll for completion
    poll_interval = 30  # seconds
    while True:
        message_batch = client.messages.batches.retrieve(batch_id)
        counts = message_batch.request_counts
        log.info(
            f"  Processing: {counts.processing} | "
            f"Succeeded: {counts.succeeded} | "
            f"Errored: {counts.errored} | "
            f"Expired: {counts.expired}"
        )
        if message_batch.processing_status == "ended":
            break
        time.sleep(poll_interval)

    # Process results
    succeeded = 0
    failed = 0
    total_words = 0

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        doc = doc_map.get(custom_id)
        display_name = (doc.get("display_title") or doc["file_name"]) if doc else custom_id

        if result.result.type == "succeeded":
            summary = result.result.message.content[0].text
            doc_id = int(custom_id.split("-", 1)[1])
            store_summary(conn, doc_id, summary)
            word_count = len(summary.split())
            total_words += word_count
            succeeded += 1
            log.info(f"  {display_name}: {word_count} words")
        elif result.result.type == "errored":
            failed += 1
            log.error(f"  {display_name}: error — {result.result.error}")
        elif result.result.type == "expired":
            failed += 1
            log.error(f"  {display_name}: expired")
        elif result.result.type == "canceled":
            failed += 1
            log.warning(f"  {display_name}: canceled")

    log.info(f"\n{'=' * 60}")
    log.info(f"Batch complete: {batch_id}")
    log.info(f"  Succeeded: {succeeded}")
    log.info(f"  Skipped:   {skipped}")
    log.info(f"  Failed:    {failed}")
    log.info(f"  Total words: {total_words:,}")
    if succeeded > 0:
        log.info(f"  Avg words/summary: {total_words // succeeded}")
    log.info(f"  Cost: 50% of standard API pricing")
    log.info(f"{'=' * 60}")


def run_sequential(client: anthropic.Anthropic, conn, docs: list[dict]):
    """Process documents one at a time (original mode)."""
    succeeded = 0
    failed = 0
    skipped = 0
    total_words = 0

    for i, doc in enumerate(docs):
        display_name = doc.get("display_title") or doc["file_name"]
        est_tokens = int((doc.get("text_length") or 0) / CHARS_PER_TOKEN)
        log.info(f"[{i + 1}/{len(docs)}] {display_name} (~{est_tokens:,} tokens)")

        try:
            summary = generate_summary(client, doc)
            if summary:
                store_summary(conn, doc["id"], summary)
                word_count = len(summary.split())
                total_words += word_count
                succeeded += 1
                log.info(f"  -> {word_count} words")
            else:
                skipped += 1
                log.warning(f"  -> Skipped (too short or empty)")

        except anthropic.RateLimitError:
            log.warning(f"  Rate limited, waiting 60s...")
            time.sleep(60)
            try:
                summary = generate_summary(client, doc)
                if summary:
                    store_summary(conn, doc["id"], summary)
                    word_count = len(summary.split())
                    total_words += word_count
                    succeeded += 1
                    log.info(f"  -> {word_count} words (after retry)")
                else:
                    skipped += 1
            except Exception as e2:
                failed += 1
                log.error(f"  -> Failed after retry: {e2}")

        except Exception as e:
            failed += 1
            log.error(f"  -> Error: {type(e).__name__}: {e}")

    log.info(f"\n{'=' * 60}")
    log.info(f"Done.")
    log.info(f"  Succeeded: {succeeded}")
    log.info(f"  Skipped:   {skipped}")
    log.info(f"  Failed:    {failed}")
    log.info(f"  Total words: {total_words:,}")
    if succeeded > 0:
        log.info(f"  Avg words/summary: {total_words // succeeded}")
    log.info(f"{'=' * 60}")


def run_sequential_from_extraction(client, conn, docs: list[dict],
                                    use_kimi: bool = False):
    """Generate summaries from structured extraction data instead of raw text."""
    succeeded = 0
    failed = 0
    skipped = 0
    total_words = 0

    for i, doc in enumerate(docs):
        display_name = doc.get("display_title") or doc["file_name"]
        log.info(f"[{i + 1}/{len(docs)}] {display_name}")

        extraction = get_extraction_data(conn, doc["id"])
        total_items = sum(extraction['counts'].values())

        if total_items == 0:
            skipped += 1
            log.warning(f"  -> Skipped (no extraction data)")
            continue

        log.info(f"  {total_items:,} extracted items")

        try:
            summary = generate_summary_from_extraction(client, doc, extraction, use_kimi=use_kimi)
            if summary:
                store_summary(conn, doc["id"], summary)
                word_count = len(summary.split())
                total_words += word_count
                succeeded += 1
                log.info(f"  -> {word_count} words")
            else:
                skipped += 1
                log.warning(f"  -> Skipped (empty response)")

        except anthropic.RateLimitError:
            log.warning(f"  Rate limited, waiting 60s...")
            time.sleep(60)
            try:
                summary = generate_summary_from_extraction(client, doc, extraction, use_kimi=use_kimi)
                if summary:
                    store_summary(conn, doc["id"], summary)
                    word_count = len(summary.split())
                    total_words += word_count
                    succeeded += 1
                    log.info(f"  -> {word_count} words (after retry)")
                else:
                    skipped += 1
            except Exception as e2:
                failed += 1
                log.error(f"  -> Failed after retry: {e2}")

        except Exception as e:
            failed += 1
            log.error(f"  -> Error: {type(e).__name__}: {e}")

    log.info(f"\n{'=' * 60}")
    log.info(f"Done.")
    log.info(f"  Succeeded: {succeeded}")
    log.info(f"  Skipped:   {skipped}")
    log.info(f"  Failed:    {failed}")
    log.info(f"  Total words: {total_words:,}")
    if succeeded > 0:
        log.info(f"  Avg words/summary: {total_words // succeeded}")
    log.info(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate analytical summaries for all documents"
    )
    parser.add_argument(
        "--db",
        default="crow_historical_docs",
        help="Database name (default: crow_historical_docs)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-summarize all documents (default: only unsummarized)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of documents to process (for testing)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Use Batch API for 50%% cost savings (async, may take up to 1 hour)",
    )
    parser.add_argument(
        "--from-extraction",
        action="store_true",
        help="Generate summaries from structured extraction data instead of raw text. "
             "No truncation — works on any size document.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model to use: 'opus' (default), 'sonnet', or 'kimi'. "
             "Kimi requires TOGETHER_API_KEY.",
    )
    args = parser.parse_args()

    # Determine model and client
    use_kimi = args.model and args.model.lower() == "kimi"

    if use_kimi:
        from together import Together
        api_key = os.environ.get("TOGETHER_API_KEY")
        if not api_key:
            log.error("TOGETHER_API_KEY not set")
            sys.exit(1)
        client = Together(api_key=api_key, timeout=600.0)
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            log.error("ANTHROPIC_API_KEY not set")
            sys.exit(1)
        client = anthropic.Anthropic(api_key=api_key)
        if args.model and args.model.lower() == "sonnet":
            global MODEL
            MODEL = "claude-sonnet-4-6"

    conn = get_connection(args.db)

    docs = get_documents(conn, force=args.force, limit=args.limit,
                         from_extraction=args.from_extraction)
    if not docs:
        log.info("No documents to summarize.")
        conn.close()
        return

    source_label = "extraction data" if args.from_extraction else "full text"
    mode_label = "BATCH (50% cost savings)" if args.batch else "sequential"
    log.info(f"{'=' * 60}")
    log.info(f"Document Summary Enrichment")
    log.info(f"Database: {args.db}")
    log.info(f"Documents to process: {len(docs)}")
    log.info(f"Model: {MODEL}")
    log.info(f"Source: {source_label}")
    log.info(f"API mode: {mode_label}")
    log.info(f"Mode: {'force (re-summarize all)' if args.force else 'unsummarized only'}")
    log.info(f"{'=' * 60}")

    if args.from_extraction:
        run_sequential_from_extraction(client, conn, docs, use_kimi=use_kimi)
    elif args.batch:
        run_batch(client, conn, docs)
    else:
        run_sequential(client, conn, docs)

    conn.close()


if __name__ == "__main__":
    main()
