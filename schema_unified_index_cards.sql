-- Unified DOJ index cards schema (Sonnet + Qwen-VL merged)
--
-- Six tables, all keyed off file_number for cross-table joins:
--   documents      — one row per source PDF (87 expected)
--   slips          — one row per UNIQUE record slip after slip-level dedup
--                    across both extractions; extraction_source tags provenance
--   cases          — one row per unique file_number; aggregate columns expose
--                    Sonnet vs Qwen counts and the master-classification flag
--                    (cases_at_file_number > 1 = catch-all file like 90-2-01)
--   persons        — one row per unique normalized name across both extractions
--   slip_cases     — many-to-many join (a slip can mention multiple cases)
--   slip_persons   — many-to-many join (a slip can name multiple persons)
--
-- Idempotent: every CREATE uses IF NOT EXISTS, every DROP can be re-run.
-- Run with:  psql unified_index_cards -f schema_unified_index_cards.sql

BEGIN;

-- ─────────────────────────────────────────────────────────────────
-- documents
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    source_pdf      TEXT NOT NULL,           -- inner PDF basename, e.g. "09112024"
    pdf_path        TEXT,                    -- relative path under "RG 60 index cards/"
    subcollection   TEXT,                    -- "90-2-11" / "90-2-5" / "" for top-level
    num_pages       INTEGER,                 -- from the PDF itself
    sonnet_extracted BOOLEAN DEFAULT FALSE,  -- did Sonnet run on this PDF?
    qwen_extracted   BOOLEAN DEFAULT FALSE,  -- did Qwen-VL run on this PDF?
    sonnet_failed_pages INTEGER DEFAULT 0,
    qwen_failed_pages   INTEGER DEFAULT 0,
    UNIQUE (source_pdf, subcollection)
);

CREATE INDEX IF NOT EXISTS idx_documents_source_pdf ON documents (source_pdf);
CREATE INDEX IF NOT EXISTS idx_documents_subcollection ON documents (subcollection);

