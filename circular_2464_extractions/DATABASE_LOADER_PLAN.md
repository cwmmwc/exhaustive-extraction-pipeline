# Circular 2464 Database Loader — Design Plan

**Status:** Design stage. Architecture agreed. Implementation blocked on resolving three design questions below.

**Precedent:** `merge_index_cards.py` and `comparisons/UNIFIED_INDEX_CARDS_MERGE.md` — the DOJ index cards merge took two parallel extractions (Sonnet + Qwen) with different strengths, deduplicated at the slip level, and exposed both contributions as columns on canonical rows. This loader does the same with three extraction layers.

**Target database:** `circular_2464` (own database, per user decision 2026-04-28).

**Streamlit integration:** New dropdown entry in `ai_analysis_interface_v4.py`.

**Graph integration:** `explore_graph.py --db circular_2464`.

---

## Three extraction layers to merge

### Layer 1: Per-allottee Sonnet text records (canonical rows)

- **Location:** `circular_2464_extractions/extractions/sonnet/*.json`
- **Count:** ~1040 records
- **Schema:** Flat — Name, Allotment number, Tribe/Reservation, Post Office Address, Fee Patent Date, Refused/Protested, Sold/Mortgaged, Buyer, Tax burden, NOTES, etc. (18 columns)
- **Granularity:** One record per allottee sub-PDF
- **Strengths:** Per-allottee retrieval, clean document-to-record mapping, complete corpus coverage
- **Weaknesses:** No structured buyer/transaction/mortgage/testimony fields; everything beyond the 18 flat columns is in NOTES as prose

### Layer 2: Per-part Kimi v5 text records (structured enrichment)

- **Location:** `circular_2464_extractions/v5/RG 75 1929 circular 2464 part N/Kimi K2.5.json`
- **Count:** ~13 files (one per source part PDF)
- **Schema:** Rich v5 — entities, fee_patents, financial_transactions, events, relationships, correspondence, legislative_actions, testimony, mortgages, taxes
- **Granularity:** Per-part (one JSON per entire multi-page source PDF)
- **Strengths:** Structured cross-allottee data (buyer names, sale prices, patent numbers, mortgage terms as discrete queryable fields); richer entity extraction
- **Weaknesses:** No per-allottee record granularity; joins to Layer 1 require name+allotment matching

### Layer 3: Per-allottee Sonnet vision records (structured enrichment, subset)

- **Location:** `validation_samples/cat1_sonnet_vision/<rid>/vision_merged.json` and `validation_samples/<name>_vision/vision_merged.json`
- **Count:** ~38 records (bundle splits + CAT_1 recovery)
- **Schema:** Rich v5 (same as Kimi), produced by Sonnet vision on per-allottee sub-PDFs
- **Granularity:** Per-allottee
- **Strengths:** Per-allottee AND structured — the best of both layers
- **Weaknesses:** Only exists for ~38 records; the other ~1002 don't have this layer
- **Current status:** Being retrofitted onto Layer 1 records (workstream 1, in progress as of 2026-05-05)

---

## Merge architecture

Per-allottee Sonnet records (Layer 1) are the canonical rows. Each row gets enriched with:

- Kimi v5 structured fields (Layer 2) joined by name+allotment matching
- Sonnet vision structured fields (Layer 3) already on the record after retrofit

Provenance is preserved as a column on every enriched field: `source = sonnet_text | kimi_v5 | sonnet_vision`.

### Database schema (sketch)

