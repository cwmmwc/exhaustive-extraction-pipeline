# Circular 2464 → `american-indian-allotment` Integration Notes

Drafted 2026-04-21 at the close of the Fort Berthold ledger replacement session. Represents the planned integration of the Circular 2464 extraction corpus (928 records across affidavits, questionnaires, agency narratives, and the Fort Berthold fee patent ledger) into the existing PostgreSQL research database that powers the Flask app at `/Users/cwm6W/projects/american-indian-allotment/`.

**Status: design only. Not implemented. Begins after the extraction pipeline closes out (four allotment recoveries, Parts 10/12 audit, allotment 969, 33-affidavit sample, matching cleanup).**

---

## Linkage model

Two join keys: **allotment number** and **tribe** (normalized).

The existing `american-indian-allotment` schema is organized around patents (BLM GLO administrative records) and claims (1983 Federal Register filings). Circular 2464 adds a third evidence layer: contemporaneous 1928 testimony — sworn statements, BIA investigation questionnaires, agency narratives, and the Fort Berthold fee patent ledger — joined to the existing tables by allotment number and normalized tribe name.

The integration does not replace anything in the existing schema. It adds new tables alongside, using the same normalization infrastructure (`tribe_name_map`, tribe identification corrections) already in place.

---

## Proposed schema additions

Three new objects: two tables and one materialized view.

### `circular_2464_documents`

One row per source document (~928 rows).

```sql
CREATE TABLE circular_2464_documents (
    id SERIAL PRIMARY KEY,
    document_id TEXT NOT NULL,           -- e.g. "part12_questionnaire_024"
    document_type TEXT NOT NULL,         -- affidavit, questionnaire, agency_narrative, ledger_entry
    source_pdf TEXT,                     -- NARA RG 75 file reference
    source_pages TEXT,                   -- e.g. "42-43"
    agency TEXT,                         -- Pine Ridge, Otoe, Fort Berthold, etc.
    model TEXT,                          -- sonnet / qwen-vl-72b — extraction provenance
    pdf_path TEXT                        -- path to single-doc PDF on filesystem
);
CREATE INDEX idx_c2464_docs_type ON circular_2464_documents(document_type);
CREATE INDEX idx_c2464_docs_agency ON circular_2464_documents(agency);
```

### `circular_2464_records`

The 18-column schema content. One row per extracted record. Key fields indexed for joining.

```sql
CREATE TABLE circular_2464_records (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES circular_2464_documents(id),
    name TEXT,
    tribe_reservation TEXT,
    post_office_address TEXT,
    allotment_number TEXT,               -- primary join key
    cancelled TEXT,
    refused_protested TEXT,
    recorded_patent TEXT,
    sold_mortgaged TEXT,
    buyer TEXT,
    tax_burden TEXT,
    trust_patent_date TEXT,
    fee_patent_date TEXT,
    gender TEXT,
    age TEXT,
    occupation_income TEXT,
    literate_illiterate TEXT,
    notes TEXT,
    tribe_normalized TEXT                -- derived via existing tribe_name_map logic
);
CREATE INDEX idx_c2464_rec_allot ON circular_2464_records(allotment_number);
CREATE INDEX idx_c2464_rec_tribe ON circular_2464_records(tribe_normalized);
CREATE INDEX idx_c2464_rec_name ON circular_2464_records(name);
CREATE INDEX idx_c2464_rec_fee_date ON circular_2464_records(fee_patent_date);
```

### `circular_2464_allotment_matches` (materialized view)

Pre-computed joins between Circular 2464 records and the existing patent/claim universe. Built by matching on `allotment_number` + `tribe_normalized`.

```sql
CREATE MATERIALIZED VIEW circular_2464_allotment_matches AS
SELECT 
    c.id AS c2464_record_id,
    c.name AS c2464_name,
    c.allotment_number,
    c.tribe_normalized,
    c.fee_patent_date AS c2464_fee_date,
    p.objectid AS blm_patent_objectid,
    p.accession_number AS blm_accession,
    p.full_name AS blm_patentee,
    p.signature_date AS blm_signature_date,
    p.forced_fee AS blm_forced_fee_flag,
    fr.id AS fr_claim_id,
    fr.case_number AS fr_case_number,
    fr.claim_type AS fr_claim_type
FROM circular_2464_records c
LEFT JOIN blm_allotment_patents p 
    ON c.allotment_number = p.indian_allotment_number 
    AND c.tribe_normalized = p.preferred_name
LEFT JOIN federal_register_claims fr
    ON c.allotment_number = fr.allotment_number
    AND c.tribe_normalized = fr.tribe_identified;
```

This is the integration payoff. One query joins an allottee's 1928 sworn testimony to their BLM patent record to any 1983 Federal Register claim filed on their behalf.

---

## Flask app additions

Follows the existing `app.py` architecture: single-file Flask, server-side DataTables, raw psycopg2, Jinja2 templates, Bootstrap 5. Circular 2464 becomes a third parallel section alongside Claims and Patents: **Testimony**.

### Routes