-- ─────────────────────────────────────────────────────────────────
-- slips
--   The atomic unit. After slip-level dedup, one row per physical card.
--   Sonnet's row wins when both extractions found the slip; Qwen's row
--   wins when only Qwen found it. extraction_source records which.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS slips (
    id                  SERIAL PRIMARY KEY,
    document_id         INTEGER REFERENCES documents(id) ON DELETE CASCADE,

    -- Core slip fields (present in both extraction schemas).
    -- file_number is nullable because some slips (especially older ones with
    -- bad OCR) genuinely lack a file_number in the source. NULL-file_number
    -- slips can't be linked to a case via slip_cases, but they're preserved
    -- in the slips table so the data isn't silently lost.
    file_number         TEXT,
    jurisdiction        TEXT,
    date                TEXT,                 -- slip dates are messy; keep as text
    correspondent       TEXT,
    case_name           TEXT,
    subject             TEXT,
    routing_division    TEXT,
    routing_date        TEXT,
    clerk_initials      TEXT,

    -- Sonnet-only fields (NULL when slip is qwen-only)
    correspondent_role  TEXT,
    case_number         TEXT,
    allottee_name       TEXT,
    allottee_number     TEXT,
    tribe_or_reservation TEXT,
    action_type         TEXT,
    enclosures          TEXT,
    processed_date      TEXT,

    -- Provenance
    source_page         TEXT,                 -- nullable; current extractions don't have it
    extraction_source   TEXT NOT NULL,        -- 'sonnet+qwen' | 'sonnet-only' | 'qwen-only'

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_slips_file_number    ON slips (file_number);
CREATE INDEX IF NOT EXISTS idx_slips_date           ON slips (date);
CREATE INDEX IF NOT EXISTS idx_slips_correspondent  ON slips (correspondent);
CREATE INDEX IF NOT EXISTS idx_slips_jurisdiction   ON slips (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_slips_extraction     ON slips (extraction_source);
CREATE INDEX IF NOT EXISTS idx_slips_document       ON slips (document_id);
CREATE INDEX IF NOT EXISTS idx_slips_named          ON slips (allottee_name);
CREATE INDEX IF NOT EXISTS idx_slips_tribe          ON slips (tribe_or_reservation);

-- Full-text search across the slip's text fields
ALTER TABLE slips
    ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(file_number, '')        || ' ' ||
            coalesce(jurisdiction, '')       || ' ' ||
            coalesce(correspondent, '')      || ' ' ||
            coalesce(correspondent_role, '') || ' ' ||
            coalesce(case_name, '')          || ' ' ||
            coalesce(case_number, '')        || ' ' ||
            coalesce(allottee_name, '')      || ' ' ||
            coalesce(tribe_or_reservation, '') || ' ' ||
            coalesce(subject, '')            || ' ' ||
            coalesce(action_type, '')        || ' ' ||
            coalesce(routing_division, '')
        )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_slips_search_vector
    ON slips USING GIN (search_vector);

-- ─────────────────────────────────────────────────────────────────
-- cases
--   One row per unique file_number. Aggregate columns expose both
--   extractions' counts so the user can spot:
--     - heavy-traffic cases (high sonnet_slip_count + qwen_slip_count)
--     - master classifications (cases_at_file_number > 1)
--     - how Qwen's per-mention enrichment compares to Sonnet's deduped view
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cases (
    file_number             TEXT PRIMARY KEY,
    canonical_case_name     TEXT,
    case_name_variants      TEXT[],          -- all variants seen across both extractions
    jurisdiction            TEXT,
    county                  TEXT,
    case_type               TEXT,
    named_individual        TEXT,
    tribe_or_reservation    TEXT,

    -- Per-extraction counts derived during the merge
    sonnet_slip_count           INTEGER DEFAULT 0,
    qwen_slip_count             INTEGER DEFAULT 0,
    sonnet_case_mention_count   INTEGER DEFAULT 0,  -- how many sonnet legal_case entries had this file_number
    qwen_case_mention_count     INTEGER DEFAULT 0,  -- how many qwen legal_case entries had this file_number (the audit-trail signal)

    -- Master-classification flag: how many distinct legal_case entries
    -- (across both extractions) share this file_number? When > 1, the
    -- file is a catch-all (e.g., 90-2-01 = 174 different bills).
    cases_at_file_number    INTEGER DEFAULT 1,

    -- Materialized count of distinct persons appearing in slips for this file_number
    distinct_persons_count  INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cases_jurisdiction ON cases (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_cases_county ON cases (county);
CREATE INDEX IF NOT EXISTS idx_cases_tribe ON cases (tribe_or_reservation);
CREATE INDEX IF NOT EXISTS idx_cases_master ON cases (cases_at_file_number) WHERE cases_at_file_number > 1;

ALTER TABLE cases
    ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(file_number, '')           || ' ' ||
            coalesce(canonical_case_name, '')   || ' ' ||
            coalesce(jurisdiction, '')          || ' ' ||
            coalesce(county, '')                || ' ' ||
            coalesce(case_type, '')             || ' ' ||
            coalesce(named_individual, '')      || ' ' ||
            coalesce(tribe_or_reservation, '')
        )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_cases_search_vector
    ON cases USING GIN (search_vector);

-- ─────────────────────────────────────────────────────────────────
-- persons
--   Deduped on a normalized name across both extractions. Each row
--   carries variants, roles, tribes, file_numbers as PG arrays so
--   "everything about Norman Littell" is one row away.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS persons (
    id                  SERIAL PRIMARY KEY,
    canonical_name      TEXT NOT NULL,
    normalized_name     TEXT NOT NULL UNIQUE,   -- lowercase, punctuation stripped, words sorted
    name_variants       TEXT[],                 -- all original spellings seen
    roles               TEXT[],                 -- distinct roles across slips
    tribes              TEXT[],                 -- distinct tribes/reservations across slips
    file_numbers        TEXT[],                 -- file_numbers this person is named in
    sources             TEXT[],                 -- {'sonnet'} | {'qwen'} | {'sonnet','qwen'}
    sonnet_mention_count INTEGER DEFAULT 0,
    qwen_mention_count   INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_persons_canonical ON persons (canonical_name);
CREATE INDEX IF NOT EXISTS idx_persons_file_numbers ON persons USING GIN (file_numbers);
CREATE INDEX IF NOT EXISTS idx_persons_tribes ON persons USING GIN (tribes);

-- FTS only on canonical_name. PG's array_to_string is STABLE, not
-- IMMUTABLE, so we can't include name_variants/roles/tribes in a STORED
-- generated column. Variants can be searched separately with ANY() against
-- the name_variants array, which is GIN-indexed below.
ALTER TABLE persons
    ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(canonical_name, ''))
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_persons_search_vector
    ON persons USING GIN (search_vector);

CREATE INDEX IF NOT EXISTS idx_persons_name_variants
    ON persons USING GIN (name_variants);

-- ─────────────────────────────────────────────────────────────────
-- slip_cases  (many-to-many: each slip can mention multiple cases)
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS slip_cases (
    slip_id                 INTEGER REFERENCES slips(id) ON DELETE CASCADE,
    file_number             TEXT REFERENCES cases(file_number) ON DELETE CASCADE,
    case_name_as_mentioned  TEXT,
    PRIMARY KEY (slip_id, file_number)
);

CREATE INDEX IF NOT EXISTS idx_slip_cases_file_number ON slip_cases (file_number);

-- ─────────────────────────────────────────────────────────────────
-- slip_persons  (many-to-many: each slip can name multiple persons)
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS slip_persons (
    slip_id             INTEGER REFERENCES slips(id) ON DELETE CASCADE,
    person_id           INTEGER REFERENCES persons(id) ON DELETE CASCADE,
    role_on_this_slip   TEXT,
    PRIMARY KEY (slip_id, person_id)
);

CREATE INDEX IF NOT EXISTS idx_slip_persons_person_id ON slip_persons (person_id);

COMMIT;