```sql
-- Canonical per-allottee records
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    document_id TEXT NOT NULL UNIQUE,     -- e.g. "part12_questionnaire_024"
    document_type TEXT NOT NULL,           -- affidavit, questionnaire, agency_narrative, ledger_entry
    source_pdf TEXT,
    source_pages TEXT,
    agency TEXT,
    extraction_model TEXT                  -- sonnet | qwen-vl-72b
);

CREATE TABLE records (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    -- Flat fields from Layer 1 (Sonnet text)
    name TEXT,
    tribe_reservation TEXT,
    post_office_address TEXT,
    allotment_number TEXT,
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
    -- Provenance
    source_layer TEXT DEFAULT 'sonnet_text'
);

-- Structured enrichment from Layers 2 and 3
-- Modeled on the v4 schema used by all other corpora

CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    record_id INTEGER REFERENCES records(id),  -- NULL if from Kimi per-part (no per-allottee link)
    name TEXT,
    entity_type TEXT,
    context TEXT,
    source_layer TEXT  -- kimi_v5 | sonnet_vision
);

CREATE TABLE fee_patents (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    record_id INTEGER REFERENCES records(id),
    allottee_name TEXT,
    allotment_number TEXT,
    acreage TEXT,
    patent_date TEXT,
    patent_number TEXT,
    mechanism TEXT,
    buyer TEXT,
    sale_price TEXT,
    attorney TEXT,
    mortgage TEXT,
    source_layer TEXT
);

CREATE TABLE financial_transactions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    record_id INTEGER REFERENCES records(id),
    transaction_type TEXT,
    amount TEXT,
    payer TEXT,
    payee TEXT,
    date TEXT,
    description TEXT,
    source_layer TEXT
);

CREATE TABLE testimony (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    record_id INTEGER REFERENCES records(id),
    witness TEXT,
    witness_title TEXT,
    hearing TEXT,
    date TEXT,
    subject TEXT,
    key_claims TEXT,
    source_layer TEXT
);

CREATE TABLE mortgages (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    record_id INTEGER REFERENCES records(id),
    borrower TEXT,
    lender TEXT,
    amount TEXT,
    land_description TEXT,
    date TEXT,
    interest_rate TEXT,
    status TEXT,
    source_layer TEXT
);

CREATE TABLE taxes (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    record_id INTEGER REFERENCES records(id),
    taxpayer TEXT,
    land_description TEXT,
    tax_type TEXT,
    amount TEXT,
    year TEXT,
    status TEXT,
    county TEXT,
    source_layer TEXT
);

-- Materialized view for cross-corpus joins
CREATE MATERIALIZED VIEW circular_2464_allotment_matches AS
SELECT
    r.id AS record_id,
    r.name,
    r.allotment_number,
    r.tribe_reservation,
    r.fee_patent_date,
    bap.objectid AS blm_patent_objectid,
    bap.accession_number AS blm_accession,
    bap.full_name AS blm_patentee,
    bap.signature_date AS blm_signature_date,
    fr.id AS fr_claim_id,
    fr.case_number AS fr_case_number,
    fr.claim_type AS fr_claim_type
FROM records r
LEFT JOIN allotment_research.blm_allotment_patents bap
    ON r.allotment_number = bap.indian_allotment_number
    AND <tribe_normalization_join>
LEFT JOIN allotment_research.federal_register_claims fr
    ON r.allotment_number = fr.allotment_number
    AND <tribe_normalization_join>;
```

---

## Three design questions to resolve before implementation

### Question 1: Name+allotment matching failure modes

**Problem:** The Sonnet vs Kimi v5 disagreement scan found 112 disagreements across 647 records. Where Sonnet has Allot=A and Kimi has Allot=B for the same person, the join either fails (no match) or produces duplicates.

**Known cases:**
- Edward Little Eagle: Sonnet text="A0L-" (garbled), Kimi v5="404", actual=Standing Rock 1371
- Mary Julia Neiss: Sonnet=1463, Kimi swapped with Alphonse Charbonneau=1466
- Sonnet captures Circular number 2464 as allotment (Nicholas Trombla — real allotment 464)
- Sonnet captures patent number in Allotment field (Anna Blackbird 35918→3518; Hannah Hardin 715412→real allotment 42)

**Options:**
- A) Strict join: name+allotment must both match. Accept that ~112 records won't link. Flag unlinked Kimi entities for manual review.
- B) Fuzzy join with confidence: primary=allotment match, secondary=name similarity score. Join at high confidence; flag low-confidence matches for review. Risk: false positives on common allotment numbers across agencies.
- C) Manual override table for known cases. Small table of `(sonnet_record_id, kimi_entity_key, override_reason)` that resolves known failures. Combined with option A or B.

**Precedent from index cards merge:** The index cards merge used `(source_pdf, file_number, date, correspondent)` as the dedup key — a multi-field composite that was more reliable than any single field. The Circular 2464 equivalent would be name+allotment+part_number (since Kimi entities come from specific parts, and Sonnet records come from sub-PDFs of those parts).

**Recommendation:** Option A + C. Strict join on name+allotment+part. Manual override table for the ~20-30 known failures. Accept that some Kimi entities won't link. This is the conservative choice that avoids false matches.

---

### Question 2: Kimi entities without allotment context

**Problem:** Many Kimi v5 entities of type "person" have no allotment number in their context string. These can only join by name, which is unreliable (multiple people share names across agencies; spelling variants are pervasive).

**Scope:** Unknown. Needs quantification: how many Kimi v5 person entities have allotment numbers vs how many don't?

