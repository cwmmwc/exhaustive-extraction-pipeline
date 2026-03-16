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

Write a dense analytical summary of this document in 150-250 words. No headers or bullet points — write in plain prose paragraphs. Cover: document type and purpose; author, recipient, date; specific claims, actions, or decisions (names, amounts, acreages); legal mechanisms invoked (statutes, policies, administrative procedures); and what it proves about land dispossession.

Prioritize specifics over generalities. Include dollar amounts, acreages, allotment numbers, and legal citations when present. If the OCR is poor or the document fragmentary, note that briefly.

DOCUMENT TEXT:
{full_text}"""


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


def get_documents(conn, force: bool = False, limit: int | None = None) -> list[dict]:
    """Get documents that need summaries."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    where = "WHERE d.full_text IS NOT NULL AND d.full_text != ''"
    if not force:
        where += " AND d.summary IS NULL"
    query = f"""
        SELECT d.id, d.file_name, d.display_title, d.collection, d.full_text,
               LENGTH(d.full_text) as text_length
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
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection(args.db)

    docs = get_documents(conn, force=args.force, limit=args.limit)
    if not docs:
        log.info("No documents to summarize.")
        conn.close()
        return

    log.info(f"{'=' * 60}")
    log.info(f"Document Summary Enrichment")
    log.info(f"Database: {args.db}")
    log.info(f"Documents to process: {len(docs)}")
    log.info(f"Model: {MODEL}")
    log.info(f"Mode: {'force (re-summarize all)' if args.force else 'unsummarized only'}")
    log.info(f"{'=' * 60}")

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

        except anthropic.RateLimitError as e:
            log.warning(f"  Rate limited, waiting 60s...")
            time.sleep(60)
            # Retry once
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

    conn.close()

    log.info(f"\n{'=' * 60}")
    log.info(f"Done.")
    log.info(f"  Succeeded: {succeeded}")
    log.info(f"  Skipped:   {skipped}")
    log.info(f"  Failed:    {failed}")
    log.info(f"  Total words: {total_words:,}")
    if succeeded > 0:
        log.info(f"  Avg words/summary: {total_words // succeeded}")
    log.info(f"{'=' * 60}")


if __name__ == "__main__":
    main()
