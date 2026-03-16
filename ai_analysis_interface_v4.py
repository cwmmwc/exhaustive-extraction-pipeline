#!/usr/bin/env python3
"""
AI Analysis Interface v4 — Three Analysis Modes

WHAT'S NEW OVER v3:
  MODE 1 — DISCOVERY: Search everything, find cross-collection connections.
    Same as v3: entity database + full-text passage retrieval.
    Best for: "What do we know about X?" / "Who was connected to Y?"

  MODE 2 — DEEP READ: Select a specific document, send its FULL TEXT to
    the AI for deep analysis. Like DevonThink — the AI reads the whole
    document, not fragments.
    Best for: "Analyze this 20-page FOIA response" / "What's in this file?"

  MODE 3 — DISCOVERY → DEEP READ: Run Discovery first, then automatically
    send the top-ranked documents' full texts + entity data to the AI for
    a comprehensive analysis that combines breadth AND depth.
    Best for: "Tell me everything about forced fee patents on Crow"

Usage:
    streamlit run ai_analysis_interface_v4.py
"""
import streamlit as st
import psycopg2
import psycopg2.extras
import anthropic
import os
import re
import math
from typing import List, Dict, Optional, Tuple

st.set_page_config(
    page_title="Historical Document Analysis v4",
    page_icon="\U0001f4dc",
    layout="wide"
)

# ─────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_available_databases() -> List[str]:
    if DATABASE_URL:
        return ["crow_historical_docs"]
    try:
        conn = psycopg2.connect("postgresql://localhost/postgres")
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            SELECT datname FROM pg_database
            WHERE datname IN ('crow_historical_docs', 'historical_docs')
               OR datname LIKE '%_historical_%'
            ORDER BY datname
        """)
        dbs = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return dbs if dbs else ["crow_historical_docs"]
    except Exception:
        return ["crow_historical_docs"]


def get_db_connection(db_name: str):
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return psycopg2.connect(
        dbname=db_name,
        user=os.environ.get("USER", "cwm6W"),
        host="localhost"
    )


def get_db_stats(db_name: str) -> Dict:
    try:
        conn = get_db_connection(db_name)
        cur = conn.cursor()
        stats = {}
        cur.execute("SELECT COUNT(*) FROM documents")
        stats['documents'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM entities")
        stats['entities'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM events")
        stats['events'] = cur.fetchone()[0]
        for table in ['financial_transactions', 'relationships']:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cur.fetchone()[0]
            except Exception:
                conn.rollback()
                stats[table] = 0
        cur.execute("SELECT type, COUNT(*) FROM entities GROUP BY type ORDER BY COUNT(*) DESC")
        stats['entity_types'] = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute("SELECT COUNT(*) FROM documents WHERE full_text IS NOT NULL AND full_text != ''")
        stats['docs_with_text'] = cur.fetchone()[0]
        cur.close()
        conn.close()
        return stats
    except Exception as e:
        return {'documents': 0, 'entities': 0, 'events': 0,
                'financial_transactions': 0, 'relationships': 0,
                'entity_types': {}, 'docs_with_text': 0, 'error': str(e)}


# ─────────────────────────────────────────────────
# LAYER 1: ENTITY DATABASE SEARCH
# ─────────────────────────────────────────────────

def search_entities(db_name: str, query: str, limit: int = 200) -> List[Dict]:
    """Search entities by name and context, with relevance boosting."""
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        terms = [query.strip()]

    name_conditions = " OR ".join(["e.name ILIKE %s"] * len(terms))
    name_params = [f"%{t}%" for t in terms]
    ctx_conditions = " OR ".join(["e.context ILIKE %s"] * len(terms))
    ctx_params = [f"%{t}%" for t in terms]

    cur.execute(f"""
        SELECT e.id, e.name, e.type, e.context, e.acres, e.land_type,
               COUNT(DISTINCT m.document_id) as doc_count,
               ARRAY_AGG(DISTINCT d.file_name) as source_files,
               ARRAY_AGG(DISTINCT COALESCE(d.display_title, d.file_name)) as source_display_names,
               CASE
                 WHEN e.type = 'person' AND ({name_conditions}) THEN 1000 + COUNT(DISTINCT m.document_id)
                 WHEN ({name_conditions}) THEN 500 + COUNT(DISTINCT m.document_id)
                 ELSE COUNT(DISTINCT m.document_id)
               END as relevance_score
        FROM entities e
        LEFT JOIN mentions m ON e.id = m.entity_id
        LEFT JOIN documents d ON m.document_id = d.id
        WHERE ({name_conditions}) OR ({ctx_conditions})
        GROUP BY e.id, e.name, e.type, e.context, e.acres, e.land_type
        ORDER BY relevance_score DESC, e.name
        LIMIT %s
    """, name_params + name_params + name_params + ctx_params + [limit])

    results = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return results


def search_events(db_name: str, query: str, limit: int = 100) -> List[Dict]:
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        terms = [query.strip()]
    conditions = " OR ".join(
        ["e.description ILIKE %s OR e.type ILIKE %s OR e.location ILIKE %s"] * len(terms)
    )
    params = []
    for t in terms:
        params.extend([f"%{t}%"] * 3)
    cur.execute(f"""
        SELECT e.type, e.date, e.location, e.description, e.metadata, d.file_name, d.display_title
        FROM events e
        JOIN documents d ON e.document_id = d.id
        WHERE {conditions}
        ORDER BY e.date ASC NULLS LAST
        LIMIT %s
    """, params + [limit])
    results = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return results


def search_financial_transactions(db_name: str, query: str, limit: int = 50) -> List[Dict]:
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        terms = [query.strip()]
    conditions = " OR ".join(
        ["ft.payer ILIKE %s OR ft.payee ILIKE %s OR ft.for_what ILIKE %s OR ft.context ILIKE %s"] * len(terms)
    )
    params = []
    for t in terms:
        params.extend([f"%{t}%"] * 4)
    try:
        cur.execute(f"""
            SELECT ft.amount, ft.type, ft.payer, ft.payee, ft.for_what,
                   ft.date, ft.context, d.file_name, d.display_title
            FROM financial_transactions ft
            JOIN documents d ON ft.document_id = d.id
            WHERE {conditions}
            ORDER BY ft.date ASC NULLS LAST
            LIMIT %s
        """, params + [limit])
        results = [dict(row) for row in cur.fetchall()]
    except Exception:
        results = []
    cur.close()
    conn.close()
    return results


def search_relationships(db_name: str, query: str, limit: int = 100) -> List[Dict]:
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        terms = [query.strip()]
    conditions = " OR ".join(
        ["r.subject ILIKE %s OR r.object ILIKE %s OR r.type ILIKE %s OR r.context ILIKE %s"] * len(terms)
    )
    params = []
    for t in terms:
        params.extend([f"%{t}%"] * 4)
    try:
        cur.execute(f"""
            SELECT r.type, r.subject, r.object, r.context, d.file_name, d.display_title
            FROM relationships r
            JOIN documents d ON r.document_id = d.id
            WHERE {conditions}
            ORDER BY r.subject, r.type
            LIMIT %s
        """, params + [limit])
        results = [dict(row) for row in cur.fetchall()]
    except Exception:
        results = []
    cur.close()
    conn.close()
    return results


def get_entity_network(db_name: str, entity_name: str) -> List[Dict]:
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT e2.name, e2.type, e2.context,
               COUNT(DISTINCT m2.document_id) as shared_docs
        FROM entities e1
        JOIN mentions m1 ON e1.id = m1.entity_id
        JOIN mentions m2 ON m1.document_id = m2.document_id AND m2.entity_id != m1.entity_id
        JOIN entities e2 ON m2.entity_id = e2.id
        WHERE e1.name ILIKE %s
        GROUP BY e2.id, e2.name, e2.type, e2.context
        ORDER BY shared_docs DESC
        LIMIT 50
    """, [f"%{entity_name}%"])
    results = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return results


# ─────────────────────────────────────────────────
# LAYER 2: FULL-TEXT PASSAGE RETRIEVAL
# ─────────────────────────────────────────────────

def extract_passages(full_text: str, search_terms: List[str],
                     context_chars: int = 500, max_passages: int = 5) -> List[str]:
    """
    Extract relevant passages from document full text.
    Finds paragraphs containing search terms and grabs surrounding context.
    Returns deduplicated passages ranked by term density.
    """
    if not full_text or not search_terms:
        return []

    text = re.sub(r'\n{3,}', '\n\n', full_text)
    text = re.sub(r'[ \t]+', ' ', text)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    scored = []
    terms_lower = [t.lower() for t in search_terms]

    for i, para in enumerate(paragraphs):
        para_lower = para.lower()
        score = sum(para_lower.count(term) for term in terms_lower)
        if score > 0 and len(para) > 30:
            start = max(0, i - 1)
            end = min(len(paragraphs), i + 2)
            context_block = "\n\n".join(paragraphs[start:end])

            if len(context_block) > context_chars * 2:
                for term in terms_lower:
                    pos = context_block.lower().find(term)
                    if pos >= 0:
                        start_pos = max(0, pos - context_chars)
                        end_pos = min(len(context_block), pos + context_chars)
                        context_block = "..." + context_block[start_pos:end_pos] + "..."
                        break

            scored.append((score, len(para), context_block))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    seen_text = set()
    passages = []
    for score, length, passage in scored[:max_passages * 2]:
        key = passage[:100].lower().strip()
        if key not in seen_text:
            seen_text.add(key)
            passages.append(passage)
            if len(passages) >= max_passages:
                break

    return passages