**Options:**
- A) Accept partial joins. Kimi entities with allotment numbers link to Sonnet rows. Kimi entities without allotment numbers remain as standalone entity rows with `record_id = NULL` (no per-allottee link). They're still queryable by name for network analysis.
- B) Enrichment pass: for each Kimi entity without an allotment, look at adjacent Kimi fee_patents rows from the same part that mention the same name. If a fee_patent has the allotment, propagate it to the entity. Then attempt the join.
- C) Both: run enrichment (B) first to maximize linkable entities, then accept remaining unlinked ones (A).

**Recommendation:** Option C. The enrichment pass is cheap (it's a Python loop over the ~13 Kimi JSONs) and could substantially increase the join rate. Remaining unlinked entities are still valuable for network queries (Valandra, Tackett, etc.) even without per-allottee linkage.

---

### Question 3: Precedence when sources disagree

**Problem:** For the ~38 records with Sonnet vision data, the loader has three potential sources for the same field (e.g., buyer name). For the other ~1002 records, it has two (Sonnet text flat fields vs Kimi v5 structured fields). When they disagree, which wins?

**Known disagreement patterns:**
- Sonnet text NOTES says "sold to Mr. Snodgrass" (prose). Kimi v5 fee_patents says `buyer: "Mr. Snodgrass"` (structured). No conflict — same data, different format.
- Sonnet text has wrong allotment (patent number in field). Kimi v5 has correct allotment. Kimi wins.
- Sonnet vision fabricated "$7,000 NW 1/4 sale" when source said "$2,000 partial allotment." Source wins — but the loader can't check the source.
- Both models wrong (Edward Little Eagle). Neither wins.

**Options:**
- A) Source-layer precedence hierarchy: sonnet_vision > kimi_v5 > sonnet_text. Higher layers overwrite lower layers on all fields.
- B) Field-level precedence: structured fields (fee_patents.buyer, fee_patents.sale_price) prefer Kimi v5 or Sonnet vision; flat identification fields (Name, Allotment) prefer Sonnet text (which has been manually verified through the cleanup campaign). NOTES always concatenates rather than overwrites.
- C) Keep all values with provenance tags. Don't resolve conflicts in the loader — expose them to the query layer. A `buyer_sonnet_text`, `buyer_kimi_v5`, `buyer_sonnet_vision` column set. The query interface or the researcher picks.

**Recommendation:** Option B. The cleanup campaign (Shawnee unbundling, Lessert corrections, Julia Bissonette recovery, allotment recoveries, vision recovery, ledger replacement) has made the Sonnet text Name and Allotment fields highly reliable for the records that were touched. Kimi v5 and Sonnet vision provide structured detail (buyers, prices, mortgages) that the flat schema never captured. Use each layer for what it's best at.

Specifically:
- `records.name`, `records.allotment_number`, `records.tribe_reservation`: Sonnet text (Layer 1), already verified through cleanup
- `fee_patents`, `financial_transactions`, `mortgages`, `testimony`, `taxes`: prefer Sonnet vision (Layer 3) where it exists; fall back to Kimi v5 (Layer 2); Sonnet text NOTES as last resort (parsed if possible)
- `entities`: union of all three layers, deduplicated by normalized name
- Provenance column on every row tracks which layer contributed the data

---

## Implementation sequence

1. **Resolve the three design questions above** — decide on options, document decisions
2. **Quantify Question 2** — count Kimi v5 entities with vs without allotment context
3. **Write the enrichment pass** (Question 2, Option B) — propagate allotments from Kimi fee_patents to Kimi entities
4. **Write the loader** — `load_circular_2464_extractions.py`, modeled on `merge_index_cards.py`
5. **Create the database** — `createdb circular_2464`, run schema SQL
6. **Load** — run the loader
7. **Add Streamlit dropdown** — one line in `ai_analysis_interface_v4.py`
8. **Rebuild graph** — `explore_graph.py --db circular_2464 survey_of_conditions historical_docs`
9. **Verify** — test queries: Sarah Thompson allot 312, Valandra network, Julia Bissonette cross-reference

---

## Dependencies

- Retrofit of Sonnet vision data onto corpus records (workstream 1) — in progress as of 2026-05-05
- Remaining extraction cleanup: Trombla/Tromble spelling, Qwen CAT_1 cross-validation when HPC clears
- `INTEGRATION_NOTES.md` — earlier schema sketch (2026-04-21), partially superseded by this plan
- `merge_index_cards.py` + `comparisons/UNIFIED_INDEX_CARDS_MERGE.md` — precedent to study before implementation

---

*Created 2026-05-05. Design stage — not yet implemented.*
