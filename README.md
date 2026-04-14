# Exhaustive Extraction Pipeline

AI-powered structured extraction from 4,925 historical PDF documents (139 million words) documenting federal Native American land dispossession, 1880–1990.

## What This Does

Instead of using Retrieval-Augmented Generation (RAG) to search for "relevant" document chunks at query time, this pipeline **pre-processes every document** and extracts all structured information into a PostgreSQL database. The result is a queryable knowledge base of every person, organization, legal case, financial transaction, land parcel, and relationship mentioned across the entire corpus.

**Why not RAG?** A RAG system retrieves the top-K most relevant chunks for a query. It cannot trace a person across 30 years of documents, aggregate financial transactions to calculate total acreage lost, or discover that the same dispossession pattern recurs across different tribes and decades. Exhaustive extraction can.

## Current Status

### Survey of Conditions of the Indians in the United States (1927–1943)

The largest single extraction campaign to date: 26 of 48 volumes loaded (26,272 total pages, 15.4 million words) from the Senate subcommittee hearings that documented conditions across Indian country for over a decade. Extracted using Kimi K2.5 via Together AI with v4 schema (10 types). Remaining 23 volumes queued on UVA HPC.

**158,351 structured items extracted** from 26 volumes:

| Type | Count |
|------|------:|
| Entities | 81,681 |
| Financial transactions | 21,926 |
| Events | 18,400 |
| Relationships | 17,483 |
| Testimony | 5,492 |
| Correspondence | 4,933 |
| Legislative actions | 3,366 |
| Fee patents | 2,487 |
| Taxes | 1,880 |
| Mortgages | 703 |

Database: `survey_of_conditions`

### AIPRC Taylor Report — Vision Extraction

The American Indian Policy Review Commission's *Report on Indian Land Consolidation* (Taylor, 1976) is a heavily tabular document — 119 pages of tables recording land taken by legislation and eminent domain (1936–1974) and land purchased under Section 5 of the Indian Reorganization Act (1934–present), organized by BIA area office, reservation, and time period.

This document was extracted using **vision mode**, which renders PDF pages as images and sends them to Claude Sonnet's vision model. PyMuPDF cannot handle these tables — multi-column layouts with aligned numbers come out as jumbled text. Vision mode reads the actual page layout and extracts structured rows and columns.

**Results from two sections extracted so far:**

| Type | Count |
|------|------:|
| Tables | 43 |
| Table rows | 366 |
| Entities | 323 |
| Financial transactions | 213 |
| Events | 207 |
| Relationships | 156 |
| Legislative actions | 42 |
| Correspondence | 1 |

Key findings from Claude Opus analysis of the extracted data:
- Section 5 recovered **595,000 acres — 0.66% of the 90 million acres lost** through allotment
- The program was effectively dead after 1946 ($86,853 spent over 20 years in Period III), years before termination was formally declared
- **Klamath termination: 862,662 acres** — the single largest taking; **Fort Berthold / Garrison Reservoir: 175,700 acres**
- Two distinct functions: allotment repair (buying back alienated land on the Plains, 100% formerly Indian-owned in Oklahoma) vs. land base creation (new reservations in Nevada, Florida, Minnesota)

```bash
# Extract via vision mode
python3 extract_single_pdf.py "taylor tables.pdf" --vision --vision-batch 3

# Load into database
python3 load_vision_extractions.py vision_taylor_tables/ vision_taylor_section5/ --collection "AIPRC Taylor Report"
```

Database: `survey_of_conditions` (collection: "AIPRC Taylor Report")

### NARA RG 60 — DOJ Index Cards (Vision Extraction)

The Department of Justice record slips (NARA Record Group 60) are typed index cards that track every piece of correspondence about legal cases involving Indian land, taxes, and allotments. Each card documents who wrote to whom about what case on what date — a finding aid for the entire DOJ Indian lands litigation archive spanning 1920–1967.

These cards were unreadable as OCR text — the column layout and typed formatting produced garbled output from PyMuPDF. Vision mode with Claude Sonnet extracted them cleanly using a custom `--index-cards` prompt.

**24,368 structured items extracted** from 80 files (~2,300 pages):

| Type | Count |
|------|------:|
| Record slips | 12,969 |
| Legal cases | 4,811 |
| Persons (allottees, attorneys, officials) | 6,588 |

Key findings from the extracted data:
- **408+ named allottees** whose land was the subject of DOJ litigation
- **291 unique case file numbers** tracking tax recovery suits, quiet title actions, fraud cases, and allotment disputes
- **Geographic concentration in Oklahoma** — Osage (322 mentions), Choctaw (157), Cherokee (48), Creek (44), Five Civilized Tribes (105)
- **175 oil/mineral cases** — allottees' land exploited by Continental Oil, Carter Oil, Furman Oil, and others
- **Cases trackable across time** — U.S. v. Ralph Hughes followed through 18 cards from decree to $42,935.44 disbursement
- **166 dollar amounts** documenting judgments, settlements, and damages

The record slips serve as a guide into the DOJ's archival case files. Each file number (e.g., 90-2-11-473) points to a box of original correspondence, motions, and decrees at NARA. The patterns across 12,969 cards reveal the scope and structure of the DOJ's Indian lands litigation program — which allottees it fought for, which counties it sued, and what happened.

```bash
# Extract index cards
python3 extract_single_pdf.py document.pdf --index-cards --vision-batch 1

# Load into database
python3 load_index_card_extractions.py vision_index_cards_full/
```

Database: `index_cards`

### Crow Nation Corpus

- **386 documents processed** across 9 batches (Crow Nation archival materials) with v3 pipeline
- **43,000+ entities**, **6,800+ financial transactions**, **8,700+ relationships**, **7,900+ events** extracted
- **959 fee patents**, **5,057 correspondence records**, **2,432 legislative actions** (v3 structured types)
- Database: `crow_historical_docs`

### Kiowa/KCA Corpus

- **180 Kiowa documents re-extracted** through v3 pipeline, producing 598 fee patents, 1,355 correspondence records, 439 legislative actions
- Database: `historical_docs`

### Infrastructure

- Five-mode analysis interface with citation linking to the [Crow Nation Digital Archive](https://github.com/cwmmwc/crow-nation-digital-archive) and DEVONthink 4 (`x-devonthink-item://` URLs for local collections)
- HTML export with preserved document links in all analysis modes
- Production deployment on Google Cloud Run with auto-deploy on push to `main`
- Multi-database support: `crow_historical_docs` (Crow), `historical_docs` (Kiowa/KCA), `survey_of_conditions`, `full_corpus_docs` (planned)
- HPC extraction pipeline on UVA Rivanna/Afton (LawData allocation, 8x A100 80GB, vLLM + Kimi K2.5)
- UVA RC GenAI integration (Kimi K2.5 on H200 GPUs, free API access for UVA researchers)

### RC GenAI Streaming Fix (April 2026)

UVA's RC GenAI service (Kimi K2.5 on H200 GPUs) initially appeared to have persistent proxy errors — requests returned 502 errors roughly 99% of the time on production-length prompts. After days of failed extraction attempts and multiple emails to RC support about nginx timeouts, debugging revealed the actual problem: **RC GenAI had switched from returning standard JSON responses to Server-Sent Events (SSE) streaming format.** Our code expected a single JSON object; the server was sending `data: {...}\ndata: {...}\n` chunks. The JSON parser failed on the first `data:` prefix, and the exception was caught and reported as a generic error.

The fix was straightforward: parse the SSE stream by iterating over lines starting with `data: `, extracting the `content` field from each chunk's `delta` object, and concatenating them. The `run_vllm()` function in `extract_single_pdf.py` now handles both formats — regular JSON (from standard vLLM servers) and SSE streaming (from RC GenAI's Open WebUI proxy).

With the fix in place, RC GenAI processes 40,000-character extraction prompts in ~110 seconds on H200 GPUs — free, no GPU queue, no allocation needed. This is the primary extraction backend for the Survey of Conditions campaign.

**Lesson learned:** When an API that previously worked starts failing, debug the response format before assuming the server is broken. A `print(raw[:500])` would have found this in minutes instead of days.

### Index Cards Analysis Pipeline Fix (April 2026) — A Real Breakthrough

A historian-user query of "tell me about taxes" against the DOJ index cards database returned an analysis whose "named allottees of note" section listed eight different women all named **Stella**. A direct PostgreSQL check showed the database actually contains 6,588 person entries across 3,637 unique names — Stella is a normal early-twentieth-century name, ~0.85% of entries. The Stella cluster was a retrieval and synthesis bug stack, not the data.

Tracing the bug exposed five distinct problems in `ai_analysis_interface_v4.py`, all of which had been silently degrading every analysis run against the index cards database since the v4 schema was added:

1. **v4 records were fetched and dropped.** `build_discovery_context()` had no sections for `taxes`, `mortgages`, or `testimony`. The discovery flow fetched them into the `evidence` dict and the prompt builder silently ignored those keys. For Survey of Conditions, this meant 1,553 tax records and 634 mortgages were invisible to the synthesis layer.
2. **The Discovery tool had no `search_record_slips()` or `search_legal_cases()` function.** The DOJ index cards use a schema (`record_slips`, `legal_cases`) added by `load_vision_extractions.py` after the original tool was built. With no specialized search, the tool found slip content only indirectly through entity context fields — which is where the Stella cluster came from.
3. **The synthesis prompt promised data it didn't deliver.** The "YOU HAVE MULTIPLE TYPES OF EVIDENCE" list was statically hardcoded with TESTIMONY, TAXES, MORTGAGES, etc. regardless of which database was being queried, so the model was told it had categories that didn't exist for the data at hand.
4. **The synthesis padded gaps with prior knowledge.** When evidence was thin, Claude Opus would fall back on its training corpus and write paragraphs about the Burke Act, Curtis Act, and Cato Sells competency commissions — none of which came from the user's archive.
5. **Retrieval treated questions as strict-AND keyword matches.** Even after `search_record_slips()` was added, the FTS query used `websearch_to_tsquery()` which requires every space-separated word to appear in a single row. *"trace U.S. v. Pennington County"* parsed to `trace & u.s & v & pennington & county` — the token "trace" isn't in DOJ slip data, so the query returned **zero rows** even though the case is documented across dozens of slips.

The fix was layered:

