#!/usr/bin/env python3
"""
Exhaustive Document Processing Pipeline - Version 3
Expanded extraction: v2's 10 entity types + fee_patents, correspondence, legislative_actions.

v3 additions over v2:
  fee_patent          - The atomic unit of land dispossession: allottee, allotment,
                        patent, chain of subsequent conveyances, attorney, mortgage.
  correspondence      - Sender/recipient/date/subject for bureaucratic network
                        reconstruction. Designed to link with Pipeline B (BIA index cards).
  legislative_action  - Bill lifecycle tracking: introduced, reported, passed, vetoed,
                        enacted — with sponsors, vote counts, and committees.

Usage:
    python3 poc_pipeline_chunked_v3.py --input /path/to/pdfs --output results_v3/
    python3 poc_pipeline_chunked_v3.py --input /path/to/pdfs --output results_v3/ --db crow_historical_docs
    python3 poc_pipeline_chunked_v3.py --input /path/to/pdfs --output results_v3/ --model claude-opus-4-6
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re
from collections import defaultdict

import fitz  # PyMuPDF
import psycopg2
from anthropic import Anthropic

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-4-6"


class DocumentProcessor:
    """Handles text extraction from PDFs — identical to v2."""

    def __init__(self):
        self.processed_count = 0
        self.error_count = 0

    def extract_text_from_pdf(self, pdf_path: Path) -> Tuple[str, Dict]:
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                full_text += f"\n--- Page {page_num} ---\n{text}"

            metadata = {
                'page_count': len(doc),
                'file_size': pdf_path.stat().st_size,
                'file_name': pdf_path.name,
                'file_path': str(pdf_path.absolute())
            }

            date_patterns = [
                r'\b(19|20)\d{2}\b',
                r'\b(?:January|February|March|April|May|June|July|'
                r'August|September|October|November|December)\s+\d{1,2},?\s+(19|20)\d{2}\b'
            ]
            dates_found = []
            for pattern in date_patterns:
                dates_found.extend(re.findall(pattern, full_text[:5000]))
            if dates_found:
                metadata['extracted_dates'] = list(set(
                    str(d) if isinstance(d, str) else d[0] for d in dates_found
                ))

            doc.close()
            self.processed_count += 1
            return full_text, metadata

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            return "", {}

    def extract_collection_metadata(self, file_path: Path, base_path: Path) -> Dict:
        try:
            relative_path = file_path.relative_to(base_path)
            parts = list(relative_path.parts)
        except ValueError:
            parts = [file_path.name]

        metadata = {
            'collection': parts[0] if len(parts) > 1 else 'Unknown',
            'subcollection': parts[1] if len(parts) > 2 else None,
            'location': None
        }
        location_keywords = ['county', 'reservation', 'agency', 'district', 'territory']
        for part in parts:
            if any(kw in part.lower() for kw in location_keywords):
                metadata['location'] = part
                break
        return metadata


class EntityExtractorV3:
    """
    v3 extraction: v2's 10 entity types + 3 new structured extraction targets.

    New in v3:
      fee_patent          - Unified record linking allottee → allotment → patent →
                            conveyance → buyer → attorney → mortgage. The fundamental
                            unit of analysis for land dispossession research.
      correspondence      - Sender, recipient, date, subject, action requested, outcome.
                            Maps the bureaucratic network; designed to link with Pipeline B
                            (1.4M BIA index cards) via sender/recipient/date matching.
      legislative_action  - Bill number, sponsor, action type, date, vote count, outcome.
                            Tracks bills through their legislative lifecycle rather than
                            treating each mention as an isolated entity.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.extraction_count = 0
        self.chunk_size = 40000
        self.overlap = 5000

    def chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk = text[start:end]
            chunks.append((chunk, start, end))
            if end >= text_len:
                break
            start = end - self.overlap
        return chunks

    def extract_from_chunk(self, chunk: str, chunk_num: int,
                           total_chunks: int, doc_metadata: Dict) -> Dict:

        prompt = f"""You are analyzing a historical document about Native American land dispossession, the Crow Act of 1920, and federal Indian policy.

This is chunk {chunk_num} of {total_chunks} from document: {doc_metadata.get('file_name', 'Unknown')}
Collection: {doc_metadata.get('collection', 'Unknown')}
Location: {doc_metadata.get('location', 'Unknown')}
Dates found: {doc_metadata.get('extracted_dates', [])}

Extract ALL of the following from this text. Return ONLY valid JSON, no markdown, no explanation.

{{
  "entities": [
    {{"type": "person", "name": "FULL NAME AS WRITTEN", "context": "their specific role or action"}},
    {{"type": "organization", "name": "FULL NAME", "context": "what they did"}},
    {{"type": "location", "name": "FULL NAME", "context": "what happened here"}},
    {{"type": "land_parcel", "name": "allotment # or legal description", "context": "what happened to this land"}},
    {{"type": "legal_case", "name": "case name e.g. Dillon v. Antler Land Co.", "context": "what this case decided or argued"}},
    {{"type": "legislation", "name": "act or bill name/number e.g. Crow Act 1920, H.R. 5477", "context": "what this law did or proposed"}},
    {{"type": "acreage_holding", "name": "entity name", "acres": "number", "land_type": "farm|grazing|allotment|leased", "context": "how they held this land, any violation of limits"}}
  ],
  "financial_transactions": [
    {{"amount": "dollar amount", "type": "sale|lease|permit|bribe|payment|fine", "payer": "who paid", "payee": "who received", "for_what": "what the payment was for", "date": "when", "context": "full context"}}
  ],
  "relationships": [
    {{"type": "owns|leases|sold|bought|approved|opposed|represented|administered|violated", "subject": "entity name", "object": "entity or land name", "context": "specific details"}}
  ],
  "events": [
    {{"type": "patent|foreclosure|tax_sale|allotment|hearing|complaint|mortgage|land_sale|amendment|ratification|lawsuit_filed|judgment", "date": "YYYY or YYYY-MM-DD", "location": "where", "description": "what happened", "entities_involved": ["name1", "name2"]}}
  ],
  "fee_patents": [
    {{"allottee": "Indian allottee's full name", "allotment_number": "e.g. 1292 or 2292", "acreage": "total acres", "land_description": "legal description if given (section/township/range)", "patent_date": "YYYY or YYYY-MM-DD", "patent_number": "if given", "trust_to_fee_mechanism": "how trust status was removed: private bill number, administrative action, Public Law, etc.", "subsequent_buyer": "non-Indian purchaser if any", "sale_price": "dollar amount if given", "sale_date": "when sold after patenting", "attorney": "attorney who facilitated the patent or sale", "mortgage_amount": "if mortgaged after patenting", "mortgage_holder": "who held the mortgage", "context": "full context of this fee patent transaction"}}
  ],
  "correspondence": [
    {{"sender": "full name of letter writer", "sender_title": "their position e.g. Superintendent, Crow Agency", "recipient": "full name of addressee", "recipient_title": "their position e.g. Commissioner of Indian Affairs", "date": "YYYY-MM-DD or as written", "subject": "what the letter is about", "action_requested": "what the sender asked for", "outcome": "what happened as a result, if known", "context": "additional details"}}
  ],
  "legislative_actions": [
    {{"bill_number": "e.g. S. 1385, H.R. 5477", "bill_title": "short title or description", "sponsor": "primary sponsor", "co_sponsors": "other sponsors, comma-separated", "action_type": "introduced|reported|amended|passed_senate|passed_house|vetoed|enacted|signed", "action_date": "YYYY or YYYY-MM-DD", "vote_count": "e.g. 169-100 or unanimous", "committee": "committee name if relevant", "outcome": "e.g. enacted as Private Law 68, or died in committee", "context": "what this action meant"}}
  ]
}}

EXTRACTION RULES:
- Extract EVERY person, even if mentioned only once
- Extract EVERY organization (agencies, companies, banks, courts, tribes, committees)
- Extract EVERY location (counties, reservations, cities, rivers, districts)
- Extract EVERY legal case by full name (e.g. "Dillon v. Antler Land Co. of Wyola")
- Extract EVERY piece of legislation by name AND number if given
- For acreage_holdings: extract whenever a specific person/company is associated with a specific acreage amount
- For financial_transactions: extract ALL dollar amounts with their context
- For relationships: extract the core structural facts (who owns what, who sold to whom, who approved what)
- For fee_patents: extract EVERY instance where an Indian allotment was converted from trust to fee status, including partial information. This is the most important extraction target — capture every allottee name, allotment number, acreage, and any subsequent sale or mortgage even if other fields are unknown.
- For correspondence: extract sender, recipient, and date for EVERY letter, memo, telegram, or report identified in the text. Include title/position when given.
- For legislative_actions: extract EVERY congressional or tribal legislative action — bill introductions, committee reports, floor votes, presidential actions. Include vote counts when given.
- Be specific — "opposed Section 2 of Crow Act" is better than "opposed legislation"

Document chunk:
{chunk}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=16000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text.strip()

            if response_text.startswith('```'):
                response_text = re.sub(r'^```(?:json)?\n', '', response_text)
                response_text = re.sub(r'\n```$', '', response_text)

            result = json.loads(response_text)
            self.extraction_count += 1
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in chunk {chunk_num}: {e}")
            return self._empty_result()
        except Exception as e:
            logger.error(f"Error extracting from chunk {chunk_num}: {str(e)}")
            return self._empty_result()

    @staticmethod
    def _empty_result() -> Dict:
        return {
            "entities": [], "financial_transactions": [],
            "relationships": [], "events": [],
            "fee_patents": [], "correspondence": [], "legislative_actions": []
        }

    def merge_results(self, chunk_results: List[Dict]) -> Dict:
        """Merge and deduplicate all extraction types across chunks."""

        # === Entities (same as v2) ===
        entity_map = defaultdict(lambda: {"contexts": [], "type": None, "name": None, "extra": {}})
        financial_list = []
        relationship_list = []
        event_list = []
        fee_patent_list = []
        correspondence_list = []
        legislative_list = []

        for chunk_result in chunk_results:
            for entity in chunk_result.get('entities', []):
                entity_type = entity.get('type')
                name = entity.get('name', '').strip()
                context = entity.get('context', '').strip()

                if not name:
                    continue

                normalized = name.lower().strip()
                key = (entity_type, normalized)

                if entity_map[key]["name"] is None:
                    entity_map[key]["name"] = name
                    entity_map[key]["type"] = entity_type
                    if entity_type == 'acreage_holding':
                        entity_map[key]["extra"] = {
                            "acres": entity.get("acres"),
                            "land_type": entity.get("land_type")
                        }

                if context and context not in entity_map[key]["contexts"]:
                    entity_map[key]["contexts"].append(context)

            financial_list.extend(chunk_result.get('financial_transactions', []))
            relationship_list.extend(chunk_result.get('relationships', []))
            event_list.extend(chunk_result.get('events', []))
            fee_patent_list.extend(chunk_result.get('fee_patents', []))
            correspondence_list.extend(chunk_result.get('correspondence', []))
            legislative_list.extend(chunk_result.get('legislative_actions', []))

        # Build merged entities list
        merged_entities = []
        for (entity_type, _), data in entity_map.items():
            combined_context = "; ".join(data["contexts"]) if data["contexts"] else "Mentioned in document"
            entity_record = {
                "type": data["type"],
                "name": data["name"],
                "context": combined_context
            }
            if data["extra"]:
                entity_record.update(data["extra"])
            merged_entities.append(entity_record)

        # Deduplicate financial transactions
        seen_financial = set()
        unique_financial = []
        for ft in financial_list:
            key = (ft.get('amount'), ft.get('payer'), ft.get('payee'), ft.get('for_what', '')[:50])
            if key not in seen_financial:
                seen_financial.add(key)
                unique_financial.append(ft)

        # Deduplicate relationships
        seen_relationships = set()
        unique_relationships = []
        for rel in relationship_list:
            key = (rel.get('type'), rel.get('subject'), rel.get('object'))
            if key not in seen_relationships:
                seen_relationships.add(key)
                unique_relationships.append(rel)

        # Deduplicate events
        seen_events = set()
        unique_events = []
        for event in event_list:
            key = (event.get('type'), event.get('date'), event.get('description', '')[:100])
            if key not in seen_events:
                seen_events.add(key)
                unique_events.append(event)

        # === v3: Deduplicate fee patents ===
        seen_patents = set()
        unique_patents = []
        for fp in fee_patent_list:
            key = (
                fp.get('allottee', '').lower().strip(),
                fp.get('allotment_number', '').strip(),
                fp.get('patent_date', '')
            )
            if key not in seen_patents:
                seen_patents.add(key)
                unique_patents.append(fp)

        # === v3: Deduplicate correspondence ===
        seen_corr = set()
        unique_corr = []
        for c in correspondence_list:
            key = (
                c.get('sender', '').lower().strip(),
                c.get('recipient', '').lower().strip(),
                c.get('date', ''),
                c.get('subject', '')[:50]
            )
            if key not in seen_corr:
                seen_corr.add(key)
                unique_corr.append(c)

        # === v3: Deduplicate legislative actions ===
        seen_legis = set()
        unique_legis = []
        for la in legislative_list:
            key = (
                la.get('bill_number', '').upper().strip(),
                la.get('action_type', ''),
                la.get('action_date', '')
            )
            if key not in seen_legis:
                seen_legis.add(key)
                unique_legis.append(la)

        return {
            "entities": merged_entities,
            "financial_transactions": unique_financial,
            "relationships": unique_relationships,
            "events": unique_events,
            "fee_patents": unique_patents,
            "correspondence": unique_corr,
            "legislative_actions": unique_legis,
        }

    def extract_all(self, text: str, doc_metadata: Dict) -> Dict:
        """Extract everything from a document (chunked)."""
        chunks = self.chunk_text(text)
        total_chunks = len(chunks)
        logger.info(f"  Processing in {total_chunks} chunks (v3 extraction)...")

        chunk_results = []
        for i, (chunk_text, start, end) in enumerate(chunks, start=1):
            logger.info(f"  Chunk {i}/{total_chunks}...")
            result = self.extract_from_chunk(chunk_text, i, total_chunks, doc_metadata)
            chunk_results.append(result)

        merged = self.merge_results(chunk_results)
        logger.info(
            f"  -> {len(merged['entities'])} entities, "
            f"{len(merged['financial_transactions'])} transactions, "
            f"{len(merged['relationships'])} relationships, "
            f"{len(merged['events'])} events, "
            f"{len(merged['fee_patents'])} fee patents, "
            f"{len(merged['correspondence'])} correspondence, "
            f"{len(merged['legislative_actions'])} legislative actions"
        )
        return merged


class DatabaseManagerV3:
    """Database manager for v3 schema — adds fee_patents, correspondence, legislative_actions."""

    def __init__(self, db_name: str = "crow_historical_docs"):
        self.db_name = db_name
        self.conn = None
        self.connect()
        self.ensure_schema()

    def connect(self):
        database_url = os.environ.get("DATABASE_URL")
        try:
            if database_url:
                self.conn = psycopg2.connect(database_url)
            else:
                self.conn = psycopg2.connect(
                    dbname=self.db_name,
                    user=os.environ.get("USER", "cwm6W"),
                    host="localhost",
                )
            self.conn.autocommit = True
            logger.info(f"Connected to database: {self.db_name}")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise

    def ensure_schema(self):
        with self.conn.cursor() as cur:
            # === v2 tables (unchanged) ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    display_title TEXT,
                    summary TEXT,
                    summary_date TIMESTAMP,
                    file_path TEXT UNIQUE,
                    page_count INTEGER,
                    file_size BIGINT,
                    full_text TEXT,
                    collection TEXT,
                    subcollection TEXT,
                    location TEXT,
                    extracted_dates TEXT,
                    extraction_model TEXT,
                    pipeline_version TEXT DEFAULT 'v3',
                    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    context TEXT,
                    acres TEXT,
                    land_type TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mentions (
                    id SERIAL PRIMARY KEY,
                    entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
                    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    context TEXT,
                    UNIQUE(entity_id, document_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    type TEXT,
                    date TEXT,
                    location TEXT,
                    description TEXT,
                    metadata JSONB
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS financial_transactions (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    amount TEXT,
                    type TEXT,
                    payer TEXT,
                    payee TEXT,
                    for_what TEXT,
                    date TEXT,
                    context TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    type TEXT,
                    subject TEXT,
                    object TEXT,
                    context TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # === v3 tables ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS fee_patents (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    allottee TEXT NOT NULL,
                    allotment_number TEXT,
                    acreage TEXT,
                    land_description TEXT,
                    patent_date TEXT,
                    patent_number TEXT,
                    trust_to_fee_mechanism TEXT,
                    subsequent_buyer TEXT,
                    sale_price TEXT,
                    sale_date TEXT,
                    attorney TEXT,
                    mortgage_amount TEXT,
                    mortgage_holder TEXT,
                    context TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS correspondence (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    sender TEXT NOT NULL,
                    sender_title TEXT,
                    recipient TEXT NOT NULL,
                    recipient_title TEXT,
                    date TEXT,
                    subject TEXT,
                    action_requested TEXT,
                    outcome TEXT,
                    context TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS legislative_actions (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    bill_number TEXT NOT NULL,
                    bill_title TEXT,
                    sponsor TEXT,
                    co_sponsors TEXT,
                    action_type TEXT NOT NULL,
                    action_date TEXT,
                    vote_count TEXT,
                    committee TEXT,
                    outcome TEXT,
                    context TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes (v2 + v3)
            for idx_sql in [
                "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)",
                "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)",
                "CREATE INDEX IF NOT EXISTS idx_entities_name_type ON entities(name, type)",
                "CREATE INDEX IF NOT EXISTS idx_entities_acres ON entities(acres)",
                "CREATE INDEX IF NOT EXISTS idx_mentions_entity ON mentions(entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_mentions_document ON mentions(document_id)",
                "CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)",
                "CREATE INDEX IF NOT EXISTS idx_events_date ON events(date)",
                "CREATE INDEX IF NOT EXISTS idx_events_document ON events(document_id)",
                "CREATE INDEX IF NOT EXISTS idx_financial_document ON financial_transactions(document_id)",
                "CREATE INDEX IF NOT EXISTS idx_financial_payer ON financial_transactions(payer)",
                "CREATE INDEX IF NOT EXISTS idx_financial_payee ON financial_transactions(payee)",
                "CREATE INDEX IF NOT EXISTS idx_financial_type ON financial_transactions(type)",
                "CREATE INDEX IF NOT EXISTS idx_relationships_document ON relationships(document_id)",
                "CREATE INDEX IF NOT EXISTS idx_relationships_subject ON relationships(subject)",
                "CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(type)",
                "CREATE INDEX IF NOT EXISTS idx_documents_file_name ON documents(file_name)",
                "CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection)",
                # v3 indexes
                "CREATE INDEX IF NOT EXISTS idx_fee_patents_document ON fee_patents(document_id)",
                "CREATE INDEX IF NOT EXISTS idx_fee_patents_allottee ON fee_patents(allottee)",
                "CREATE INDEX IF NOT EXISTS idx_fee_patents_allotment ON fee_patents(allotment_number)",
                "CREATE INDEX IF NOT EXISTS idx_fee_patents_buyer ON fee_patents(subsequent_buyer)",
                "CREATE INDEX IF NOT EXISTS idx_fee_patents_attorney ON fee_patents(attorney)",
                "CREATE INDEX IF NOT EXISTS idx_fee_patents_date ON fee_patents(patent_date)",
                "CREATE INDEX IF NOT EXISTS idx_correspondence_document ON correspondence(document_id)",
                "CREATE INDEX IF NOT EXISTS idx_correspondence_sender ON correspondence(sender)",
                "CREATE INDEX IF NOT EXISTS idx_correspondence_recipient ON correspondence(recipient)",
                "CREATE INDEX IF NOT EXISTS idx_correspondence_date ON correspondence(date)",
                "CREATE INDEX IF NOT EXISTS idx_legislative_document ON legislative_actions(document_id)",
                "CREATE INDEX IF NOT EXISTS idx_legislative_bill ON legislative_actions(bill_number)",
                "CREATE INDEX IF NOT EXISTS idx_legislative_sponsor ON legislative_actions(sponsor)",
                "CREATE INDEX IF NOT EXISTS idx_legislative_action_type ON legislative_actions(action_type)",
                "CREATE INDEX IF NOT EXISTS idx_legislative_date ON legislative_actions(action_date)",
            ]:
                cur.execute(idx_sql)

            # Upgrade columns if migrating from v1/v2
            for col_sql in [
                "ALTER TABLE entities ADD COLUMN IF NOT EXISTS acres TEXT",
                "ALTER TABLE entities ADD COLUMN IF NOT EXISTS land_type TEXT",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS display_title TEXT",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary_date TIMESTAMP",
            ]:
                try:
                    cur.execute(col_sql)
                except Exception:
                    pass

        logger.info("Schema ready (v3: entities + fee_patents + correspondence + legislative_actions)")

    def is_processed(self, file_path: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM documents WHERE file_path = %s", (file_path,))
            return cur.fetchone() is not None

    def find_existing_doc(self, file_name: str) -> Optional[int]:
        """Find an existing document by file_name (for --force re-extraction)."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM documents WHERE file_name = %s", (file_name,))
            row = cur.fetchone()
            return row[0] if row else None

    def clear_extracted_data(self, doc_id: int):
        """Remove all extracted data for a document, preserving the doc row, summary, and display_title."""
        with self.conn.cursor() as cur:
            # Delete mentions first (references entities)
            cur.execute("DELETE FROM mentions WHERE document_id = %s", (doc_id,))
            # Delete document-level extracted data
            cur.execute("DELETE FROM events WHERE document_id = %s", (doc_id,))
            cur.execute("DELETE FROM financial_transactions WHERE document_id = %s", (doc_id,))
            cur.execute("DELETE FROM relationships WHERE document_id = %s", (doc_id,))
            cur.execute("DELETE FROM fee_patents WHERE document_id = %s", (doc_id,))
            cur.execute("DELETE FROM correspondence WHERE document_id = %s", (doc_id,))
            cur.execute("DELETE FROM legislative_actions WHERE document_id = %s", (doc_id,))
            self.conn.commit()
            logger.info(f"  -> Cleared existing extracted data for doc_id={doc_id}")

    def update_document_for_reextraction(self, doc_id: int, text: str, metadata: Dict,
                                          collection_metadata: Dict, model_name: str):
        """Update an existing document row for v3 re-extraction (preserves summary, display_title)."""
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE documents SET
                    file_path = %s,
                    page_count = %s,
                    file_size = %s,
                    full_text = %s,
                    collection = %s,
                    subcollection = %s,
                    location = %s,
                    extracted_dates = %s,
                    extraction_model = %s,
                    pipeline_version = 'v3',
                    processed_date = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                metadata['file_path'],
                metadata.get('page_count'),
                metadata.get('file_size'),
                text,
                collection_metadata.get('collection'),
                collection_metadata.get('subcollection'),
                collection_metadata.get('location'),
                metadata.get('extracted_dates', []),
                model_name,
                doc_id,
            ))
            self.conn.commit()
        return doc_id

    def insert_document(self, text: str, metadata: Dict,
                        collection_metadata: Dict, model_name: str = DEFAULT_MODEL) -> int:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents
                (file_name, file_path, page_count, file_size, full_text,
                 collection, subcollection, location, extracted_dates,
                 extraction_model, pipeline_version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                metadata['file_name'],
                metadata['file_path'],
                metadata.get('page_count'),
                metadata.get('file_size'),
                text,
                collection_metadata.get('collection'),
                collection_metadata.get('subcollection'),
                collection_metadata.get('location'),
                metadata.get('extracted_dates', []),
                model_name,
                'v3'
            ))
            return cur.fetchone()[0]

    def insert_entity_batch(self, entities: List[Dict], document_id: int):
        with self.conn.cursor() as cur:
            for entity in entities:
                name = entity.get('name', '').strip()
                etype = entity.get('type', 'unknown')
                context = entity.get('context', '')
                acres = entity.get('acres')
                land_type = entity.get('land_type')

                if not name:
                    continue

                cur.execute(
                    "SELECT id FROM entities WHERE name = %s AND type = %s",
                    (name, etype)
                )
                row = cur.fetchone()
                if row:
                    entity_id = row[0]
                    cur.execute("""
                        UPDATE entities
                        SET context = CASE
                            WHEN context IS NULL OR context = '' THEN %s
                            WHEN context NOT LIKE %s THEN context || '; ' || %s
                            ELSE context
                        END,
                        acres = COALESCE(%s, acres),
                        land_type = COALESCE(%s, land_type)
                        WHERE id = %s
                    """, (context, f'%{context[:50]}%', context, acres, land_type, entity_id))
                else:
                    cur.execute(
                        "INSERT INTO entities (name, type, context, acres, land_type) "
                        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                        (name, etype, context, acres, land_type)
                    )
                    entity_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO mentions (entity_id, document_id, context)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (entity_id, document_id) DO NOTHING
                """, (entity_id, document_id, context))

    def insert_financial_transactions(self, transactions: List[Dict], document_id: int):
        with self.conn.cursor() as cur:
            for ft in transactions:
                cur.execute("""
                    INSERT INTO financial_transactions
                    (document_id, amount, type, payer, payee, for_what, date, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    document_id,
                    ft.get('amount'),
                    ft.get('type'),
                    ft.get('payer'),
                    ft.get('payee'),
                    ft.get('for_what'),
                    ft.get('date'),
                    ft.get('context')
                ))

    def insert_relationships(self, relationships: List[Dict], document_id: int):
        with self.conn.cursor() as cur:
            for rel in relationships:
                cur.execute("""
                    INSERT INTO relationships (document_id, type, subject, object, context)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    document_id,
                    rel.get('type'),
                    rel.get('subject'),
                    rel.get('object'),
                    rel.get('context')
                ))

    def insert_events(self, events: List[Dict], document_id: int):
        with self.conn.cursor() as cur:
            for event in events:
                cur.execute("""
                    INSERT INTO events (document_id, type, date, location, description, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    document_id,
                    event.get('type'),
                    event.get('date'),
                    event.get('location'),
                    event.get('description'),
                    json.dumps(event.get('entities_involved', []))
                ))

    # === v3 insertion methods ===

    def insert_fee_patents(self, fee_patents: List[Dict], document_id: int):
        with self.conn.cursor() as cur:
            for fp in fee_patents:
                allottee = (fp.get('allottee') or '').strip()
                if not allottee:
                    continue
                cur.execute("""
                    INSERT INTO fee_patents
                    (document_id, allottee, allotment_number, acreage, land_description,
                     patent_date, patent_number, trust_to_fee_mechanism,
                     subsequent_buyer, sale_price, sale_date, attorney,
                     mortgage_amount, mortgage_holder, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    document_id,
                    allottee,
                    fp.get('allotment_number'),
                    fp.get('acreage'),
                    fp.get('land_description'),
                    fp.get('patent_date'),
                    fp.get('patent_number'),
                    fp.get('trust_to_fee_mechanism'),
                    fp.get('subsequent_buyer'),
                    fp.get('sale_price'),
                    fp.get('sale_date'),
                    fp.get('attorney'),
                    fp.get('mortgage_amount'),
                    fp.get('mortgage_holder'),
                    fp.get('context'),
                ))

    def insert_correspondence(self, correspondence: List[Dict], document_id: int):
        with self.conn.cursor() as cur:
            for c in correspondence:
                sender = (c.get('sender') or '').strip()
                recipient = (c.get('recipient') or '').strip()
                if not sender or not recipient:
                    continue
                cur.execute("""
                    INSERT INTO correspondence
                    (document_id, sender, sender_title, recipient, recipient_title,
                     date, subject, action_requested, outcome, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    document_id,
                    sender,
                    c.get('sender_title'),
                    recipient,
                    c.get('recipient_title'),
                    c.get('date'),
                    c.get('subject'),
                    c.get('action_requested'),
                    c.get('outcome'),
                    c.get('context'),
                ))

    def insert_legislative_actions(self, actions: List[Dict], document_id: int):
        with self.conn.cursor() as cur:
            for la in actions:
                bill_number = (la.get('bill_number') or '').strip()
                action_type = (la.get('action_type') or '').strip()
                if not bill_number or not action_type:
                    continue
                cur.execute("""
                    INSERT INTO legislative_actions
                    (document_id, bill_number, bill_title, sponsor, co_sponsors,
                     action_type, action_date, vote_count, committee, outcome, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    document_id,
                    bill_number,
                    la.get('bill_title'),
                    la.get('sponsor'),
                    la.get('co_sponsors'),
                    action_type,
                    la.get('action_date'),
                    la.get('vote_count'),
                    la.get('committee'),
                    la.get('outcome'),
                    la.get('context'),
                ))


def main():
    parser = argparse.ArgumentParser(
        description='Extraction pipeline v3 — v2 entities + fee patents + correspondence + legislative actions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
v3 extraction types (13 total):
  From v2:  person, organization, location, land_parcel, legal_case,
            legislation, acreage_holding, financial_transaction,
            relationship, event
  New v3:   fee_patent, correspondence, legislative_action

Example:
  python3 poc_pipeline_chunked_v3.py --input ~/Desktop/CROW_BATCH_10 --output results_v3/
  python3 poc_pipeline_chunked_v3.py --input ~/Desktop/CROW_BATCH_10 --output results_v3/ --model claude-opus-4-6
        """
    )
    parser.add_argument('--input', required=True, help='Input directory containing PDFs')
    parser.add_argument('--output', required=True, help='Output directory for results')
    parser.add_argument('--db', default='crow_historical_docs', help='PostgreSQL database name')
    parser.add_argument('--model', default=DEFAULT_MODEL, help=f'Model to use (default: {DEFAULT_MODEL})')
    parser.add_argument('--force', action='store_true',
                        help='Re-extract documents already in the database (matches by file_name, preserves doc IDs/summaries)')
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("EXTRACTION PIPELINE v3")
    logger.info("v2 entities + fee_patents + correspondence + legislative_actions")
    logger.info("=" * 60)
    logger.info(f"Input:    {input_path}")
    logger.info(f"Database: {args.db}")
    logger.info(f"Model:    {args.model}")
    if args.force:
        logger.info(f"Mode:     FORCE RE-EXTRACTION (preserving doc IDs and summaries)")

    doc_processor = DocumentProcessor()
    extractor = EntityExtractorV3(model=args.model)
    db_manager = DatabaseManagerV3(db_name=args.db)

    pdf_files = sorted(input_path.glob("**/*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files\n")

    results = {
        'processed': 0, 'skipped': 0, 'errors': 0,
        'entities': 0, 'transactions': 0, 'relationships': 0, 'events': 0,
        'fee_patents': 0, 'correspondence': 0, 'legislative_actions': 0,
        'pipeline': 'v3',
        'model': args.model,
        'start_time': datetime.now().isoformat()
    }

    for i, pdf_path in enumerate(pdf_files, start=1):
        logger.info(f"[{i}/{len(pdf_files)}] {pdf_path.name}")

        try:
            # Check if already processed
            if not args.force and db_manager.is_processed(str(pdf_path.absolute())):
                logger.info("  -> Already processed, skipping")
                results['skipped'] += 1
                continue

            text, metadata = doc_processor.extract_text_from_pdf(pdf_path)
            if not text.strip():
                logger.warning(f"  -> No text extracted")
                results['errors'] += 1
                continue

            collection_metadata = doc_processor.extract_collection_metadata(pdf_path, input_path)

            # In force mode, reuse existing doc row (preserves ID, summary, display_title)
            doc_id = None
            if args.force:
                doc_id = db_manager.find_existing_doc(metadata['file_name'])
                if doc_id:
                    db_manager.clear_extracted_data(doc_id)
                    db_manager.update_document_for_reextraction(
                        doc_id, text, metadata, collection_metadata, args.model
                    )

            if doc_id is None:
                doc_id = db_manager.insert_document(text, metadata, collection_metadata, args.model)

            extraction = extractor.extract_all(
                text, {**metadata, **collection_metadata}
            )

            if extraction['entities']:
                db_manager.insert_entity_batch(extraction['entities'], doc_id)
                results['entities'] += len(extraction['entities'])

            if extraction['financial_transactions']:
                db_manager.insert_financial_transactions(extraction['financial_transactions'], doc_id)
                results['transactions'] += len(extraction['financial_transactions'])

            if extraction['relationships']:
                db_manager.insert_relationships(extraction['relationships'], doc_id)
                results['relationships'] += len(extraction['relationships'])

            if extraction['events']:
                db_manager.insert_events(extraction['events'], doc_id)
                results['events'] += len(extraction['events'])

            if extraction['fee_patents']:
                db_manager.insert_fee_patents(extraction['fee_patents'], doc_id)
                results['fee_patents'] += len(extraction['fee_patents'])

            if extraction['correspondence']:
                db_manager.insert_correspondence(extraction['correspondence'], doc_id)
                results['correspondence'] += len(extraction['correspondence'])

            if extraction['legislative_actions']:
                db_manager.insert_legislative_actions(extraction['legislative_actions'], doc_id)
                results['legislative_actions'] += len(extraction['legislative_actions'])

            results['processed'] += 1

        except Exception as e:
            logger.error(f"  Error: {str(e)}")
            results['errors'] += 1

    results['end_time'] = datetime.now().isoformat()
    results['total_files'] = len(pdf_files)

    summary_path = output_path / 'processing_summary_v3.json'
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info("\n" + "=" * 60)
    logger.info("EXTRACTION COMPLETE (v3)")
    logger.info("=" * 60)
    logger.info(f"Processed:           {results['processed']}/{results['total_files']}")
    logger.info(f"Skipped:             {results['skipped']} (already in database)")
    logger.info(f"Errors:              {results['errors']}")
    logger.info(f"Entities:            {results['entities']}")
    logger.info(f"Transactions:        {results['transactions']}")
    logger.info(f"Relationships:       {results['relationships']}")
    logger.info(f"Events:              {results['events']}")
    logger.info(f"Fee patents:         {results['fee_patents']}")
    logger.info(f"Correspondence:      {results['correspondence']}")
    logger.info(f"Legislative actions: {results['legislative_actions']}")


if __name__ == "__main__":
    main()
