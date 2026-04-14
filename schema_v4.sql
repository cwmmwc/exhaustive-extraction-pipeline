-- Exhaustive Entity Extraction Pipeline - v4 Schema
-- Extends v3 with: testimony, taxes, mortgages
-- Compatible with PostgreSQL 12+
--
-- v3: entities, events, financial_transactions, relationships,
--     fee_patents, correspondence, legislative_actions
-- v4 additions: testimony, taxes, mortgages

-- ============================================================
-- v3 TABLES (unchanged)
-- ============================================================

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
    pipeline_version TEXT DEFAULT 'v4',
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_file_name   ON documents(file_name);
CREATE INDEX IF NOT EXISTS idx_documents_collection  ON documents(collection);
CREATE INDEX IF NOT EXISTS idx_documents_processed   ON documents(processed_date);

CREATE INDEX IF NOT EXISTS idx_documents_fulltext ON documents
    USING gin(to_tsvector('english', coalesce(full_text, '')));

-- Named entities
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

-- Junction table: entities <-> documents
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

-- Financial transactions
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

-- Relationships
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

-- Fee patents
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
);

CREATE INDEX IF NOT EXISTS idx_fee_patents_document   ON fee_patents(document_id);
CREATE INDEX IF NOT EXISTS idx_fee_patents_allottee   ON fee_patents(allottee);
CREATE INDEX IF NOT EXISTS idx_fee_patents_allotment  ON fee_patents(allotment_number);
CREATE INDEX IF NOT EXISTS idx_fee_patents_buyer      ON fee_patents(subsequent_buyer);
CREATE INDEX IF NOT EXISTS idx_fee_patents_attorney   ON fee_patents(attorney);
CREATE INDEX IF NOT EXISTS idx_fee_patents_date       ON fee_patents(patent_date);

-- Correspondence
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
);

CREATE INDEX IF NOT EXISTS idx_correspondence_document  ON correspondence(document_id);
CREATE INDEX IF NOT EXISTS idx_correspondence_sender    ON correspondence(sender);
CREATE INDEX IF NOT EXISTS idx_correspondence_recipient ON correspondence(recipient);
CREATE INDEX IF NOT EXISTS idx_correspondence_date      ON correspondence(date);

-- Legislative actions
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
);

CREATE INDEX IF NOT EXISTS idx_legislative_document    ON legislative_actions(document_id);
CREATE INDEX IF NOT EXISTS idx_legislative_bill        ON legislative_actions(bill_number);
CREATE INDEX IF NOT EXISTS idx_legislative_sponsor     ON legislative_actions(sponsor);
CREATE INDEX IF NOT EXISTS idx_legislative_action_type ON legislative_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_legislative_date        ON legislative_actions(action_date);

-- ============================================================
-- v4 ADDITIONS
-- ============================================================