def search_full_text_passages(db_name: str, query: str,
                               max_docs: int = 15,
                               max_passages_per_doc: int = 3) -> List[Dict]:
    """
    Search document full text using PostgreSQL full-text search (GIN index).

    Uses websearch_to_tsquery for natural query parsing and ts_rank_cd
    (cover density) for relevance ranking. Falls back to plainto_tsquery
    if websearch syntax fails. Passage extraction is done in Python for
    better context blocks.
    """
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        terms = [query.strip()]

    # Try websearch_to_tsquery first (handles natural language queries),
    # fall back to plainto_tsquery (simpler, more forgiving)
    docs = []
    for tsquery_fn in ['websearch_to_tsquery', 'plainto_tsquery']:
        try:
            cur.execute(f"""
                SELECT d.id, d.file_name, d.display_title, d.collection, d.full_text,
                       d.page_count, d.pipeline_version,
                       ts_rank_cd(to_tsvector('english', full_text),
                                  {tsquery_fn}('english', %s), 32) as rank,
                       (SELECT COUNT(*) FROM mentions m WHERE m.document_id = d.id) as entity_count
                FROM documents d
                WHERE d.full_text IS NOT NULL
                  AND to_tsvector('english', full_text) @@ {tsquery_fn}('english', %s)
                ORDER BY rank DESC
                LIMIT %s
            """, [query, query, max_docs])
            docs = [dict(row) for row in cur.fetchall()]
            if docs:
                break
        except Exception:
            conn.rollback()
            continue

    # Final fallback: ILIKE for queries that FTS can't parse
    if not docs:
        any_conditions = " OR ".join(["d.full_text ILIKE %s"] * len(terms))
        params = [f"%{t}%" for t in terms]
        cur.execute(f"""
            SELECT d.id, d.file_name, d.display_title, d.collection, d.full_text,
                   d.page_count, d.pipeline_version,
                   0.0 as rank,
                   (SELECT COUNT(*) FROM mentions m WHERE m.document_id = d.id) as entity_count
            FROM documents d
            WHERE d.full_text IS NOT NULL AND d.full_text != ''
              AND ({any_conditions})
            ORDER BY entity_count DESC
            LIMIT %s
        """, params + [max_docs])
        docs = [dict(row) for row in cur.fetchall()]

    cur.close()
    conn.close()

    results = []
    for doc in docs:
        full_text = doc.get('full_text', '')
        if not full_text:
            continue
        passages = extract_passages(full_text, terms,
                                     context_chars=600,
                                     max_passages=max_passages_per_doc)
        if passages:
            results.append({
                'file_name': doc['file_name'],
                'display_title': doc.get('display_title'),
                'collection': doc.get('collection', ''),
                'page_count': doc.get('page_count'),
                'pipeline_version': doc.get('pipeline_version', ''),
                'rank': round(doc.get('rank', 0), 6),
                'passages': passages,
                'passage_count': len(passages),
            })

    return results


def search_documents_metadata(db_name: str, query: str, limit: int = 30) -> List[Dict]:
    """Search documents by full text (FTS) and filename, return metadata only."""
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        terms = [query.strip()]

    # Combine FTS on full_text with ILIKE on file_name
    fname_conditions = " OR ".join(["d.file_name ILIKE %s"] * len(terms))
    fname_params = [f"%{t}%" for t in terms]

    try:
        cur.execute(f"""
            SELECT d.file_name, d.display_title, d.collection, d.page_count, d.pipeline_version,
                   (SELECT COUNT(*) FROM mentions m WHERE m.document_id = d.id) as entity_count,
                   COALESCE(ts_rank_cd(to_tsvector('english', full_text),
                            websearch_to_tsquery('english', %s), 32), 0) as rank
            FROM documents d
            WHERE (d.full_text IS NOT NULL
                   AND to_tsvector('english', full_text) @@ websearch_to_tsquery('english', %s))
               OR ({fname_conditions})
            ORDER BY rank DESC, entity_count DESC
            LIMIT %s
        """, [query, query] + fname_params + [limit])
    except Exception:
        conn.rollback()
        # Fallback to ILIKE
        all_conditions = " OR ".join(
            ["d.full_text ILIKE %s OR d.file_name ILIKE %s"] * len(terms))
        params = []
        for t in terms:
            params.extend([f"%{t}%", f"%{t}%"])
        cur.execute(f"""
            SELECT d.file_name, d.display_title, d.collection, d.page_count, d.pipeline_version,
                   (SELECT COUNT(*) FROM mentions m WHERE m.document_id = d.id) as entity_count,
                   0.0 as rank
            FROM documents d
            WHERE {all_conditions}
            ORDER BY entity_count DESC
            LIMIT %s
        """, params + [limit])

    results = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return results


def rank_documents_for_deep_read(db_name: str, query: str,
                                  max_token_budget: int = 130000) -> List[Dict]:
    """
    Smart document ranking for hybrid mode.
    Scores by: term frequency (how often query terms appear) × entity richness,
    penalized by document size.
    Filters out finding aids and other low-value reference documents.
    """
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        terms = [query.strip()]

    # Stop words — filter these from term frequency counting
    STOP_WORDS = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
        'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been', 'some', 'them',
        'than', 'its', 'over', 'such', 'that', 'this', 'with', 'will', 'each',
        'make', 'from', 'they', 'also', 'been', 'many', 'then', 'what', 'when',
        'who', 'how', 'which', 'their', 'said', 'were', 'into', 'more', 'other',
        'about', 'would', 'there', 'could', 'after', 'should', 'these', 'where',
        'being', 'those', 'still', 'between', 'tell', 'know', 'consider',
        'look', 'find', 'evidence', 'discuss', 'describe', 'explain',
    }

    # Filter terms: remove stop words and very short terms
    content_terms = [t for t in terms if t.lower() not in STOP_WORDS and len(t) > 2]
    if not content_terms:
        content_terms = terms  # fallback to original if everything was filtered

    # Find documents containing search terms using FTS (GIN index).
    # Fetch all matching candidates — scoring happens in Python below.
    content_query = " ".join(content_terms)
    try:
        cur.execute("""
            SELECT d.id, d.file_name, d.display_title, d.collection, d.page_count, d.pipeline_version,
                   d.full_text,
                   LENGTH(d.full_text) as text_length,
                   ts_rank_cd(to_tsvector('english', full_text),
                              websearch_to_tsquery('english', %s), 32) as fts_rank,
                   (SELECT COUNT(*) FROM mentions m WHERE m.document_id = d.id) as entity_count,
                   (SELECT COUNT(*) FROM financial_transactions ft WHERE ft.document_id = d.id) as transaction_count,
                   (SELECT COUNT(*) FROM relationships r WHERE r.document_id = d.id) as relationship_count
            FROM documents d
            WHERE d.full_text IS NOT NULL
              AND to_tsvector('english', full_text) @@ websearch_to_tsquery('english', %s)
        """, [content_query, content_query])
    except Exception:
        conn.rollback()
        # Fallback to ILIKE if FTS fails
        any_conditions = " OR ".join(["d.full_text ILIKE %s"] * len(content_terms))
        params = [f"%{t}%" for t in content_terms]
        cur.execute(f"""
            SELECT d.id, d.file_name, d.display_title, d.collection, d.page_count, d.pipeline_version,
                   d.full_text,
                   LENGTH(d.full_text) as text_length,
                   0.0 as fts_rank,
                   (SELECT COUNT(*) FROM mentions m WHERE m.document_id = d.id) as entity_count,
                   (SELECT COUNT(*) FROM financial_transactions ft WHERE ft.document_id = d.id) as transaction_count,
                   (SELECT COUNT(*) FROM relationships r WHERE r.document_id = d.id) as relationship_count
            FROM documents d
            WHERE d.full_text IS NOT NULL AND d.full_text != ''
              AND ({any_conditions})
        """, params)

    candidates = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()

    if not candidates:
        return []

    # Score each document
    scored = []
    for doc in candidates:
        text_len = doc.get('text_length') or 1
        est_tokens = int(text_len / 3.2)
        entity_count = doc.get('entity_count', 0)
        transaction_count = doc.get('transaction_count', 0)
        relationship_count = doc.get('relationship_count', 0)
        fname = doc['file_name'].lower()
        full_text_lower = (doc.get('full_text') or '').lower()

        # Don't pass full_text through to the results (save memory)
        doc.pop('full_text', None)

        # Skip finding aids and reference documents
        if any(skip in fname for skip in ['finding aid', 'archives west',
                                            'haley papers', 'mansfield papers']):
            continue

        # ── TERM FREQUENCY: how many times do query terms appear? ──
        # Uses content_terms (stop words removed) for accurate counting.
        term_hits = 0
        for term in content_terms:
            term_hits += full_text_lower.count(term.lower())

        # Two term-frequency signals:
        # 1. Term density (hits per 1K tokens) — rewards focused documents
        # 2. Raw term count — rewards documents with extensive coverage
        # Both matter: a 2-page letter with 3 hits is focused but thin;
        # a 50-page case file with 80 hits has both depth and coverage.
        term_density = term_hits / max(1, est_tokens / 1000)
        # Log-scale raw hits to prevent huge docs from dominating purely by size
        import math
        term_volume = math.log(max(1, term_hits)) * 3

        # ── FILENAME RELEVANCE ──
        # If the document is literally named after a search term, that's a
        # strong signal. "Stanton Collection Series 5" should rank high for
        # a "Stanton" query even if the letters inside don't say "Stanton"
        # on every page (because they're FROM Stanton's files).
        fname_hits = 0
        for term in content_terms:
            if term.lower() in fname:
                fname_hits += 1
        # Bonus: scale by number of matching terms relative to total terms
        fname_bonus = (fname_hits / max(1, len(content_terms))) * 15

        # ── RICHNESS: structured data quality ──
        # Transactions and relationships are more valuable than raw entity count
        richness = entity_count + (transaction_count * 5) + (relationship_count * 3)
        richness_density = richness / max(1, est_tokens / 1000)

        # ── SIZE PREFERENCE FOR DEEP READ ──
        # Deep Read mode exists to read substantial documents deeply.
        # Very small documents (<3K tokens, ~2 pages) aren't worth deep reading —
        # they're already fully captured by Discovery passage extraction.
        # Medium documents (5K-45K tokens) are ideal for deep read.
        # Large documents get partial truncation but still have value.
        if est_tokens < 3000:
            size_factor = 0.3   # too small for deep read — Discovery handles these
        elif est_tokens < 5000:
            size_factor = 0.6   # marginal — short doc
        elif est_tokens <= 45000:
            size_factor = 1.0   # ideal — fits in full
        elif est_tokens <= 100000:
            size_factor = 0.7   # partial truncation
        else:
            size_factor = 0.3   # heavy truncation — most content lost

        # ── FTS RANK: PostgreSQL full-text search relevance ──
        # Cover density rank from the database, scaled to be comparable
        # with our other signals (typically 0-1, scaled by 10).
        fts_score = doc.get('fts_rank', 0) * 10

        # ── FINAL SCORE ──
        # Combines FTS rank, density (focus), volume (coverage), richness,
        # and filename match. Size factor applied to prefer documents worth
        # deep reading.
        score = (fts_score + term_density + term_volume + richness_density + fname_bonus) * size_factor

        doc['score'] = score
        doc['est_tokens'] = est_tokens
        doc['richness'] = richness
        doc['term_hits'] = term_hits
        scored.append(doc)

    # Sort by score descending
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored


# ─────────────────────────────────────────────────
# DEEP READ: Full document retrieval (NEW in v4)
# ─────────────────────────────────────────────────

def list_documents(db_name: str, search: str = "") -> List[Dict]:
    """List all documents, optionally filtered by search term."""
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if search.strip():
        terms = [t.strip() for t in search.split() if len(t.strip()) > 2]
        if not terms:
            terms = [search.strip()]
        # FTS on full_text + ILIKE on file_name
        fname_conditions = " OR ".join(["d.file_name ILIKE %s"] * len(terms))
        fname_params = [f"%{t}%" for t in terms]
        try:
            cur.execute(f"""
                SELECT d.id, d.file_name, d.display_title, d.collection, d.page_count,
                       d.pipeline_version,
                       LENGTH(d.full_text) as text_length,
                       (SELECT COUNT(*) FROM mentions m WHERE m.document_id = d.id) as entity_count,
                       (d.full_text IS NOT NULL AND d.full_text != '') as has_text,
                       COALESCE(ts_rank_cd(to_tsvector('english', full_text),
                                websearch_to_tsquery('english', %s), 32), 0) as rank
                FROM documents d
                WHERE (d.full_text IS NOT NULL
                       AND to_tsvector('english', full_text) @@ websearch_to_tsquery('english', %s))
                   OR ({fname_conditions})
                ORDER BY rank DESC, entity_count DESC
                LIMIT 100
            """, [search, search] + fname_params)
        except Exception:
            conn.rollback()
            conditions = " OR ".join(["d.file_name ILIKE %s OR d.full_text ILIKE %s"] * len(terms))
            params = []
            for t in terms:
                params.extend([f"%{t}%", f"%{t}%"])
            cur.execute(f"""
                SELECT d.id, d.file_name, d.display_title, d.collection, d.page_count,
                       d.pipeline_version,
                       LENGTH(d.full_text) as text_length,
                       (SELECT COUNT(*) FROM mentions m WHERE m.document_id = d.id) as entity_count,
                       (d.full_text IS NOT NULL AND d.full_text != '') as has_text,
                       0.0 as rank
                FROM documents d
                WHERE {conditions}
                ORDER BY entity_count DESC
                LIMIT 100
            """, params)
    else:
        cur.execute("""
            SELECT d.id, d.file_name, d.display_title, d.collection, d.page_count,
                   d.pipeline_version,
                   LENGTH(d.full_text) as text_length,
                   (SELECT COUNT(*) FROM mentions m WHERE m.document_id = d.id) as entity_count,
                   (d.full_text IS NOT NULL AND d.full_text != '') as has_text
            FROM documents d
            ORDER BY d.file_name
            LIMIT 200
        """)
    results = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return results


def get_document_full(db_name: str, doc_id: int) -> Optional[Dict]:
    """Get a single document with its FULL text and all associated data."""
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get document
    cur.execute("""
        SELECT d.id, d.file_name, d.display_title, d.file_path, d.collection,
               d.page_count, d.pipeline_version, d.full_text
        FROM documents d WHERE d.id = %s
    """, [doc_id])
    doc = cur.fetchone()
    if not doc:
        cur.close()
        conn.close()
        return None
    doc = dict(doc)

    # Get entities for this document
    cur.execute("""
        SELECT e.name, e.type, e.context, e.acres, e.land_type
        FROM entities e
        JOIN mentions m ON e.id = m.entity_id
        WHERE m.document_id = %s
        ORDER BY e.type, e.name
    """, [doc_id])
    doc['entities'] = [dict(row) for row in cur.fetchall()]

    # Get events
    cur.execute("""
        SELECT type, date, location, description, metadata
        FROM events WHERE document_id = %s
        ORDER BY date ASC NULLS LAST
    """, [doc_id])
    doc['events'] = [dict(row) for row in cur.fetchall()]

    # Get transactions
    try:
        cur.execute("""
            SELECT amount, type, payer, payee, for_what, date, context
            FROM financial_transactions WHERE document_id = %s
            ORDER BY date ASC NULLS LAST
        """, [doc_id])
        doc['transactions'] = [dict(row) for row in cur.fetchall()]
    except Exception:
        conn.rollback()
        doc['transactions'] = []

    # Get relationships
    try:
        cur.execute("""
            SELECT type, subject, object, context
            FROM relationships WHERE document_id = %s
            ORDER BY subject, type
        """, [doc_id])
        doc['relationships'] = [dict(row) for row in cur.fetchall()]
    except Exception:
        conn.rollback()
        doc['relationships'] = []

    cur.close()
    conn.close()
    return doc


def get_documents_full_by_names(db_name: str, file_names: List[str]) -> List[Dict]:
    """Get multiple documents by filename with full text and extracted data."""
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if not file_names:
        return []

    placeholders = ", ".join(["%s"] * len(file_names))
    cur.execute(f"""
        SELECT id, file_name FROM documents
        WHERE file_name IN ({placeholders})
    """, file_names)
    doc_ids = {row['file_name']: row['id'] for row in cur.fetchall()}
    cur.close()
    conn.close()

    docs = []
    for fname in file_names:
        if fname in doc_ids:
            doc = get_document_full(db_name, doc_ids[fname])
            if doc:
                docs.append(doc)
    return docs


# ─────────────────────────────────────────────────
# CONTEXT SIZE ESTIMATION
# ─────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Conservative token estimate: ~3.2 chars per token for OCR'd historical text.
    OCR text has more whitespace, special chars, and fragments that tokenize less
    efficiently than clean English prose (which runs ~4 chars/token)."""
    return int(len(text) / 3.2)


def truncate_text_to_tokens(text: str, max_tokens: int) -> Tuple[str, bool]:
    """Truncate text to approximate token limit. Returns (text, was_truncated)."""
    estimated = estimate_tokens(text)
    if estimated <= max_tokens:
        return text, False
    max_chars = int(max_tokens * 3.2)
    return text[:max_chars] + "\n\n[... DOCUMENT TRUNCATED — full text exceeds context window ...]", True


# ─────────────────────────────────────────────────
# EVIDENCE CONTEXT BUILDERS
# ─────────────────────────────────────────────────

def extract_doc_date(file_name: str) -> str:
    """
    Extract an approximate date from a filename.

    Many archival filenames encode dates:
      "1972 Dillon v. Antler Land Co.pdf" → "c. 1972"
      "PrettyOnTop_Jun18_1947.pdf" → "c. 1947"
      "1929-35 Crow SANSAR.pdf" → "c. 1929-35"
      "Survey of Cond part 33 Montana.pdf" → "" (no date)
    """
    if not file_name:
        return ""
    # Match 4-digit year at start or after common separators
    # Also match year ranges like 1929-35 or 1958-75
    m = re.search(r'\b(1[89]\d{2}(?:\s*[-–]\s*\d{2,4})?)\b', file_name)
    if m:
        return f"c. {m.group(1)}"
    return ""


def escape_dollars(text: str) -> str:
    """Escape $ signs so Streamlit markdown doesn't render them as LaTeX."""
    return text.replace("$", "\\$")


def doc_label(d) -> str:
    """Return display_title if available, otherwise file_name."""
    if isinstance(d, dict):
        return d.get('display_title') or d.get('file_name', '')
    return str(d)