- **Layer 0:** wired `taxes`, `mortgages`, and the new index card schema into the prompt builders, UI summaries, and Browse Raw Evidence tabs
- **Layer 1:** raised slip/case search limits from 100 to 500
- **Layer 2:** two-phase case-trace expansion. After Phase 1's keyword search, the discovery flow extracts the most-frequent `file_number`s and runs a Phase 2 query that pulls **every slip with those file_numbers** (top 20 file_numbers, capped at 30 slips each). Even if a keyword only matches one slip, Phase 2 drags in the full case chronology.
- **Layer 3:** PostgreSQL full-text search with `STORED` `tsvector` generated columns and GIN indexes on `record_slips` and `legal_cases`, plus an OR-based tsquery builder that strips command words like "trace", "tell", "show", "describe" and natural-language stopwords before building the query. Migration script: `migrate_fts_record_slips.sql`.
- **Layer 4:** synthesis prompts now build the evidence-type list dynamically from `db_stats` (so a database with zero testimony rows never sees TESTIMONY listed), plus three new caveats: *report only what's in the evidence below; cite a specific source filename for every claim; do not pad short evidence with speculation*. Plus an explicit instruction that the user is a historian who already knows the secondary literature.

**Verification — two queries that previously failed now produce real archival analyses:**

1. **"tell me about taxes"** → produces a chronologically organized analysis spanning 1922–1943, with concrete file numbers and dollar amounts ($10,746.97 across 43 judgments in four South Dakota counties), naming the Pennington County treasurer C.I. Leedy and tax-deed purchasers I.H. Chase and Ray E. Lemley, surfacing parallel campaigns in Franklin County NY (239 slips), Jackson County KS (109 slips), and Bryan County OK (55 slips).
2. **"trace U.S. v. Pennington County"** → produces a day-by-day chronology of 15+ individual allottee cases under 90-2-5 sub-numbers, traced from August 1935 bills of complaint through November 1935 filings, March 1936 amended complaints, the September 1936 decree pro confesso in the Twiss case, and the October 1937 aggregate judgment report.
3. **"forced fee patents"** → reconstructs the litigation aftermath of the forced-patent era, citing the smoking-gun phrase *"Without application by or consent of allottee and pursuant to so-called declaration of policy then in force"* from the Pearly DeRoin slip, surfacing 12+ named allottees with file and allottee numbers, the H.R. 10644 / H.R. 952 / H.R. 6393 legislative remedy thread, and a separate strand of forced-fee-patent litigation aimed at stripping Blackfeet mineral rights (Valerie Aspling Mathews case, 31 slips).
4. **"compare states"** → produces a state-by-state ranking by litigation volume (Oklahoma 695+ slips, Montana 289+, New York 239, California 154, Wisconsin 103+, etc.) with primary case types per state and analytical observations about jurisdictional patterns.

None of this was visible to the broken pipeline, which kept reporting "no records returned" while reaching for the same Stella cluster and the same Burke Act backstory. The fix took the analysis tool from generating misleading textbook summaries to generating evidence-grounded archival research.

Full post-mortem with code-level details: [`comparisons/INDEX_CARDS_ANALYSIS_FIX.md`](comparisons/INDEX_CARDS_ANALYSIS_FIX.md).

**Lesson learned:** When an analysis output looks suspicious (eight Stellas, no Johns), don't assume the synthesis layer is hallucinating. Check the retrieval first. The Stellas weren't fabricated — they were a faithful summary of a tiny biased sample, where the bias came from the search functions not being able to query the relevant tables and the keyword matcher requiring every word in the question to be present.

### Text Passage Discipline and Mandatory Gap-Flagging (April 2026)

After the index card pipeline fix landed, the same prompt-honesty discipline was extended to **text-based corpora** (Survey of Conditions, Crow Nation, Kiowa/KCA, full corpus). Index cards have a structural advantage: each slip is one short atomic record with a subject line you can quote exactly and a file_number you can cite. Narrative text corpora are subtly harder — the model has 100+ paragraphs of OCR'd hearing testimony to work with, and the temptation to *paraphrase* a witness's words "as if it were your own framing" is much stronger than the temptation to invent slip data. Without explicit constraints, Survey analyses tended to slide into smooth narrative summary that blurred the line between (a) direct quotation from the document text, (b) AI-extracted entity records that summarize what some passage said, and (c) the model's own analytical voice.

Three new caveats were added to the **Discovery**, **Hybrid**, and **Corpus Synthesis** prompts in `ai_analysis_interface_v4.py`:

