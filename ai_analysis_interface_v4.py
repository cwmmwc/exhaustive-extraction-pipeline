#!/usr/bin/env python3
"""
AI Analysis Interface v4 — Five Analysis Modes

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
import json
import math
from typing import List, Dict, Optional, Tuple

st.set_page_config(
    page_title="Historical Document Analysis",
    page_icon="\U0001f3db\ufe0f",
    layout="wide"
)

# ─────────────────────────────────────────────────
# CUSTOM STYLING
# ─────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Color palette: warm archival tones ── */
:root {
    --parchment: #faf6f0;
    --ink: #2c2418;
    --sepia: #8b7355;
    --accent: #6b4c3b;
    --accent-light: #d4c4b0;
    --highlight: #e8ddd0;
    --border: #d5cec4;
    --success-bg: #e8f0e4;
    --info-bg: #eae4f0;
}

/* ── Main container ── */
.main .block-container {
    padding-top: 2rem;
    max-width: 1100px;
}

/* ── Header area ── */
.app-header {
    border-bottom: 2px solid var(--accent-light);
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
}
.app-header h1 {
    font-family: 'Georgia', 'Times New Roman', serif;
    color: var(--ink);
    font-size: 2rem;
    font-weight: 600;
    margin-bottom: 0.2rem;
    letter-spacing: -0.02em;
}
.app-header .subtitle {
    color: var(--sepia);
    font-size: 0.95rem;
    margin-top: 0;
}

/* ── Mode selector (horizontal radio) ── */
div[data-testid="stRadio"] > div {
    flex-direction: row;
    gap: 0.5rem;
    flex-wrap: wrap;
}
div[data-testid="stRadio"] > div > label {
    background: var(--parchment);
    border: 1.5px solid var(--border);
    border-radius: 8px;
    padding: 0.5rem 1rem;
    cursor: pointer;
    transition: all 0.15s;
    font-size: 0.9rem;
}
div[data-testid="stRadio"] > div > label:hover {
    border-color: var(--accent);
    background: var(--highlight);
}
div[data-testid="stRadio"] > div > label[data-checked="true"],
div[data-testid="stRadio"] > div > label:has(input:checked) {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
}

/* ── Mode description box ── */
.mode-desc {
    background: var(--parchment);
    border-left: 3px solid var(--accent);
    padding: 0.8rem 1rem;
    margin: 0.5rem 0 1.5rem 0;
    border-radius: 0 6px 6px 0;
    font-size: 0.92rem;
    color: var(--ink);
}

/* ── Sidebar styling ── */
section[data-testid="stSidebar"] {
    background: var(--parchment);
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem;
}
.sidebar-section {
    background: white;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.8rem;
}
.sidebar-section h4 {
    color: var(--accent);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 0 0 0.5rem 0;
    font-weight: 600;
}
.stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.4rem;
}
.stat-item {
    text-align: center;
    padding: 0.4rem;
}
.stat-item .stat-value {
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--ink);
    line-height: 1.2;
}
.stat-item .stat-label {
    font-size: 0.72rem;
    color: var(--sepia);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* ── Section headers ── */
.section-header {
    font-family: 'Georgia', 'Times New Roman', serif;
    color: var(--ink);
    border-bottom: 1px solid var(--accent-light);
    padding-bottom: 0.4rem;
    margin-top: 1.5rem;
    font-size: 1.3rem;
}

/* ── Evidence cards ── */
.stExpander {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

/* ── Footer ── */
.app-footer {
    border-top: 1px solid var(--border);
    padding-top: 0.8rem;
    margin-top: 2rem;
    text-align: center;
    color: var(--sepia);
    font-size: 0.82rem;
}
.app-footer a {
    color: var(--accent);
}

/* ── Better button styling ── */
.stButton > button[kind="primary"] {
    background-color: var(--accent);
    border-color: var(--accent);
}
.stButton > button[kind="primary"]:hover {
    background-color: var(--ink);
    border-color: var(--ink);
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.85rem;
}

/* ── Clean up metric display ── */
[data-testid="stMetric"] {
    background: var(--parchment);
    border-radius: 6px;
    padding: 0.5rem 0.8rem;
    border: 1px solid var(--border);
}
[data-testid="stMetricValue"] {
    font-size: 1.4rem;
}
</style>
""", unsafe_allow_html=True)

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
            WHERE datname IN ('crow_historical_docs', 'historical_docs', 'full_corpus_docs')
               OR datname LIKE '%_historical_%'
               OR datname LIKE '%_corpus_%'
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
        for table in ['financial_transactions', 'relationships',
                      'fee_patents', 'correspondence', 'legislative_actions']:
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


def search_fee_patents(db_name: str, query: str, limit: int = 50) -> List[Dict]:
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        terms = [query.strip()]
    conditions = " OR ".join(
        ["fp.allottee ILIKE %s OR fp.allotment_number ILIKE %s OR fp.subsequent_buyer ILIKE %s "
         "OR fp.attorney ILIKE %s OR fp.trust_to_fee_mechanism ILIKE %s OR fp.context ILIKE %s"] * len(terms)
    )
    params = []
    for t in terms:
        params.extend([f"%{t}%"] * 6)
    try:
        cur.execute(f"""
            SELECT fp.allottee, fp.allotment_number, fp.acreage, fp.land_description,
                   fp.patent_date, fp.patent_number, fp.trust_to_fee_mechanism,
                   fp.subsequent_buyer, fp.sale_price, fp.sale_date,
                   fp.attorney, fp.mortgage_amount, fp.mortgage_holder, fp.context,
                   d.file_name, d.display_title
            FROM fee_patents fp
            JOIN documents d ON fp.document_id = d.id
            WHERE {conditions}
            ORDER BY fp.patent_date ASC NULLS LAST
            LIMIT %s
        """, params + [limit])
        results = [dict(row) for row in cur.fetchall()]
    except Exception:
        results = []
    cur.close()
    conn.close()
    return results


def search_correspondence(db_name: str, query: str, limit: int = 50) -> List[Dict]:
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        terms = [query.strip()]
    conditions = " OR ".join(
        ["c.sender ILIKE %s OR c.recipient ILIKE %s OR c.sender_title ILIKE %s "
         "OR c.recipient_title ILIKE %s OR c.subject ILIKE %s OR c.context ILIKE %s"] * len(terms)
    )
    params = []
    for t in terms:
        params.extend([f"%{t}%"] * 6)
    try:
        cur.execute(f"""
            SELECT c.sender, c.sender_title, c.recipient, c.recipient_title,
                   c.date, c.subject, c.action_requested, c.outcome, c.context,
                   d.file_name, d.display_title
            FROM correspondence c
            JOIN documents d ON c.document_id = d.id
            WHERE {conditions}
            ORDER BY c.date ASC NULLS LAST
            LIMIT %s
        """, params + [limit])
        results = [dict(row) for row in cur.fetchall()]
    except Exception:
        results = []
    cur.close()
    conn.close()
    return results


