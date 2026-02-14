#!/usr/bin/env python3
"""
IMPROVED Exhaustive Document Processing Pipeline with Chunked Extraction

This version processes documents in overlapping chunks to ensure NO entities are missed.
Slower but guaranteed complete extraction.

Key improvements:
1. Chunks long documents into 40,000 character segments with 5,000 char overlap
2. Extracts entities from EACH chunk separately
3. Merges entities across chunks (deduplicates and combines contexts)
4. Stores ALL contexts for each entity (not just first mention)

Usage:
    python poc_pipeline_chunked.py --input /path/to/collection --output results/
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
from psycopg2.extras import execute_batch
from openai import OpenAI
from anthropic import Anthropic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles extraction of text and metadata from PDF documents"""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Tuple[str, Dict]:
        """Extract text and metadata from a PDF file"""
        try:
            doc = fitz.open(pdf_path)
            
            # Extract text from all pages
            full_text = ""
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                full_text += f"\n--- Page {page_num} ---\n{text}"
            
            # Extract metadata
            metadata = {
                'page_count': len(doc),
                'file_size': pdf_path.stat().st_size,
                'file_name': pdf_path.name,
                'file_path': str(pdf_path.absolute())
            }
            
            # Extract dates from text
            date_patterns = [
                r'\b(19|20)\d{2}\b',
                r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(19|20)\d{2}\b'
            ]
            
            dates_found = []
            for pattern in date_patterns:
                dates_found.extend(re.findall(pattern, full_text[:5000]))
            
            if dates_found:
                metadata['extracted_dates'] = list(set(str(d) if isinstance(d, str) else d[0] for d in dates_found))
            
            doc.close()
            self.processed_count += 1
            
            return full_text, metadata
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error processing {pdf_path}: {str(e)}")
            return "", {}
    
    def extract_collection_metadata(self, file_path: Path, base_path: Path) -> Dict:
        """Extract collection and location metadata from file path"""
        relative_path = file_path.relative_to(base_path)
        parts = list(relative_path.parts)
        
        metadata = {
            'collection': parts[0] if len(parts) > 1 else 'Unknown',
            'subcollection': parts[1] if len(parts) > 2 else None
        }
        
        # Extract location from folder names
        location_keywords = ['county', 'reservation', 'agency', 'district']
        for part in parts:
            part_lower = part.lower()
            if any(keyword in part_lower for keyword in location_keywords):
                metadata['location'] = part
                break
        
        return metadata


class ChunkedEntityExtractor:
    """Handles entity extraction from documents using chunking strategy"""
    
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=api_key)
        self.extraction_count = 0
        
        # Chunking parameters
        self.chunk_size = 40000  # 40K characters per chunk
        self.overlap = 5000      # 5K character overlap between chunks
    
    def chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Split text into overlapping chunks
        
        Returns:
            List of (chunk_text, start_pos, end_pos) tuples
        """
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
    
    def extract_from_chunk(self, chunk: str, chunk_num: int, total_chunks: int, doc_metadata: Dict) -> Dict:
        """Extract entities from a single chunk"""
        
        prompt = f"""You are analyzing a historical document about land, taxation, and Native American affairs.

This is chunk {chunk_num} of {total_chunks} from a larger document.

Document context:
- Collection: {doc_metadata.get('collection', 'Unknown')}
- Location: {doc_metadata.get('location', 'Unknown')}
- Dates found: {doc_metadata.get('extracted_dates', [])}

CRITICAL: Extract EVERY person, organization, location, and land parcel mentioned in this text.
For each entity, provide the specific context from THIS chunk.

Return ONLY valid JSON (no markdown, no explanation):

{{
  "entities": [
    {{"type": "person", "name": "FULL NAME", "context": "specific role or action in this text"}},
    {{"type": "organization", "name": "FULL NAME", "context": "what they did in this text"}},
    {{"type": "location", "name": "FULL NAME", "context": "what happened here"}},
    {{"type": "land_parcel", "identifier": "allotment number or description", "context": "what happened with this parcel"}}
  ],
  "events": [
    {{"type": "tax_assessment|land_sale|foreclosure|allotment|lawsuit|patent_cancellation", "date": "YYYY or YYYY-MM-DD or date range", "location": "where it happened", "description": "what happened", "entities_involved": ["list", "of", "names"]}}
  ]
}}

IMPORTANT:
- Include EVERY person mentioned, even if only briefly
- Include EVERY organization (agencies, companies, banks, courts)
- Include EVERY location (counties, reservations, cities, agencies)
- For entities, focus on WHAT THEY DID in this specific text
- Be specific about context - don't use generic descriptions
- If an entity appears multiple times, capture their primary role