-- Testimony: sworn statements from congressional hearings
-- Captures who testified, where, when, and what they claimed
CREATE TABLE IF NOT EXISTS testimony (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    witness TEXT NOT NULL,
    witness_title TEXT,
    hearing TEXT,
    committee TEXT,
    location TEXT,
    date TEXT,
    subject TEXT,
    key_claims TEXT,
    questioner TEXT,
    context TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_testimony_document  ON testimony(document_id);
CREATE INDEX IF NOT EXISTS idx_testimony_witness   ON testimony(witness);
CREATE INDEX IF NOT EXISTS idx_testimony_committee ON testimony(committee);
CREATE INDEX IF NOT EXISTS idx_testimony_date      ON testimony(date);
CREATE INDEX IF NOT EXISTS idx_testimony_location  ON testimony(location);

-- Taxes: property taxes, delinquencies, and tax sales as a dispossession mechanism
CREATE TABLE IF NOT EXISTS taxes (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    taxpayer TEXT,
    land_description TEXT,
    tax_type TEXT,
    amount TEXT,
    year TEXT,
    status TEXT,
    county TEXT,
    context TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_taxes_document  ON taxes(document_id);
CREATE INDEX IF NOT EXISTS idx_taxes_taxpayer  ON taxes(taxpayer);
CREATE INDEX IF NOT EXISTS idx_taxes_status    ON taxes(status);
CREATE INDEX IF NOT EXISTS idx_taxes_county    ON taxes(county);
CREATE INDEX IF NOT EXISTS idx_taxes_year      ON taxes(year);

-- Mortgages: land mortgages as a dispossession mechanism
CREATE TABLE IF NOT EXISTS mortgages (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    borrower TEXT,
    lender TEXT,
    amount TEXT,
    land_description TEXT,
    acreage TEXT,
    date TEXT,
    interest_rate TEXT,
    status TEXT,
    context TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mortgages_document ON mortgages(document_id);
CREATE INDEX IF NOT EXISTS idx_mortgages_borrower ON mortgages(borrower);
CREATE INDEX IF NOT EXISTS idx_mortgages_lender   ON mortgages(lender);
CREATE INDEX IF NOT EXISTS idx_mortgages_status   ON mortgages(status);
CREATE INDEX IF NOT EXISTS idx_mortgages_date     ON mortgages(date);

-- Document tables: structured tabular data extracted via vision mode
-- Stores tables from scanned documents (land transaction schedules, financial ledgers, etc.)
CREATE TABLE IF NOT EXISTS document_tables (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    title TEXT,
    columns JSONB,  -- array of column names
    row_data JSONB, -- array of row objects
    row_count INTEGER,
    source_pages TEXT, -- e.g., "64-70"
    context TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_doc_tables_document ON document_tables(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_tables_title    ON document_tables(title);

-- Individual table rows flattened for querying
-- Each row from each table gets its own record for SQL-friendly access
CREATE TABLE IF NOT EXISTS table_rows (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    table_id INTEGER REFERENCES document_tables(id) ON DELETE CASCADE,
    table_title TEXT,
    row_data JSONB,  -- the full row as key-value pairs
    -- Common columns extracted for direct querying:
    area_or_tribe TEXT,
    acreage TEXT,
    cost TEXT,
    date TEXT,
    project_or_purpose TEXT,
    citation TEXT,
    remarks TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_table_rows_document ON table_rows(document_id);
CREATE INDEX IF NOT EXISTS idx_table_rows_table    ON table_rows(table_id);
CREATE INDEX IF NOT EXISTS idx_table_rows_tribe    ON table_rows(area_or_tribe);
CREATE INDEX IF NOT EXISTS idx_table_rows_data     ON table_rows USING gin(row_data);

-- ============================================================
-- INDEX CARD TABLES (DOJ Record Slips, NARA RG 60)
-- ============================================================

-- Record slips: one row per index card
-- Each card documents a piece of correspondence about a legal case
CREATE TABLE IF NOT EXISTS record_slips (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    file_number TEXT NOT NULL,        -- DOJ file number (e.g., 90-2-5-49)
    jurisdiction TEXT,                 -- District/state (e.g., Montana, N. Oklahoma)
    date TEXT,                         -- Date of correspondence (YYYY-MM-DD)
    correspondent TEXT,                -- Who the letter is to/from
    correspondent_role TEXT,           -- outgoing/incoming
    case_name TEXT,                    -- Legal case (e.g., U.S. v. Bennett County, et al)
    case_number TEXT,                  -- Court case number if given
    named_individual TEXT,             -- Person referenced (allottee, attorney, official, etc.)
    allottee_number TEXT,              -- Allotment number if given
    tribe_or_reservation TEXT,         -- Tribe or reservation referenced
    subject TEXT,                      -- Description of the action/content
    action_type TEXT,                  -- filing|acknowledgment|enclosure|request|ruling|settlement|appeal|other
    enclosures TEXT,                   -- What was enclosed
    routing_division TEXT,             -- Division that processed (e.g., Lands)
    routing_date TEXT,                 -- Date routed
    clerk_initials TEXT,               -- Processing clerk initials
    processed_date TEXT,               -- Date processed
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_record_slips_document    ON record_slips(document_id);
CREATE INDEX IF NOT EXISTS idx_record_slips_file_number ON record_slips(file_number);
CREATE INDEX IF NOT EXISTS idx_record_slips_case_name   ON record_slips(case_name);
CREATE INDEX IF NOT EXISTS idx_record_slips_individual  ON record_slips(named_individual);
CREATE INDEX IF NOT EXISTS idx_record_slips_tribe       ON record_slips(tribe_or_reservation);
CREATE INDEX IF NOT EXISTS idx_record_slips_date        ON record_slips(date);
CREATE INDEX IF NOT EXISTS idx_record_slips_jurisdiction ON record_slips(jurisdiction);

-- Legal cases: one row per unique case referenced in the cards
-- File number is the unique identifier; case names vary and need dedup
CREATE TABLE IF NOT EXISTS legal_cases (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    case_name TEXT NOT NULL,           -- Canonical case name
    file_number TEXT,                  -- DOJ file number (unique per case)
    jurisdiction TEXT,                 -- District/state
    case_type TEXT,                    -- tax_recovery|quiet_title|allotment|termination|other
    named_individual TEXT,             -- Primary person referenced
    allottee_number TEXT,
    tribe_or_reservation TEXT,
    county TEXT,                       -- County defendant (for tax cases)
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_legal_cases_document    ON legal_cases(document_id);
CREATE INDEX IF NOT EXISTS idx_legal_cases_file_number ON legal_cases(file_number);
CREATE INDEX IF NOT EXISTS idx_legal_cases_case_name   ON legal_cases(case_name);
CREATE INDEX IF NOT EXISTS idx_legal_cases_individual  ON legal_cases(named_individual);
CREATE INDEX IF NOT EXISTS idx_legal_cases_tribe       ON legal_cases(tribe_or_reservation);
CREATE INDEX IF NOT EXISTS idx_legal_cases_county      ON legal_cases(county);

-- v4 schema upgrade helper (run on existing v3 databases to add new tables)
-- Just run this entire file — CREATE TABLE IF NOT EXISTS is safe on existing tables.
