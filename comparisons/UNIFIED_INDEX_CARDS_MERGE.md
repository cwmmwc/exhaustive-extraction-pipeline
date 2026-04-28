# Unified DOJ Index Cards Database (April 2026)

This document records the design and implementation of the
`unified_index_cards` PostgreSQL database, which merges the Sonnet 4.6
vision and Qwen-VL-72B vision extractions of the 87-PDF NARA RG 60 DOJ
record slip collection into a single normalized research database.

## Why merge?

By April 11, 2026, both extraction pipelines had completed end-to-end runs
on the full 87-PDF collection:

| | Sonnet 4.6 vision | Qwen-VL-72B (HPC) |
|---|---|---|
| Cost | ~$130 | Free (HPC GPU hours) |
| Output | `vision_index_cards_full/` (80 dirs, see "Why 80 vs 87" below) | `qwen_vl_index_cards_full/` (87 JSON files) |
| record_slips total | 12,969 | 13,887 |
| legal_cases total | 4,811 | 9,591 |
| persons total | 6,588 | 3,998 |
| Reliability | 0% failed pages | 0.49% failed pages (11 of 2,264) |

The two extractions disagree in opposite directions and the differences
turn out to be complementary, not redundant:

- **Slips: roughly tied (Qwen +7%).** Both find the same record slips
  most of the time, but each extraction finds ~900 slips the other
  missed (different OCR reads of borderline-quality cards).
- **Cases: Qwen +99% (almost exactly 2x).** Qwen produces a per-mention
  audit trail — each correspondence about a case generates a separate
  `legal_case` entry. Sonnet dedupes case names aggressively. Both
  behaviors are research-useful for different questions.
- **Persons: Sonnet +65%.** Sonnet captures secondary mentions (assistant
  U.S. attorneys, county treasurers, judges, clerks named in routing
  fields). Qwen focuses on case principals.

The two extractions are not duplicates of each other. The merge preserves
the strengths of each in a single canonical database where most queries
return clean answers without needing a `WHERE extraction_source = ...`
filter.

## Why 80 Sonnet PDFs vs 87 Qwen PDFs

The source `RG 60 index cards/` directory tree contains 87 distinct
physical PDFs but only 81 unique inner basenames. Five basenames appear
in 2-3 different DOJ boxes (date-stamped scan filenames like
`09062024.pdf` exist in three separate boxes — Outgoing Box 91, Incoming
Box 21, Outgoing Box 126). Sonnet's directory structure
(`vision_index_cards_full/<basename>/vision_merged.json`) cannot represent
multiple physical PDFs that share an inner basename, so it processed only
one of each collision. Plus one PDF (`RG 60 Subj Index boxes`) was never
extracted by Sonnet at all.

**Math:** 87 distinct physical PDFs - 6 collisions invisible to Sonnet's
naming scheme - 1 fully missing PDF = 80 Sonnet directories.

Qwen's output, which mirrors the full source directory tree, correctly
disambiguates all 87 PDFs.

The merge handles this by **content-based pairing**: for each Sonnet
directory whose basename collides with multiple Qwen files, the script
counts how many `(file_number, date, correspondent)` keys overlap between
Sonnet's slips and each Qwen candidate's slips, then pairs Sonnet with
the Qwen file having the highest overlap. The other Qwen siblings become
qwen-only documents in the merged database.

Pairing results from the actual run:

| basename | siblings | paired with | overlap |
|---|---|---|---|
| 09062024 | 3 | RG 60 Box 91 (Outgoing) | 42 / 72 |
| 09102024 | 2 | 1938-41 Box 854 | 212 / 294 |
| 09132024 | 2 | 1936 Box 576 | 306 / 384 |
| 09242024 | 2 | 1940 Box 859 (continued) | 254 / 340 |
| 09242024_001 | 2 | 1940 Box 859 (continued) | 279 / 354 |

Every pairing has a clear winner — the chosen Qwen file shares roughly
4-7x more slip keys with Sonnet than the unchosen siblings. The
content-pairing approach makes the right call without any manual review.

## Schema overview

Six tables, all keyed off `file_number` for cross-table joins. Schema in
[`schema_unified_index_cards.sql`](../schema_unified_index_cards.sql);
loader in [`merge_index_cards.py`](../merge_index_cards.py).

### `documents` (87 rows)

One row per source PDF. `source_pdf` is the **full relative path** from
`qwen_vl_index_cards_full/` (without the .json extension), so basename
collisions don't merge separate PDFs into a single document row.
Subcollection records the top-level directory (`90-2-11`, `90-2-5`, etc.).
Two boolean flags record whether each extraction processed this PDF, so
researchers can filter by extraction availability.

### `slips` (17,211 rows)

The atomic unit. After slip-level dedup, one row per **physical card** in
the source documents. The primary fields (file_number, date,
correspondent, case_name, subject, etc.) are populated from whichever
extraction is canonical for this row. Sonnet-only fields
(`correspondent_role`, `case_number`, `allottee_name`, `allottee_number`,
`tribe_or_reservation`, `action_type`, `enclosures`, `processed_date`)
fall back to NULL for qwen-only rows.

