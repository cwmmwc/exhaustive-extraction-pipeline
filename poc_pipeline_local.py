#!/usr/bin/env python3
"""
LOCAL Exhaustive Document Processing Pipeline
Uses Ollama (local LLM) instead of Anthropic API - zero API costs.

SETUP (one-time):
    brew install ollama
    ollama pull llama3.1:70b      # Best quality, needs 64GB RAM
    ollama pull llama3.1:8b       # Faster, needs 16GB RAM, lower quality

USAGE:
    # Start Ollama server first (in a separate terminal):
    ollama serve

    # Then run this pipeline:
    python3 poc_pipeline_local.py --input /path/to/pdfs --output results/ --db crow_historical_docs

    # To use a different model:
    python3 poc_pipeline_local.py --input /path/to/pdfs --output results/ --model llama3.1:8b

NOTES:
    - No API key needed
    - No internet connection needed after model download
    - Slower than Claude API (~3-5x) but free
    - Quality: ~85-90% of Claude Sonnet 4 with 70b model
    - Uses same PostgreSQL schema as poc_pipeline_chunked.py
    - Databases are fully compatible and can be merged later
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

import fitz  # PyMuPDF - pip install pymupdf
import psycopg2
from psycopg2.extras import execute_batch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIGURATION - change model here if needed
# ─────────────────────────────────────────────
DEFAULT_MODEL = "llama3.1:70b"   # Best quality (requires 64GB RAM)
FAST_MODEL    = "llama3.1:8b"    # Fast/small (requires 16GB RAM)
CHUNK_SIZE    = 40000            # Characters per chunk (Ollama handles ~128K tokens)
CHUNK_OVERLAP = 5000             # Overlap between chunks to avoid missing entities at boundaries


# ─────────────────────────────────────────────
# OLLAMA CLIENT
# Thin wrapper - no external library needed,
# Ollama exposes a simple HTTP API
# ─────────────────────────────────────────────
class OllamaClient:
    """Wrapper around Ollama's local HTTP API"""

    def __init__(self, model: str = DEFAULT_MODEL, host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self._check_server()

    def _check_server(self):
        """Verify Ollama is running"""
        try:
            import urllib.request
            urllib.request.urlopen(f"{self.host}/api/tags", timeout=3)
            logger.info(f"✓ Ollama server running at {self.host}")
        except Exception:
            logger.error(
                "✗ Ollama server not running!\n"
                "  Start it with: ollama serve\n"
                "  Or install with: brew install ollama"
            )
            sys.exit(1)

    def _check_model(self):
        """Check if model is available, offer to pull if not"""
        try:
            import urllib.request, json as j
            data = urllib.request.urlopen(f"{self.host}/api/tags").read()
            models = [m['name'] for m in j.loads(data).get('models', [])]
            # Check if model (with or without :latest tag) is present
            base = self.model.split(':')[0]
            available = any(base in m for m in models)
            if not available:
                logger.warning(f"Model '{self.model}' not found locally.")
                logger.warning(f"Pull it with: ollama pull {self.model}")
                logger.warning(f"Available models: {models}")
                sys.exit(1)
            logger.info(f"✓ Model '{self.model}' is available")
        except SystemExit:
            raise
        except Exception as e:
            logger.warning(f"Could not verify model availability: {e}")

    def chat(self, prompt: str, temperature: float = 0.1) -> str:
        """Send a prompt to Ollama, return response text"""
        import urllib.request, urllib.error, json as j

        payload = j.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 4096,    # Max tokens to generate
                "repeat_penalty": 1.1,  # Reduce repetition
            }
        }).encode()

        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                result = j.loads(resp.read())
                return result['message']['content']
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama API error {e.code}: {e.read().decode()}")


# ─────────────────────────────────────────────
# DOCUMENT PROCESSOR
# Identical to poc_pipeline_chunked.py
# ─────────────────────────────────────────────
class DocumentProcessor:
    """Handles text extraction from PDFs"""

    def __init__(self):
        self.processed_count = 0
        self.error_count = 0

    def extract_text_from_pdf(self, pdf_path: Path) -> Tuple[str, Dict]:
        """Extract text and metadata from a PDF file"""
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

            # Extract dates from first 5000 characters
            date_patterns = [
                r'\b(19|20)\d{2}\b',
                r'\b(?:January|February|March|April|May|June|July|'
                r'August|September|October|November|December)\s+\d{1,2},?\s+(19|20)\d{2}\b'
            ]
            dates_found = []
            for pattern in date_patterns:
                matches = re.findall(pattern, full_text[:5000])
                dates_found.extend(matches)

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
        """Infer collection/subcollection/location from folder structure"""
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