- `/testimony` — record search, DataTables with filters (document type, agency, tribe, year, allotment)
- `/testimony/<id>` — record detail showing all 18 columns plus links to matched BLM patent, matched FR claim, and PDF page
- `/allottee/<tribe_slug>/<allotment>` — **the composite view** — pulls from all four sources (BLM patent, FR claim, Circular 2464 records, trust/fee linkage) to show everything the database knows about one specific allotment. This is the Phase 6 endpoint from the extraction pipeline, now living in the research app.
- `/testimony/timeline` — fee patent dates from Circular 2464 records plotted alongside BLM patent dates, per-tribe or per-agency
- `/testimony/lenders` — buyer/lender network analysis (Commerce Trust, Gumm Bros, LeVan, etc.) across all mortgage records in the corpus
- `/api/testimony`, `/api/testimony/csv` — DataTables JSON + CSV export

### Cross-links (bidirectional)

- From `/claim/<id>` detail: panel "Circular 2464 testimony for this allotment" if any matching records exist
- From `/patent/<objectid>` detail: same panel
- From `/testimony/<id>` detail: links to BLM patent and FR claim if matches exist
- Navigation: Claims | Patents | **Testimony** | Map | Tribes | Visualizations | About | Main Site

### Map integration

If allotments in Circular 2464 have matching PLSS geometry via the BLM patent join, they can appear on the existing `/map` with testimony-specific styling.

---

## Implementation phases

Each phase is bounded and can be tackled in one to a few focused sessions.

1. **Schema migration** — add the three tables, write the SQL file. One evening.
2. **Loader script** — reads the 928 extraction JSONs from `extractions/sonnet/`, maps 18-column fields to the schema, normalizes tribe names using the existing `tribe_name_map`, inserts into `circular_2464_documents` + `circular_2464_records`, refreshes the materialized view. A day.
3. **Flask routes + templates** — testimony search, detail, timeline, composite allottee view, cross-links. Two to four days.
4. **Map integration** — testimony overlay on `/map`. A day.

Total: one to two focused weeks.

---

## Open questions to resolve before implementation

1. **Tribe normalization for Circular 2464 records.** The Tribe/Reservation field in the corpus is often "not stated" or contains agency names like "Otoe Agency" or "Pine Ridge" rather than proper tribe names. A pre-load normalization pass using the existing `tribe_name_map` plus targeted additions for agency-derived names will be needed. Match the established pattern from the 2026-03-17 tribe identification corrections.

2. **Dual-allotment records.** The Fort Berthold ledger has four compound-allotment entries (Cecil Grant "448a 1535", Olive Hoffman "206a 1411", William Weeks "809a-1468", Clarence S. Soldier "1659 918a") plus a few on other pages (Allen Smith 1334-284, Mary Gillette 1309-300, Joseph Irwin 464-487a, John Grinnell 1052-193). These were preserved as compound strings in the allotment_number field per the "preserve source structure, derive splits on demand" decision. The loader will need to handle these specially when matching to BLM records, which use one allotment number per row. Suggested approach: during the materialized view refresh, split on space/hyphen and produce one match row per component allotment number, preserving the source compound value in a `compound_allotment_source` field.

3. **Provenance on individual field values.** Some records have correction history (the seven character-OCR patches applied during the ledger replacement, the Haragarra 025 Tribe/Reservation patch, etc.). The NOTES field captures provenance as appended text. For richer queryable provenance, consider a separate `circular_2464_field_history` table. Probably not worth the complexity in Phase 1 — the NOTES-based provenance is adequate for now.

4. **Document-level narrative content.** The affidavits and questionnaires contain substantive narrative beyond the 18 structured columns — sworn testimony about how patents were issued, fraud claims, mortgage terms, etc. The current extraction captures key details in NOTES but not full narrative. Phase 5 validation and Phase 6 cross-document linking would benefit from optional full-text capture. Defer.

---

## What's ready vs. what's not

**Ready:**
- Extraction pipeline has produced 928 records across 4 document types.
- Fort Berthold ledger (277 records) is research-grade as of 2026-04-21, Qwen vision-based with 1 correction and 9 annotations applied.
- Affidavits/questionnaires/narratives are Sonnet OCR-text based; stratified check confirmed no systemic artifact problem.
- Existing `american-indian-allotment` schema is stable and well-documented in `DATABASE.md`.
- Existing Flask app patterns are clear from `CLAUDE.md`.

**Not ready (blocks integration):**
- Four "not stated" allotment recoveries (Florence Twiis Cuny, Louis Hawkins, Cecilia Armstrong Ross, Susie Keester-nee Harvey) — task written, pending execution.
- Parts 10/12 audit (Rosebud+Shawnee, Otoe+Pawnee+Ponca).
- Allotment 969 manual record creation.
- 33-affidavit OCR-failure sample classification.
- Matching issue cleanup (3 combined-allottee splits, 3 allotment discrepancies, 1 matcher bug).
- KCA and Shawnee integration decision.

Once those close, the extraction corpus is final and the integration can begin on stable data.
