#!/usr/bin/env python3
"""
Append session 2026-05-04 findings to OPERATIONS.md.

Adds five sections:
  1. Three-extraction architecture (clarifies the per-allottee Sonnet vs
     per-part Kimi vs per-record Sonnet vision distinction)
  2. Vision extraction retrofit (vision_extraction_v5 field on records)
  3. New document type: agency_buyer_report
  4. Continuation page convention
  5. Pending workstream: Sonnet+Kimi merge for the database loader
  6. CAT_1 batch completion summary
"""
from pathlib import Path

OPERATIONS_PATH = Path(
    "/Users/cwm6W/projects/exhaustive-extraction-pipeline/OPERATIONS.md"
)

ADDITIONS = """

---

## Three-extraction architecture (clarified 2026-05-04)

The Circular 2464 corpus has been processed by three parallel extraction layers, each with different units of analysis and different schemas. Understanding the distinction matters for cleanup decisions and for the eventual database load.

**Layer 1 — Sonnet text (per-allottee, flat schema)**
- Location: `circular_2464_extractions/extractions/sonnet/*.json`
- ~1040 records, one per allottee sub-PDF
- Schema: flat `extraction` object with `Name`, `Allotment number`, `Tribe/Reservation`, `Post Office Address`, `Date`, `Document type`, `NOTES`
- Per-allottee retrieval is clean: grep by name, get the record
- Cross-allottee structured queries are not supported; buyer/transaction/mortgage data lives in `NOTES` as free text

**Layer 2 — Kimi text v3/v4/v5 (per-part, v5 schema)**
- Location: `circular_2464_extractions/v3/`, `v4/`, `v5/`
- ~13 records per version, one per whole-part PDF (each part PDF contains many allottees)
- Schema: rich v5 with structured tables (`entities`, `fee_patents`, `financial_transactions`, `events`, `relationships`, `correspondence`, `legislative_actions`, `testimony`, `mortgages`)
- Cross-allottee structured queries work natively (e.g., aggregate `subsequent_buyer` across the corpus)
- Per-allottee retrieval requires entity-level filtering and join back to source pages

**Layer 3 — Sonnet vision (per-record, v5 schema)**
- Location: `validation_samples/<stem>_vision/vision_merged.json` and `validation_samples/cat1_sonnet_vision/<stem>/vision_merged.json`
- ~38 records (multi-allottee bundle splits + CAT_1 recovery batch)
- Schema: rich v5 (same as Kimi), but generated per-allottee via `extract_single_pdf.py --vision --claude-only`
- Combines per-allottee retrieval with structured cross-allottee data

**Important methodology consequence:** when patching a record, we now check all three layers where applicable. The Sonnet text layer is the canonical corpus record. The Kimi v5 layer provides cross-corpus cross-checks. The Sonnet vision layer provides structured per-record data.

---

## Vision extraction retrofit (2026-05-04)

After running Sonnet vision recovery on the 12 multi-allottee bundles (2026-05-03) and 26 CAT_1 records (2026-05-04), the structured v5 data was initially collapsed into the corpus records' `NOTES` field as free text — losing the structured fee_patents, financial_transactions, mortgages, etc.

The retrofit script (`retrofit_sonnet_vision_v2.py`) walks corpus records and adds the structured v5 data as a new top-level key `vision_extraction_v5` on each record. The flat `extraction` object remains unchanged for backwards compatibility; the structured data is available alongside it for database load and analytical queries.

For multi-allottee bundle records (`_NNNa.json` / `_NNNb.json`), the retrofit filters relevant tables (fee_patents, financial_transactions, mortgages, relationships, testimony, taxes) by allottee name match — so each sibling record only carries data about its own allottee.

A `_retrofit_filter_note` field on each retrofitted record's `vision_extraction_v5` documents what was filtered.

Usage notes:
- The retrofit is idempotent for non-bundle records (skipped if already present)
- For bundle records, it always re-filters (so the latest filter logic takes effect)
- Re-run `retrofit_sonnet_vision_v2.py` if vision content is updated for any record

---

## New document type: agency_buyer_report

Established 2026-05-04 for `part11_agency_narrative_003` (M.B. Gregg, Frank Ktilienk, authored by Supt. H.E. Wright).

**Purpose:** distinguishes agency narrative records that report on land buyers/lessors from those that report on allottees, and from administrative correspondence.

**Distinction from related types:**
- `agency_narrative` — agency report on an allottee's case
- `agency_correspondence` — superintendent transmittal letter to Commissioner of Indian Affairs (the 6 records reclassified 2026-05-03)
- `agency_buyer_report` — agency narrative describing buyers/lessors as the primary subject (no allottee Name/Allotment to recover; named actors are the data)

When patching `agency_buyer_report` records, set:
- `Name` = "(buyer report — see NOTES for named actors)"
- `Allotment number` = "(not applicable — non-allottee record)"
- `Tribe/Reservation` = the reservation context (e.g., "Crow Creek")
- `Document type` = "agency_buyer_report"
- NOTES enriched with per-actor details (name, role, location, agency context)

This type supports future Valandra-style buyer-network queries by giving them a discoverable filter.

---

## Continuation page convention

Some splitter cuts produced two corpus records for the same source document — typically a lead record with the main content and a continuation record with the trailing biographical/health/signature page.

**Examples (2026-05-04):**
- `part1_questionnaire_020` (Louise Drapeau, pages 1-3 of her 5-page Form 5-105) and `part1_questionnaire_021` (page 5, the trailing page)
- `part1_questionnaire_013` (Margaret DeCory main questionnaire) and `part1_questionnaire_022` (continuation page with biographical/health section)

**Decision rule:** retain BOTH records as separate corpus entries (do NOT delete the continuation page). Patch the continuation page with the same Name/Allotment/Tribe as the lead. Cross-reference both directions in NOTES.

**Distinguish from duplicates:** if the continuation page's content is genuinely a duplicate of pages already in the lead (overlapping/repeated content, not a different page section), delete it as a duplicate. Example: `part1_questionnaire_016` (Anna Shuck) was a partial duplicate of `part1_questionnaire_015` and was deleted with q016 content archived in q015's recovery_notes. Different from continuation pages where each record covers different page content.

---

## CAT_1 batch — completion summary (2026-05-03 and 2026-05-04)

Original CAT_1 list (from `enumerate_task5_candidates.py`): 34 records (Sonnet missed both Name and Allotment).

**Pre-batch reclassifications (2026-05-03):**
- 6 administrative cover letters → `agency_correspondence`
- 1 known answer (Mrs. Addie Easton Payne) patched directly from Shawnee master list
- 1 record (`part10_affidavit_004`) excluded as likely Hannah Hardin signature page (her main record at part10_questionnaire_012)

**Vision recovery batch (2026-05-04):** 26 records processed
- Sonnet vision (local): 26/26 succeeded
- Qwen vision (HPC): 49/49 pages succeeded (after server-job-then-recovery-job dual-submit pattern)
- Comparison via `compare_cat1_vision.py` produced verdict TSV: 8 agree, 11 disagree_name, 2 disagree_allot, 5 partial/empty

**Resolutions (all 26):**
- 23 records patched with verified Name/Allotment/Tribe (mix of dual-model agreement, user verification of disagreements, and cross-references to records elsewhere in the corpus)
- 1 duplicate removed (`part1_questionnaire_016`)
- 1 reclassified to `agency_buyer_report` (`part11_agency_narrative_003`)
- 1 left as blank Circular 2464 template (`part3_questionnaire_022`)

**Methodology lessons established:**
- Dual-model vision recovery (Sonnet + Qwen) does work, but each model has distinct failure modes (Sonnet over-confident on numerical content; Qwen prone to surname mis-spellings and place-name confabulation)
- User source-page verification is essential where models disagree — the disagreement is the signal, not the answer
- Cross-references across the corpus (master lists, sibling records, prior project research) often resolve disagreements without further source review
- Continuation pages and duplicates are distinct situations requiring different patches

---

## Pending workstream: Sonnet + Kimi merge for database loader

**Architecture (per Claude Code design note 2026-05-04, following `merge_index_cards.py` precedent):**

Three extraction layers merge at the per-allottee row, with provenance preserved:
1. Per-allottee Sonnet records → canonical rows (one per allottee)
2. Per-part Kimi v5 entities/fee_patents/transactions → join to canonical rows by name+allotment matching
3. Sonnet vision structured fields (~38 records) → already retrofitted onto canonical rows as `vision_extraction_v5`

**Output:** new `circular_2464` PostgreSQL database with its own schema, dropdown entry in Streamlit, graph support via `explore_graph.py --db circular_2464`.

**Open design questions to resolve before implementation:**

1. **Name+allotment matching has known failure modes.** The Sonnet vs Kimi v5 disagreement scan found 112 disagreements in 647 records. Where Sonnet has Allot=A and Kimi has Allot=B for the same person, the join either fails or produces duplicates. Need: confidence-scored fuzzy matching, plus a manual override table for known mismatches (e.g., Edward Little Eagle = 1371 not 404).

2. **Per-part Kimi entities don't always carry allotment context.** Many Kimi `entities` of type "person" have no allotment in their context string. Either accept partial joins (some Kimi entities never link to a Sonnet row) or run an enrichment pass pulling allotments from adjacent Kimi `fee_patents` rows mentioning the same name.

3. **Vision retrofit covers 38 records; ~1002 don't have vision data.** The merge needs a precedence rule for which extraction layer's value wins when multiple sources disagree.

4. **Multi-allottee bundle handling.** The bundle splits we did (Decory/Whiting, Real Rider/Peters, etc.) created `_NNNa.json` / `_NNNb.json` records — each has filtered vision data, but the underlying source PDF was the same. The Kimi v5 entities might list both allottees in the same part-level extraction. Need: clear linkage from Kimi entities back to the correct sibling record.

5. **Continuation pages.** Records like `part1_questionnaire_021` (Drapeau continuation) and `part1_questionnaire_022` (DeCory continuation) share an allottee with their lead records. The merge needs to consolidate them into a single canonical row (or carry them as separate rows with a `continuation_of` link).

**Reference:** `comparisons/UNIFIED_INDEX_CARDS_MERGE.md` and `merge_index_cards.py` worked through equivalent issues for the slips corpus. Same reasoning applies here. Read those before designing the loader.

**Status:** design only. No implementation yet. Loader writes to a new database, doesn't modify existing corpus records.
"""

MARKER = "## Three-extraction architecture (clarified 2026-05-04)"


def main():
    if not OPERATIONS_PATH.exists():
        print(f"ERROR: {OPERATIONS_PATH} does not exist.")
        return

    with open(OPERATIONS_PATH) as f:
        existing = f.read()

    if MARKER in existing:
        print(f"Additions already present (marker: '{MARKER}'). Refusing to duplicate.")
        return

    with open(OPERATIONS_PATH, "a") as f:
        f.write(ADDITIONS)

    print(f"Appended {len(ADDITIONS.splitlines())} lines to OPERATIONS.md")
    print()
    print("New sections:")
    print("  - Three-extraction architecture (per-allottee Sonnet, per-part Kimi, per-record Sonnet vision)")
    print("  - Vision extraction retrofit (vision_extraction_v5 field)")
    print("  - New document type: agency_buyer_report")
    print("  - Continuation page convention")
    print("  - CAT_1 batch completion summary")
    print("  - Pending workstream: Sonnet + Kimi merge for database loader")


if __name__ == "__main__":
    main()