def build_discovery_context(question: str, evidence: Dict) -> str:
    """Build evidence block for Discovery mode."""
    sections = []

    # Full-text passages (most important)
    passages = evidence.get('passages', [])
    if passages:
        lines = []
        total_passages = sum(p['passage_count'] for p in passages)
        for doc in passages:
            doc_date = extract_doc_date(doc['file_name'])
            date_label = f", date: {doc_date}" if doc_date else ""
            lines.append(f"\n  === {doc_label(doc)} (collection: {doc.get('collection', 'n/a')}{date_label}) ===")
            for i, passage in enumerate(doc['passages']):
                if len(passage) > 800:
                    passage = passage[:800] + "..."
                lines.append(f"  [Passage {i+1}]:")
                lines.append(f"  {passage}")
                lines.append("")
        sections.append(
            f"DOCUMENT TEXT PASSAGES ({total_passages} passages from {len(passages)} documents):\n"
            f"These are actual excerpts from the source documents. Use these as primary evidence.\n"
            + "\n".join(lines)
        )

    # Entities
    entities = evidence.get('entities', [])
    if entities:
        lines = []
        by_type = {}
        for e in entities:
            by_type.setdefault(e['type'], []).append(e)
        for etype, ents in sorted(by_type.items()):
            lines.append(f"\n  [{etype.upper()}] ({len(ents)} found)")
            for e in ents[:25]:
                sources = ", ".join(e.get('source_display_names', e.get('source_files', []))[:3]) if e.get('source_files') else "unknown"
                ctx = (e.get('context') or '')[:200]
                extras = ""
                if e.get('acres'):
                    extras += f" | Acres: {e['acres']}"
                if e.get('land_type'):
                    extras += f" | Land type: {e['land_type']}"
                lines.append(f"    - {e['name']} (in {e.get('doc_count', 0)} docs): {ctx}{extras}")
                lines.append(f"      Sources: {sources}")
        sections.append(f"EXTRACTED ENTITIES ({len(entities)} total):" + "\n".join(lines))

    # Events
    events = evidence.get('events', [])
    if events:
        lines = []
        for ev in events[:40]:
            lines.append(f"  - [{ev.get('date', 'n/d')}] {ev.get('type', '')}: {ev.get('description', '')[:200]}")
            lines.append(f"    Location: {ev.get('location', 'n/a')} | Source: {doc_label(ev)}")
        sections.append(f"EVENTS ({len(events)} total):\n" + "\n".join(lines))

    # Financial transactions
    transactions = evidence.get('financial_transactions', [])
    if transactions:
        lines = []
        for ft in transactions[:30]:
            lines.append(f"  - [{ft.get('date', 'n/d')}] {ft.get('type', '')}: {ft.get('payer', '?')} \u2192 {ft.get('payee', '?')}, Amount: {ft.get('amount', '?')}")
            lines.append(f"    For: {ft.get('for_what', 'n/a')} | Context: {(ft.get('context') or '')[:150]} | Source: {doc_label(ft)}")
        sections.append(f"FINANCIAL TRANSACTIONS ({len(transactions)} total):\n" + "\n".join(lines))

    # Relationships
    relationships = evidence.get('relationships', [])
    if relationships:
        lines = []
        for r in relationships[:40]:
            lines.append(f"  - {r.get('subject', '?')} \u2014[{r.get('type', '?')}]\u2192 {r.get('object', '?')}")
            lines.append(f"    Context: {(r.get('context') or '')[:150]} | Source: {doc_label(r)}")
        sections.append(f"RELATIONSHIPS ({len(relationships)} total):\n" + "\n".join(lines))

    # Entity networks
    networks = evidence.get('networks', {})
    if networks:
        lines = []
        for person, connections in networks.items():
            lines.append(f"\n  Network for {person}:")
            for c in connections[:15]:
                lines.append(f"    - {c['name']} ({c['type']}): {c['shared_docs']} shared documents")
        sections.append("ENTITY NETWORKS (who appears alongside whom):\n" + "\n".join(lines))

    # Source documents
    docs = evidence.get('documents', [])
    if docs:
        lines = []
        for d in docs[:25]:
            doc_date = extract_doc_date(d['file_name'])
            date_label = f", date: {doc_date}" if doc_date else ""
            lines.append(f"  - {doc_label(d)} (collection: {d.get('collection', 'n/a')}{date_label}, "
                         f"{d.get('entity_count', 0)} entities)")
        sections.append(f"SOURCE DOCUMENTS ({len(docs)} matching):\n" + "\n".join(lines))

    return "\n\n".join(sections)


