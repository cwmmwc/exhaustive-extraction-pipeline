-- Exhaustive Entity Extraction Pipeline - v3 Schema
-- Database Schema
-- Compatible with PostgreSQL 12+
--
-- v3 additions: fee_patents, correspondence, legislation lifecycle fields

-- Core document storage
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
    pipeline_version TEXT DEFAULT 'v2',
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_file_name   ON documents(file_name);
CREATE INDEX IF NOT EXISTS idx_documents_collection  ON documents(collection);
CREATE INDEX IF NOT EXISTS idx_documents_processed   ON documents(processed_date);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_documents_fulltext ON documents
    USING gin(to_tsvector('english', coalesce(full_text, '')));

-- Named entities (10 types in v2, same in v3)
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

-- ============================================================
-- v3 ADDITIONS
-- ============================================================

-- Fee patents: the atomic unit of land dispossession
-- Links allottee, allotment, patent, and chain of subsequent conveyances
CREATE TABLE IF NOT EXISTS fee_patents (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    allottee TEXT NOT NULL,
    allotment_number TEXT,
    acreage TEXT,
    land_description TEXT,           -- legal description (section/township/range)
    patent_date TEXT,
    patent_number TEXT,
    trust_to_fee_mechanism TEXT,     -- e.g. "private bill S. 1385", "administrative", "Public Law 49"
    subsequent_buyer TEXT,
    sale_price TEXT,
    sale_date TEXT,
    attorney TEXT,                   -- attorney who facilitated the transaction
    mortgage_amount TEXT,
    mortgage_holder TEXT,
    context TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fee_patents_document   ON fee_patents(document_id);
CREATE INDEX IF NOT EXISTS idx_fee_patents_allottee   ON fee_patents(allottee);
CREATE INDEX IF NOT EXISTS idx_fee_patents_allotment  ON fee_patents(allotment_number);
CREATE INDEX IF NOT EXISTS idx_fee_patents_buyer      ON fee_patents(subsequent_buyer);
CREATE INDEX IF NOT EXISTS idx_fee_patents_attorney   ON fee_patents(attorney);
CREATE INDEX IF NOT EXISTS idx_fee_patents_date       ON fee_patents(patent_date);

-- Correspondence: sender/recipient/date/subject for bureaucratic network reconstruction
-- Designed to link with Pipeline B (BIA index cards) via sender/recipient/date
CREATE TABLE IF NOT EXISTS correspondence (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    sender TEXT NOT NULL,
    sender_title TEXT,               -- e.g. "Superintendent, Crow Agency"
    recipient TEXT NOT NULL,
    recipient_title TEXT,            -- e.g. "Commissioner of Indian Affairs"
    date TEXT,
    subject TEXT,
    action_requested TEXT,           -- what the sender asked for
    outcome TEXT,                    -- what happened as a result
    context TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_correspondence_document  ON correspondence(document_id);
CREATE INDEX IF NOT EXISTS idx_correspondence_sender    ON correspondence(sender);
CREATE INDEX IF NOT EXISTS idx_correspondence_recipient ON correspondence(recipient);
CREATE INDEX IF NOT EXISTS idx_correspondence_date      ON correspondence(date);

-- Legislative actions: bill lifecycle tracking
-- Extends the legislation entity type with structured action data
CREATE TABLE IF NOT EXISTS legislative_actions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    bill_number TEXT NOT NULL,       -- e.g. "S. 1385", "H.R. 5477"
    bill_title TEXT,                 -- e.g. "Crow Act of 1920"
    sponsor TEXT,
    co_sponsors TEXT,                -- comma-separated
    action_type TEXT NOT NULL,       -- introduced|reported|amended|passed_senate|passed_house|vetoed|enacted|signed
    action_date TEXT,
    vote_count TEXT,                 -- e.g. "169-100", "306-5", "unanimous"
    committee TEXT,                  -- e.g. "Senate Interior Committee"
    outcome TEXT,                    -- e.g. "enacted as Private Law 68"
    context TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_legislative_document    ON legislative_actions(document_id);
CREATE INDEX IF NOT EXISTS idx_legislative_bill        ON legislative_actions(bill_number);
CREATE INDEX IF NOT EXISTS idx_legislative_sponsor     ON legislative_actions(sponsor);
CREATE INDEX IF NOT EXISTS idx_legislative_action_type ON legislative_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_legislative_date        ON legislative_actions(action_date);

-- v3 schema upgrade helper (run on existing v2 databases)
-- ALTER TABLE documents ADD COLUMN IF NOT EXISTS pipeline_version TEXT DEFAULT 'v2';
-- Then update pipeline_version to 'v3' for newly processed documents.