The `extraction_source` column tags each row's provenance:

| value | meaning | count |
|---|---|---|
| `sonnet+qwen` | Both extractions found this slip; Sonnet's row stored | 9,645 |
| `sonnet-only` | Only Sonnet found this slip | 3,324 |
| `qwen-only` | Only Qwen found it (or it's from a Qwen-only PDF) | 4,242 |
| **total** | | **17,211** |

The merge captured **33% more unique slips than either extraction alone**
(Sonnet had 12,969, Qwen had 13,887). The high `sonnet+qwen` count
(9,645) shows the two extractions agree on the bulk of the data; the
~3,300 sonnet-only and ~4,200 qwen-only rows are the genuine
disagreements where one model read a card the other missed or split
differently.

A STORED tsvector column indexes the slip's text fields for FTS queries;
search using `to_tsquery('english', '...') @@ search_vector`.

### `cases` (2,108 rows)

One row per unique `file_number`. The aggregate columns expose what each
extraction contributed:

| column | meaning |
|---|---|
| `canonical_case_name` | longest case_name variant seen across both extractions |
| `case_name_variants` | Postgres array of all case_name variants (paraphrases preserved) |
| `sonnet_slip_count` | how many slips with this file_number came from Sonnet |
| `qwen_slip_count` | same for Qwen |
| `sonnet_case_mention_count` | how many entries in Sonnet's `legal_cases` extraction had this file_number |
| `qwen_case_mention_count` | same for Qwen — the per-mention audit-trail signal |
| `cases_at_file_number` | distinct case_names in **Sonnet's** `legal_cases` (deduped, normalized) |
| `distinct_persons_count` | how many unique persons appear across all slips for this file_number |

### Interpreting `cases_at_file_number`

This is the metric that flags master classifications, but it's not a
boolean — interpret it carefully:

| value | typical meaning |
|---|---|
| **1** | One canonical case under this file_number. ~95% of file_numbers. |
| **2-10** | A small case family. Could be a few related sub-suits filed under one file_number, or paraphrase variation that defeated normalization. Inspect `case_name_variants`. |
| **10-50** | A campaign with many distinct sub-cases, e.g. 90-2-5-49 Fort Peck = 32 separate allottee tax-recovery suits filed under one campaign file. |
| **50+** | A genuine master classification. Top hits: 90-2-01 Indians--Legislation = 165 distinct bills; 90-2-20-01 = 50; 90-2-5-49 = 32. |

The metric is computed from **Sonnet's `legal_cases` extraction only**
(not slips' `case_name` fields, not Qwen's `legal_cases`). Sonnet dedupes
case names aggressively at extraction time, so it's the most reliable
source for "how many distinct cases live under this file_number." Qwen's
legal_cases is too noisy because it produces per-correspondence paraphrase
variants. For Qwen-only PDFs (the 7 PDFs Sonnet didn't process), the
metric falls back to 1.

**To investigate any high-count row:** query `case_name_variants` to see
the actual list of distinct cases.

### `persons` (4,359 rows)

One row per unique normalized name across both extractions. Normalization
strips punctuation, lowercases, and sorts words alphabetically so
"Smith, John" and "John Smith" merge.

| column | meaning |
|---|---|
| `canonical_name` | longest variant seen — closest to a "best" spelling |
| `normalized_name` | unique key for dedup (lowercased, sorted words) |
| `name_variants` | Postgres array of all original spellings observed |
| `roles` | array of distinct roles seen across slips ("allottee", "defendant", "U.S. Atty.", etc.) |
| `tribes` | array of distinct tribal affiliations |
| `file_numbers` | array of file_numbers this person appears in |
| `sources` | which extractions found this person: `{sonnet}` / `{qwen}` / `{sonnet,qwen}` |
| `sonnet_mention_count` | how many times Sonnet found this person |
| `qwen_mention_count` | same for Qwen |

The `file_numbers` array (with a GIN index) makes person→case lookups
fast: "every case Stella D. Twiss appears in" is one query.

### `slip_cases` (17,087 rows) and `slip_persons` (7,032 rows)

Many-to-many join tables. Most slips reference a single case via their
own `file_number`, but the join structure leaves room for slips that
mention multiple cases (rare but possible).

`slip_persons` links slips to deduped persons via the slip's
`allottee_name` field. A slip whose `allottee_name` was a list (Qwen
sometimes returns a JSON array) gets exploded into multiple person rows.

## Slip-level matching logic

The merge needs to recognize "the same physical slip extracted twice." It
does this with a join key on `(source_pdf, normalized_file_number,
normalized_date, normalized_correspondent)`. Two slips from the same PDF
with the same file_number, date, and correspondent are very likely the
same card.

Within a per-PDF match group, the merge greedily pairs Sonnet slips to
Qwen slips by key. When both extractions found the slip, Sonnet's row
wins (it has the broader 17-field schema). Qwen's row contributes any
non-empty fields that Sonnet had empty (rare augmentation case). When
only one extraction found the slip, that row is canonical.

**Known limitation:** the match key relies on the model getting
file_number, date, and correspondent right on both passes. If both models
made the same OCR error, they'll match correctly but on the wrong values.
If they made different errors, the slip becomes both `sonnet-only` and
`qwen-only` in the database — counted twice when it should be counted
once. We accept this rare false-negative because the alternative (fuzzy
matching on subject lines) creates more false positives than it prevents
false negatives.

**Known limitation: no source_page.** Neither current extraction stored
which page of the source PDF each slip came from. Both extraction scripts
have been patched (`extract_single_pdf.py` and
`run_qwen_vl_index_cards_full.py` as of 2026-04-11) to stamp `source_page`
on every item in their merged outputs. Re-extracting the collection would
populate the column. The merge can use page numbers when they're
available; for now they are NULL on every row.

## Sample queries

```sql
-- Trace U.S. v. Pennington County across the corpus.
-- Returns ~25 slips spanning August 1935 → September 1936.
SELECT s.file_number, s.date, s.correspondent, s.case_name, s.subject,
       s.extraction_source, d.source_pdf
FROM slips s JOIN documents d ON s.document_id = d.id
WHERE s.file_number LIKE '90-2-5-7%'
  AND (s.case_name ILIKE '%pennington%' OR s.subject ILIKE '%pennington%')
ORDER BY s.date;

-- Heavy-traffic case files (top 15 by total slip count).
SELECT file_number, canonical_case_name,
       sonnet_slip_count, qwen_slip_count, cases_at_file_number,
       distinct_persons_count
FROM cases
ORDER BY (sonnet_slip_count + qwen_slip_count) DESC
LIMIT 15;

-- Master classifications: file_numbers with > 5 distinct cases per Sonnet.
SELECT file_number, canonical_case_name, cases_at_file_number,
       sonnet_slip_count + qwen_slip_count AS total_slips
FROM cases
WHERE cases_at_file_number > 5
ORDER BY cases_at_file_number DESC;

-- Trace a person across the corpus.
SELECT canonical_name, file_numbers, sources,
       sonnet_mention_count, qwen_mention_count
FROM persons
WHERE canonical_name ILIKE '%pourier%';

-- Persons that ONLY Sonnet found (the 65% advantage).
SELECT canonical_name, array_length(file_numbers, 1) AS n_files
FROM persons
WHERE sources = ARRAY['sonnet']
ORDER BY array_length(file_numbers, 1) DESC NULLS LAST
LIMIT 20;

-- Compare extraction agreement on a specific case.
SELECT extraction_source, COUNT(*) AS n_slips
FROM slips
WHERE file_number = '90-2-5-49'
GROUP BY extraction_source;

-- Full-text search slips for Indian taxation cases.
SELECT s.file_number, s.date, s.case_name, s.subject
FROM slips s
WHERE s.search_vector @@ to_tsquery('english', 'tax & restricted & allotment')
ORDER BY s.date
LIMIT 30;

-- All persons who appear in any case under master file 90-2-01.
SELECT DISTINCT p.canonical_name
FROM persons p
WHERE '90-2-01' = ANY(p.file_numbers);
```

## Files

- [`schema_unified_index_cards.sql`](../schema_unified_index_cards.sql) — DDL
- [`merge_index_cards.py`](../merge_index_cards.py) — the merge loader
- This file (`UNIFIED_INDEX_CARDS_MERGE.md`)

## What this does NOT do

- The merge does not modify the source extractions (`vision_index_cards_full/`
  and `qwen_vl_index_cards_full/`). They remain on disk as the
  authoritative raw data and can be re-merged with different rules at any
  time.
- The merge does not update Streamlit's collection dropdown. That's a
  separate task — see the README for how the analysis tool gets pointed
  at the new database.
- The merge is not idempotent across schema changes. To re-run after
  changing the schema, drop and recreate the database
  (`psql postgres -c "DROP DATABASE unified_index_cards;"` then
  `psql postgres -c "CREATE DATABASE unified_index_cards;"` then re-apply
  the schema and re-run the merge with `--reset`).

## Lessons captured

- **Use full relative paths, not basenames, as document identifiers.**
  Basename collisions in source data are real (here: 6 of 87 PDFs share
  inner filenames with at least one sibling). A merge keyed on basename
  silently loses data.
- **Content-based pairing handles ambiguous joins.** When two structures
  to be merged share an ambiguous key, count overlap of secondary keys
  to pick the right match. The pairing in this merge had clear winners
  every time (overlap ratios 3-7x higher for the right pair than the
  wrong ones).
- **Per-mention vs deduped counts are both research-useful — store
  both.** Qwen's per-mention `legal_cases` and Sonnet's deduped
  `legal_cases` describe the same data at different granularities. The
  cases table stores both as separate columns rather than picking one.
- **`cases_at_file_number` is a count, not a category.** The metric
  flags master classifications when high, but for case families (one
  campaign with many sub-suits) it produces meaningful intermediate
  values. The user reads it as a number, not a yes/no flag.
- **NOT NULL constraints on extracted text fields are dangerous.** Some
  slips genuinely lack a file_number (bad OCR, marginal cards). Schema
  fields populated from extraction output should default to NULLABLE
  unless there's a specific reason otherwise.