1. **TEXT PASSAGE DISCIPLINE.** When the model uses a quotation from a document text passage, it must format it as a markdown block quote (`> ...`) with the source filename in the attribution immediately after. No paraphrasing-as-framing — either quote it or explicitly summarize "the [filename] hearing records that…". For Corpus Synthesis specifically, where the model only sees AI-compressed summaries (not raw text), the rule becomes: never present summary text as if it were a verbatim quotation from the underlying document.
2. **DISTINGUISH EVIDENCE TYPES IN PROSE.** Use clear signal phrases so the reader can tell what kind of evidence each claim rests on: *"the document text states…"* (a primary text quote), *"the AI extraction recorded a [type] entry showing…"* (an AI summary of some passage), and *"across N records the data shows…"* (an aggregate count). Never blur a database aggregate with a direct quotation, and never present an extracted entity as if it were a verbatim quote.
3. **MANDATORY "What this archive does not tell you" CLOSING SECTION.** Required on every analysis, every database, every mode. Must name *specific* gaps — e.g. *"the data does not include the final decree in U.S. v. X County"* not *"outcomes are not documented."* This is methodology, not weakness — it tells the historian which gaps to fill from other archival sources. The Corpus Synthesis version of this rule additionally instructs the model to flag when a topic is poorly served by the SUMMARY MODE specifically (i.e. when the summaries probably compressed out detail that is in the underlying documents but isn't visible here).

A parallel set of caveats was already in place for the same three prompts: *report only what's in the evidence* (no Burke Act, Curtis Act, Dawes Act, Cato Sells competency commissions from training data); *every claim must cite a source*; *do not pad short evidence with speculation*; *the user is a historian who already knows the secondary literature*.

**Verification — Discovery mode.** A `tell me about the effects of fee patents and taxes` query against Survey of Conditions in Discovery mode now produces:

- Direct block quotes from hearing testimony with explicit source attribution (the Kickapoo dispossession-by-tax-purchase passage, the Wisconsin allottee whose taxes accumulated unbeknownst to her, the Yakima/Klamath irrigation-lien-vs-fee-patent conflict, the Pueblo Cayuga land-sale historical reference)
- Visible signal phrases distinguishing direct text quotes from AI-summarized atoms from aggregate counts ("the document text states…" vs "the AI extraction of the corresponding tax record confirms…" vs "the AI extraction of relationship entries provides several aggregate figures…")
- A 10-item "What This Archive Does Not Tell You" section listing specific gaps: county tax sale records, acreage lost specifically to tax delinquency, county-level assessment rolls, the text of *Choate v. Trapp*, the outcome of the Kickapoo taxation question, North/South Dakota and Wisconsin tax records, county-fiscal-pressure-to-restriction-removal correspondence, individual-level tracing from fee patent to tax sale to new owner, post-1932 outcomes under the IRA, dollar amounts of taxes actually paid by Indians

**Verification — Corpus Synthesis mode.** The same `tell me about the effects of fee patents on american indian land` query against the Survey of Conditions corpus in Corpus Synthesis mode (after extending the same caveats to `analyze_corpus()`) now produces:

- **Provenance-tagged claims throughout.** Every factual assertion is framed as *"the Doc N summary records that…"* — the reader can never confuse a verbatim witness quote with an AI-compressed summary phrasing. Pre-fix outputs paraphrased witnesses ("Edgar B. Meritt acknowledged…"); post-fix outputs make the AI compression explicit ("**The Doc 29 summary records that** Assistant Commissioner Edgar B. Meritt acknowledged…").
- **A three-section conclusion** (What the Documents Prove / What the Documents Suggest / What This Corpus Does Not Tell You) where every "Suggest" claim is explicitly hedged. Example: *"The fee patent system functioned as a coordinated mechanism of wealth transfer from Indian to non-Indian ownership… **However, the corpus does not contain explicit evidence of a single coordinated conspiracy**; rather, it documents a policy environment in which multiple actors independently exploited the same structural vulnerability."*
- **A "What This Corpus Does Not Tell You" section that explicitly flags summary-mode limitations.** The post-fix Corpus Synthesis output includes items like *"The 2,317 fee patents in the database likely contain far more granular information than the summaries convey"* and *"The 4,283 correspondence records and 634 mortgages in the database almost certainly contain far more granular evidence of individual dispossession than is visible in the summaries. The summaries necessarily compress thousands of individual transactions into pattern descriptions."* The model is now telling the historian, explicitly, *"I'm working from compressed summaries; for granular evidence drop into Discovery mode."* That's the SUMMARY MODE LIMITATION caveat doing its work.
- **Other actionable gap items:** the text of key policy directives (April 17, 1917 letter), individual-level tract data, post-1932 outcomes for individuals named in 1928–1931 testimony, tribal-specific acreage losses attributable specifically to fee patents (vs other mechanisms), legal outcomes of challenges to forced fee patents, the role of state courts in facilitating or resisting dispossession, comparative data by blood quantum, any systematic federal remediation effort beyond the underfunded IRA Section 5 program.

Compare to a pre-fix April 1 corpus synthesis on the same Survey corpus: that output had real doc citations and concrete numbers (it wasn't broken), but it paraphrased every witness, blurred extracted entity records into the same narrative voice as direct testimony, and ended without a methodology gap-flagging section. The new discipline is what you actually want from a tool described as *"a way to navigate my archive which is too big to read on my own"* — a structured map of where the evidence lives, with direct quotes for the load-bearing passages, explicit labeling of provenance, and an honest map of what's missing so you know which gaps to fill from other sources.

The full post-mortem on the index card analysis fix is at [`comparisons/INDEX_CARDS_ANALYSIS_FIX.md`](comparisons/INDEX_CARDS_ANALYSIS_FIX.md).

**Lesson learned:** Honest gap-flagging is a research virtue, not a software shortcoming. A good monograph footnote is "the X archive does not preserve Y; for Y see Z." Building that habit into the prompt produces analyses you can actually cite from instead of having to manually verify every claim.

### Unified DOJ Index Cards Database (April 2026)

By April 11, 2026, both extraction pipelines had completed end-to-end runs on the full 87-PDF NARA RG 60 DOJ record slip collection: Sonnet 4.6 vision (`vision_index_cards_full/`, ~$130) and Qwen2.5-VL-72B on HPC (`qwen_vl_index_cards_full/`, free). The two extractions disagree in opposite directions, and the differences turn out to be complementary rather than redundant: Sonnet captures 65% more named persons (including secondary mentions like clerks, county treasurers, judges); Qwen produces 99% more `legal_cases` entries (a per-mention audit trail of correspondence about each case); on slips themselves they roughly tie but each finds ~900 slips the other missed.

To make both extractions queryable as a single research database without duplicating slip rows or pushing query-time dedup burden onto every reader, the two were merged into `unified_index_cards` — a new PostgreSQL database with a normalized 6-table schema that exposes provenance as a column tag rather than as parallel duplicate rows. The merge logic does **slip-level matching** on `(source_pdf, file_number, date, correspondent)`, prefers Sonnet when both extractions found a slip (it has the broader 17-field schema), and uses **content-based pairing** to resolve a subtle complication: 6 of the 87 source PDFs share inner filenames across DOJ boxes, which Sonnet's directory naming scheme cannot disambiguate. The pairing logic counts how many slip keys each Qwen sibling shares with Sonnet and picks the highest-overlap match — overlap ratios were 3-7x higher for the correct pair than for the wrong ones in every case.

**Final unified database counts:**

| table | rows | meaning |
|---|---|---|
| documents | 87 | one per source PDF, full relative path as ID |
| **slips** | **17,211** | 33% more than either extraction alone (Sonnet: 12,969, Qwen: 13,887) |
| cases | 2,108 | one per unique `file_number`, with both Sonnet and Qwen aggregate counts |
| persons | 4,359 | deduped on normalized name; tracks variants, roles, file_numbers, sources |
| slip_cases | 17,087 | many-to-many join |
| slip_persons | 7,032 | many-to-many join |

**Slip-level dedup breakdown:**

| extraction_source | rows | what it means |
|---|---|---|
| `sonnet+qwen` | 9,645 | both extractions agreed on this slip; Sonnet's row stored |
| `sonnet-only` | 3,324 | Sonnet found this slip; Qwen missed it or read it differently |
| `qwen-only` | 4,242 | Qwen found this slip; from a Qwen-only PDF or a card Sonnet missed |

The high agreement count (~9,645) shows both models find the bulk of slips identically. The ~3,300 sonnet-only and ~4,200 qwen-only rows are the genuine discrepancies — and they're the slips you'd lose by picking either extraction alone.

The merge also stores both `sonnet_case_mention_count` and `qwen_case_mention_count` per case — Qwen's per-mention behavior becomes an actually-useful research variable (correspondence volume per case) without requiring duplicate slip storage. A `cases_at_file_number` column flags master classifications: 90-2-01 (Indians--Legislation) has 165 distinct bills under one master file number; 90-2-5-49 (Fort Peck) has 32 distinct allottee-specific sub-suits under one campaign file. The metric is computed from Sonnet's deduped `legal_cases` extraction, which is more reliable than counting paraphrase variants in slips.

Full design, sample SQL, interpretation rules, and post-mortem at [`comparisons/UNIFIED_INDEX_CARDS_MERGE.md`](comparisons/UNIFIED_INDEX_CARDS_MERGE.md). Schema in [`schema_unified_index_cards.sql`](schema_unified_index_cards.sql); merge loader in [`merge_index_cards.py`](merge_index_cards.py).

**Lesson learned:** The standard "merge two datasets by picking one as canonical" approach assumes the datasets are noisy versions of the same ground truth. When they're different *kinds* of correct (Sonnet captures secondary mentions; Qwen captures correspondence audit trails), the merge needs to preserve both signals as separate columns on a deduped row. Picking one extraction wholesale loses the complementary data; storing both as parallel duplicate rows pushes query-time dedup burden onto every reader. The right design exposes both contributions on a canonical row.

## Repository Contents

| File | Description |
|------|-------------|
| `poc_pipeline_chunked_v3.py` | **v3 extraction pipeline** — 10 entity types + fee patents, correspondence, legislative actions. Supports `--force` for re-extraction preserving doc IDs and summaries |
| `poc_pipeline_chunked_v2.py` | v2 extraction pipeline using Anthropic API (10 entity types) |
| `poc_pipeline_v2_local.py` | v2 extraction pipeline using Ollama (for HPC deployment, zero API cost) |
| `ai_analysis_interface_v4.py` | Streamlit query interface with four analysis modes, citation linking, v3 data support |
| `enrich_summaries.py` | Generate per-document analytical summaries for corpus-wide synthesis (supports Batch API) |
| `load_vision_extractions.py` | Load vision-mode extractions (tables + standard types) into PostgreSQL |
| `process_crow_batch.sh` | Batch staging helper script |
| `dedup_entities_phase1.py` | Entity deduplication: case normalization + title stripping |
| `compare_claude_vs_local_models.py` | Claude vs. open-source model comparison (Ollama, vLLM, Together AI, Fireworks, Groq) |
| `generate_display_titles.py` | AI-generated archival display titles for all documents |
| `devonthink_uuids.json` | DEVONthink 4 UUID mapping for local document linking (Kiowa/KCA) |
| `schema.sql` | PostgreSQL database schema (v3) |
| `comparisons/` | Baseline and comparison outputs (v2 vs v3 extraction, model comparisons) |

## The Pipeline

The pipeline has four stages. The loading scripts automatically trigger summarization, so in practice you run extract → load and the rest happens.

```
Extract ──→ Load ──→ Summarize (auto) ──→ Analyze
  │            │          │                   │
  │            │          │                   └─ Streamlit app (Opus/Sonnet/Kimi)
  │            │          └─ enrich_summaries.py (runs automatically after load)
  │            └─ load_survey_extractions.py or load_vision_extractions.py
  └─ extract_single_pdf.py (text mode or --vision mode)
```

### Step 1: Extraction

The pipeline offers two extraction modes. The choice depends on the document:

| Mode | Flag | Best For | Model | How It Works |
|------|------|----------|-------|-------------|
| **Text** | (default) | Narrative prose — testimony, correspondence, case histories | Kimi K2.5 | PyMuPDF extracts OCR'd text → 40K-char chunks → LLM returns structured JSON |
| **Vision (tables)** | `--vision` | Tables, ledgers, allotment schedules, financial data | Claude Sonnet | Pages rendered as images → sent to Claude vision → structured JSON with tables |
| **Vision (index cards)** | `--vision --index-cards` | DOJ record slips, structured index cards | Qwen2.5-VL-72B (HPC) | Pages rendered as images → sent to Qwen-VL vLLM server → record_slips/legal_cases/persons JSON |

**When to use which:** If the document is mostly running text (congressional hearings, correspondence files, litigation records), use text mode with Kimi — it finds more fee patents and dispossession evidence than any other model. If the document has tables with columns and aligned numbers (land transaction schedules, financial reports, census-style data), use vision mode with Claude Sonnet — PyMuPDF turns tables into jumbled text, but Claude vision reads the actual page layout. If the document is a stack of typed DOJ index cards, use Qwen-VL on HPC with the `--index-cards` schema.

**Sonnet vs Qwen-VL on index cards.** Both models were tested on the DOJ record slip collection with the same `--index-cards` prompt. The 20-page test PDF was sparse (1.4 slips/page) and showed Qwen-VL tying Sonnet on slips, beating it on cases, and trailing on persons. A larger 2-PDF apples-to-apples on 66 dense pages (~11 slips/page) painted a more nuanced picture:

| Combined across 66 pages, 744 slips | Sonnet | Qwen-VL | Δ |
|--|--|--|--|
| Record slips | 763 | 744 | tied (Sonnet +2.5%) |
| Legal cases | 275 | 523 | **Qwen +90%** |
| Persons | 462 | 272 | **Sonnet +70%** |

The slip extraction is equivalent. The cases and persons differences appear to be about deduplication strategy: Qwen-VL extracts every case *mention* as a separate entry (closer to a per-mention audit trail) while Sonnet consolidates to unique cases; conversely Sonnet captures every named person including secondary mentions while Qwen-VL focuses on case principals. Both behaviors are useful for different research questions.

For the full 87-PDF collection: Sonnet has already been run end-to-end with the index card schema (output at `vision_index_cards_full/`). Qwen-VL is also being run on HPC for the corpus-scale comparison, with no incremental cost since the GPU hours are free. Kimi K2.5 vision is not competitive — it puts analysis into a reasoning field instead of producing structured JSON output and fails on 45% of pages. See `comparisons/MODEL_COMPARISON_SUMMARY.md` §8 for the full breakdown.

```bash
# Text mode (default) — narrative documents
python3 extract_single_pdf.py hearing.pdf --chunked --vllm-url http://server:8000

# Vision mode — tabular documents
python3 extract_single_pdf.py report.pdf --vision --vision-batch 3

# Vision mode — specific pages only
python3 extract_single_pdf.py report.pdf --vision --vision-pages 64-70
```

Vision mode automatically reduces image DPI for pages that exceed Claude's 5MB limit. It extracts the same 10 structured types as text mode, plus a **tables** type that captures tabular data with column names and row values.

**Example:** The 119-page AIPRC Taylor Report (1976) — entirely tabular — was extracted via vision mode: 40 batches, 2,128 items, 75 tables with 686 queryable rows, zero failures, in 51 minutes.

### Index Card Extraction (extract_single_pdf.py --index-cards)

For DOJ record slips (NARA RG 60) and similar index cards, the pipeline offers a specialized `--index-cards` mode with a custom prompt tailored to the card format. These are typed cards that track correspondence about legal cases involving Indian land, taxes, and allotments — each card documents who wrote to whom about what case on what date.

Each card has a consistent structure:
- **Header**: File number (e.g., 90-2-5-49) | Jurisdiction (e.g., Montana) | Date
- **Correspondent**: U.S. Attorney, First Asst. Secretary, etc.
- **Re: line**: Case name and description of action
- **Footer**: Division routing, processing dates, clerk initials

```bash
# Extract index cards via vision mode
python3 extract_single_pdf.py document.pdf --index-cards --vision-batch 1

# Extract specific pages
python3 extract_single_pdf.py document.pdf --index-cards --vision-pages 1-20
```

The custom prompt extracts three structured types: `record_slips` (one per card), `legal_cases` (unique cases referenced), and `persons` (allottees, attorneys, officials). Dates are converted from the card format (3-17-36) to YYYY-MM-DD.

**Test results:** 20 pages of 1935 DOJ record slips extracted in 141 seconds — 28 record slips, 20 legal cases, 16 persons identified. The extraction tracked U.S. v. Ralph Hughes through 18 cards spanning January to October 1935, capturing the full lifecycle from decree through appeal debate to a $42,935.44 disbursement.

**Case name deduplication:** A single case appears with many name variants across cards (e.g., "U.S. v. Ralph Hughes" appears 11 different ways across 18 cards). The file number (90-2-5-10) is the unique identifier — a post-extraction dedup step normalizes case names to one canonical form per file number.

**Scale:** The full RG 60 index card collection is 87 PDFs, ~2,400 pages. At ~7 seconds per page on Claude Sonnet, the full extraction takes about 5 hours and costs ~$35. Qwen2.5-VL-72B on HPC is being tested as a free alternative.

### Step 2: Load

```bash
# Load text-mode extractions (Survey of Conditions, etc.)
python3 load_survey_extractions.py --db survey_of_conditions

# Load vision-mode extractions (Taylor Report, etc.)
python3 load_vision_extractions.py vision_taylor_full/ --collection "AIPRC Taylor Report"
```

### Step 3: Summarize (automatic)

Both loading scripts automatically run `enrich_summaries.py --from-extraction --model sonnet` after loading. This generates per-document analytical summaries needed for Corpus Synthesis mode in the Streamlit app. Summaries can also be generated manually with different models:

```bash
python3 enrich_summaries.py --db survey_of_conditions --from-extraction --model opus   # deepest
python3 enrich_summaries.py --db survey_of_conditions --from-extraction --model sonnet  # default
python3 enrich_summaries.py --db survey_of_conditions --from-extraction --model kimi    # cheapest
```

#### What the summary step actually does

The summary is not generated from the raw document text. It is generated from a **curated sample** of the structured extraction data already in the database. For a 221-page document with 950 extracted items, the model sees approximately 400 representative items:

| Type | Sample Size | Selection Strategy |
|------|------------|-------------------|
| Fee patents | up to 75 | Evenly spaced across document, prioritizing records with the most populated fields |
| Testimony | up to 50 | Sorted by longest key_claims first |
| Correspondence | up to 40 | Evenly spaced across document |
| Legislative actions | all | Usually not too many per document |
| Financial transactions | up to 40 | Evenly spaced, prioritizing records with amounts |
| Taxes | up to 40 | Evenly spaced |
| Mortgages | all | Usually not too many |
| Person entities | up to 60 | Distinct names, prioritizing longest context descriptions |
| Events | up to 40 | Evenly spaced, prioritizing ones with dates |

Each category is capped at 20,000 characters of JSON. The total prompt is ~8,000–10,000 tokens. The model produces a 200–350 word summary in plain prose: date range, document type, key individuals, specific claims with dollar amounts and acreages, legal mechanisms, and what the document reveals about dispossession.

#### What Corpus Synthesis mode can and cannot see

Corpus Synthesis is the only analysis mode that relies on summaries. It works by concatenating every document's 200–350 word summary and sending the full set to the analysis model in a single prompt — so the AI can trace patterns across the entire corpus.

In practice, the summaries preserve a remarkable amount of specificity. A Corpus Synthesis query about fee patent opposition produced an analysis naming individual allottees (Margaret Tayiah, Claude McCauley, Harry Stubbs), exact statistics (613 Yankton patentees, 550 disposed of land, 84 of 140 at Crow sold everything), and granular details (Nez Perce full-bloods investing in mortgages on white men's farms). The sampling algorithm prioritizes the richest records and spreads them across the full span of each document, so the summaries are dense with specifics — names, dollar amounts, acreages, legal citations.

The limitation is more subtle: the synthesis model can only work with what the summary captured. It cannot discover things the summary didn't mention. For a 221-page document with 950 extracted items, the summary was built from ~400 sampled items, then compressed to 200–350 words. Most of the detail survives, but:

- **Exhaustive lists are compressed.** A fee patent schedule listing 50 Kaw allottees may have a dozen names in the summary, not all 50. The synthesis model can identify patterns among those named but cannot count the total.

- **Cross-document individual tracking depends on sampling.** If the same attorney appears in 5 documents but was only sampled in 3 of their summaries, the synthesis model sees a pattern across 3 documents, not 5.

- **The original documentary language is paraphrased.** "Land sold. Money spent. Nothing left. Not located now." — that devastating bureaucratic compression of a human life may survive as a quoted fragment in the summary, or may be paraphrased as "allottee sold land and was left destitute."

The other three analysis modes do not have this limitation. **Discovery** searches the actual database — all 950 items, every allottee name, every dollar amount, directly queryable. **Deep Read** sends the full document text to the AI. **Discovery → Deep Read** combines both: database search to find relevant documents, then full text analysis of the ones you select. Only Corpus Synthesis trades some precision for the ability to see the entire corpus at once.

### Step 4: Analyze

```bash
streamlit run ai_analysis_interface_v4.py
```

The Streamlit app has four analysis modes. Each sees different data, which means each is suited to different kinds of questions. Choosing the right mode matters — the same question can produce dramatically different results depending on which mode you use.

#### Choosing the right mode

A concrete example: the 221-page CCF 56074 document contains a Kaw allottee schedule listing 40+ named individuals with their blood quantum, age, and disposition of property — Abby Conn, Ralph Pepper, Forrest Chouteau, Henry Wy-e-nah-she, Robert Sands, the Bellmard family, and dozens more. Kimi extracted 268 allottees from the full document. Here's what each mode sees:

| Mode | What it sees | What it finds for "list everyone who lost their land" |
|------|-------------|------------------------------------------------------|
| **Discovery** | The actual database: all 268 fee patent records, every name, every amount | All 268 allottees by name, queryable and sortable |
| **Deep Read** | The full document text (all 221 pages sent to the AI) | Every name in the original text, with the original language ("Land sold. Money spent. Nothing left.") |
| **Discovery → Deep Read** | Database search results + full text of selected documents | All 268 from the database, plus the AI reads the original text for context and nuance |
| **Corpus Synthesis** | 200–350 word summaries of every document in the corpus | 4 names (Margaret Tayiah, Claude McCauley, Harry Stubbs, Samuel Charger) — the summary compressed 268 allottees to a handful of examples |

#### The four modes in detail

**Discovery** — Searches the actual extraction database across all documents. Best for questions that require **completeness**: "list all fee patent allottees," "which attorneys appeared most often," "total acreage sold by reservation." The AI sees every extracted record — all entities, fee patents, financial transactions, testimony, correspondence, legislative actions, taxes, and mortgages. This is the only mode that can answer counting and aggregation questions reliably, because it queries the full structured data rather than summaries.

**Deep Read** — Sends the complete text of one document to the AI for close analysis. Best for questions that require **the original language and full context**: "what did John Clendening actually say about fee patents?", "how did the field agent describe Barclay Delano's situation?" The AI reads the actual document, not a summary, so it can quote directly and catch nuances that extraction might have missed. Limited to one document at a time.

**Discovery → Deep Read** — The most powerful mode. First runs a Discovery search to find relevant documents and data across the corpus, then sends the full text of selected documents to the AI along with the cross-corpus database results. Best for questions that require **both breadth and depth**: "find all documents mentioning the Bellmard family, then analyze what happened to them." Produces the richest analysis because the AI sees both the structured data (for completeness) and the original text (for language and context).

**Corpus Synthesis** — Concatenates every document's summary and sends the full set to the AI in a single prompt. Best for questions about **patterns, trends, and arguments that span the entire corpus**: "what mechanisms drove dispossession across different reservations?", "how did field officers view the fee patent policy?", "what changed between the 1920s and 1930s?" This is the only mode that sees the entire corpus at once — but it sees it through summaries, not raw data. It excels at identifying structural patterns and making arguments across dozens of documents simultaneously. It should not be used for completeness questions ("list every person who...") because the summaries compress hundreds of names into a few representative examples.

All four modes let you choose the analysis model: Claude Opus 4.6 (deepest analysis), Claude Sonnet 4.6 (faster, cheaper), or Kimi K2.5 (Moonshot AI, best value).

### Extraction Types

The pipeline extracts 10 types of structured information from each document. The v4 prompt (current default) extracts all 10; the v3 prompt extracts the first 7.

#### Entities

Entities are named things — the full cast of characters, places, and instruments in the documents. Each entity has a name, a type, and a context field that briefly describes who or what it is and why it matters.

| Entity Type | What It Captures | Example |
|-------------|-----------------|---------|
| **person** | Named individuals — allottees, officials, attorneys, witnesses, family members | V. Stinchecum, Superintendent of Kiowa Agency |
| **organization** | Agencies, companies, tribes, committees, courts | Bureau of Indian Affairs, Campbell Farming Corporation |
| **location** | Places — reservations, towns, counties, states, specific sites | Crow Reservation, Anadarko, Oklahoma |
| **land_parcel** | Specific described land — section/township/range, allotment numbers | Allotment 2237, Section 12 T1S R32E |
| **legal_case** | Named lawsuits, court actions | Dillon v. Antler Land Co. of Wyola |
| **legislation** | Named bills, acts, treaties, executive orders | Crow Act of 1920, S-716 |
| **acreage_holding** | Land ownership with quantities | Homer Scott: 90,000 acres |

Entities are the broadest category by design — they catch everything that has a name. The other 9 types capture *what happened* with structured fields. Entities capture *who and what was involved*. You need both: an entity tells you George Peters exists; a fee_patent record tells you his land was patented, sold, and to whom.

#### Structured Record Types

These capture specific kinds of historical evidence as structured records with defined fields. Each record type was designed to answer particular research questions directly via database queries.

| Type | Key Fields | Example | Version |
|------|-----------|---------|---------|
| **events** | type, date, location, description | March 18, 1940 — House passed H.R. 5477 | v2 |
| **financial_transactions** | type, amount, payer, payee, date | $32,691.20 oil lease bonus payment, BIA to Crow Tribe | v2 |
| **relationships** | subject, type, object, context | Stanton represented Crow Tribe as tribal attorney | v2 |
| **fee_patents** | allottee, allotment_number, acreage, patent_date, mechanism, buyer, sale_price, attorney, mortgage | George Peters, Allotment 1292, 840 acres, sold to Stanton | v3 |
| **correspondence** | sender, sender_title, recipient, recipient_title, date, subject, action_requested, outcome | Murray to BIA Commissioner, 1947-06-15, re: Peters fee patent | v3 |
| **legislative_actions** | bill_number, sponsor, action_type, date, vote_count, committee, outcome | S. 1385 introduced by Murray, 1947-06, enacted as Private Law 68 | v3 |
| **testimony** | witness, witness_title, hearing, committee, location, date, subject, key_claims, questioner | Stinchecum testified at Anadarko, 1930: only 1 of 60 fee patent recipients retained their land | v4 |
| **taxes** | taxpayer, land_description, tax_type, amount, year, status, county | Delinquent property tax, Hughes County, 1921, tax deed issued | v4 |
| **mortgages** | borrower, lender, amount, land_description, acreage, date, interest_rate, status | Ben Told, mortgage $6,500, land leased for five years, active | v4 |

### Why These Types Matter

**Fee patents** are the atomic unit of land dispossession. The v2 pipeline scattered fee patent data across `person`, `land_parcel`, `financial_transaction`, and `relationship` entities — forcing the AI to reassemble it at query time. The v3 `fee_patent` type links allottee, allotment number, acreage, patent date, trust-to-fee mechanism (private bill, administrative action, application, certificate of competency), subsequent buyer, sale price, facilitating attorney, and any mortgage into a single record. This enables direct SQL queries like "total acreage patented by decade" or "which attorneys appeared in the most fee patent chains."

**Correspondence** captures the bureaucratic network: sender, recipient, titles/positions, date, subject, action requested, and outcome. Designed to link with Pipeline B (1.4M BIA index cards from the National Archives) via sender/recipient/date matching. This is the cross-corpus integration layer described in the HAVI Level I proposal.

**Legislative actions** track bills through their lifecycle: introduced, reported, amended, passed, vetoed, enacted — with sponsors, vote counts, and committee assignments. The v2 `legislation` entity captured bill names but not their trajectories. The Murray synthesis (which reconstructed 5 major bills across 30+ documents from summaries alone) demonstrated how much analytical leverage structured legislative data provides.

**Testimony** (v4) captures sworn statements from congressional hearings — the witness, their title, the hearing context, and a summary of their key claims. The Survey of Conditions hearings (1927-1934) contain hundreds of witnesses testifying about the effects of fee patents across Indian country. Without a structured testimony type, these statements were lost inside generic entity and event records.

**Taxes** (v4) capture the tax trap as a mechanism of dispossession. Once land was patented, it became taxable. Many allottees could not pay property taxes on land they had never farmed, leading to tax sales and tax deeds. The structured record captures taxpayer, tax type, amount, year, delinquency status, and county — enabling systematic analysis of tax-driven land loss.

**Mortgages** (v4) capture another dispossession mechanism. Allottees frequently mortgaged land immediately after receiving fee patents, often at unfavorable terms. The structured record captures borrower, lender, amount, interest rate, and outcome (foreclosed, paid, default). In the existing extractions, mortgage data appeared 126 times but was scattered across entities, events, financial transactions, and fee patent records with no structured home.

### Analysis Interface (ai_analysis_interface_v4.py)

Streamlit web interface with four modes:

- **Discovery** — Search the entity database across all documents, including v3 structured types (fee patents, correspondence, legislative actions). Evidence browser with tabs for each data type. Best for broad research questions spanning multiple archival collections.
- **Deep Read** — Send a complete document to the AI for close analysis. Replicates single-document depth of DevonThink AI.
- **Discovery → Deep Read** — Run Discovery to find relevant documents, select which ones to deep-read, then send full texts plus cross-collection entity data to the AI. Produces the richest analysis.
- **Corpus Synthesis** — Send analytical summaries of ALL documents to the AI for corpus-wide pattern analysis. No context window limit — the AI sees every document in the collection. Requires summaries to be generated first (see below).

### Verification and Source Checking

The pipeline produces analysis that is grounded in specific evidence — named witnesses, dollar amounts, acreages, dates — but every number passes through two AI layers before reaching the researcher: extraction (Kimi or Claude reading the PDF) and synthesis (Claude Opus assembling extracted data into an argument). Neither layer is infallible. Verification is essential for any claim that will appear in published work.

**The verification chain:**

A claim like "99% of Oneida allottees were placed on tax rolls" traces back through:

1. **Visualization or synthesis** — cites "Doc 13" as the source
2. **Document summary** — the Opus-generated summary mentions Oneida tax rolls
3. **Testimony record in database** — a structured record with witness "William Skenandore," subject "Oneida fee patents," and key_claims containing the 2,700/21 figures
4. **Per-chunk extraction JSON** — the specific chunk file where Kimi extracted this testimony
5. **The original PDF** — the actual page of congressional testimony where Skenandore spoke

Steps 1-4 are queryable in the database and the extraction output files. Step 5 requires going to the source document. The goal is to make every step clickable — from synthesis to PDF — so verification takes seconds, not hours.

**What can go wrong at each layer:**

- **Extraction errors** — The AI misreads an OCR-degraded number ($18,455 vs $18,445), attributes testimony to the wrong witness, or conflates two separate statements into one record. OCR quality varies widely across the corpus.
- **Synthesis errors** — Claude correctly has access to the extracted data but draws an incorrect inference, miscalculates a percentage, or presents a claim as proven when the evidence only suggests it.
- **Category confusion** — Kimi sometimes creates duplicate records across categories (e.g., the same land sale appears as both a fee_patent and a financial_transaction). This can inflate counts if not deduplicated.
- **Truncation gaps** — Documents exceeding ~180K tokens are truncated for summary generation. Evidence from later pages may be absent from the summary even if it was captured in the extraction.

**How to verify:**

- **Spot-check the highest-stakes claims.** Any number that would appear in a publication — especially acreages, dollar amounts, and percentages — should be traced back to the source PDF.
- **Query the database directly.** Use SQL or the Discovery mode to find the specific testimony, fee patent, or tax record underlying a claim. The structured records include the document they came from.
- **Compare extraction models.** Running the same document through both Kimi and Claude and comparing the outputs reveals what each model missed or added. Discrepancies flag areas for manual review.
- **Check the per-chunk JSON files.** Each chunk's extraction is saved separately in the output directory. If a claim seems wrong, find the chunk file and read the raw extraction alongside the corresponding section of the PDF.
- **Use the "Gaps in the Record" section.** The Corpus Synthesis prompt instructs Claude to identify what the evidence does NOT prove. This section is often the most important for a historian — it tells you where to be cautious.

**The fundamental limitation:**

This pipeline does not replace reading the documents. It replaces the impossible task of reading 5,000 documents and holding them all in memory simultaneously. The extraction and synthesis make the corpus navigable and queryable. But any specific claim derived from AI analysis should be verified against the source before it enters published historical argument. The pipeline is a research tool, not a substitute for the historian's judgment.

**Citation linking:** All modes convert document references in AI output to clickable links. For the Crow corpus, links go to the [Crow Nation Digital Archive](https://github.com/cwmmwc/crow-nation-digital-archive). For collections without an archive website (e.g., Historical Documents), links use DEVONthink's `x-devonthink-item://` URL scheme to open source documents directly in DEVONthink 4. The UUID mapping is stored in `devonthink_uuids.json` and loaded automatically per database. Corpus Synthesis links `[Doc N]` references (including ranges like `[Doc 213–225]`); Discovery, Deep Read, and Hybrid link filename citations. A Sources Cited appendix is appended to corpus synthesis output.

**Save/download:** All analysis modes include a download button that saves the AI output as a styled HTML file with preserved document links (archive URLs or DEVONthink links).

**Corpus Synthesis prompt:** Instructs the AI to surface cross-document patterns, ground every claim in specific evidence (names, allotment numbers, acreages, dollar amounts, bill numbers, dates), show connections across time and place, quantify where possible, and conclude with three sections: What the Documents Prove, What the Documents Suggest, and Gaps in the Record.

```bash
streamlit run ai_analysis_interface_v4.py
```

Requires: PostgreSQL with extracted data, Anthropic API key.

### Document Summary Enrichment (enrich_summaries.py)

Generates a 200-350 word analytical summary of each document using Claude Opus. Summaries capture document type, key parties, dates, specific claims/actions, legal mechanisms, financial details, and evidentiary value. Stored in the `summary` column of the documents table.

```bash
export ANTHROPIC_API_KEY="your-key"
python3 enrich_summaries.py                                # summarize all unsummarized docs (default: crow_historical_docs)
python3 enrich_summaries.py --db survey_of_conditions      # target a specific database
python3 enrich_summaries.py --from-extraction --force      # summarize from extraction data (no truncation)
python3 enrich_summaries.py --limit 5                      # test on 5 documents first
python3 enrich_summaries.py --force                        # re-summarize all documents
python3 enrich_summaries.py --batch                        # use Batch API (50% cost savings)
python3 enrich_summaries.py --batch --force                # re-summarize all via Batch API
```

**Why summaries?** 386 summaries x ~300 words = ~100K tokens — fits in a single Claude call. 386 full documents x ~50K words each = impossible in any context window. Summaries are the bridge between exhaustive extraction and corpus-wide reasoning.

**Two summary modes:**

- **Full-text mode** (default): sends the raw document text to Claude Opus. Works well for documents under ~350 pages. Larger documents are truncated to fit Opus's 200K token context window, meaning the summary only reflects the first portion of the document.
- **Extraction-based mode** (`--from-extraction`): sends the structured data already extracted by Kimi or Claude — fee patents, testimony, correspondence, legislative actions, etc. — as representative samples spread evenly across the document. A 1,300-page document with 23,000+ extracted items compresses to ~16K tokens. No truncation, complete coverage, and much cheaper per call. This is the recommended mode for large documents and for databases built from Kimi extraction. Sampling is intelligent: fee patents prioritize records with the most populated fields (acreage, sale price, buyer); testimony prioritizes the longest key_claims; person entities are deduplicated by name; all types are drawn from evenly-spaced segments of the document so the summary reflects the whole volume, not just the beginning.

**Model options:** Use `--model opus` (default, best quality), `--model sonnet` (cheaper), or `--model kimi` (cheapest, requires TOGETHER_API_KEY). Kimi summaries cost pennies vs. dollars for Opus. For document summaries (not corpus-wide synthesis), Kimi is adequate.

**Batch API:** The `--batch` flag submits all requests via the Anthropic Message Batches API, which processes them asynchronously at 50% of standard pricing ($2.50/MTok input, $12.50/MTok output for Opus). Batches typically complete within an hour.

## Setup

### Virtual Environment

**Always activate the project venv before running any script.** This machine has Python 3.13 and 3.14 installed; packages are only in the venv.

```bash
cd /Users/cwm6W/projects/exhaustive-extraction-pipeline
source venv/bin/activate
```

### Requirements

```bash
pip install pymupdf psycopg2-binary anthropic streamlit markdown together
```

For local/HPC extraction (no API key needed):
```bash
# Install Ollama
brew install ollama        # macOS
# or see https://ollama.ai for Linux

# Pull model
ollama pull llama3.1:70b   # Best quality (requires 64GB RAM)
```

### Database

**Local development:**
```bash
createdb crow_historical_docs
```

The pipeline creates all tables automatically on first run.

**Production:** Cloud SQL PostgreSQL (`crow_historical_docs` on the `allotment-db` instance in `lunar-mercury-397321`). Shared with the [Crow Nation Digital Archive](https://github.com/cwmmwc/crow-nation-digital-archive) site.

### Running Extraction

**v3 pipeline (recommended):**
```bash
export ANTHROPIC_API_KEY="your-key"
python3 poc_pipeline_chunked_v3.py --input /path/to/pdfs --output results_v3/
python3 poc_pipeline_chunked_v3.py --input /path/to/pdfs --output results_v3/ --model claude-sonnet-4-6
python3 poc_pipeline_chunked_v3.py --input /path/to/pdfs --output results_v3/ --db historical_docs
```

**Re-extract existing documents** (preserves doc IDs, summaries, and display_titles):
```bash
python3 poc_pipeline_chunked_v3.py --input /path/to/pdfs --output results_v3/ --force
python3 poc_pipeline_chunked_v3.py --input corpora/KIOWA --output results_v3/ --db historical_docs --force --model claude-sonnet-4-6
```

**v2 pipeline (Anthropic API):**
```bash
export ANTHROPIC_API_KEY="your-key"
python3 poc_pipeline_chunked_v2.py --input /path/to/pdfs --output results/
```

**With Ollama (local/HPC):**
```bash
ollama serve  # in a separate terminal
python3 poc_pipeline_v2_local.py --input /path/to/pdfs --output results/
```

### Cloud Run Deployment

The Streamlit analysis interface is deployed on Google Cloud Run at `https://extraction-pipeline-996830241007.us-east1.run.app`.

**Auto-deploy:** Pushes to `main` trigger a Cloud Build that deploys to Cloud Run automatically via the `deploy-extraction-pipeline` trigger.

- **Database**: Cloud SQL via `DATABASE_URL` env var
- **PDF source**: `gs://crow-archive-pdfs/` (shared with the archive site)
- **API key**: Stored in Secret Manager (`anthropic-api-key`), injected at runtime
- **Memory**: 1 GiB (Streamlit + Anthropic API calls)
- **Build config**: `cloudbuild.yaml` + `Dockerfile`

### Deploying v3 Data to Cloud SQL

After running v3 extraction locally, push the data to Cloud SQL:

```bash
# Start Cloud SQL proxy
cloud-sql-proxy lunar-mercury-397321:us-east1:allotment-db --port=5433

# Create v3 tables on Cloud SQL (if first time)
pg_dump -d crow_historical_docs --table=fee_patents --table=correspondence --table=legislative_actions --schema-only --no-owner | \
  psql "host=localhost port=5433 dbname=crow_historical_docs user=appuser password=YOUR_PASSWORD"

# Export from local, import to Cloud SQL
psql -d crow_historical_docs -c "\copy fee_patents TO '/tmp/fee_patents.csv' WITH CSV HEADER"
psql -d crow_historical_docs -c "\copy correspondence TO '/tmp/correspondence.csv' WITH CSV HEADER"
psql -d crow_historical_docs -c "\copy legislative_actions TO '/tmp/legislative_actions.csv' WITH CSV HEADER"

psql "host=localhost port=5433 ..." -c "\copy fee_patents FROM '/tmp/fee_patents.csv' WITH CSV HEADER"
psql "host=localhost port=5433 ..." -c "\copy correspondence FROM '/tmp/correspondence.csv' WITH CSV HEADER"
psql "host=localhost port=5433 ..." -c "\copy legislative_actions FROM '/tmp/legislative_actions.csv' WITH CSV HEADER"
```

Note: Filter out document IDs that don't exist in Cloud SQL if the local database contains test documents.

## Database Schema

Nine tables in PostgreSQL (v3):

- **documents** — One row per PDF (full text, metadata, summary, archival provenance)
- **entities** — Unique entities with type, context, acres, land_type
- **mentions** — Junction table linking entities to source documents
- **events** — Dated historical events with location and description
- **financial_transactions** — Dollar amounts with payer, payee, purpose, date
- **relationships** — Structured triples (subject → type → object)
- **fee_patents** *(v3)* — Allottee, allotment, acreage, patent date, buyer, attorney, mortgage — the atomic unit of dispossession
- **correspondence** *(v3)* — Sender, recipient, titles, date, subject, action requested, outcome — bureaucratic network reconstruction
- **legislative_actions** *(v3)* — Bill number, sponsor, action type, date, vote count, committee, outcome — bill lifecycle tracking

### Extraction Counts

**Crow Corpus** (`crow_historical_docs`, v3):

| Table | Records |
|-------|---------|
| Documents | 386 |
| Entities | 43,458 |
| Events | 7,992 |
| Financial Transactions | 6,853 |
| Relationships | 8,766 |
| Fee Patents | 959 |
| Correspondence | 5,057 |
| Legislative Actions | 2,432 |

**Kiowa/KCA Corpus** (`historical_docs`, v3 re-extraction):

| Table | Records |
|-------|---------|
| Documents | 256 (180 Kiowa + 76 other) |
| Entities | 14,300 |
| Events | 2,627 |
| Financial Transactions | 4,207 |
| Relationships | 3,164 |
| Fee Patents | 598 |
| Correspondence | 1,355 |
| Legislative Actions | 439 |

## Entity Deduplication

The extraction pipeline produces duplicate entities when the same name appears in different cases or with varying title prefixes across documents. Deduplication is run in phases after extraction.

**Phase 1** (`dedup_entities_phase1.py`) — Safe, mechanical merges:
- Case normalization: "FRANK YARLOTT" → "Frank Yarlott"
- Title stripping: "Mr. FRANK YARLOTT", "Senator Murray" → base name
- Picks the most-referenced variant as the canonical display name
- Reassigns all mentions; consolidates when both variants appear in the same document
- Writes a JSON audit log of every merge

```bash
python3 dedup_entities_phase1.py              # dry run
python3 dedup_entities_phase1.py --execute    # perform merges
```

**Phase 2** (planned) — Fuzzy matching for OCR variants ("Yarlotte" → "Yarlott"), abbreviations ("Chas." → "Charles"), with human review.

**Phase 3** (planned) — AI-assisted resolution for ambiguous cases (surname-only entities like "Murray" that may refer to multiple people).

## Architecture Document

A detailed architecture document (`Extraction_Pipeline_Architecture_v3.docx`) describes the full system design, HPC deployment plan, Ollama/API hybrid strategy, and validation approach. Prepared for UVA Research Computing / Data Analytics Center.

## Corpus

The research corpus is a DevonThink 4 database containing:

- 4,925 OCR'd PDFs (139 million words, ~82 GB)
- Bureau of Indian Affairs Central Classified Files
- Congressional papers (Murray, Mansfield)
- Court records, tribal collections, personal papers
- 1,252 researcher annotations, 340 topical tags

## Model Comparison: Claude vs. Open Source

`compare_claude_vs_local_models.py` runs the same extraction or synthesis task through Claude and open-source models, saving outputs side by side for human evaluation. Full benchmark results from March 2026 testing are below.

**Supported models:**
- Claude Opus (synthesis) / Claude Sonnet (extraction)
- Llama 4 Maverick / Scout (latest — preferred for new comparisons)
- Llama 3.3 70B (`meta-llama/Llama-3.3-70B-Instruct`) — 2x A100 80GB or 128GB MacBook
- Qwen 2.5 72B (`Qwen/Qwen2.5-72B-Instruct`) — 2x A100 80GB
- Gemma 3 27B (`google/gemma-3-27b-it`) — 1x A100

### Benchmark Results (March 2026)

Conducted 2026-03-23 via Together AI hosted API. All open-source models ran on Together's infrastructure; Claude ran via Anthropic's API. The comparison script (`--doc-ids`) ensures identical inputs across all models.

#### Extraction Benchmark

Three documents were used across all models, chosen for variety (bureaucratic records, legislative correspondence, multi-decade litigation):

| Doc ID | Title | Chunk Size | Type |
|--------|-------|-----------|------|
| 695 | 1952–1956: BIA Billings Area Office Administrative Records | 40,000 chars | Bureaucratic/administrative |
| 798 | 1949: Murray Papers — Senate Bill S-716, Fee Patent for George Peters | ~30,000 chars | Legislative/correspondence |
| 811 | 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 | 40,000 chars | Litigation/multi-decade |

**Aggregate results across all three documents:**

| Model | JSON Valid | Total Items | Entities | Events | Financial | Relationships | Fee Patents | Correspondence | Legislative |
|-------|-----------|-------------|----------|--------|-----------|--------------|-------------|----------------|------------|
| **Claude Sonnet** | **3/3** | **327** | 132 | 66 | 16 | 60 | 5 | 35 | 13 |
| **Llama 3.3 70B** | **3/3** | **171** | 93 | 28 | 10 | 19 | 3 | 10 | 8 |
| **Llama 4 Maverick** | 2/3 | **80** | 38 | 11 | 6 | 9 | 2 | 8 | 6 |
| **Llama 4 Scout** | 0/3 | **0** | — | — | — | — | — | — | — |

**Per-document detail:**

| Model | Doc 695 (BIA Admin) | Doc 798 (Fee Patent) | Doc 811 (Litigation) |
|-------|-------------------|---------------------|---------------------|
| Claude Sonnet | 98–106 items | 74–86 items | 128–135 items |
| Llama 3.3 70B | 48 items | 64 items | 59 items |
| Llama 4 Maverick | 0 (invalid JSON) | 34 items | 46 items |
| Llama 4 Scout | 0 (invalid JSON) | 0 (invalid JSON) | 0 (invalid JSON) |

Claude Sonnet shows slight variation across runs because extraction is non-deterministic (temperature 0.3).

#### Extraction Quality: Side-by-Side Examples

**Doc 798 (George Peters Fee Patent)** — the closest competition, where Llama 3.3 70B extracted 64 items vs Claude's 74.

*Entity identification:* Llama 3.3 70B found 35 entities vs Claude's 38 — nearly equal. Both identified George Peters, Senator Murray, the key committees, Oscar Chapman, and all 10 Senate committee members by name. Llama 3.3 also found the exact land descriptions (Section 29, Township 4 south, Range 37 east) and the archival provenance (University of Montana). This is genuinely competitive entity extraction.

*Where Claude pulled ahead — correspondence chains:* Both models found 5 correspondence records, but Claude populated every field (sender title, recipient address, specific subject lines, action requested, outcome). Llama 3.3 left `action_requested` and `outcome` as "none" on most entries:

```
# Claude's correspondence record:
{"sender": "Oscar L. Chapman", "sender_title": "Undersecretary of the Interior",
 "recipient": "Joseph C. O'Mahoney", "recipient_title": "Chairman, Senate Committee on Interior and Insular Affairs",
 "date": "1949-03-09",
 "subject": "Report on S. 716 authorizing patent in fee to George Peters, Crow Indian",
 "action_requested": "Recommendation to enact bill if amended to allow sale to a Crow Indian under existing regulations",
 "outcome": "Report forwarded to Senator Murray by O'Mahoney on March 10, 1949; bill subsequently amended"}

# Llama 3.3's same record:
{"sender": "Oscar L. Chapman", "sender_title": "Undersecretary of the Interior",
 "recipient": "Joseph C. O'Mahoney", "recipient_title": "Chairman, Committee on Interior and Insular Affairs",
 "date": "1949-03-09",
 "subject": "Report on S. 716",
 "action_requested": "consideration of amendments",
 "outcome": "none"}
```

Claude reconstructed the chain of action (Chapman recommended → O'Mahoney forwarded → Murray agreed → bill amended). Llama 3.3 captured the individual letters but not the causal sequence.

*Where Claude pulled ahead — relationships:* Claude extracted 12 relationships vs Llama 3.3's 6. Claude captured "George Peters intended_to_sell_to George Redfield" (a 1921 prior sale indication) and "James E. Murray MSS held_at Mansfield Library, University of Montana" — contextual connections that Llama 3.3 missed entirely.

**Doc 811 (Illegal Patent Dispossession)** — the widest gap.

Claude extracted 128 items vs Llama 3.3's 59. The biggest differences:

| Category | Claude | Llama 3.3 |
|----------|--------|-----------|
| Events | 31 | 10 |
| Correspondence | 21 | 3 |
| Relationships | 17 | 5 |
| Financial transactions | 10 | 5 |

Llama 3.3 found the core transaction (Thomas R. Powers purchased allotment 2336 for $1,500) and correctly identified the key parties, family relationships (Emily J. Geisdorff as widow, Emily Lucile as minor daughter), and dollar amounts ($1,500, $1,350, $150). But Claude traced the full bureaucratic chain: 21 pieces of correspondence between Superintendent Asbury, the Commissioner of Indian Affairs, Superintendent Kneale at Uintah and Ouray Agency, and the General Land Office — reconstructing how the illegal patent was processed step by step over 14 months.

**Doc 695 (BIA Administrative Records)** — OCR challenges.

Llama 3.3 extracted 48 items vs Claude's 98. Both struggled with OCR artifacts in this document. Llama 3.3 reproduced the OCR error "Relnhol t lirust" verbatim as an entity name; Claude resolved it to "Reinholdt Hurst" and identified his role as Acting Area Director. Claude also found Rex Carey (agency soil scientist transferred to Pine Ridge), Bill Smith (on educational leave), and specific legislation (Act of March 7, 1928, 45 Stat. 210) that Llama 3.3 missed.

#### Synthesis Benchmark

Synthesis used the full corpus (368 documents, ~147,264 tokens per prompt) with three research questions. Only Maverick was tested for synthesis; Scout and 3.3 70B were not tested in synthesis mode. Claude Opus was the baseline.

| Metric | Claude Opus | Maverick |
|--------|------------|----------|
| **Q1 (Harlow Pease): Words** | 2,826 | 708 |
| **Q1: Document citations** | 23 | 2 |
| **Q1: Specific dates** | 19 | 1 |
| **Q1: Acreage mentions** | 21 | 1 |
| **Q2 (Fee patent mechanisms): Words** | 4,024 | 846 |
| **Q2: Document citations** | 72 | 17 |
| **Q2: Dollar amounts** | 18 | 0 |
| **Q2: Specific dates** | 24 | 0 |
| **Q3 (Land dispossession): Words** | 4,508 | 857 |
| **Q3: Document citations** | 80 | 13 |
| **Q3: Dollar amounts** | 97 | 2 |
| **Q3: Acreage mentions** | 71 | 4 |
| **Q3: Specific dates** | 13 | 0 |

The synthesis gap is wider than extraction. On Question 3 — which explicitly asked to quantify land dispossession using specific acreages, dollar amounts, and transaction counts — Claude cited 97 dollar amounts and 71 acreage mentions from 80 documents. Maverick cited 2 dollar amounts and 4 acreage mentions from 13 documents.

On Question 1, Claude reconstructed Harlow Pease's 35-year biography from documentary fragments across 23 sources, tracing the Pease family's connections to Crow allottees and the multi-decade failure to enforce Section 2 acreage limitations. Maverick produced a 708-word "Step 1... Step 2... Step 3..." chain-of-thought summary with 2 document citations that correctly identified Pease as a Field Solicitor but could not reconstruct the narrative.

Maverick followed the requested three-part conclusion structure (Prove/Suggest/Gaps) on all three questions — demonstrating prompt compliance. But the content was generic. Where Claude identified specific missing records by file number, Maverick cited "OCR quality issues" and "gaps exist."

**Bottom line:** Maverick recognizes what a document is about. Claude tells you what the document says.

### Model Rankings for This Pipeline

1. **Claude (Opus for synthesis, Sonnet for extraction)** — dramatically superior on both tasks. 100% JSON reliability, 2–3x more items extracted, qualitatively richer output with specific names, dates, amounts, and archival references. The only model that can do corpus-wide synthesis at scale.

2. **Llama 3.3 70B** — the best open-source option. 100% JSON reliability, roughly 50% of Claude's extraction depth. Competitive on entity identification (near-parity on Doc 798). Weak on correspondence chains, relationship mapping, and events. Could serve as a first-pass extractor if cost were a concern. **Runs locally on a 128GB Apple Silicon MacBook via Ollama.** See "Tuning Llama 3.3 70B" below.

3. **Llama 4 Maverick (17B × 128 experts)** — disappointing. 67% JSON reliability, ~25% of Claude's extraction depth. Slower than 3.3 70B despite MoE efficiency. Hallucination issues: fabricated "Jones E. Murray" (instead of James), invented a "bill signed into law" event not in the source. Not recommended.

4. **Llama 4 Scout (17B × 16 experts)** — failed completely on extraction (0/3 valid JSON, 0.2s responses). The model either refused or errored on all 40K-character inputs. Not viable.

### Tuning Llama 3.3 70B for Better Extraction

Llama 3.3 70B shows genuine promise — it found 64 of Claude's 74 items on Doc 798, with near-parity on entities and legislative actions. The gaps are systematic and potentially addressable:

**1. Few-shot examples in the extraction prompt.** The biggest gap is correspondence field population — Llama 3.3 leaves `action_requested` and `outcome` as "none" even when the data is in the document. Adding 2–3 worked examples of fully-populated correspondence and fee_patent records to the system prompt would likely improve field completion. Claude doesn't need few-shot examples because it infers field semantics from the schema alone; smaller models benefit from seeing what "good" output looks like.

**2. Structured output enforcement.** Llama 3.3 sometimes wraps its JSON in markdown code fences (\`\`\`json ... \`\`\`). The comparison script already strips these, but using a constrained decoding library like [Outlines](https://github.com/dottxt-ai/outlines) or Together AI's [JSON mode](https://docs.together.ai/docs/json-mode) would guarantee valid JSON and enforce the exact schema, eliminating the "not specified" placeholder fields.

**3. Two-pass extraction.** Run a first pass for entities and events (where Llama 3.3 is near-parity), then a second pass focused specifically on correspondence chains and relationships (where the gap is widest). The second pass can include the first-pass entities as context, helping the model connect senders/recipients to already-identified people.

**4. Quantized vs. full-precision.** The Together AI benchmark used Instruct-Turbo (likely INT8 quantized). Running the full FP16 model locally via Ollama on a 128GB MacBook (~40GB at Q4, ~70GB at Q8) may improve extraction quality, particularly for OCR-degraded text where quantization noise compounds recognition errors.

**5. Fine-tuning on extraction output (tested — negative result).** We fine-tuned Llama 3.3 70B on 109 training examples (Claude's extraction output as ground truth) using Together AI's LoRA fine-tuning API ($12.89, 55 minutes). The fine-tuned model **performed worse than the untuned base model**: 122 total items across 3 test documents (38% of Claude) vs 148 items untuned (46% of Claude). Fine-tuning actually reduced extraction volume by 18%.

Two factors likely contributed: (1) training data imbalance — 59% of examples had empty v3 fields (correspondence, fee_patents, legislative_actions), teaching the model that sparse output is correct; (2) 10% of the richest examples were truncated at Together AI's 24K token limit. But the deeper issue is that Claude's extraction advantage comes from comprehension of long, OCR-degraded documents, not from knowing a specific output format. A LoRA adapter cannot bridge that capability gap.

Additionally, fine-tuned models on Together AI require **dedicated endpoints** ($0.532/min = $31.92/hr), eliminating the cost advantage over Claude. Total experiment cost: ~$71 (including $50 in platform credits for endpoint access). See `FINE_TUNING_PLAN.md` for the full write-up, training data analysis, and detailed results.

**6. Temperature and sampling.** Current extraction runs use temperature 0.3. For structured extraction (not creative text), dropping to 0.1 or 0.0 may reduce hallucinations like the fabricated names seen in Maverick. Worth testing with Llama 3.3 as well.

**Practical recommendation:** Use Claude for all extraction and synthesis work. Open-source models cannot match Claude's extraction thoroughness (best result: 48% of Claude's volume), and fine-tuning did not close the gap — it widened it. The cost difference ($0.50–1.00/doc for Claude vs near-free for open-source) does not justify 50–60% data loss. For a corpus of 5,000 documents, Claude extraction would cost $2,500–5,000 but produce 2–3x more structured data per document than any open-source alternative tested.

### Cost Context

| Experiment | Cost |
|-----------|------|
| Open-source model inference testing (Llama 3.3, Maverick, Scout) | ~$0.25 |
| Fine-tuning job (LoRA, 3 epochs, 109 examples) | $12.89 |
| Together AI credits for dedicated endpoint tier | $50.00 |
| Dedicated endpoint runtime (~15 min) | ~$8.00 |
| **Total open-source experimentation** | **~$71** |

Claude API costs for the same extraction work are significantly higher (roughly $0.50–$1.00 per document at Sonnet pricing) but produce 2–3x more structured data per document. For synthesis, Claude Opus costs ~$3–5 per question (147K token input) but produces output that no open-source model can match.

### Raw Benchmark Data

All raw outputs (JSON extractions, synthesis markdown, summary tables) are stored in `comparisons/`:

| Run | Directory |
|-----|-----------|
| Synthesis: Claude Opus vs Maverick | `synthesis_20260323_132103_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Synthesis: Maverick only (re-run) | `synthesis_20260323_133836_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Extraction: Maverick (fixed docs) | `extraction_20260323_142938_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Extraction: Scout (fixed docs) | `extraction_20260323_143734_meta-llama-Llama-4-Scout-17B-16E-Instruct/` |
| Extraction: Llama 3.3 70B (fixed docs) | `extraction_20260323_144208_meta-llama-Llama-3.3-70B-Instruct-Turbo/` |
| Extraction: Llama 3.3 70B few-shot | `extraction_20260323_155714_meta-llama-Llama-3.3-70B-Instruct-Turbo_tuned/` |
| Extraction: Maverick few-shot | `extraction_20260323_161751_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8_tuned/` |
| Extraction: Llama 3.3 70B **fine-tuned** | `extraction_20260323_182629_cwm6w_eacd-Llama-3.3-70B-Instruct-Reference-extraction-v1-a3211159-eb529166/` |
| Comprehensive summary | `MODEL_COMPARISON_SUMMARY.md` |

To reproduce the extraction benchmark:

```bash
export TOGETHER_API_KEY=your_key
python3 compare_claude_vs_local_models.py --provider together --local-models llama4-maverick --mode extraction --doc-ids 798 811 695
python3 compare_claude_vs_local_models.py --provider together --local-models llama4-scout --mode extraction --doc-ids 798 811 695
python3 compare_claude_vs_local_models.py --provider together --local-models llama3.3-70b --mode extraction --doc-ids 798 811 695
```

### Running on UVA Rivanna/Afton (HPC)

**One-time setup:**
```bash
git clone https://github.com/cwmmwc/exhaustive-extraction-pipeline.git
cd exhaustive-extraction-pipeline
bash hpc/setup_vllm.sh
```

Edit your allocation group in `hpc/run_comparison.slurm` and `hpc/run_all_models.sh` (replace `<your_allocation>`).

Set your HuggingFace token (needed for gated models like Llama and Gemma):
```bash
export HF_TOKEN=hf_your_token_here
```

**Run all three models:**
```bash
# Extraction mode (default)
bash hpc/run_all_models.sh

# Synthesis mode
MODE=synthesis bash hpc/run_all_models.sh
```

Monitor with `squeue -u $USER`. Results appear in `comparisons/`.

**Run a single model:**
```bash
sbatch --export=MODEL=google/gemma-3-27b-it hpc/run_comparison.slurm
sbatch --export=MODEL=Qwen/Qwen2.5-72B-Instruct hpc/run_comparison.slurm
```

#### Kimi K2.5 on HPC

Kimi K2.5 is the best open-source extraction model (73% of Claude overall, 105–159% on fee patents). It's a 1T-parameter MoE model requiring 8x A100 80GB GPUs.

**One-time setup:**
```bash
bash hpc/setup_kimi.sh
```

This creates the project directory at `/project/LawData/kimi-extraction/`, downloads the model (~549GB), and sets up dependencies.

**Run extraction:**
```bash
# Stage PDFs
cp /path/to/your/pdfs/*.pdf /project/LawData/kimi-extraction/pdfs/

# Start the vLLM server (8x A100 80GB, runs up to 3 days)
sbatch hpc/start_kimi_server.slurm

# Submit extraction worker (CPU node, reads server address automatically)
sbatch --export=PDF=ALL hpc/run_kimi_extraction.slurm

# Or extract a single document first to test:
sbatch --export=PDF="1921 CCF 56074-21-312 GS.pdf" hpc/run_kimi_extraction.slurm
```

The worker has skip-on-exists logic — if a job dies mid-run, resubmit and it picks up where it left off. Results go to `/project/LawData/kimi-extraction/outputs/`.

**Monitor:**
```bash
squeue -u $USER
tail -f /project/LawData/kimi-extraction/logs/server_*.out
```

### Comparing with Claude (locally)

After the Rivanna jobs finish, copy results back and run Claude against the same data:

```bash
# Copy results from Rivanna
scp -r rivanna:~/exhaustive-extraction-pipeline/comparisons/ ./comparisons/

# Run Claude on the same documents (uses corpus_context.json for identical inputs)
python3 compare_claude_vs_local_models.py --claude-only --mode extraction --context-file corpus_context.json
python3 compare_claude_vs_local_models.py --claude-only --mode synthesis --context-file corpus_context.json
```

If `corpus_context.json` needs refreshing (e.g., after adding documents):
```bash
python3 compare_claude_vs_local_models.py --dump-context
```

### Testing via Hosted API (no local hardware needed)

The comparison script supports hosted API providers that serve open-source models. This lets you evaluate Llama 4, Qwen, and Gemma without any local GPU or HPC access.

**Supported providers:**

| Provider | Env var | Notable models |
|----------|---------|----------------|
| Together AI | `TOGETHER_API_KEY` | Kimi K2.5, Llama 4 Maverick, Llama 3.3 70B, Qwen 2.5 72B |
| Fireworks AI | `FIREWORKS_API_KEY` | Llama 3.3 70B, Qwen 2.5 72B |
| Groq | `GROQ_API_KEY` | Llama 3.3 70B |

```bash
# List available models for a provider
python3 compare_claude_vs_local_models.py --provider together --list-models

# Run Llama 4 Maverick vs Claude Opus (synthesis)
export TOGETHER_API_KEY=your_key
python3 compare_claude_vs_local_models.py --provider together \
    --local-models llama4-maverick

# Run Llama 4 Scout vs Claude Sonnet (extraction)
python3 compare_claude_vs_local_models.py --provider together \
    --local-models llama4-scout --mode extraction

# Compare multiple models at once
python3 compare_claude_vs_local_models.py --provider together \
    --local-models llama4-maverick llama4-scout qwen2.5-72b

# Skip Claude, just test the open-source model
python3 compare_claude_vs_local_models.py --provider together \
    --local-models llama4-maverick --local-only

# Use a different database
python3 compare_claude_vs_local_models.py --provider together \
    --local-models llama4-maverick --context-file corpus_context.json
```

Use short model names (e.g., `llama4-maverick`) — the script maps them to the provider's full model IDs automatically. You can also pass the full model ID directly.

### Running locally with Ollama

Works well on Apple Silicon with sufficient unified memory. A MacBook Pro with 128GB RAM can run 70B models comfortably (Q4: ~40GB, Q8: ~70GB).

```bash
ollama pull llama3.3:70b    # Best quality (requires 64GB+ RAM)
ollama pull gemma3:27b      # Faster, lower RAM (requires 32GB+)
ollama serve                # in a separate terminal
python3 compare_claude_vs_local_models.py --local-models llama3.3:70b --mode extraction
```

### HPC Files

| File | Description |
|------|-------------|
| `hpc/setup_vllm.sh` | One-time setup: pull vLLM container, create virtualenv |
| `hpc/setup_kimi.sh` | One-time setup: download Kimi K2.5 model, create project directories |
| `hpc/start_kimi_server.slurm` | SLURM job: start Kimi K2.5 vLLM server on 8x A100 80GB |
| `hpc/run_kimi_extraction.slurm` | SLURM job: extraction worker (CPU node) that calls the Kimi server |
| `hpc/run_comparison.slurm` | SLURM job: launch vLLM + run comparison for one model |
| `hpc/run_all_models.sh` | Submit jobs for all three models in parallel |
| `corpus_context.json` | Pre-dumped corpus data (no DB needed on cluster) |

## Future Work

### Hybrid Extraction: Text + Vision on the Same Document

Most documents in this corpus are mixed: narrative testimony interspersed with tabular allottee schedules, financial ledgers embedded in correspondence files, land transaction tables surrounded by case histories. The 221-page CCF 56074 (Board of Indian Commissioners) is a typical example — pages of narrative testimony about Kaw, Ponca, and Otoe allottees alternate with tabular schedules listing every fee patent recipient by name, blood quantum, age, and disposition of property ("Land sold. Money spent. Nothing left.").

Currently the pipeline requires a manual choice: text mode (Kimi K2.5, best for narrative comprehension) or vision mode (Claude Sonnet, best for tabular layout). For mixed documents, the ideal is **both modes on the same document**, with automatic routing of each page to the appropriate model.

**How this would work technically:**

1. **Page classification.** For each page in the PDF, extract the text via PyMuPDF and analyze its structure. Pages with high ratios of whitespace-to-text, repeated column-like patterns, or very short lines of aligned numbers are likely tabular. Pages with long continuous paragraphs are narrative. A simple heuristic (e.g., average line length, number of tab/space clusters per line, ratio of numeric to alphabetic characters) would classify each page as "narrative" or "tabular" — no ML model needed.

2. **Dual extraction.** Narrative pages get chunked and sent to Kimi K2.5 in text mode, where its comprehension advantage matters — recognizing that "Henry Wy-e-nah-she, Land sold. Allottee broke. Lives with other tribes" is a fee patent case with a named allottee, a completed land sale, and a resulting condition. Tabular pages get rendered as images and sent to Claude Sonnet in vision mode, where its layout reading matters — extracting every row and column with exact values that PyMuPDF would have jumbled.

3. **Merge with deduplication.** Both extractions produce the same structured types (entities, fee_patents, events, etc.). The merge step combines them and deduplicates: if Kimi found "Abby Conn, Kaw, land sold" from the text and Claude vision found the same person in a table row with blood quantum 4/4 and age 43, the merged record gets both the narrative context and the precise tabular fields.

4. **Tables type preserved.** Only vision mode produces the `tables` type (structured rows and columns). Text mode cannot recover tabular structure from jumbled OCR text. The merged output includes tables from vision pages and narrative extraction from text pages — the complete picture.

**Why this matters for the full corpus:** At 4,925 PDFs spanning 40 years of federal Indian administration, the documents range from entirely narrative (correspondence files) to entirely tabular (census schedules, land transaction registers) to deeply mixed (congressional hearings with testimony and exhibits). A hybrid pipeline would handle all three without manual classification of each document, maximizing both comprehension depth (Kimi on narrative) and structural accuracy (Claude vision on tables).

**Estimated implementation:** The page classifier is straightforward — a few hundred lines of Python using PyMuPDF's text block metadata. The dual extraction and merge logic already exist as separate code paths in `extract_single_pdf.py`; they would need to be combined into a single `--hybrid` mode that splits pages, runs both models, and merges the output.

## Contact

Christian McMillen, Department of History, University of Virginia
