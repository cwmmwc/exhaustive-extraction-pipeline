-- Exhaustive Entity Extraction Pipeline
-- Database Schema
-- Compatible with PostgreSQL 12+

-- Core document storage
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
    extraction_model TEXT,          -- tracks which model extracted (claude/llama etc)
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_file_name   ON documents(file_name);
CREATE INDEX IF NOT EXISTS idx_documents_collection  ON documents(collection);
CREATE INDEX IF NOT EXISTS idx_documents_processed   ON documents(processed_date);

-- Full-text search index (enables fast keyword search across all document text)
CREATE INDEX IF NOT EXISTS idx_documents_fulltext ON documents
    USING gin(to_tsvector('english', coalesce(full_text, '')));

-- Named entities (people, organizations, locations, land parcels)
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,     -- person | organization | location | land_parcel
    context TEXT,           -- accumulated context from all mentions
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_name_type ON entities(name, type);

-- Junction table: which entities appear in which documents
CREATE TABLE IF NOT EXISTS mentions (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    context TEXT,           -- specific context for this mention
    UNIQUE(entity_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_mentions_entity   ON mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_mentions_document ON mentions(document_id);

-- Historical events (land transactions, hearings, patents, foreclosures)
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    type TEXT,              -- patent | foreclosure | tax_sale | allotment | hearing | complaint | mortgage | land_sale
    date TEXT,              -- stored as text to handle partial dates (YYYY, YYYY-MM, YYYY-MM-DD)
    location TEXT,
    description TEXT,
    metadata JSONB          -- flexible storage for entities_involved, amounts, etc.
);

CREATE INDEX IF NOT EXISTS idx_events_type     ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_date     ON events(date);
CREATE INDEX IF NOT EXISTS idx_events_document ON events(document_id);

-- Optional: Congressional/spreadsheet records table
-- Used for structured data integrated from Excel/CSV sources
CREATE TABLE IF NOT EXISTS congressional_records (
    id SERIAL PRIMARY KEY,
    last_name TEXT,
    first_name TEXT,
    full_name TEXT,
    record_date DATE,
    location TEXT,
    acres NUMERIC,
    description TEXT,
    pages_in_document INTEGER,
    allotment_number TEXT,
    document_type TEXT,
    entity_id INTEGER REFERENCES entities(id),  -- linked to entities table
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_congressional_name ON congressional_records(full_name);
CREATE INDEX IF NOT EXISTS idx_congressional_date ON congressional_records(record_date);
