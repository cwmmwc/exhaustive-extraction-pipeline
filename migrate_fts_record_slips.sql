-- Layer 3 retrieval improvement: PostgreSQL full-text search on the
-- DOJ record_slips and legal_cases tables.
--
-- Adds STORED generated tsvector columns and GIN indexes so that the
-- analysis tool can use websearch_to_tsquery + ts_rank instead of crude
-- ILIKE matching. This handles stemming, plurals, phrase queries, and
-- gives much better relevance ordering.
--
-- Safe to run multiple times — every step uses IF NOT EXISTS guards.
--
-- Run against any database that has the record_slips / legal_cases tables:
--   psql index_cards -f migrate_fts_record_slips.sql
--
-- Requires PostgreSQL 12+ (we use PG 15.15).

BEGIN;

-- ─────────────────────────────────────────────────
-- record_slips
-- ─────────────────────────────────────────────────

ALTER TABLE record_slips
    ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(file_number, '')        || ' ' ||
            coalesce(jurisdiction, '')       || ' ' ||
            coalesce(correspondent, '')      || ' ' ||
            coalesce(correspondent_role, '') || ' ' ||
            coalesce(case_name, '')          || ' ' ||
            coalesce(case_number, '')        || ' ' ||
            coalesce(named_individual, '')   || ' ' ||
            coalesce(tribe_or_reservation, '') || ' ' ||
            coalesce(subject, '')            || ' ' ||
            coalesce(action_type, '')        || ' ' ||
            coalesce(routing_division, '')
        )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_record_slips_search_vector
    ON record_slips USING GIN (search_vector);

-- ─────────────────────────────────────────────────
-- legal_cases
-- ─────────────────────────────────────────────────

ALTER TABLE legal_cases
    ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(case_name, '')          || ' ' ||
            coalesce(file_number, '')        || ' ' ||
            coalesce(jurisdiction, '')       || ' ' ||
            coalesce(case_type, '')          || ' ' ||
            coalesce(named_individual, '')   || ' ' ||
            coalesce(tribe_or_reservation, '') || ' ' ||
            coalesce(county, '')
        )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_legal_cases_search_vector
    ON legal_cases USING GIN (search_vector);

COMMIT;

-- Verify (read-only, run after the migration commits):
-- SELECT COUNT(*) FROM record_slips WHERE search_vector IS NOT NULL;
-- SELECT COUNT(*) FROM legal_cases  WHERE search_vector IS NOT NULL;