def build_deep_read_context(doc: Dict) -> str:
    """Build evidence block for Deep Read mode — full document text + extracted data."""
    sections = []

    # Document metadata
    sections.append(
        f"DOCUMENT: {doc_label(doc)}\n"
        f"Collection: {doc.get('collection', 'n/a')}\n"
        f"Pages: {doc.get('page_count', 'n/a')}\n"
        f"Pipeline: {doc.get('pipeline_version', 'n/a')}"
    )

    # Full text (the big one)
    full_text = doc.get('full_text', '')
    if full_text:
        # Sonnet limit 200K tokens. Reserve 10K for prompt, 8K for response,
        # 10K for extracted data = ~172K for text. Use 160K with safety margin.
        text, was_truncated = truncate_text_to_tokens(full_text, 160000)
        trunc_note = " [TRUNCATED — document exceeds context window]" if was_truncated else ""
        est_pages = max(1, len(full_text) // 3000)  # ~3000 chars per page
        sections.append(
            f"FULL DOCUMENT TEXT (~{est_pages} pages{trunc_note}):\n"
            f"This is the complete OCR'd text of the document. Read it carefully.\n\n"
            f"{text}"
        )
    else:
        sections.append("FULL DOCUMENT TEXT: [Not available — document has no extracted text]")

    # Extracted entities
    entities = doc.get('entities', [])
    if entities:
        lines = []
        by_type = {}
        for e in entities:
            by_type.setdefault(e['type'], []).append(e)
        for etype, ents in sorted(by_type.items()):
            lines.append(f"\n  [{etype.upper()}]")
            for e in ents:
                ctx = (e.get('context') or '')[:150]
                extras = ""
                if e.get('acres'):
                    extras += f" | Acres: {e['acres']}"
                lines.append(f"    - {e['name']}: {ctx}{extras}")
        sections.append(f"AI-EXTRACTED ENTITIES ({len(entities)} total):" + "\n".join(lines))

    # Events
    events = doc.get('events', [])
    if events:
        lines = []
        for ev in events:
            lines.append(f"  - [{ev.get('date', 'n/d')}] {ev.get('type', '')}: {ev.get('description', '')[:200]}")
        sections.append(f"AI-EXTRACTED EVENTS ({len(events)}):\n" + "\n".join(lines))

    # Transactions
    transactions = doc.get('transactions', [])
    if transactions:
        lines = []
        for ft in transactions:
            lines.append(f"  - [{ft.get('date', 'n/d')}] {ft.get('payer', '?')} \u2192 {ft.get('payee', '?')}: {ft.get('amount', '?')}")
            lines.append(f"    For: {ft.get('for_what', 'n/a')} | {(ft.get('context') or '')[:100]}")
        sections.append(f"AI-EXTRACTED TRANSACTIONS ({len(transactions)}):\n" + "\n".join(lines))

    # Relationships
    relationships = doc.get('relationships', [])
    if relationships:
        lines = []
        for r in relationships:
            lines.append(f"  - {r.get('subject', '?')} \u2014[{r.get('type', '?')}]\u2192 {r.get('object', '?')}")
            if r.get('context'):
                lines.append(f"    {r['context'][:150]}")
        sections.append(f"AI-EXTRACTED RELATIONSHIPS ({len(relationships)}):\n" + "\n".join(lines))

    return "\n\n".join(sections)


def build_hybrid_context(question: str, discovery_evidence: Dict,
                          deep_docs: List[Dict], max_doc_tokens: int = 40000) -> str:
    """
    Build evidence block for Mode 3: Discovery + Deep Read.
    Includes full text of top documents + entity data from discovery.
    """
    sections = []

    # Full texts of top documents (the deep read part)
    for i, doc in enumerate(deep_docs):
        full_text = doc.get('full_text', '')
        if not full_text:
            continue
        text, was_truncated = truncate_text_to_tokens(full_text, max_doc_tokens)
        trunc_note = " [TRUNCATED]" if was_truncated else ""
        est_pages = max(1, len(full_text) // 3000)

        doc_date = extract_doc_date(doc['file_name'])
        date_label = f", date: {doc_date}" if doc_date else ""
        doc_section = f"=== FULL DOCUMENT {i+1}: {doc_label(doc)} (~{est_pages} pages{trunc_note}) ===\n"
        doc_section += f"Collection: {doc.get('collection', 'n/a')}{date_label}\n\n"
        doc_section += text

        # Add this document's extracted data
        entities = doc.get('entities', [])
        events = doc.get('events', [])
        transactions = doc.get('transactions', [])
        relationships = doc.get('relationships', [])

        if entities or events or transactions or relationships:
            doc_section += f"\n\n--- Extracted data for {doc_label(doc)} ---"
            if entities:
                ent_summary = ", ".join([f"{e['name']} ({e['type']})" for e in entities[:30]])
                doc_section += f"\nEntities ({len(entities)}): {ent_summary}"
            if transactions:
                for ft in transactions[:15]:
                    doc_section += f"\n  Transaction: {ft.get('payer', '?')} \u2192 {ft.get('payee', '?')}: {ft.get('amount', '?')} for {ft.get('for_what', 'n/a')}"
            if relationships:
                for r in relationships[:15]:
                    doc_section += f"\n  Relationship: {r.get('subject', '?')} \u2014[{r.get('type', '')}]\u2192 {r.get('object', '?')}"
            if events:
                for ev in events[:15]:
                    doc_section += f"\n  Event: [{ev.get('date', 'n/d')}] {ev.get('description', '')[:150]}"

        sections.append(doc_section)

    # Cross-collection discovery data (entities, relationships from OTHER documents)
    # Filter out data already in the deep-read docs
    deep_doc_names = {d['file_name'] for d in deep_docs}

    # Additional entities from discovery not in deep-read docs
    other_entities = [e for e in discovery_evidence.get('entities', [])
                      if not all(sf in deep_doc_names for sf in (e.get('source_files') or []))]
    if other_entities:
        lines = []
        for e in other_entities[:40]:
            sources = ", ".join(e.get('source_files', [])[:3]) if e.get('source_files') else "?"
            lines.append(f"  - {e['name']} ({e['type']}): {(e.get('context') or '')[:120]} | Sources: {sources}")
        sections.append(f"ADDITIONAL ENTITIES FROM OTHER DOCUMENTS ({len(other_entities)}):\n" + "\n".join(lines))

    # Additional transactions from other documents
    other_transactions = [ft for ft in discovery_evidence.get('financial_transactions', [])
                          if ft.get('file_name') not in deep_doc_names]
    if other_transactions:
        lines = []
        for ft in other_transactions[:20]:
            lines.append(f"  - [{ft.get('date', 'n/d')}] {ft.get('payer', '?')} \u2192 {ft.get('payee', '?')}: {ft.get('amount', '?')} | {doc_label(ft)}")
        sections.append(f"ADDITIONAL TRANSACTIONS FROM OTHER DOCUMENTS ({len(other_transactions)}):\n" + "\n".join(lines))

    # Additional relationships from other documents
    other_relationships = [r for r in discovery_evidence.get('relationships', [])
                           if r.get('file_name') not in deep_doc_names]
    if other_relationships:
        lines = []
        for r in other_relationships[:20]:
            lines.append(f"  - {r.get('subject', '?')} \u2014[{r.get('type', '')}]\u2192 {r.get('object', '?')} | {doc_label(r)}")
        sections.append(f"ADDITIONAL RELATIONSHIPS FROM OTHER DOCUMENTS ({len(other_relationships)}):\n" + "\n".join(lines))

    # Networks
    networks = discovery_evidence.get('networks', {})
    if networks:
        lines = []
        for person, connections in networks.items():
            lines.append(f"\n  Network for {person}:")
            for c in connections[:10]:
                lines.append(f"    - {c['name']} ({c['type']}): {c['shared_docs']} shared docs")
        sections.append("ENTITY NETWORKS:\n" + "\n".join(lines))

    return "\n\n".join(sections)


# ─────────────────────────────────────────────────
# CORPUS SYNTHESIS — all document summaries
# ─────────────────────────────────────────────────

def get_all_summaries(db_name: str) -> List[Dict]:
    """Get all documents that have summaries."""
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT d.id, d.file_name, d.display_title, d.collection, d.summary,
               d.page_count, d.summary_date
        FROM documents d
        WHERE d.summary IS NOT NULL
        ORDER BY d.collection, d.file_name
    """)
    results = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return results


def build_corpus_context(summaries: List[Dict]) -> str:
    """Build context block with all document summaries for corpus-wide synthesis."""
    lines = []
    current_collection = None
    for i, doc in enumerate(summaries):
        collection = doc.get('collection') or 'Unknown'
        if collection != current_collection:
            current_collection = collection
            lines.append(f"\n--- Collection: {collection} ---\n")
        name = doc.get('display_title') or doc.get('file_name', '')
        doc_date = extract_doc_date(doc.get('file_name', ''))
        date_label = f" ({doc_date})" if doc_date else ""
        lines.append(f"[Doc {i+1}] {name}{date_label}")
        lines.append(doc['summary'])
        lines.append("")
    return "\n".join(lines)


def analyze_corpus(question: str, summaries: List[Dict], db_stats: Dict,
                   model: str = "claude-opus-4-6") -> str:
    """Mode 4: Corpus-wide synthesis using all document summaries."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set."

    client = anthropic.Anthropic(api_key=api_key)
    corpus_context = build_corpus_context(summaries)

    # Count collections
    collections = set(d.get('collection', 'Unknown') for d in summaries)

    prompt = f"""You are a historian analyzing a complete archival collection about Native American land dispossession, federal Indian policy, and Bureau of Indian Affairs records.

You have analytical summaries of ALL {len(summaries)} documents in this collection, spanning {len(collections)} archival collections. Each summary captures the document type, key parties, specific actions, legal mechanisms, and evidentiary value. This is the ENTIRE corpus — you are seeing everything, not a sample.

DATABASE SCOPE: {db_stats.get('documents', 0)} documents, {db_stats.get('entities', 0)} entities, {db_stats.get('events', 0)} events, {db_stats.get('financial_transactions', 0)} transactions, {db_stats.get('relationships', 0)} relationships.

RESEARCH QUESTION: {question}

{corpus_context}

SYNTHESIS GUIDELINES:
1. Identify PATTERNS across documents: recurring actors, repeated legal mechanisms, systematic processes that appear across multiple documents and decades.
2. Construct TIMELINES: trace how specific actions (allotment, fee patents, land sales, legislative efforts) played out over time.
3. Map NETWORKS: which actors appear together across documents? Who were the key facilitators, opponents, and victims?
4. Trace MECHANISMS: how exactly did land pass from Native ownership to non-Indian ownership? What legal, administrative, and extralegal mechanisms do the documents reveal?
5. QUANTIFY where possible: total acreages, dollar amounts, numbers of allotments affected across the corpus.
6. Identify GAPS: what topics, time periods, or actors are poorly represented?
7. Cite specific documents by [Doc N] reference when making claims.
8. Distinguish between what the documents collectively PROVE and what they SUGGEST.
9. This is corpus-wide synthesis — prioritize patterns and systemic analysis over individual document summaries.

Begin your corpus-wide synthesis:"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        import traceback
        return f"Error during analysis: {type(e).__name__}: {str(e)}\n\n```\n{traceback.format_exc()}\n```"


# ─────────────────────────────────────────────────
# AI ANALYSIS — Discovery, Deep Read, Hybrid
# ─────────────────────────────────────────────────

def analyze_discovery(question: str, evidence: Dict, db_stats: Dict, model: str = "claude-opus-4-6") -> str:
    """Mode 1: Discovery analysis (same as v3)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set."

    client = anthropic.Anthropic(api_key=api_key)
    evidence_text = build_discovery_context(question, evidence)

    total_structured = (len(evidence.get('entities', [])) + len(evidence.get('events', [])) +
                        len(evidence.get('financial_transactions', [])) + len(evidence.get('relationships', [])))
    total_passages = sum(p['passage_count'] for p in evidence.get('passages', []))
    passage_docs = len(evidence.get('passages', []))

    prompt = f"""You are a historian analyzing evidence from an archival database about Native American land dispossession, federal Indian policy, and Bureau of Indian Affairs records.

DATABASE SCOPE: {db_stats.get('documents', 0)} documents processed, containing {db_stats.get('entities', 0)} entities, {db_stats.get('events', 0)} events, {db_stats.get('financial_transactions', 0)} financial transactions, and {db_stats.get('relationships', 0)} relationships. {db_stats.get('docs_with_text', 0)} documents have full text available.

YOU HAVE TWO TYPES OF EVIDENCE:
1. DOCUMENT TEXT PASSAGES: Actual excerpts from the source documents. These are your PRIMARY evidence — quote and cite them directly.
2. EXTRACTED ENTITIES/EVENTS/TRANSACTIONS/RELATIONSHIPS: Structured data extracted by AI from the documents. Use these to identify patterns, networks, and connections.

IMPORTANT CAVEATS:
- The text passages come from OCR'd historical documents and may contain OCR errors.
- Entity extraction is imperfect — names may be fragmented across variants.
- If evidence seems thin for a well-documented topic, the gap may be in the search, not the archive.
- DATING: Some documents include an approximate date (marked "c. YYYY" in the header). Use these dates when discussing what a document shows. Do NOT guess or infer dates for documents that lack a date marker. If a document has no date, say "undated" or cite only the filename. Never place undated evidence in a specific decade unless the document text itself contains an explicit date.

RESEARCH QUESTION: {question}

EVIDENCE SUMMARY: {total_structured} structured items + {total_passages} text passages from {passage_docs} documents

{evidence_text}

ANALYSIS GUIDELINES:
1. Lead with what the documents actually say. Quote specific passages and cite source documents by filename.
2. Use the structured entity/relationship data to identify patterns and networks that span multiple documents.
3. Organize thematically or chronologically, not by evidence type.
4. Where documents reveal specific mechanisms (how something was done, who authorized it, what legal basis was cited), describe those mechanisms in detail.
5. Note where evidence is strong vs. where gaps suggest more may exist under different search terms.
6. For financial transactions, trace the flow of money and land.
7. Use precise historical terminology. When citing a source, include its date if known (e.g., "Survey of Cond part 33 Montana.pdf, c. 1930s").
8. End with specific follow-up queries that would surface additional evidence from this database.

Begin your analysis:"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=8000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        import traceback
        return f"Error during analysis: {type(e).__name__}: {str(e)}\n\n```\n{traceback.format_exc()}\n```"


def analyze_deep_read(question: str, doc: Dict, db_stats: Dict, model: str = "claude-opus-4-6") -> str:
    """Mode 2: Deep Read — send full document text to AI."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set."

    client = anthropic.Anthropic(api_key=api_key)
    evidence_text = build_deep_read_context(doc)

    doc_date = extract_doc_date(doc.get('file_name', ''))
    date_note = f" Approximate document date from filename: {doc_date}." if doc_date else " No date could be determined from the filename — look for dates within the document text itself."

    prompt = f"""You are a historian conducting a deep reading of a single archival document from a collection about Native American land dispossession, federal Indian policy, and Bureau of Indian Affairs records.

DATABASE CONTEXT: This document is part of a collection of {db_stats.get('documents', 0)} processed documents containing {db_stats.get('entities', 0)} entities.{date_note}

You have been given the COMPLETE TEXT of this document, along with structured data (entities, events, transactions, relationships) that were previously extracted from it by AI. Your job is to read the full text carefully and provide deep analysis that goes beyond what automated extraction could capture.

RESEARCH QUESTION: {question}

{evidence_text}

DEEP READING GUIDELINES:
1. Read the full document text carefully. Identify the document's type, purpose, author(s), recipient(s), and date(s).
2. Trace the document's argument or narrative arc. What is it trying to accomplish? What legal, political, or administrative mechanisms does it describe or invoke?
3. Quote specific passages that are historically significant — the exact language matters for legal and policy analysis.
4. Identify what the AI extraction captured vs. what it missed. The full text likely contains nuance, implications, and context that entity extraction cannot capture.
5. Note any cross-references to other documents, cases, people, or events that suggest connections to the broader collection.
6. Pay attention to what is NOT said — silences, omissions, and implicit assumptions can be as revealing as explicit statements.
7. Assess the document's evidentiary value: What does it prove? What does it suggest? What questions does it raise?
8. End with specific research leads — other documents, names, or topics this document points to.

Begin your deep reading:"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=8000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        import traceback
        return f"Error during analysis: {type(e).__name__}: {str(e)}\n\n```\n{traceback.format_exc()}\n```"


def analyze_hybrid(question: str, discovery_evidence: Dict,
                    deep_docs: List[Dict], db_stats: Dict, model: str = "claude-opus-4-6") -> str:
    """Mode 3: Discovery → Deep Read hybrid."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set."

    client = anthropic.Anthropic(api_key=api_key)

    # Calculate token budget per doc based on how many we're sending
    # Sonnet limit: 200K tokens. Reserve 10K for system prompt, 8K for response,
    # 15K for discovery data = ~167K for document text.
    # But we need safety margin since token estimation is approximate.
    num_docs = len(deep_docs)
    HARD_BUDGET = 130000  # conservative — leaves ~70K for prompt overhead + discovery data + response
    tokens_per_doc = min(45000, HARD_BUDGET // max(1, num_docs))

    evidence_text = build_hybrid_context(question, discovery_evidence,
                                          deep_docs, max_doc_tokens=tokens_per_doc)

    # Safety check: estimate total prompt size and truncate if needed
    prompt_estimate = estimate_tokens(evidence_text)
    if prompt_estimate > 170000:
        # Emergency truncation — cut evidence text to fit
        safe_chars = int(170000 * 3.2)
        evidence_text = evidence_text[:safe_chars] + "\n\n[... EVIDENCE TRUNCATED TO FIT CONTEXT WINDOW ...]"

    doc_names = [doc_label(d) for d in deep_docs]
    total_other = (len(discovery_evidence.get('entities', [])) +
                   len(discovery_evidence.get('financial_transactions', [])) +
                   len(discovery_evidence.get('relationships', [])))

    prompt = f"""You are a historian conducting comprehensive research using an archival database about Native American land dispossession, federal Indian policy, and Bureau of Indian Affairs records.

DATABASE SCOPE: {db_stats.get('documents', 0)} documents processed, containing {db_stats.get('entities', 0)} entities, {db_stats.get('events', 0)} events, {db_stats.get('financial_transactions', 0)} financial transactions, and {db_stats.get('relationships', 0)} relationships.

YOU HAVE TWO LEVELS OF EVIDENCE:
1. FULL DOCUMENT TEXTS: The complete text of {num_docs} top-ranked documents: {', '.join(doc_names)}. Read these deeply — quote them, trace their arguments, identify mechanisms.
2. CROSS-COLLECTION DATA: Entities, transactions, and relationships from additional documents beyond those {num_docs}. Use these to identify patterns and connections the full texts alone wouldn't reveal.

IMPORTANT CAVEATS:
- Texts are OCR'd and may contain errors.
- Entity extraction is imperfect.
- The full documents were selected as the most relevant by entity count and search term matching. Other relevant documents may exist.
- DATING: Some documents include an approximate date (marked "c. YYYY" in headers). Use these dates when discussing what a document shows. Do NOT guess dates for undated documents — say "undated" or cite only the filename. Never place undated evidence in a specific decade unless the document text itself contains an explicit date.

RESEARCH QUESTION: {question}

{evidence_text}

ANALYSIS GUIDELINES:
1. Start with the full documents. Read them carefully and build your analysis from their actual content. Quote specific language.
2. Layer in the cross-collection data to show how the full documents connect to the broader archival record.
3. Organize by theme or chronology, not by document. Weave evidence from multiple sources into a coherent narrative.
4. Trace specific mechanisms: legal authorities, administrative procedures, financial flows, and chains of responsibility.
5. Where the full documents and the cross-collection data tell different or complementary stories, note what each adds.
6. Identify what these documents prove, what they suggest, and what remains uncertain. When citing a source, include its date if known.
7. End with specific follow-up queries for this database.

Begin your analysis:"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=8000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        import traceback
        return f"Error during analysis: {type(e).__name__}: {str(e)}\n\n```\n{traceback.format_exc()}\n```"


# ─────────────────────────────────────────────────
# STREAMLIT UI
# ─────────────────────────────────────────────────

st.title("\U0001f4dc Historical Document Analysis v4")
st.markdown("*Three modes: Discovery \u2022 Deep Read \u2022 Discovery \u2192 Deep Read*")

# Sidebar
with st.sidebar:
    st.header("Database")
    available_dbs = get_available_databases()
    selected_db = st.selectbox(
        "Select database:", available_dbs,
        index=available_dbs.index("crow_historical_docs") if "crow_historical_docs" in available_dbs else 0
    )

    stats = get_db_stats(selected_db)

    if stats.get('error'):
        st.error(f"Connection error: {stats['error']}")
    else:
        st.metric("Documents", f"{stats['documents']:,}")
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Entities", f"{stats['entities']:,}")
            st.metric("Events", f"{stats['events']:,}")
        with col_b:
            st.metric("Transactions", f"{stats['financial_transactions']:,}")
            st.metric("Relationships", f"{stats['relationships']:,}")

        st.metric("Docs with full text", f"{stats.get('docs_with_text', 0):,}")

        st.markdown("---")
        st.markdown("**Entity types:**")
        for etype, count in stats.get('entity_types', {}).items():
            st.text(f"  {etype}: {count:,}")

    ai_model = "claude-opus-4-6"
    max_passage_docs = 30
    passages_per_doc = 5
    hybrid_doc_count = 5


# ─────────────────────────────────────────────────
# MODE SELECTION
# ─────────────────────────────────────────────────

mode = st.radio(
    "Analysis Mode:",
    [
        "\U0001f50d **Discovery** — Search everything, find cross-collection connections",
        "\U0001f4d6 **Deep Read** — Select a document, send full text to AI",
        "\U0001f50d\u2192\U0001f4d6 **Discovery \u2192 Deep Read** — Find top documents, then read them deeply",
        "\U0001f3db\ufe0f **Corpus Synthesis** — Analyze ALL documents for corpus-wide patterns",
    ],
    index=0,
    help="Discovery = breadth. Deep Read = depth. Hybrid = both. Corpus = everything."
)

mode_key = mode.split("**")[1].split("**")[0].strip() if "**" in mode else "Discovery"

st.markdown("---")


# ═════════════════════════════════════════════════
# MODE 1: DISCOVERY
# ═════════════════════════════════════════════════
if mode_key == "Discovery":
    question = st.text_area(
        "Research question:",
        placeholder="e.g., Tell me about Crow fee patents and James Murray",
        height=100
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        run_analysis = st.button("\U0001f50d Search & Analyze", type="primary")
    with col2:
        search_only = st.button("\U0001f4cb Search Only (no AI)")

    if run_analysis or search_only:
        if not question:
            st.warning("Please enter a research question.")
        else:
            st.markdown("---")

            with st.spinner("Layer 1: Searching entity database..."):
                evidence = {
                    'entities': search_entities(selected_db, question),
                    'events': search_events(selected_db, question),
                    'financial_transactions': search_financial_transactions(selected_db, question),
                    'relationships': search_relationships(selected_db, question),
                }

            with st.spinner("Layer 2: Retrieving full-text passages..."):
                evidence['passages'] = search_full_text_passages(
                    selected_db, question,
                    max_docs=max_passage_docs,
                    max_passages_per_doc=passages_per_doc
                )

            with st.spinner("Building entity networks..."):
                evidence['documents'] = search_documents_metadata(selected_db, question)
                person_entities = [e for e in evidence['entities']
                                   if e['type'] == 'person' and e.get('doc_count', 0) >= 2]
                if person_entities and len(person_entities) <= 10:
                    networks = {}
                    for person in person_entities[:5]:
                        net = get_entity_network(selected_db, person['name'])
                        if net:
                            networks[person['name']] = net
                    evidence['networks'] = networks
                else:
                    evidence['networks'] = {}

            # Summary
            passage_count = sum(p['passage_count'] for p in evidence.get('passages', []))
            counts = {
                'Entities': len(evidence['entities']),
                'Events': len(evidence['events']),
                'Transactions': len(evidence['financial_transactions']),
                'Relationships': len(evidence['relationships']),
                'Text Passages': passage_count,
                'Documents': len(evidence['documents']),
            }
            count_str = " | ".join([f"**{k}:** {v}" for k, v in counts.items() if v > 0])
            st.success(f"Evidence found: {count_str}")

            # Evidence browser
            with st.expander("\U0001f50e Browse Raw Evidence", expanded=False):
                tabs = st.tabs(["\U0001f4c4 Passages", "\U0001f3f7\ufe0f Entities", "\U0001f4c5 Events",
                               "\U0001f4b0 Transactions", "\U0001f517 Relationships", "\U0001f578\ufe0f Networks"])

                with tabs[0]:
                    if evidence['passages']:
                        for doc in evidence['passages']:
                            st.markdown(f"### \U0001f4c4 {doc_label(doc)}")
                            st.caption(f"Collection: {doc.get('collection', 'n/a')} | "
                                       f"Pipeline: {doc.get('pipeline_version', 'n/a')}")
                            for i, passage in enumerate(doc['passages']):
                                st.markdown(f"**Passage {i+1}:**")
                                st.text_area(f"p_{doc['file_name']}_{i}", passage[:1000],
                                             height=150, label_visibility="collapsed", disabled=True)
                            st.markdown("---")
                    else:
                        st.info("No full-text passages found.")

                with tabs[1]:
                    for e in evidence['entities'][:50]:
                        sources = ", ".join(e.get('source_display_names', e.get('source_files', []))[:3]) if e.get('source_files') else ""
                        st.markdown(f"**{e['name']}** ({e['type']}) \u2014 {e.get('doc_count', 0)} docs"
                                    f" {'\u2b50' if e.get('relevance_score', 0) > 500 else ''}")
                        if e.get('context'):
                            st.caption(e['context'][:300])
                        if sources:
                            st.caption(f"\U0001f4c4 {sources}")
                        st.markdown("---")

                with tabs[2]:
                    for ev in evidence['events'][:30]:
                        st.markdown(f"**[{ev.get('date', 'n/d')}]** {ev.get('type', '')} \u2014 {ev.get('description', '')[:200]}")
                        st.caption(f"\U0001f4c4 {doc_label(ev)}")

                with tabs[3]:
                    for ft in evidence['financial_transactions'][:20]:
                        st.markdown(f"**{ft.get('payer', '?')}** \u2192 **{ft.get('payee', '?')}**: {ft.get('amount', '?')}")
                        st.caption(f"{ft.get('for_what', '')} [{ft.get('date', 'n/d')}] | "
                                   f"Context: {(ft.get('context') or '')[:150]}")
                        st.caption(f"\U0001f4c4 {doc_label(ft)}")

                with tabs[4]:
                    for r in evidence['relationships'][:30]:
                        st.markdown(f"**{r.get('subject', '?')}** \u2014[{r.get('type', '')}]\u2192 **{r.get('object', '?')}**")
                        if r.get('context'):
                            st.caption(r['context'][:200])
                        st.caption(f"\U0001f4c4 {doc_label(r)}")

                with tabs[5]:
                    for person, connections in evidence.get('networks', {}).items():
                        st.markdown(f"**Network: {person}**")
                        for c in connections[:15]:
                            st.text(f"  \u2194 {c['name']} ({c['type']}) \u2014 {c['shared_docs']} shared docs")
                        st.markdown("---")

            # AI Analysis
            if run_analysis:
                st.markdown("---")
                st.subheader("\U0001f4d6 AI Analysis (Discovery Mode)")
                with st.spinner("Analyzing evidence..."):
                    analysis = analyze_discovery(question, evidence, stats, model=ai_model)
                st.markdown(escape_dollars(analysis))

                st.markdown("---")
                st.caption(
                    "\u26a0\ufe0f Discovery mode: full-text passages + extracted entities. "
                    "For deeper analysis of specific documents, try Deep Read mode. "
                    f"({passage_count} passages from {len(evidence.get('passages', []))} docs "
                    f"+ {len(evidence['entities'])} entities)"
                )


# ═════════════════════════════════════════════════
# MODE 2: DEEP READ
# ═════════════════════════════════════════════════
elif mode_key == "Deep Read":
    st.markdown("Select a document to send its **complete text** to the AI for deep analysis.")

    # Document search/filter
    doc_filter = st.text_input("Filter documents:", placeholder="Type to search by filename or content...")
    docs = list_documents(selected_db, doc_filter)

    if not docs:
        st.info("No documents found. Try a different search term.")
    else:
        # Show documents with metadata
        doc_options = []
        for d in docs:
            text_len = d.get('text_length') or 0
            est_pages = max(1, text_len // 3000) if text_len else 0
            has_text = "\u2705" if d.get('has_text') else "\u274c"
            doc_options.append(
                f"{has_text} {doc_label(d)} "
                f"({d.get('entity_count', 0)} entities, ~{est_pages} pages)"
            )

        selected_idx = st.selectbox(
            f"Select document ({len(docs)} found):",
            range(len(doc_options)),
            format_func=lambda i: doc_options[i]
        )

        selected_doc_info = docs[selected_idx]
        text_len = selected_doc_info.get('text_length') or 0
        est_tokens = text_len // 4
        est_pages = max(1, text_len // 3000) if text_len else 0

        # Document info
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Entities", selected_doc_info.get('entity_count', 0))
        with col_b:
            st.metric("Est. Pages", est_pages)
        with col_c:
            st.metric("Est. Tokens", f"{est_tokens:,}")

        if est_tokens > 150000:
            st.warning(f"This document is very large (~{est_tokens:,} tokens). "
                       f"It will be truncated to fit the AI context window (~150K tokens).")

        if not selected_doc_info.get('has_text'):
            st.error("This document has no extracted text. Deep Read requires full text.")
        else:
            question = st.text_area(
                "Research question (or leave blank for general analysis):",
                placeholder="e.g., What legal mechanisms does this document describe?",
                height=80
            )

            if st.button("\U0001f4d6 Deep Read", type="primary"):
                if not question:
                    question = f"Provide a comprehensive analysis of this document: {doc_label(selected_doc_info)}"

                with st.spinner(f"Loading full document..."):
                    doc = get_document_full(selected_db, selected_doc_info['id'])

                if not doc:
                    st.error("Failed to load document.")
                else:
                    # Show document stats
                    full_text = doc.get('full_text', '')
                    actual_tokens = estimate_tokens(full_text)
                    st.info(f"Loaded: {doc_label(doc)} | "
                            f"{len(doc.get('entities', []))} entities, "
                            f"{len(doc.get('events', []))} events, "
                            f"{len(doc.get('transactions', []))} transactions, "
                            f"{len(doc.get('relationships', []))} relationships | "
                            f"~{actual_tokens:,} tokens of text")

                    with st.expander("Preview document text", expanded=False):
                        st.text_area("doc_preview", full_text[:5000],
                                     height=300, disabled=True, label_visibility="collapsed")
                        if len(full_text) > 5000:
                            st.caption(f"Showing first 5,000 of {len(full_text):,} characters")

                    st.markdown("---")
                    st.subheader("\U0001f4d6 AI Deep Reading")
                    with st.spinner("AI is reading the full document..."):
                        analysis = analyze_deep_read(question, doc, stats, model=ai_model)
                    st.markdown(escape_dollars(analysis))

                    st.markdown("---")
                    st.caption(
                        f"\u26a0\ufe0f Deep Read: AI analyzed the full text of {doc_label(doc)} "
                        f"(~{actual_tokens:,} tokens). For cross-collection analysis, "
                        f"try Discovery or Hybrid mode."
                    )


# ═════════════════════════════════════════════════
# MODE 3: DISCOVERY → DEEP READ (with document picker)
# ═════════════════════════════════════════════════
elif "Deep Read" in mode_key and "Discovery" in mode_key:
    st.markdown(
        "**Step 1:** Run Discovery to find relevant documents. "
        "**Step 2:** Pick which documents to deep-read. "
        "**Step 3:** AI reads full texts + cross-collection data."
    )

    question = st.text_area(
        "Research question:",
        placeholder="e.g., What were the mechanisms of forced fee patent issuance on Crow reservation?",
        height=100,
        key="hybrid_question"
    )

    # Initialize session state for hybrid mode
    if 'hybrid_evidence' not in st.session_state:
        st.session_state.hybrid_evidence = None
    if 'hybrid_ranked' not in st.session_state:
        st.session_state.hybrid_ranked = None
    if 'hybrid_question_run' not in st.session_state:
        st.session_state.hybrid_question_run = None

    # ── STEP 1: Discovery ──
    if st.button("\U0001f50d Step 1: Run Discovery", type="primary"):
        if not question:
            st.warning("Please enter a research question.")
        else:
            with st.spinner("Searching entity database..."):
                evidence = {
                    'entities': search_entities(selected_db, question),
                    'events': search_events(selected_db, question),
                    'financial_transactions': search_financial_transactions(selected_db, question),
                    'relationships': search_relationships(selected_db, question),
                }

            with st.spinner("Retrieving full-text passages..."):
                evidence['passages'] = search_full_text_passages(
                    selected_db, question,
                    max_docs=max_passage_docs,
                    max_passages_per_doc=passages_per_doc
                )

            with st.spinner("Building entity networks..."):
                evidence['documents'] = search_documents_metadata(selected_db, question)
                person_entities = [e for e in evidence['entities']
                                   if e['type'] == 'person' and e.get('doc_count', 0) >= 2]
                if person_entities and len(person_entities) <= 10:
                    networks = {}
                    for person in person_entities[:5]:
                        net = get_entity_network(selected_db, person['name'])
                        if net:
                            networks[person['name']] = net
                    evidence['networks'] = networks
                else:
                    evidence['networks'] = {}

            with st.spinner("Ranking documents for deep reading..."):
                ranked_docs = rank_documents_for_deep_read(selected_db, question)

            # Store in session state
            st.session_state.hybrid_evidence = evidence
            st.session_state.hybrid_ranked = ranked_docs
            st.session_state.hybrid_question_run = question
            st.rerun()

    # ── Show results and document picker if Discovery has been run ──
    if st.session_state.hybrid_evidence is not None and st.session_state.hybrid_ranked is not None:
        evidence = st.session_state.hybrid_evidence
        ranked_docs = st.session_state.hybrid_ranked
        discovery_question = st.session_state.hybrid_question_run

        # Discovery summary
        passage_count = sum(p['passage_count'] for p in evidence.get('passages', []))
        counts = {
            'Entities': len(evidence['entities']),
            'Events': len(evidence['events']),
            'Transactions': len(evidence['financial_transactions']),
            'Relationships': len(evidence['relationships']),
            'Text Passages': passage_count,
            'Documents': len(evidence['documents']),
        }
        count_str = " | ".join([f"**{k}:** {v}" for k, v in counts.items() if v > 0])
        st.success(f"Discovery found: {count_str}")

        # Evidence browser
        with st.expander("\U0001f50e Browse Discovery Evidence", expanded=False):
            tabs = st.tabs(["\U0001f4c4 Passages", "\U0001f3f7\ufe0f Entities",
                           "\U0001f4b0 Transactions", "\U0001f517 Relationships"])
            with tabs[0]:
                if evidence['passages']:
                    for doc in evidence['passages']:
                        st.markdown(f"### {doc_label(doc)}")
                        for i, passage in enumerate(doc['passages']):
                            st.text_area(f"hp_{doc['file_name']}_{i}", passage[:800],
                                         height=120, label_visibility="collapsed", disabled=True)
                        st.markdown("---")
            with tabs[1]:
                for e in evidence['entities'][:30]:
                    st.markdown(f"**{e['name']}** ({e['type']}) \u2014 {e.get('doc_count', 0)} docs")
            with tabs[2]:
                for ft in evidence['financial_transactions'][:15]:
                    st.markdown(f"**{ft.get('payer', '?')}** \u2192 **{ft.get('payee', '?')}**: {ft.get('amount', '?')}")
            with tabs[3]:
                for r in evidence['relationships'][:15]:
                    st.markdown(f"**{r.get('subject', '?')}** \u2014[{r.get('type', '')}]\u2192 **{r.get('object', '?')}**")

        # ── STEP 2: Document picker ──
        st.markdown("---")
        st.subheader("Step 2: Select documents for Deep Read")
        st.markdown("The AI-ranked suggestions are pre-selected. "
                    "**Add or remove documents** based on what Discovery found.")

        if ranked_docs:
            # Build selection options with metadata
            doc_options = []
            for rd in ranked_docs:
                label = (f"{doc_label(rd)}  "
                        f"(score: {rd['score']:.1f}, "
                        f"hits: {rd.get('term_hits', 0)}, "
                        f"~{rd['est_tokens']:,} tok, "
                        f"{rd.get('entity_count', 0)} ent, "
                        f"{rd.get('transaction_count', 0)} txn)")
                doc_options.append(label)

            # Pre-select top N by default
            default_selections = list(range(min(hybrid_doc_count, len(doc_options))))

            selected_indices = st.multiselect(
                f"Select documents to deep-read ({len(ranked_docs)} available):",
                options=range(len(doc_options)),
                default=default_selections,
                format_func=lambda i: doc_options[i],
                key="doc_picker"
            )

            # Show token budget estimate
            if selected_indices:
                selected_filenames = [ranked_docs[i]['file_name'] for i in selected_indices]
                total_est_tokens = sum(ranked_docs[i]['est_tokens'] for i in selected_indices)
                token_budget = 130000
                tokens_per_doc = token_budget // max(1, len(selected_indices))

                if total_est_tokens > token_budget:
                    st.warning(
                        f"Selected documents total ~{total_est_tokens:,} tokens, "
                        f"exceeding the {token_budget:,} token budget. "
                        f"Each document will be truncated to ~{tokens_per_doc:,} tokens. "
                        f"Consider selecting fewer documents for deeper reading."
                    )
                else:
                    st.info(
                        f"Selected {len(selected_indices)} documents, "
                        f"~{total_est_tokens:,} tokens total "
                        f"(budget: {token_budget:,}). All will be read in full."
                    )

                # ── STEP 3: Run Deep Read ──
                if st.button("\U0001f4d6 Step 3: Deep Read Selected Documents", type="primary"):
                    with st.spinner(f"Loading {len(selected_indices)} full documents..."):
                        deep_docs = get_documents_full_by_names(selected_db, selected_filenames)
                        deep_docs = [d for d in deep_docs if d.get('full_text')]

                    if not deep_docs:
                        st.warning("No documents with full text found. Running Discovery-only analysis.")
                        with st.spinner("Analyzing with Discovery evidence..."):
                            analysis = analyze_discovery(
                                discovery_question, evidence, stats, model=ai_model)
                    else:
                        # Show what's being read
                        total_tokens = 0
                        doc_info_lines = []
                        for d in deep_docs:
                            tokens = estimate_tokens(d.get('full_text', ''))
                            total_tokens += tokens
                            doc_info_lines.append(
                                f"  \U0001f4c4 **{doc_label(d)}** — ~{tokens:,} tokens, "
                                f"{len(d.get('entities', []))} entities, "
                                f"{len(d.get('transactions', []))} transactions"
                            )

                        st.info(
                            f"Deep reading {len(deep_docs)} documents "
                            f"(~{total_tokens:,} tokens total):\n\n"
                            + "\n".join(doc_info_lines)
                        )

                        st.markdown("---")
                        st.subheader("\U0001f4d6 AI Analysis (Discovery + Deep Read)")
                        with st.spinner(
                            f"AI is reading {len(deep_docs)} full documents "
                            f"+ cross-collection data..."
                        ):
                            analysis = analyze_hybrid(
                                discovery_question, evidence, deep_docs, stats, model=ai_model)

                    st.markdown(escape_dollars(analysis))

                    st.markdown("---")
                    deep_doc_names = ", ".join(
                        [doc_label(d) for d in deep_docs]) if deep_docs else "none"
                    st.caption(
                        f"\u26a0\ufe0f Hybrid mode: Deep-read {len(deep_docs)} documents "
                        f"({deep_doc_names}) "
                        f"+ {len(evidence['entities'])} entities "
                        f"+ {len(evidence.get('financial_transactions', []))} "
                        f"transactions from cross-collection discovery."
                    )
            else:
                st.warning("Select at least one document for deep reading.")
        else:
            st.warning("No documents found matching your query.")


# ═════════════════════════════════════════════════
# MODE 4: CORPUS SYNTHESIS
# ═════════════════════════════════════════════════
elif mode_key == "Corpus Synthesis":
    st.markdown(
        "Send **all** document summaries to the AI for corpus-wide pattern analysis. "
        "No context window limit — the AI sees every document in the collection."
    )

    # Check summary availability
    summaries = get_all_summaries(selected_db)
    total_docs = stats.get('documents', 0)
    summarized = len(summaries)

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Documents with summaries", f"{summarized:,}")
    with col_b:
        st.metric("Total documents", f"{total_docs:,}")

    if summarized < total_docs:
        unsummarized = total_docs - summarized
        st.warning(
            f"{unsummarized} documents lack summaries. "
            f"Run `python3 enrich_summaries.py` to generate them."
        )

    if summarized == 0:
        st.error("No document summaries available. Run `python3 enrich_summaries.py` first.")
    else:
        est_words = sum(len((s.get('summary') or '').split()) for s in summaries)
        est_tokens = int(est_words * 1.33)
        st.caption(f"~{est_words:,} words / ~{est_tokens:,} tokens in summaries")

        question = st.text_area(
            "Research question:",
            placeholder="e.g., What were the primary mechanisms of Crow land dispossession and who were the key actors?",
            height=100,
            key="corpus_question"
        )

        if st.button("\U0001f3db\ufe0f Synthesize Across Entire Corpus", type="primary"):
            if not question:
                st.warning("Please enter a research question.")
            else:
                with st.expander(f"Document summaries sent to AI ({summarized})", expanded=False):
                    for i, s in enumerate(summaries):
                        name = s.get('display_title') or s.get('file_name', '')
                        st.markdown(f"**[Doc {i+1}]** {name}")
                        st.caption(s.get('summary', '')[:300] + "...")
                        if (i + 1) % 50 == 0:
                            st.markdown("---")

                st.markdown("---")
                st.subheader("\U0001f3db\ufe0f AI Corpus-Wide Synthesis")
                with st.spinner(
                    f"AI is analyzing summaries of all {summarized} documents..."
                ):
                    analysis = analyze_corpus(question, summaries, stats)
                st.markdown(escape_dollars(analysis))

                st.markdown("---")
                st.caption(
                    f"\U0001f3db\ufe0f Corpus Synthesis: AI analyzed summaries of all "
                    f"{summarized} documents (~{est_tokens:,} tokens). "
                    f"For deep reading of specific documents, use Deep Read or Hybrid mode."
                )


# Footer
st.markdown("---")
st.caption(
    f"v4 \u2014 Four modes: Discovery \u2022 Deep Read \u2022 Hybrid \u2022 Corpus Synthesis | "
    f"Database: {selected_db if 'selected_db' in dir() else 'not connected'}"
)
