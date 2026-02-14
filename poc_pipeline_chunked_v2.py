#!/usr/bin/env python3
"""
ENHANCED Exhaustive Document Processing Pipeline - Version 2
Expanded entity extraction: 10 entity types instead of 4.

NEW entity types vs v1:
  v1: person, organization, location, land_parcel
  v2: person, organization, location, land_parcel,
      legal_case, legislation, financial_transaction,
      date_event, relationship, acreage_holding

Usage:
    python3 poc_pipeline_chunked_v2.py --input /path/to/pdfs --output results/ --db crow_historical_docs
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


class DocumentProcessor:
    """Handles text extraction from PDFs - identical to v1"""

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


class EnhancedEntityExtractor:
    """
    Enhanced extraction with 10 entity types.

    New types and why they matter for this research:

    legal_case       - Dillon v. Antler Land Co. appears 20+ times across documents
                       but was buried in context fields. Now a first-class entity.

    legislation      - Crow Act 1920, H.R. 5477, S. 3698, specific bill numbers
                       are the legal scaffolding of dispossession. Track them directly.

    financial_transaction - Dollar amounts with parties: "$7,000 sheep permit",
                       "$35,000 bribe to tribal council", "$11/acre purchase price".
                       Critical for showing systematic undervaluation.

    date_event       - Specific dated actions: "March 18, 1940 - House passed H.R. 5477"
                       Enables timeline construction across documents.

    relationship     - Structured triples: "Murphy OWNS 3,160 acres",
                       "Bair LEASED grazing rights FROM Crow Tribe",
                       "BIA APPROVED sale TO Kennedy". The edges of the network graph.

    acreage_holding  - Named entity + acreage + type (farm/grazing/allotment):
                       "Murphy Land & Cattle: 3,160 acres farm + 22,000 acres leased"
                       Directly tracks Crow Act Section 2 violations.
    """

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=api_key)
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
- Be specific - "opposed Section 2 of Crow Act" is better than "opposed legislation"

Document chunk:
{chunk}"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
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
            return {"entities": [], "financial_transactions": [], "relationships": [], "events": []}
        except Exception as e:
            logger.error(f"Error extracting from chunk {chunk_num}: {str(e)}")
            return {"entities": [], "financial_transactions": [], "relationships": [], "events": []}

    def merge_results(self, chunk_results: List[Dict]) -> Dict:
        """Merge and deduplicate all extraction types across chunks"""

        # Merge entities (same as v1 for persons/orgs/locations/land_parcels)
        entity_map = defaultdict(lambda: {"contexts": [], "type": None, "name": None, "extra": {}})
        financial_list = []
        relationship_list = []
        event_list = []

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
                    # Store extra fields for acreage_holding
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

        return {
            "entities": merged_entities,
            "financial_transactions": unique_financial,
            "relationships": unique_relationships,
            "events": unique_events
        }

    def extract_entities_and_relationships(self, text: str, doc_metadata: Dict) -> Dict:
        chunks = self.chunk_text(text)
        total_chunks = len(chunks)
        logger.info(f"  Processing in {total_chunks} chunks (enhanced extraction)...")

        chunk_results = []
        for i, (chunk_text, start, end) in enumerate(chunks, start=1):
            logger.info(f"  Chunk {i}/{total_chunks}...")
            result = self.extract_from_chunk(chunk_text, i, total_chunks, doc_metadata)
            chunk_results.append(result)

        merged = self.merge_results(chunk_results)
        logger.info(
            f"  → {len(merged['entities'])} entities, "
            f"{len(merged['financial_transactions'])} transactions, "
            f"{len(merged['relationships'])} relationships, "
            f"{len(merged['events'])} events"
        )
        return merged


class DatabaseManager:
    """Enhanced database manager - adds tables for new extraction types"""

    def __init__(self, db_name: str = "crow_historical_docs"):
        self.db_name = db_name
        self.conn = None
        self.connect()
        self.ensure_schema()

    def connect(self):
        try:
            self.conn = psycopg2.connect(f"postgresql://localhost/{self.db_name}")
            self.conn.autocommit = True
            logger.info(f"✓ Connected to database: {self.db_name}")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise

    def ensure_schema(self):
        with self.conn.cursor() as cur:
            # Existing tables (compatible with v1)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_path TEXT UNIQUE,
                    page_count INTEGER,
                    file_size BIGINT,
                    full_text TEXT,
                    collection TEXT,
                    subcollection TEXT,
                    location TEXT,
                    extracted_dates TEXT,
                    extraction_model TEXT,
                    pipeline_version TEXT DEFAULT 'v2',
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
                    entity_id INTEGER REFERENCES entities(id),
                    document_id INTEGER REFERENCES documents(id),
                    context TEXT,
                    UNIQUE(entity_id, document_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id),
                    type TEXT,
                    date TEXT,
                    location TEXT,
                    description TEXT,
                    metadata JSONB
                )
            """)

            # NEW tables for v2
            cur.execute("""
                CREATE TABLE IF NOT EXISTS financial_transactions (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id),
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
                    document_id INTEGER REFERENCES documents(id),
                    type TEXT,
                    subject TEXT,
                    object TEXT,
                    context TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes
            for idx_sql in [
                "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)",
                "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)",
                "CREATE INDEX IF NOT EXISTS idx_entities_acres ON entities(acres)",
                "CREATE INDEX IF NOT EXISTS idx_events_date ON events(date)",
                "CREATE INDEX IF NOT EXISTS idx_financial_payer ON financial_transactions(payer)",
                "CREATE INDEX IF NOT EXISTS idx_financial_payee ON financial_transactions(payee)",
                "CREATE INDEX IF NOT EXISTS idx_relationships_subject ON relationships(subject)",
                "CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(type)",
                "CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection)",
            ]:
                cur.execute(idx_sql)

            # Add new columns to existing entities table if upgrading from v1
            for col_sql in [
                "ALTER TABLE entities ADD COLUMN IF NOT EXISTS acres TEXT",
                "ALTER TABLE entities ADD COLUMN IF NOT EXISTS land_type TEXT",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS pipeline_version TEXT DEFAULT 'v1'",
            ]:
                try:
                    cur.execute(col_sql)
                except Exception:
                    pass

        logger.info("✓ Enhanced schema ready (v2)")

    def is_processed(self, file_path: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM documents WHERE file_path = %s", (file_path,))
            return cur.fetchone() is not None

    def insert_document(self, text: str, metadata: Dict,
                        collection_metadata: Dict) -> int:
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
                str(metadata.get('extracted_dates', [])),
                'claude-sonnet-4-20250514',
                'v2'
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


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced extraction pipeline v2 - 10 entity types',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
New entity types vs v1:
  legal_case           - Court cases by name
  legislation          - Acts and bills by name/number
  acreage_holding      - Named entity + specific acreage (tracks Section 2 violations)
  financial_transaction - Dollar amounts with parties and context
  relationship         - Structured triples (owns, sold, approved, violated)
  date_event           - Specific dated actions for timeline construction

Example:
  python3 poc_pipeline_chunked_v2.py --input ~/Desktop/CROW_BATCH_6 --output results_v2/
        """
    )
    parser.add_argument('--input',  required=True, help='Input directory containing PDFs')
    parser.add_argument('--output', required=True, help='Output directory for results')
    parser.add_argument('--db',     default='crow_historical_docs', help='PostgreSQL database name')
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("ENHANCED EXTRACTION PIPELINE v2")
    logger.info("10 entity types: person, organization, location,")
    logger.info("land_parcel, legal_case, legislation, acreage_holding,")
    logger.info("financial_transaction, relationship, event")
    logger.info("=" * 60)
    logger.info(f"Input:    {input_path}")
    logger.info(f"Database: {args.db}")

    doc_processor = DocumentProcessor()
    extractor     = EnhancedEntityExtractor()
    db_manager    = DatabaseManager(db_name=args.db)

    pdf_files = sorted(input_path.glob("**/*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files\n")

    results = {
        'processed': 0, 'skipped': 0, 'errors': 0,
        'entities': 0, 'transactions': 0, 'relationships': 0, 'events': 0,
        'pipeline': 'v2',
        'start_time': datetime.now().isoformat()
    }

    for i, pdf_path in enumerate(pdf_files, start=1):
        logger.info(f"[{i}/{len(pdf_files)}] {pdf_path.name}")

        try:
            if db_manager.is_processed(str(pdf_path.absolute())):
                logger.info("  → Already processed, skipping")
                results['skipped'] += 1
                continue

            text, metadata = doc_processor.extract_text_from_pdf(pdf_path)
            if not text.strip():
                logger.warning(f"  → No text extracted")
                results['errors'] += 1
                continue

            collection_metadata = doc_processor.extract_collection_metadata(pdf_path, input_path)
            doc_id = db_manager.insert_document(text, metadata, collection_metadata)

            extraction = extractor.extract_entities_and_relationships(
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

            results['processed'] += 1

        except Exception as e:
            logger.error(f"  ✗ Error: {str(e)}")
            results['errors'] += 1

    results['end_time'] = datetime.now().isoformat()
    results['total_files'] = len(pdf_files)

    summary_path = output_path / 'processing_summary_v2.json'
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info("\n" + "=" * 60)
    logger.info("ENHANCED EXTRACTION COMPLETE (v2)")
    logger.info("=" * 60)
    logger.info(f"Processed:     {results['processed']}/{results['total_files']}")
    logger.info(f"Skipped:       {results['skipped']} (already in database)")
    logger.info(f"Errors:        {results['errors']}")
    logger.info(f"Entities:      {results['entities']}")
    logger.info(f"Transactions:  {results['transactions']}")
    logger.info(f"Relationships: {results['relationships']}")
    logger.info(f"Events:        {results['events']}")


if __name__ == "__main__":
    main()