def search_legislative_actions(db_name: str, query: str, limit: int = 50) -> List[Dict]:
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        terms = [query.strip()]
    conditions = " OR ".join(
        ["la.bill_number ILIKE %s OR la.bill_title ILIKE %s OR la.sponsor ILIKE %s "
         "OR la.action_type ILIKE %s OR la.outcome ILIKE %s OR la.context ILIKE %s"] * len(terms)
    )
    params = []
    for t in terms:
        params.extend([f"%{t}%"] * 6)
    try:
        cur.execute(f"""
            SELECT la.bill_number, la.bill_title, la.sponsor, la.co_sponsors,
                   la.action_type, la.action_date, la.vote_count, la.committee,
                   la.outcome, la.context,
                   d.file_name, d.display_title
            FROM legislative_actions la
            JOIN documents d ON la.document_id = d.id
            WHERE {conditions}
            ORDER BY la.action_date ASC NULLS LAST
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

    # Fee patents (v3)
    fee_patents = evidence.get('fee_patents', [])
    if fee_patents:
        lines = []
        for fp in fee_patents[:30]:
            parts = [f"Allottee: {fp.get('allottee', '?')}"]
            if fp.get('allotment_number'):
                parts.append(f"Allotment: {fp['allotment_number']}")
            if fp.get('acreage'):
                parts.append(f"Acreage: {fp['acreage']}")
            if fp.get('patent_date'):
                parts.append(f"Patent date: {fp['patent_date']}")
            if fp.get('trust_to_fee_mechanism'):
                parts.append(f"Mechanism: {fp['trust_to_fee_mechanism']}")
            if fp.get('subsequent_buyer'):
                parts.append(f"Sold to: {fp['subsequent_buyer']}")
            if fp.get('sale_price'):
                parts.append(f"Sale price: {fp['sale_price']}")
            if fp.get('attorney'):
                parts.append(f"Attorney: {fp['attorney']}")
            if fp.get('mortgage_amount'):
                parts.append(f"Mortgage: {fp['mortgage_amount']} to {fp.get('mortgage_holder', '?')}")
            lines.append(f"  - {' | '.join(parts)}")
            lines.append(f"    Source: {doc_label(fp)}")
        sections.append(f"FEE PATENTS ({len(fee_patents)} total — the atomic unit of land dispossession):\n" + "\n".join(lines))

    # Correspondence (v3)
    correspondence = evidence.get('correspondence', [])
    if correspondence:
        lines = []
        for c in correspondence[:30]:
            sender = c.get('sender', '?')
            s_title = f" ({c['sender_title']})" if c.get('sender_title') else ""
            recipient = c.get('recipient', '?')
            r_title = f" ({c['recipient_title']})" if c.get('recipient_title') else ""
            date = c.get('date', 'n/d')
            lines.append(f"  - [{date}] {sender}{s_title} \u2192 {recipient}{r_title}")
            if c.get('subject'):
                lines.append(f"    Subject: {c['subject'][:200]}")
            if c.get('action_requested'):
                lines.append(f"    Action requested: {c['action_requested'][:200]}")
            if c.get('outcome'):
                lines.append(f"    Outcome: {c['outcome'][:200]}")
            lines.append(f"    Source: {doc_label(c)}")
        sections.append(f"CORRESPONDENCE ({len(correspondence)} total — bureaucratic network):\n" + "\n".join(lines))

    # Legislative actions (v3)
    legislative = evidence.get('legislative_actions', [])
    if legislative:
        lines = []
        for la in legislative[:30]:
            bill = la.get('bill_number', '?')
            action = la.get('action_type', '?')
            date = la.get('action_date', 'n/d')
            parts = [f"[{date}] {bill}: {action}"]
            if la.get('bill_title'):
                parts.append(f"Title: {la['bill_title']}")
            if la.get('sponsor'):
                parts.append(f"Sponsor: {la['sponsor']}")
            if la.get('vote_count'):
                parts.append(f"Vote: {la['vote_count']}")
            if la.get('committee'):
                parts.append(f"Committee: {la['committee']}")
            if la.get('outcome'):
                parts.append(f"Outcome: {la['outcome']}")
            lines.append(f"  - {' | '.join(parts)}")
            lines.append(f"    Source: {doc_label(la)}")
        sections.append(f"LEGISLATIVE ACTIONS ({len(legislative)} total — bill lifecycle tracking):\n" + "\n".join(lines))

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
    """Build context block with all document summaries for corpus-wide synthesis.

    Uses actual database IDs as [Doc N] references so citations can be linked
    to the archive website at /documents/N.
    """
    lines = []
    current_collection = None
    for doc in summaries:
        collection = doc.get('collection') or 'Unknown'
        if collection != current_collection:
            current_collection = collection
            lines.append(f"\n--- Collection: {collection} ---\n")
        name = doc.get('display_title') or doc.get('file_name', '')
        doc_date = extract_doc_date(doc.get('file_name', ''))
        date_label = f" ({doc_date})" if doc_date else ""
        lines.append(f"[Doc {doc['id']}] {name}{date_label}")
        lines.append(doc['summary'])
        lines.append("")
    return "\n".join(lines)


# Archive website base URL for document links
ARCHIVE_BASE_URL = "https://crow-archive-996830241007.us-east1.run.app"


def build_citation_index(summaries: List[Dict]) -> Dict[int, Dict]:
    """Build a mapping from document ID to metadata for citation generation."""
    return {doc['id']: doc for doc in summaries}


def build_filename_index(db_name: str) -> Dict[str, Dict]:
    """Build a mapping from file_name to {id, display_title, file_name} for all documents."""
    conn = get_db_connection(db_name)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id, file_name, display_title FROM documents")
    except Exception:
        conn.rollback()
        cur.execute("SELECT id, file_name, file_name as display_title FROM documents")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    index = {}
    for row in rows:
        index[row['file_name']] = dict(row)
        # Also index without .pdf extension
        base = row['file_name']
        if base.lower().endswith('.pdf'):
            index[base[:-4]] = dict(row)
    return index


def linkify_filename_citations(text: str, filename_index: Dict[str, Dict]) -> str:
    """Convert filename references in AI output to clickable archive links.

    Matches patterns like (filename.pdf) or (filename.pdf, date) that the AI
    uses in Discovery, Deep Read, and Hybrid modes.
    """
    if not filename_index:
        return text

    # Sort by length (longest first) to avoid partial matches
    filenames = sorted(filename_index.keys(), key=len, reverse=True)
    cited_ids: List[int] = []

    for fname in filenames:
        escaped = re.escape(fname)
        # Match: ( [optional *] filename [optional *] [optional , date...] )
        pattern = r'\((\*?)' + escaped + r'(\*?)((?:,\s*[^)]*)?)\)'

        def make_replacer(fn: str):
            def replacer(match):
                star1 = match.group(1)
                star2 = match.group(2)
                after = match.group(3)
                doc = filename_index.get(fn)
                if doc:
                    doc_id = doc['id']
                    if doc_id not in cited_ids:
                        cited_ids.append(doc_id)
                    url = f"{ARCHIVE_BASE_URL}/documents/{doc_id}"
                    return f"({star1}[{fn}]({url}){star2}{after})"
                return match.group(0)
            return replacer

        text = re.sub(pattern, make_replacer(fname), text)

    return text


def _expand_doc_references(ref_text: str) -> List[int]:
    """Parse a Doc reference string into individual document IDs.

    Handles:
      "42"           → [42]
      "42, 55"       → [42, 55]
      "213–225"      → [213, 214, ..., 225]
      "32–39, 42, 52–53" → [32, 33, ..., 39, 42, 52, 53]
    """
    ids = []
    # Split on commas first
    for part in re.split(r'\s*,\s*', ref_text):
        part = part.strip()
        # Check for range (em-dash, en-dash, or hyphen between numbers)
        range_match = re.match(r'(\d+)\s*[–—-]\s*(\d+)$', part)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            # If end is shorter (e.g., 52–53 or 213–25), infer full number
            if end < start:
                prefix = str(start)[:len(str(start)) - len(str(end))]
                end = int(prefix + str(end))
            ids.extend(range(start, end + 1))
        else:
            num_match = re.match(r'(\d+)$', part)
            if num_match:
                ids.append(int(num_match.group(1)))
    return ids


def linkify_citations(text: str, citation_index: Dict[int, Dict]) -> str:
    """Convert [Doc N] references in AI output to clickable links with tooltips.

    Handles single refs [Doc 42], comma lists [Doc 42, 55], ranges [Doc 213–225],
    and mixed [Doc 32–39, 42, 52–53]. Appends a Sources Cited appendix at the bottom.
    """
    cited_ids = []

    def _make_link(doc_id: int) -> str:
        """Create a markdown link for a single document ID."""
        doc = citation_index.get(doc_id)
        if doc:
            if doc_id not in cited_ids:
                cited_ids.append(doc_id)
            name = doc.get('display_title') or doc.get('file_name', '')
            url = f"{ARCHIVE_BASE_URL}/documents/{doc_id}"
            return f"[Doc {doc_id}, {name}]({url})"
        return f"[Doc {doc_id}]"

    def replace_doc_group(match):
        """Replace any [Doc ...] pattern — single, list, range, or mixed."""
        inner = match.group(1)  # everything after "Doc "
        doc_ids = _expand_doc_references(inner)
        if not doc_ids:
            return match.group(0)
        return ", ".join(_make_link(did) for did in doc_ids)

    # Match [Doc N] or [Doc N, title text] or [Doc N, N, N]
    # but NOT already-linked patterns (negative lookahead for opening paren)
    # First pass: handle [Doc N, title] format (number followed by non-numeric text)
    def replace_doc_with_title(match):
        doc_id = int(match.group(1))
        return _make_link(doc_id)

    linked = re.sub(
        r'\[Doc\s+(\d+),\s*[^]\d][^]]*\](?!\()',
        replace_doc_with_title,
        text
    )

    # Second pass: handle [Doc N], [Doc N, N], [Doc N-N] (number-only references)
    linked = re.sub(
        r'\[Doc\s+([\d\s,–—-]+)\](?!\()',
        replace_doc_group,
        linked
    )

    # Build citation appendix
    if cited_ids:
        linked += "\n\n---\n\n### Sources Cited\n\n"
        for doc_id in cited_ids:
            doc = citation_index.get(doc_id)
            if doc:
                name = doc.get('display_title') or doc.get('file_name', '')
                collection = doc.get('collection') or ''
                doc_date = extract_doc_date(doc.get('file_name', ''))
                date_str = f", {doc_date}" if doc_date else ""
                url = f"{ARCHIVE_BASE_URL}/documents/{doc_id}"
                linked += f"- **[Doc {doc_id}]({url})** — {name}"
                if collection:
                    linked += f" (*{collection}*{date_str})"
                linked += "\n"

    return linked


def analyze_corpus_followup(followup: str, conversation: List[Dict],
                            summaries: List[Dict], db_stats: Dict,
                            model: str = "claude-opus-4-6") -> str:
    """Follow-up question in a corpus synthesis conversation."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set."

    client = anthropic.Anthropic(api_key=api_key)
    corpus_context = build_corpus_context(summaries)
    collections = set(d.get('collection', 'Unknown') for d in summaries)

    system_prompt = f"""You are a historian analyzing a complete archival collection about Native American land dispossession, federal Indian policy, and Bureau of Indian Affairs records.

You have analytical summaries of ALL {len(summaries)} documents in this collection, spanning {len(collections)} archival collections.

DATABASE SCOPE: {db_stats.get('documents', 0)} documents, {db_stats.get('entities', 0)} entities, {db_stats.get('events', 0)} events, {db_stats.get('financial_transactions', 0)} transactions, {db_stats.get('relationships', 0)} relationships, {db_stats.get('fee_patents', 0)} fee patents, {db_stats.get('correspondence', 0)} correspondence records, {db_stats.get('legislative_actions', 0)} legislative actions.

DOCUMENT SUMMARIES:
{corpus_context}

Continue your analysis. Ground every claim in specific documentary evidence with [Doc N] citations. Be thorough and specific — names, dates, acreages, dollar amounts."""

    # Build messages: prior conversation + new follow-up
    messages = list(conversation) + [{"role": "user", "content": followup}]

    try:
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            temperature=0.3,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        import traceback
        return f"Error during analysis: {type(e).__name__}: {str(e)}\n\n```\n{traceback.format_exc()}\n```"


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

DATABASE SCOPE: {db_stats.get('documents', 0)} documents, {db_stats.get('entities', 0)} entities, {db_stats.get('events', 0)} events, {db_stats.get('financial_transactions', 0)} transactions, {db_stats.get('relationships', 0)} relationships, {db_stats.get('fee_patents', 0)} fee patents, {db_stats.get('correspondence', 0)} correspondence records, {db_stats.get('legislative_actions', 0)} legislative actions.

RESEARCH QUESTION: {question}

{corpus_context}

SYNTHESIS GUIDELINES:

1. SURFACE PATTERNS across documents. Identify recurring actors, repeated legal mechanisms, and systematic processes that appear across multiple documents and decades. This is corpus-wide synthesis — prioritize cross-document patterns over summarizing individual documents.

2. GROUND EVERYTHING IN EVIDENCE. Every claim must be supported by specific documentary evidence: names, allotment numbers, acreages, dollar amounts, bill numbers, dates, vote counts, patent numbers, legal descriptions. Do not make assertions without citing the specific details from the documents that support them.

3. SHOW CONNECTIONS. Trace which actors appear together across documents. Identify sequences of events that recur. Show how specific mechanisms (fee patenting, private bills, administrative trust-to-fee conversion) operated across time and place, citing the specific cases that demonstrate each pattern.

4. QUANTIFY WHERE POSSIBLE. Aggregate total acreages, dollar amounts, numbers of transactions, vote tallies, and other numerical evidence across the corpus. When exact totals aren't possible, provide ranges or lower bounds based on what the documents contain.

5. Cite specific documents using their title and [Doc N] reference, like: [Doc 42, 1919 CCF 62648-19-013 Crow delegates]. Use the exact ID numbers from the summaries above. When multiple documents support a claim, list them: [Doc 42, 55, 103]. Every substantive claim needs at least one citation.

6. CONCLUDE WITH THREE SECTIONS:
   - **What the Documents Prove**: claims fully supported by the documentary evidence, with citations.
   - **What the Documents Suggest**: plausible interpretations that the evidence points toward but does not definitively establish.
   - **Gaps in the Record**: what topics, time periods, actors, or questions are poorly represented or unanswerable from this corpus.

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
                        len(evidence.get('financial_transactions', [])) + len(evidence.get('relationships', [])) +
                        len(evidence.get('fee_patents', [])) + len(evidence.get('correspondence', [])) +
                        len(evidence.get('legislative_actions', [])))
    total_passages = sum(p['passage_count'] for p in evidence.get('passages', []))
    passage_docs = len(evidence.get('passages', []))

    v3_scope = ""
    if db_stats.get('fee_patents', 0) or db_stats.get('correspondence', 0) or db_stats.get('legislative_actions', 0):
        v3_scope = (f" Additionally: {db_stats.get('fee_patents', 0)} fee patents, "
                    f"{db_stats.get('correspondence', 0)} correspondence records, "
                    f"{db_stats.get('legislative_actions', 0)} legislative actions.")

    prompt = f"""You are a historian analyzing evidence from an archival database about Native American land dispossession, federal Indian policy, and Bureau of Indian Affairs records.

DATABASE SCOPE: {db_stats.get('documents', 0)} documents processed, containing {db_stats.get('entities', 0)} entities, {db_stats.get('events', 0)} events, {db_stats.get('financial_transactions', 0)} financial transactions, and {db_stats.get('relationships', 0)} relationships. {db_stats.get('docs_with_text', 0)} documents have full text available.{v3_scope}

YOU HAVE MULTIPLE TYPES OF EVIDENCE:
1. DOCUMENT TEXT PASSAGES: Actual excerpts from the source documents. These are your PRIMARY evidence — quote and cite them directly.
2. EXTRACTED ENTITIES/EVENTS/TRANSACTIONS/RELATIONSHIPS: Structured data extracted by AI from the documents. Use these to identify patterns, networks, and connections.
3. FEE PATENTS: Structured records of the atomic unit of land dispossession — allottee, allotment, acreage, patent mechanism, subsequent buyer, attorney, mortgage. Use these to trace specific chains of land loss.
4. CORRESPONDENCE: Bureaucratic network records — sender, recipient, titles, date, subject, action requested, outcome. Use these to reconstruct decision-making chains.
5. LEGISLATIVE ACTIONS: Bill lifecycle records — bill number, sponsor, action type, date, vote count, committee, outcome. Use these to trace how legislation moved through Congress.

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

DATABASE SCOPE: {db_stats.get('documents', 0)} documents processed, containing {db_stats.get('entities', 0)} entities, {db_stats.get('events', 0)} events, {db_stats.get('financial_transactions', 0)} financial transactions, {db_stats.get('relationships', 0)} relationships, {db_stats.get('fee_patents', 0)} fee patents, {db_stats.get('correspondence', 0)} correspondence records, {db_stats.get('legislative_actions', 0)} legislative actions.

YOU HAVE TWO LEVELS OF EVIDENCE:
1. FULL DOCUMENT TEXTS: The complete text of {num_docs} top-ranked documents: {', '.join(doc_names)}. Read these deeply — quote them, trace their arguments, identify mechanisms.
2. CROSS-COLLECTION DATA: Entities, transactions, relationships, fee patents, correspondence, and legislative actions from additional documents beyond those {num_docs}. Use these to identify patterns and connections the full texts alone wouldn't reveal.

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

st.markdown(f"""
<div class="app-header">
    <h1>\U0001f3db\ufe0f Historical Document Analysis</h1>
    <p class="subtitle">
        AI-powered research across historical archival collections
        &nbsp;\u2022&nbsp;
        <a href="{ARCHIVE_BASE_URL}/about" target="_blank">About this tool</a>
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    available_dbs = get_available_databases()
    db_labels = {
        "crow_historical_docs": "Crow Nation Archive",
        "full_corpus_docs": "Full Research Corpus",
        "historical_docs": "Historical Documents",
    }
    selected_db = st.selectbox(
        "Archive collection:",
        available_dbs,
        index=available_dbs.index("crow_historical_docs") if "crow_historical_docs" in available_dbs else 0,
        format_func=lambda d: db_labels.get(d, d),
    )

    stats = get_db_stats(selected_db)
    filename_index = build_filename_index(selected_db)

    if stats.get('error'):
        st.error(f"Connection error: {stats['error']}")
    else:
        st.markdown(f"""
        <div class="sidebar-section">
            <h4>Corpus</h4>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-value">{stats['documents']:,}</div>
                    <div class="stat-label">Documents</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{stats['entities']:,}</div>
                    <div class="stat-label">Entities</div>
                </div>
            </div>
        </div>
        <div class="sidebar-section">
            <h4>Extracted Data</h4>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-value">{stats['events']:,}</div>
                    <div class="stat-label">Events</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{stats['financial_transactions']:,}</div>
                    <div class="stat-label">Transactions</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{stats['relationships']:,}</div>
                    <div class="stat-label">Relationships</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{stats.get('fee_patents', 0):,}</div>
                    <div class="stat-label">Fee Patents</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{stats.get('correspondence', 0):,}</div>
                    <div class="stat-label">Correspondence</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{stats.get('legislative_actions', 0):,}</div>
                    <div class="stat-label">Legislation</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.caption(f"{stats.get('docs_with_text', 0):,} documents with extractable text")

    ai_model = "claude-opus-4-6"
    max_passage_docs = 30
    passages_per_doc = 5
    hybrid_doc_count = 5


# ─────────────────────────────────────────────────
# MODE SELECTION
# ─────────────────────────────────────────────────

MODE_OPTIONS = [
    "Discovery",
    "Deep Read",
    "Discovery \u2192 Deep Read",
    "Corpus Synthesis",
    "Process Document",
]

MODE_DESCRIPTIONS = {
    "Discovery": "Search the extracted database for people, places, events, financial transactions, "
                 "and connections across all documents. Uses **Search Only** (free, no AI) or "
                 "**Search & Analyze** (AI synthesizes the database results into a narrative).",
    "Deep Read": "Send a single document's **complete text** to the AI for close, detailed analysis. "
                 "The AI reads the entire document\u2014not fragments\u2014like a research assistant reading over your shoulder.",
    "Discovery \u2192 Deep Read": "Run Discovery first to find relevant documents, then select which ones "
                 "to deep-read. The AI gets **full texts** of your chosen documents plus cross-collection "
                 "entity data\u2014combining breadth and depth.",
    "Corpus Synthesis": "Send summaries of **every** document to the AI for corpus-wide pattern analysis. "
                 "No context window limit. Ask follow-up questions to drill deeper without re-running the synthesis.",
    "Process Document": "Upload an OCR'd PDF to run the full extraction pipeline: text extraction, "
                 "entity/event/relationship extraction, summary generation, and title generation.",
}

mode_key = st.radio(
    "Analysis Mode:",
    MODE_OPTIONS,
    index=0,
    horizontal=True,
)

st.markdown(
    f'<div class="mode-desc">{MODE_DESCRIPTIONS[mode_key]}</div>',
    unsafe_allow_html=True,
)


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
                    'fee_patents': search_fee_patents(selected_db, question),
                    'correspondence': search_correspondence(selected_db, question),
                    'legislative_actions': search_legislative_actions(selected_db, question),
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
                'Fee Patents': len(evidence.get('fee_patents', [])),
                'Correspondence': len(evidence.get('correspondence', [])),
                'Legislative Actions': len(evidence.get('legislative_actions', [])),
                'Text Passages': passage_count,
                'Documents': len(evidence['documents']),
            }
            count_str = " | ".join([f"**{k}:** {v}" for k, v in counts.items() if v > 0])
            st.success(f"Evidence found: {count_str}")

            # Evidence browser
            with st.expander("\U0001f50e Browse Raw Evidence", expanded=False):
                tabs = st.tabs(["\U0001f4c4 Passages", "\U0001f3f7\ufe0f Entities", "\U0001f4c5 Events",
                               "\U0001f4b0 Transactions", "\U0001f517 Relationships",
                               "\U0001f4dc Fee Patents", "\U0001f4e8 Correspondence",
                               "\U0001f3db\ufe0f Legislation", "\U0001f578\ufe0f Networks"])

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
                    if evidence.get('fee_patents'):
                        for fp in evidence['fee_patents'][:30]:
                            allottee = fp.get('allottee', '?')
                            allotment = fp.get('allotment_number', '')
                            acreage = fp.get('acreage', '')
                            header = f"**{allottee}**"
                            if allotment:
                                header += f" — Allotment {allotment}"
                            if acreage:
                                header += f" ({acreage} acres)"
                            st.markdown(header)
                            details = []
                            if fp.get('patent_date'):
                                details.append(f"Patent: {fp['patent_date']}")
                            if fp.get('trust_to_fee_mechanism'):
                                details.append(f"Mechanism: {fp['trust_to_fee_mechanism']}")
                            if fp.get('subsequent_buyer'):
                                details.append(f"Sold to: {fp['subsequent_buyer']}")
                            if fp.get('sale_price'):
                                details.append(f"Price: {fp['sale_price']}")
                            if fp.get('attorney'):
                                details.append(f"Attorney: {fp['attorney']}")
                            if fp.get('mortgage_amount'):
                                details.append(f"Mortgage: {fp['mortgage_amount']} ({fp.get('mortgage_holder', '?')})")
                            if details:
                                st.caption(" | ".join(details))
                            st.caption(f"\U0001f4c4 {doc_label(fp)}")
                            st.markdown("---")
                    else:
                        st.info("No fee patents found.")

                with tabs[6]:
                    if evidence.get('correspondence'):
                        for c in evidence['correspondence'][:30]:
                            sender = c.get('sender', '?')
                            recipient = c.get('recipient', '?')
                            date = c.get('date', 'n/d')
                            st.markdown(f"**{sender}** \u2192 **{recipient}** [{date}]")
                            if c.get('sender_title') or c.get('recipient_title'):
                                titles = f"{c.get('sender_title', '')} \u2192 {c.get('recipient_title', '')}"
                                st.caption(titles)
                            if c.get('subject'):
                                st.caption(f"Re: {c['subject'][:200]}")
                            if c.get('action_requested'):
                                st.caption(f"Action: {c['action_requested'][:200]}")
                            if c.get('outcome'):
                                st.caption(f"Outcome: {c['outcome'][:200]}")
                            st.caption(f"\U0001f4c4 {doc_label(c)}")
                            st.markdown("---")
                    else:
                        st.info("No correspondence found.")

                with tabs[7]:
                    if evidence.get('legislative_actions'):
                        for la in evidence['legislative_actions'][:30]:
                            bill = la.get('bill_number', '?')
                            action = la.get('action_type', '?')
                            date = la.get('action_date', 'n/d')
                            st.markdown(f"**{bill}** — {action} [{date}]")
                            if la.get('bill_title'):
                                st.caption(la['bill_title'])
                            details = []
                            if la.get('sponsor'):
                                details.append(f"Sponsor: {la['sponsor']}")
                            if la.get('vote_count'):
                                details.append(f"Vote: {la['vote_count']}")
                            if la.get('committee'):
                                details.append(f"Committee: {la['committee']}")
                            if la.get('outcome'):
                                details.append(f"Outcome: {la['outcome']}")
                            if details:
                                st.caption(" | ".join(details))
                            st.caption(f"\U0001f4c4 {doc_label(la)}")
                            st.markdown("---")
                    else:
                        st.info("No legislative actions found.")

                with tabs[8]:
                    for person, connections in evidence.get('networks', {}).items():
                        st.markdown(f"**Network: {person}**")
                        for c in connections[:15]:
                            st.text(f"  \u2194 {c['name']} ({c['type']}) \u2014 {c['shared_docs']} shared docs")
                        st.markdown("---")

            # AI Analysis
            if run_analysis:
                st.markdown("---")
                st.markdown('<h3 class="section-header">AI Analysis</h3>', unsafe_allow_html=True)
                with st.spinner("Analyzing evidence..."):
                    analysis = analyze_discovery(question, evidence, stats, model=ai_model)
                st.markdown(linkify_filename_citations(escape_dollars(analysis), filename_index))

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
    # Deep Read mode UI

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
                    st.markdown('<h3 class="section-header">AI Deep Reading</h3>', unsafe_allow_html=True)
                    with st.spinner("AI is reading the full document..."):
                        analysis = analyze_deep_read(question, doc, stats, model=ai_model)
                    st.markdown(linkify_filename_citations(escape_dollars(analysis), filename_index))

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
    # Hybrid mode UI

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
                    'fee_patents': search_fee_patents(selected_db, question),
                    'correspondence': search_correspondence(selected_db, question),
                    'legislative_actions': search_legislative_actions(selected_db, question),
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
        st.markdown('<h3 class="section-header">Step 2: Select Documents for Deep Read</h3>', unsafe_allow_html=True)
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
                        st.markdown('<h3 class="section-header">AI Analysis \u2014 Discovery + Deep Read</h3>', unsafe_allow_html=True)
                        with st.spinner(
                            f"AI is reading {len(deep_docs)} full documents "
                            f"+ cross-collection data..."
                        ):
                            analysis = analyze_hybrid(
                                discovery_question, evidence, deep_docs, stats, model=ai_model)

                    st.markdown(linkify_filename_citations(escape_dollars(analysis), filename_index))

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
    # Corpus Synthesis mode UI

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

        # Initialize conversation state
        if "corpus_conversation" not in st.session_state:
            st.session_state.corpus_conversation = []  # list of {"role": ..., "content": ...}
            st.session_state.corpus_displays = []      # list of rendered markdown strings
            st.session_state.corpus_initial_q = ""

        if st.button("\U0001f3db\ufe0f Synthesize Across Entire Corpus", type="primary"):
            if not question:
                st.warning("Please enter a research question.")
            else:
                # Clear previous conversation on new primary query
                st.session_state.corpus_conversation = []
                st.session_state.corpus_displays = []
                st.session_state.corpus_initial_q = question

                with st.expander(f"Document summaries sent to AI ({summarized})", expanded=False):
                    for s in summaries:
                        name = s.get('display_title') or s.get('file_name', '')
                        doc_url = f"{ARCHIVE_BASE_URL}/documents/{s['id']}"
                        st.markdown(f"**[Doc {s['id']}]({doc_url})** {name}")
                        st.caption(s.get('summary', '')[:300] + "...")

                st.markdown("---")
                st.markdown('<h3 class="section-header">Corpus-Wide Synthesis</h3>', unsafe_allow_html=True)
                with st.spinner(
                    f"AI is analyzing summaries of all {summarized} documents..."
                ):
                    analysis = analyze_corpus(question, summaries, stats)

                # Store in conversation
                st.session_state.corpus_conversation = [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": analysis},
                ]

                citation_index = build_citation_index(summaries)
                linked_analysis = linkify_citations(escape_dollars(analysis), citation_index)
                st.session_state.corpus_displays = [
                    {"label": question, "content": linked_analysis}
                ]

        # Display conversation history
        if st.session_state.corpus_displays:
            citation_index = build_citation_index(summaries)

            for i, entry in enumerate(st.session_state.corpus_displays):
                if i > 0:
                    st.markdown("---")
                    st.markdown(f"**Follow-up:** {entry['label']}")
                st.markdown(entry["content"], unsafe_allow_html=False)

            st.markdown("---")
            st.caption(
                f"\U0001f3db\ufe0f Corpus Synthesis: AI analyzed summaries of all "
                f"{summarized} documents (~{est_tokens:,} tokens). "
                f"Document citations link to the Crow Nation Digital Archive. "
                f"For deep reading of specific documents, use Deep Read or Hybrid mode."
            )

            # Follow-up input
            st.markdown("---")
            followup = st.text_input(
                "Ask a follow-up question:",
                placeholder="e.g., Tell me more about the Nez Perce paradox",
                key=f"followup_{len(st.session_state.corpus_displays)}"
            )

            if st.button("\U0001f504 Ask Follow-up", type="secondary"):
                if not followup:
                    st.warning("Please enter a follow-up question.")
                else:
                    with st.spinner("AI is analyzing your follow-up..."):
                        followup_response = analyze_corpus_followup(
                            followup,
                            st.session_state.corpus_conversation,
                            summaries, stats
                        )

                    # Append to conversation
                    st.session_state.corpus_conversation.append(
                        {"role": "user", "content": followup}
                    )
                    st.session_state.corpus_conversation.append(
                        {"role": "assistant", "content": followup_response}
                    )

                    linked_followup = linkify_citations(
                        escape_dollars(followup_response), citation_index
                    )
                    st.session_state.corpus_displays.append(
                        {"label": followup, "content": linked_followup}
                    )

                    st.rerun()


# ═════════════════════════════════════════════════
# MODE 5: PROCESS DOCUMENT
# ═════════════════════════════════════════════════
elif mode_key == "Process Document":
    st.info(
        "The PDF must already be OCR'd (e.g., via ABBYY FineReader). "
        "Scanned images without OCR will produce no results."
    )

    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

    col_coll, col_sub = st.columns(2)
    with col_coll:
        collection = st.text_input(
            "Collection name",
            value="",
            placeholder="e.g., CROW_BATCH_10",
            help="Archival collection this document belongs to"
        )
    with col_sub:
        subcollection = st.text_input(
            "Subcollection (optional)",
            value="",
            placeholder="e.g., Series 1",
        )

    upload_to_gcs = st.checkbox("Upload PDF to Google Cloud Storage", value=True,
                                 help="Makes the PDF available on the archive website")

    if uploaded_file and st.button("\U0001f680 Process Document", type="primary"):
        import fitz  # PyMuPDF
        import tempfile
        import io

        status = st.status("Processing document...", expanded=True)

        try:
            # ── Step 1: Extract text ──
            status.update(label="Step 1/6: Extracting text from PDF...")
            pdf_bytes = uploaded_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            full_text = ""
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                full_text += f"\n--- Page {page_num} ---\n{text}"
            page_count = len(doc)
            doc.close()

            word_count = len(full_text.split())
            st.write(f"Extracted {word_count:,} words from {page_count} pages")

            if word_count < 50:
                st.error("Very little text extracted. Is this PDF OCR'd?")
                st.stop()

            # ── Step 2: Insert document into database ──
            status.update(label="Step 2/6: Saving document to database...")
            conn = get_db_connection(selected_db)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO documents
                (file_name, file_path, page_count, file_size, full_text,
                 collection, subcollection, extraction_model, pipeline_version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                uploaded_file.name,
                f"uploaded/{uploaded_file.name}",
                page_count,
                len(pdf_bytes),
                full_text,
                collection or None,
                subcollection or None,
                "claude-sonnet-4-6",
                "v3",
            ))
            doc_id = cur.fetchone()[0]
            conn.commit()
            st.write(f"Document saved as **Doc {doc_id}**")

            # ── Step 3: Chunked extraction ──
            status.update(label="Step 3/6: Running AI extraction (this takes a while)...")
            client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )

            # Chunk the text
            chunk_size = 40000
            overlap = 5000
            chunks = []
            start = 0
            while start < len(full_text):
                end = min(start + chunk_size, len(full_text))
                chunks.append(full_text[start:end])
                if end >= len(full_text):
                    break
                start = end - overlap

            st.write(f"Processing {len(chunks)} chunk(s)...")
            progress = st.progress(0)

            extraction_prompt_template = """You are analyzing a historical document about Native American land dispossession, the Crow Act of 1920, and federal Indian policy.

This is chunk {chunk_num} of {total_chunks} from document: {file_name}

Extract ALL of the following from this text. Return ONLY valid JSON, no markdown, no explanation.

{{
  "entities": [
    {{"type": "person|organization|location|land_parcel|legal_case|legislation|acreage_holding", "name": "...", "context": "...", "acres": "...", "land_type": "..."}}
  ],
  "financial_transactions": [
    {{"amount": "...", "type": "sale|lease|payment|fee|other", "payer": "...", "payee": "...", "for_what": "...", "date": "...", "context": "..."}}
  ],
  "relationships": [
    {{"type": "...", "subject": "...", "object": "...", "context": "..."}}
  ],
  "events": [
    {{"type": "...", "date": "...", "location": "...", "description": "...", "entities_involved": ["..."]}}
  ],
  "fee_patents": [
    {{"allottee": "...", "allotment_number": "...", "acreage": "...", "patent_date": "...", "trust_to_fee_mechanism": "...", "subsequent_buyer": "...", "sale_price": "...", "attorney": "...", "context": "..."}}
  ],
  "correspondence": [
    {{"sender": "...", "sender_title": "...", "recipient": "...", "recipient_title": "...", "date": "...", "subject": "...", "action_requested": "...", "outcome": "...", "context": "..."}}
  ],
  "legislative_actions": [
    {{"bill_number": "...", "sponsor": "...", "action_type": "introduced|reported|amended|passed|vetoed|enacted", "action_date": "...", "vote_count": "...", "committee": "...", "outcome": "...", "context": "..."}}
  ]
}}

Extract EVERY person, organization, location, legal case, legislation, financial transaction, relationship, event, fee patent, correspondence record, and legislative action. Be thorough.

Document chunk:
{chunk_text}"""

            all_chunk_results = []
            for i, chunk in enumerate(chunks):
                try:
                    response = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=16000,
                        messages=[{"role": "user", "content":
                            extraction_prompt_template.format(
                                chunk_num=i+1,
                                total_chunks=len(chunks),
                                file_name=uploaded_file.name,
                                chunk_text=chunk,
                            )
                        }]
                    )
                    response_text = response.content[0].text.strip()
                    if response_text.startswith("```"):
                        response_text = re.sub(r'^```(?:json)?\n', '', response_text)
                        response_text = re.sub(r'\n```$', '', response_text)
                    result = json.loads(response_text)
                    all_chunk_results.append(result)
                except Exception as e:
                    st.warning(f"Chunk {i+1} extraction error: {e}")
                    all_chunk_results.append({
                        "entities": [], "financial_transactions": [],
                        "relationships": [], "events": [],
                        "fee_patents": [], "correspondence": [], "legislative_actions": []
                    })
                progress.progress((i + 1) / len(chunks))

            # Merge results across chunks
            merged = {
                "entities": [], "financial_transactions": [],
                "relationships": [], "events": [],
                "fee_patents": [], "correspondence": [], "legislative_actions": []
            }
            seen_entities = set()
            for cr in all_chunk_results:
                for ent in cr.get("entities", []):
                    key = (ent.get("name", "").lower(), ent.get("type", ""))
                    if key not in seen_entities:
                        seen_entities.add(key)
                        merged["entities"].append(ent)
                for key in ["financial_transactions", "relationships", "events",
                            "fee_patents", "correspondence", "legislative_actions"]:
                    merged[key].extend(cr.get(key, []))

            # ── Step 4: Store extraction results ──
            status.update(label="Step 4/6: Saving extracted data...")

            # Entities
            for ent in merged["entities"]:
                cur.execute("""
                    INSERT INTO entities (name, type, context, acres, land_type)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name, type) DO UPDATE SET context = EXCLUDED.context
                    RETURNING id
                """, (ent.get("name"), ent.get("type"), ent.get("context"),
                      ent.get("acres"), ent.get("land_type")))
                entity_id = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO mentions (entity_id, document_id, context)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (entity_id, document_id) DO NOTHING
                """, (entity_id, doc_id, ent.get("context")))

            # Events
            for ev in merged["events"]:
                cur.execute("""
                    INSERT INTO events (document_id, type, date, location, description, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (doc_id, ev.get("type"), ev.get("date"), ev.get("location"),
                      ev.get("description"),
                      json.dumps({"entities_involved": ev.get("entities_involved", [])})))

            # Financial transactions
            for ft in merged["financial_transactions"]:
                cur.execute("""
                    INSERT INTO financial_transactions
                    (document_id, amount, type, payer, payee, for_what, date, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (doc_id, ft.get("amount"), ft.get("type"), ft.get("payer"),
                      ft.get("payee"), ft.get("for_what"), ft.get("date"), ft.get("context")))

            # Relationships
            for rel in merged["relationships"]:
                cur.execute("""
                    INSERT INTO relationships (document_id, type, subject, object, context)
                    VALUES (%s, %s, %s, %s, %s)
                """, (doc_id, rel.get("type"), rel.get("subject"),
                      rel.get("object"), rel.get("context")))

            # Fee patents
            for fp in merged["fee_patents"]:
                cur.execute("""
                    INSERT INTO fee_patents
                    (document_id, allottee, allotment_number, acreage, patent_date,
                     trust_to_fee_mechanism, subsequent_buyer, sale_price, attorney, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (doc_id, fp.get("allottee"), fp.get("allotment_number"),
                      fp.get("acreage"), fp.get("patent_date"),
                      fp.get("trust_to_fee_mechanism"), fp.get("subsequent_buyer"),
                      fp.get("sale_price"), fp.get("attorney"), fp.get("context")))

            # Correspondence
            for corr in merged["correspondence"]:
                cur.execute("""
                    INSERT INTO correspondence
                    (document_id, sender, sender_title, recipient, recipient_title,
                     date, subject, action_requested, outcome, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (doc_id, corr.get("sender"), corr.get("sender_title"),
                      corr.get("recipient"), corr.get("recipient_title"),
                      corr.get("date"), corr.get("subject"),
                      corr.get("action_requested"), corr.get("outcome"),
                      corr.get("context")))

            # Legislative actions
            for la in merged["legislative_actions"]:
                cur.execute("""
                    INSERT INTO legislative_actions
                    (document_id, bill_number, sponsor, action_type, action_date,
                     vote_count, committee, outcome, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (doc_id, la.get("bill_number"), la.get("sponsor"),
                      la.get("action_type"), la.get("action_date"),
                      la.get("vote_count"), la.get("committee"),
                      la.get("outcome"), la.get("context")))

            conn.commit()

            st.write(
                f"Extracted: {len(merged['entities'])} entities, "
                f"{len(merged['events'])} events, "
                f"{len(merged['financial_transactions'])} transactions, "
                f"{len(merged['relationships'])} relationships, "
                f"{len(merged['fee_patents'])} fee patents, "
                f"{len(merged['correspondence'])} correspondence, "
                f"{len(merged['legislative_actions'])} legislative actions"
            )

            # ── Step 5: Generate summary and title ──
            status.update(label="Step 5/6: Generating summary and display title...")

            # Summary
            summary_text = full_text[:int(180000 * 3.2)]  # Truncate to fit context
            summary_prompt = f"""You are analyzing a historical document from an archival collection about Native American land dispossession, the Crow Reservation, federal Indian policy, and Bureau of Indian Affairs records.

Document: {uploaded_file.name}
Collection: {collection or 'Unknown'}

Begin with a date line in this exact format: "DATE RANGE: [earliest year]-[latest year]" (or "DATE RANGE: undated" if no dates are discernible). Then write a dense analytical summary in 150-250 words. No headers or bullet points - write in plain prose paragraphs. Cover: document type and purpose; author, recipient, date; specific claims, actions, or decisions (names, amounts, acreages); legal mechanisms invoked (statutes, policies, administrative procedures); and what it proves about land dispossession.

Full text:
{summary_text}"""

            try:
                summary_response = client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=1000,
                    temperature=0.2,
                    messages=[{"role": "user", "content": summary_prompt}]
                )
                summary = summary_response.content[0].text.strip()

                cur.execute(
                    "UPDATE documents SET summary = %s, summary_date = CURRENT_TIMESTAMP WHERE id = %s",
                    (summary, doc_id)
                )
                conn.commit()
                st.write("Summary generated")
            except Exception as e:
                summary = None
                st.warning(f"Summary generation failed: {e}")

            # Display title
            if summary:
                title_prompt = f"""Generate a short, clear display title for this historical archival document about the Crow Nation.

Rules:
- Include the year or date range at the START: "1920: House Hearings on..."
- The date should reflect when the document was CREATED, not the full historical span referenced
- Be concise but descriptive, like a library catalog entry
- Do NOT include ".pdf" or file classification numbers unless they add meaning

Document file name: {uploaded_file.name}
Summary: {summary}

Return ONLY the title, nothing else."""

                try:
                    title_response = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=200,
                        temperature=0.2,
                        messages=[{"role": "user", "content": title_prompt}]
                    )
                    display_title = title_response.content[0].text.strip().strip('"')
                    cur.execute(
                        "UPDATE documents SET display_title = %s WHERE id = %s",
                        (display_title, doc_id)
                    )
                    conn.commit()
                    st.write(f"Title: **{display_title}**")
                except Exception as e:
                    st.warning(f"Title generation failed: {e}")

            # ── Step 6: Upload to GCS ──
            if upload_to_gcs:
                status.update(label="Step 6/6: Uploading PDF to Google Cloud Storage...")
                try:
                    from google.cloud import storage as gcs
                    gcs_client = gcs.Client()
                    bucket = gcs_client.bucket("crow-archive-pdfs")
                    blob = bucket.blob(uploaded_file.name)
                    blob.upload_from_string(pdf_bytes, content_type="application/pdf")
                    st.write(f"Uploaded to `gs://crow-archive-pdfs/{uploaded_file.name}`")
                except Exception as e:
                    st.warning(f"GCS upload failed: {e}")
            else:
                st.info("Skipped GCS upload")

            cur.close()
            conn.close()

            status.update(label="Processing complete!", state="complete")

            # Show results summary
            st.success(
                f"Document **{uploaded_file.name}** processed as "
                f"**[Doc {doc_id}]({ARCHIVE_BASE_URL}/documents/{doc_id})**. "
                f"It is now searchable in Discovery and Corpus Synthesis modes."
            )

        except Exception as e:
            status.update(label="Processing failed", state="error")
            st.error(f"Error: {e}")
            import traceback
            st.code(traceback.format_exc())


# Footer
db_display = db_labels.get(selected_db, selected_db) if 'selected_db' in dir() else 'not connected'
st.markdown(f"""
<div class="app-footer">
    Historical Document Analysis &nbsp;\u2022&nbsp;
    <a href="{ARCHIVE_BASE_URL}" target="_blank">Crow Nation Digital Archive</a> &nbsp;\u2022&nbsp;
    {db_display}
</div>
""", unsafe_allow_html=True)