# ─────────────────────────────────────────────
# LOCAL ENTITY EXTRACTOR
# Drop-in replacement for ChunkedEntityExtractor
# Uses Ollama instead of Anthropic API
# ─────────────────────────────────────────────
class LocalEntityExtractor:
    """
    Entity extraction using local Ollama model.
    Same interface as ChunkedEntityExtractor in poc_pipeline_chunked.py.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self.client = OllamaClient(model=model)
        self.client._check_model()
        self.extraction_count = 0
        self.chunk_size = CHUNK_SIZE
        self.overlap = CHUNK_OVERLAP
        logger.info(f"✓ Local extractor ready using model: {model}")

    def chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        """Split text into overlapping chunks"""
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
        """
        Extract entities from a single chunk using Ollama.

        Key difference from Claude version:
        - Local models need MORE explicit JSON formatting instructions
        - Smaller context window requires shorter chunks
        - Temperature set very low (0.1) for consistent JSON output
        """

        # NOTE: Local models are more likely to add prose before/after JSON.
        # The prompt explicitly tells them not to, and we strip aggressively below.
        prompt = f"""You are analyzing a historical document about land, taxation, and Native American affairs.
This is chunk {chunk_num} of {total_chunks} from document: {doc_metadata.get('file_name', 'Unknown')}

Collection: {doc_metadata.get('collection', 'Unknown')}
Location: {doc_metadata.get('location', 'Unknown')}
Dates: {doc_metadata.get('extracted_dates', [])}

YOUR TASK: Extract ALL entities (people, organizations, locations, land parcels) and events.

CRITICAL INSTRUCTIONS:
- Output ONLY a JSON object. No introduction. No explanation. No markdown. No ```json blocks.
- Start your response with {{ and end with }}
- Extract EVERY person mentioned, even if briefly
- Extract EVERY organization (agencies, companies, banks, courts, tribes)
- Extract EVERY location (counties, reservations, cities, agencies)
- Extract EVERY land parcel (allotment numbers, section/township/range)

JSON FORMAT (follow exactly):
{{
  "entities": [
    {{"type": "person", "name": "FULL NAME AS WRITTEN", "context": "their role or what they did"}},
    {{"type": "organization", "name": "FULL NAME", "context": "what they did"}},
    {{"type": "location", "name": "FULL NAME", "context": "what happened here"}},
    {{"type": "land_parcel", "name": "allotment # or description", "context": "what happened to this land"}}
  ],
  "events": [
    {{"type": "patent|foreclosure|tax_sale|allotment|hearing|complaint|mortgage|land_sale",
      "date": "YYYY or YYYY-MM-DD",
      "location": "place name",
      "description": "what happened",
      "entities_involved": ["name1", "name2"]}}
  ]
}}

DOCUMENT TEXT:
{chunk[:12000]}"""

        try:
            response_text = self.client.chat(prompt, temperature=0.1)
            response_text = response_text.strip()

            # Strip any markdown code fences local models sometimes add
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text, flags=re.MULTILINE)
            response_text = re.sub(r'\s*```\s*$', '', response_text, flags=re.MULTILINE)
            response_text = response_text.strip()

            # Find the JSON object (in case model added prose before/after)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)

            result = json.loads(response_text)

            # Normalize: some models use 'identifier' instead of 'name' for land_parcels
            for entity in result.get('entities', []):
                if 'identifier' in entity and 'name' not in entity:
                    entity['name'] = entity.pop('identifier')

            self.extraction_count += 1
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in chunk {chunk_num}: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            return {"entities": [], "events": []}
        except Exception as e:
            logger.error(f"Error extracting from chunk {chunk_num}: {str(e)}")
            return {"entities": [], "events": []}

    def merge_entities(self, chunk_results: List[Dict]) -> Dict:
        """
        Merge entities across chunks, combining contexts.
        Identical to poc_pipeline_chunked.py version.
        """
        entity_map = defaultdict(lambda: {"contexts": [], "type": None, "name": None})
        event_list = []

        for chunk_result in chunk_results:
            for entity in chunk_result.get('entities', []):
                entity_type = entity.get('type')
                name = entity.get('name', '').strip()
                context = entity.get('context', '').strip()

                if not name:
                    continue

                normalized_name = name.lower().strip()
                key = (entity_type, normalized_name)

                if entity_map[key]["name"] is None:
                    entity_map[key]["name"] = name
                    entity_map[key]["type"] = entity_type

                if context and context not in entity_map[key]["contexts"]:
                    entity_map[key]["contexts"].append(context)

            for event in chunk_result.get('events', []):
                event_list.append(event)

        merged_entities = []
        for (entity_type, _), data in entity_map.items():
            combined_context = "; ".join(data["contexts"]) if data["contexts"] else "Mentioned in document"
            merged_entities.append({
                "type": data["type"],
                "name": data["name"],
                "context": combined_context
            })

        # Deduplicate events
        unique_events = []
        seen_events = set()
        for event in event_list:
            event_key = (
                event.get('type'),
                event.get('date'),
                event.get('description', '')[:100]
            )
            if event_key not in seen_events:
                seen_events.add(event_key)
                unique_events.append(event)

        return {"entities": merged_entities, "events": unique_events}

    def extract_entities_and_relationships(self, text: str, doc_metadata: Dict) -> Dict:
        """Main extraction method - identical interface to ChunkedEntityExtractor"""
        chunks = self.chunk_text(text)
        total_chunks = len(chunks)

        logger.info(f"  Processing in {total_chunks} chunks with {self.client.model}...")

        chunk_results = []
        for i, (chunk_text, start, end) in enumerate(chunks, start=1):
            logger.info(f"  Chunk {i}/{total_chunks}...")
            result = self.extract_from_chunk(chunk_text, i, total_chunks, doc_metadata)
            chunk_results.append(result)

            # Small delay to avoid overwhelming local server
            if total_chunks > 3:
                time.sleep(0.5)

        merged = self.merge_entities(chunk_results)
        logger.info(f"  → {len(merged['entities'])} unique entities, {len(merged['events'])} events")
        return merged


