-- Exhaustive Entity Extraction Pipeline - v2 Schema
-- Database Schema
-- Compatible with PostgreSQL 12+

-- Core document storage
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    display_title TEXT,
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
);

CREATE INDEX IF NOT EXISTS idx_documents_file_name   ON documents(file_name);
CREATE INDEX IF NOT EXISTS idx_documents_collection  ON documents(collection);
CREATE INDEX IF NOT EXISTS idx_documents_processed   ON documents(processed_date);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_documents_fulltext ON documents
    USING gin(to_tsvector('english', coalesce(full_text, '')));

-- Named entities (10 types in v2)
-- Types: person, organization, location, land_parcel,
--        legal_case, legislation, acreage_holding,
--        financial_transaction, relationship, date_event
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    context TEXT,
    acres TEXT,
    land_type TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_name_type ON entities(name, type);
CREATE INDEX IF NOT EXISTS idx_entities_acres ON entities(acres);

-- Junction table: which entities appear in which documents
CREATE TABLE IF NOT EXISTS mentions (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    context TEXT,
    UNIQUE(entity_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_mentions_entity   ON mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_mentions_document ON mentions(document_id);

-- Historical events
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    type TEXT,
    date TEXT,
    location TEXT,
    description TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_events_type     ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_date     ON events(date);
CREATE INDEX IF NOT EXISTS idx_events_document ON events(document_id);

-- Financial transactions (new in v2)
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
);

CREATE INDEX IF NOT EXISTS idx_financial_document ON financial_transactions(document_id);
CREATE INDEX IF NOT EXISTS idx_financial_payer    ON financial_transactions(payer);
CREATE INDEX IF NOT EXISTS idx_financial_payee    ON financial_transactions(payee);
CREATE INDEX IF NOT EXISTS idx_financial_type     ON financial_transactions(type);

-- Relationships (new in v2)
CREATE TABLE IF NOT EXISTS relationships (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    type TEXT,
    subject TEXT,
    object TEXT,
    context TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_relationships_document ON relationships(document_id);
CREATE INDEX IF NOT EXISTS idx_relationships_subject  ON relationships(subject);
CREATE INDEX IF NOT EXISTS idx_relationships_type     ON relationships(type);