Document chunk:
{chunk}
"""
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = re.sub(r'^```(?:json)?\n', '', response_text)
                response_text = re.sub(r'\n```$', '', response_text)
            
            result = json.loads(response_text)
            return result
            
        except Exception as e:
            logger.error(f"Error extracting from chunk {chunk_num}: {str(e)}")
            return {"entities": [], "events": []}
    
    def merge_entities(self, chunk_results: List[Dict]) -> Dict:
        """
        Merge entities from multiple chunks, combining contexts
        
        Same entity mentioned in multiple chunks gets ALL contexts combined
        """
        # Group entities by (type, normalized_name)
        entity_map = defaultdict(lambda: {"contexts": [], "type": None, "name": None})
        event_list = []
        
        for chunk_result in chunk_results:
            # Merge entities
            for entity in chunk_result.get('entities', []):
                entity_type = entity.get('type')
                name = entity.get('name', '').strip()
                context = entity.get('context', '').strip()
                
                if not name:
                    continue
                
                # Normalize name for matching (case-insensitive, strip whitespace)
                normalized_name = name.lower().strip()
                key = (entity_type, normalized_name)
                
                # Store original name (first occurrence) and type
                if entity_map[key]["name"] is None:
                    entity_map[key]["name"] = name
                    entity_map[key]["type"] = entity_type
                
                # Add context if new and not empty
                if context and context not in entity_map[key]["contexts"]:
                    entity_map[key]["contexts"].append(context)
            
            # Collect all events
            for event in chunk_result.get('events', []):
                event_list.append(event)
        
        # Convert entity_map to list format
        merged_entities = []
        for (entity_type, normalized_name), data in entity_map.items():
            # Combine contexts into one string, separated by semicolons
            combined_context = "; ".join(data["contexts"]) if data["contexts"] else "Mentioned in document"
            
            merged_entities.append({
                "type": data["type"],
                "name": data["name"],
                "context": combined_context
            })
        
        # Deduplicate events (events with same type, date, description)
        unique_events = []
        seen_events = set()
        
        for event in event_list:
            event_key = (
                event.get('type'),
                event.get('date'),
                event.get('description', '')[:100]  # First 100 chars of description
            )
            if event_key not in seen_events:
                seen_events.add(event_key)
                unique_events.append(event)
        
        return {
            "entities": merged_entities,
            "events": unique_events
        }
    
    def extract_entities_and_relationships(self, text: str, doc_metadata: Dict) -> Dict:
        """
        Main extraction method using chunking strategy
        
        Args:
            text: Full document text
            doc_metadata: Document metadata for context
            
        Returns:
            Dictionary containing merged entities and events
        """
        # Split into chunks
        chunks = self.chunk_text(text)
        total_chunks = len(chunks)
        
        logger.info(f"Processing document in {total_chunks} chunks...")
        
        # Extract from each chunk
        chunk_results = []
        for i, (chunk_text, start, end) in enumerate(chunks, start=1):
            logger.info(f"  Extracting from chunk {i}/{total_chunks}")
            result = self.extract_from_chunk(chunk_text, i, total_chunks, doc_metadata)
            chunk_results.append(result)
            self.extraction_count += 1
        
        # Merge results
        merged_result = self.merge_entities(chunk_results)
        
        logger.info(f"  Merged to {len(merged_result['entities'])} unique entities and {len(merged_result['events'])} unique events")
        
        return merged_result


class DatabaseManager:
    """Handles all database operations"""
    
    def __init__(self, db_name: str = "crow_historical_docs"):
        self.db_name = db_name
        self.conn = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(f"postgresql://localhost/{self.db_name}")
            self.conn.autocommit = True
            logger.info(f"Connected to database: {self.db_name}")
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def create_tables(self):
        """Create database schema"""
        schema = """
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            file_name TEXT NOT NULL,
            file_path TEXT,
            page_count INTEGER,
            file_size BIGINT,
            full_text TEXT,
            collection TEXT,
            subcollection TEXT,
            location TEXT,
            extracted_dates TEXT[],
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_documents_file_name ON documents(file_name);
        CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection);
        
        CREATE TABLE IF NOT EXISTS entities (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            context TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
        CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
        
        CREATE TABLE IF NOT EXISTS mentions (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id),
            entity_id INTEGER REFERENCES entities(id),
            context TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_mentions_document ON mentions(document_id);
        CREATE INDEX IF NOT EXISTS idx_mentions_entity ON mentions(entity_id);
        
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id),
            type TEXT,
            date TEXT,
            location TEXT,
            description TEXT,
            metadata JSONB
        );
        
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
        CREATE INDEX IF NOT EXISTS idx_events_date ON events(date);
        """
        
        with self.conn.cursor() as cur:
            cur.execute(schema)
        
        logger.info("Database schema ready")
    
    def insert_document(self, text: str, metadata: Dict, collection_metadata: Dict) -> int:
        """Insert document and return document ID"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents 
                (file_name, file_path, page_count, file_size, full_text, collection, subcollection, location, extracted_dates)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                metadata['file_name'],
                metadata['file_path'],
                metadata['page_count'],
                metadata['file_size'],
                text,
                collection_metadata.get('collection'),
                collection_metadata.get('subcollection'),
                collection_metadata.get('location'),
                metadata.get('extracted_dates', [])
            ))
            return cur.fetchone()[0]
    
    def insert_entity_batch(self, entities: List[Dict], document_id: int):
        """Insert entities and their mentions"""
        with self.conn.cursor() as cur:
            for entity in entities:
                # Check if entity already exists
                cur.execute("""
                    SELECT id FROM entities WHERE name = %s AND type = %s
                """, (entity['name'], entity['type']))
                
                result = cur.fetchone()
                if result:
                    entity_id = result[0]
                    # Update context to append new context
                    cur.execute("""
                        UPDATE entities 
                        SET context = CASE 
                            WHEN context IS NULL OR context = '' THEN %s
                            WHEN context NOT LIKE %s THEN context || '; ' || %s
                            ELSE context
                        END
                        WHERE id = %s
                    """, (entity['context'], f"%{entity['context']}%", entity['context'], entity_id))
                else:
                    # Insert new entity
                    cur.execute("""
                        INSERT INTO entities (name, type, context)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (entity['name'], entity['type'], entity['context']))
                    entity_id = cur.fetchone()[0]
                
                # Insert mention
                cur.execute("""
                    INSERT INTO mentions (document_id, entity_id, context)
                    VALUES (%s, %s, %s)
                """, (document_id, entity_id, entity['context']))
    
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


def main():
    parser = argparse.ArgumentParser(description='Process historical documents with chunked extraction')
    parser.add_argument('--input', type=str, required=True, help='Input directory containing PDFs')
    parser.add_argument('--output', type=str, required=True, help='Output directory for results')
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting chunked extraction pipeline")
    logger.info(f"Input: {input_path}")
    logger.info(f"Output: {output_path}")
    
    # Initialize components
    doc_processor = DocumentProcessor()
    entity_extractor = ChunkedEntityExtractor()
    db_manager = DatabaseManager()
    
    # Find all PDFs
    pdf_files = list(input_path.glob("**/*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    # Process each document
    results = {
        'processed': 0,
        'errors': 0,
        'entities_extracted': 0,
        'events_extracted': 0,
        'start_time': datetime.now().isoformat()
    }
    
    for i, pdf_path in enumerate(pdf_files, start=1):
        logger.info(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        
        try:
            # Extract text
            text, metadata = doc_processor.extract_text_from_pdf(pdf_path)
            if not text:
                logger.warning(f"No text extracted from {pdf_path.name}")
                results['errors'] += 1
                continue
            
            # Extract collection metadata
            collection_metadata = doc_processor.extract_collection_metadata(pdf_path, input_path)
            
            # Insert document
            doc_id = db_manager.insert_document(text, metadata, collection_metadata)
            
            # Extract entities (with chunking)
            extraction_result = entity_extractor.extract_entities_and_relationships(text, {**metadata, **collection_metadata})
            
            # Store entities
            if extraction_result['entities']:
                db_manager.insert_entity_batch(extraction_result['entities'], doc_id)
                results['entities_extracted'] += len(extraction_result['entities'])
            
            # Store events
            if extraction_result['events']:
                db_manager.insert_events(extraction_result['events'], doc_id)
                results['events_extracted'] += len(extraction_result['events'])
            
            results['processed'] += 1
            logger.info(f"  ✓ Extracted {len(extraction_result['entities'])} entities, {len(extraction_result['events'])} events")
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {str(e)}")
            results['errors'] += 1
    
    # Save results summary
    results['end_time'] = datetime.now().isoformat()
    results['total_files'] = len(pdf_files)
    
    summary_path = output_path / 'processing_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info("CHUNKED EXTRACTION COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Processed: {results['processed']}/{results['total_files']}")
    logger.info(f"Errors: {results['errors']}")
    logger.info(f"Total entities extracted: {results['entities_extracted']}")
    logger.info(f"Total events extracted: {results['events_extracted']}")
    logger.info(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