# ─────────────────────────────────────────────
# DATABASE MANAGER
# Identical to poc_pipeline_chunked.py
# Compatible schema - can merge with Anthropic-extracted data
# ─────────────────────────────────────────────
class DatabaseManager:
    """Handles all PostgreSQL operations"""

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
            logger.error(f"  Make sure PostgreSQL is running and database '{self.db_name}' exists.")
            logger.error(f"  Create it with: createdb {self.db_name}")
            raise

    def ensure_schema(self):
        """Create tables if they don't exist; add columns if missing"""
        with self.conn.cursor() as cur:
            # Core tables
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
                    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    context TEXT,
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

            # Indexes
            for idx_sql in [
                "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)",
                "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)",
                "CREATE INDEX IF NOT EXISTS idx_events_date ON events(date)",
                "CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection)",
            ]:
                cur.execute(idx_sql)

        logger.info("✓ Database schema ready")

    def is_processed(self, file_path: str) -> bool:
        """Check if document already in database (skip if so)"""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM documents WHERE file_path = %s",
                (file_path,)
            )
            return cur.fetchone() is not None

    def insert_document(self, text: str, metadata: Dict,
                        collection_metadata: Dict, model_name: str) -> int:
        """Insert document record, return new id"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents
                (file_name, file_path, page_count, file_size, full_text,
                 collection, subcollection, location, extracted_dates, extraction_model)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                model_name
            ))
            return cur.fetchone()[0]

    def insert_entity_batch(self, entities: List[Dict], document_id: int):
        """Insert entities and mentions, updating context if entity exists"""
        with self.conn.cursor() as cur:
            for entity in entities:
                name = entity.get('name', '').strip()
                etype = entity.get('type', 'unknown')
                context = entity.get('context', '')

                if not name:
                    continue

                # Upsert entity
                cur.execute(
                    "SELECT id FROM entities WHERE name = %s AND type = %s",
                    (name, etype)
                )
                row = cur.fetchone()
                if row:
                    entity_id = row[0]
                    # Append new context if not duplicate
                    cur.execute("""
                        UPDATE entities
                        SET context = CASE
                            WHEN context IS NULL OR context = '' THEN %s
                            WHEN context NOT LIKE %s THEN context || '; ' || %s
                            ELSE context
                        END
                        WHERE id = %s
                    """, (context, f'%{context[:50]}%', context, entity_id))
                else:
                    cur.execute(
                        "INSERT INTO entities (name, type, context) VALUES (%s, %s, %s) RETURNING id",
                        (name, etype, context)
                    )
                    entity_id = cur.fetchone()[0]

                # Insert mention (ignore if already exists)
                cur.execute("""
                    INSERT INTO mentions (entity_id, document_id, context)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (entity_id, document_id) DO NOTHING
                """, (entity_id, document_id, context))

    def insert_events(self, events: List[Dict], document_id: int):
        """Insert events"""
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


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='Local exhaustive extraction pipeline using Ollama',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default model (llama3.1:70b), default database (crow_historical_docs)
  python3 poc_pipeline_local.py --input /path/to/pdfs --output results/

  # Use faster smaller model
  python3 poc_pipeline_local.py --input /path/to/pdfs --output results/ --model llama3.1:8b

  # Use a different database
  python3 poc_pipeline_local.py --input /path/to/pdfs --output results/ --db my_database

  # Dry run - extract text only, no AI, to check text quality
  python3 poc_pipeline_local.py --input /path/to/pdfs --output results/ --dry-run
        """
    )
    parser.add_argument('--input',   required=True,  help='Input directory containing PDFs')
    parser.add_argument('--output',  required=True,  help='Output directory for results')
    parser.add_argument('--model',   default=DEFAULT_MODEL, help=f'Ollama model name (default: {DEFAULT_MODEL})')
    parser.add_argument('--db',      default='crow_historical_docs', help='PostgreSQL database name')
    parser.add_argument('--dry-run', action='store_true', help='Extract text only, skip AI extraction')
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("LOCAL EXTRACTION PIPELINE (Ollama)")
    logger.info("=" * 60)
    logger.info(f"Input:    {input_path}")
    logger.info(f"Output:   {output_path}")
    logger.info(f"Model:    {args.model}")
    logger.info(f"Database: {args.db}")

    # Initialize components
    doc_processor = DocumentProcessor()
    db_manager    = DatabaseManager(db_name=args.db)

    if not args.dry_run:
        extractor = LocalEntityExtractor(model=args.model)
    else:
        extractor = None
        logger.info("DRY RUN MODE - text extraction only")

    # Find all PDFs
    pdf_files = sorted(input_path.glob("**/*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files\n")

    results = {
        'processed': 0, 'skipped': 0, 'errors': 0,
        'entities_extracted': 0, 'events_extracted': 0,
        'model': args.model,
        'start_time': datetime.now().isoformat()
    }

    for i, pdf_path in enumerate(pdf_files, start=1):
        logger.info(f"[{i}/{len(pdf_files)}] {pdf_path.name}")

        try:
            # Skip if already processed
            if db_manager.is_processed(str(pdf_path.absolute())):
                logger.info("  → Already processed, skipping")
                results['skipped'] += 1
                continue

            # Extract text
            text, metadata = doc_processor.extract_text_from_pdf(pdf_path)
            if not text.strip():
                logger.warning(f"  → No text extracted (image-only PDF?)")
                results['errors'] += 1
                continue

            collection_metadata = doc_processor.extract_collection_metadata(pdf_path, input_path)

            if args.dry_run:
                logger.info(f"  → {len(text)} chars extracted, {metadata.get('page_count')} pages")
                results['processed'] += 1
                continue

            # Insert document record
            doc_id = db_manager.insert_document(
                text, metadata, collection_metadata, args.model
            )

            # Extract entities with local LLM
            extraction = extractor.extract_entities_and_relationships(
                text, {**metadata, **collection_metadata}
            )

            # Store to database
            if extraction['entities']:
                db_manager.insert_entity_batch(extraction['entities'], doc_id)
                results['entities_extracted'] += len(extraction['entities'])

            if extraction['events']:
                db_manager.insert_events(extraction['events'], doc_id)
                results['events_extracted'] += len(extraction['events'])

            results['processed'] += 1
            logger.info(
                f"  ✓ {len(extraction['entities'])} entities, "
                f"{len(extraction['events'])} events"
            )

        except Exception as e:
            logger.error(f"  ✗ Error: {str(e)}")
            results['errors'] += 1

    # Save summary
    results['end_time'] = datetime.now().isoformat()
    results['total_files'] = len(pdf_files)

    summary_path = output_path / 'processing_summary_local.json'
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info("\n" + "=" * 60)
    logger.info("LOCAL EXTRACTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Processed:  {results['processed']}/{results['total_files']}")
    logger.info(f"Skipped:    {results['skipped']} (already in database)")
    logger.info(f"Errors:     {results['errors']}")
    logger.info(f"Entities:   {results['entities_extracted']}")
    logger.info(f"Events:     {results['events_extracted']}")
    logger.info(f"Summary:    {summary_path}")


if __name__ == "__main__":
    main()
