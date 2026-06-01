# PROJECT_CONTEXT.md — Exhaustive Extraction Pipeline

Orientation file for new conversations about this project. Written in the first person so it can be dropped into a Claude project as foundational context. Sanitized of credentials. Current as of 2026-05-22.

## Who I am, what I'm doing

I am Christian McMillen, professor of Native American History at the University of Virginia. This project extracts structured information from approximately **4,925 historical PDFs (139 million words)** documenting federal Native American land dispossession from 1880 to 1990. The goal is a queryable knowledge base of every person, organization, legal case, financial transaction, land parcel, and relationship mentioned across the entire corpus.

This is a sister project to `~/projects/american-indian-allotment/`, which is the Flask web application and PostgreSQL database for the BLM allotment patent + 1983 Federal Register claims data. Same researcher, complementary corpora.

## Why pre-extraction, not RAG

Standard practice with large document collections is Retrieval-Augmented Generation: retrieve the top-K most relevant chunks at query time and pass them to an LLM. RAG is fine for chat-with-your-documents but unfit for systematic historical research. It cannot trace a single allottee across thirty years of correspondence, aggregate financial transactions to calculate total acreage lost in a region, or discover that the same dispossession pattern recurs across different tribes and decades. Exhaustive extraction processes every document once, ahead of any question, and produces structured tables that can be queried, joined, aggregated, and counted like any other dataset. That tradeoff (large up-front compute cost for the ability to ask questions of the whole corpus) is what this project is built around.

## Corpora and databases

Several distinct extraction campaigns, each loaded into its own PostgreSQL database.

**Survey of Conditions of the Indians in the United States, 1927–1943** — database `survey_of_conditions`. The largest extraction in the project, now complete: all 41 numbered parts of this Senate subcommittee hearing record are loaded, and nothing remains queued. The database holds 45 Survey documents (the 41 canonical parts plus four extras: the 1927 predecessor hearings, a "Part 0" digitizer artifact and a "Part 1" Washington DC section both belonging to Part 3, and a second Sonnet extraction of Part 33 alongside the Kimi one), totaling 23,565 recorded pages and **175,997 structured items**. Extracted with Kimi K2.5 on the v4 schema, initially via Together AI and then on the UVA RC GenAI H200 service. Item breakdown: 80,838 entity mentions (64,665 distinct entities), 25,735 events, 25,002 financial transactions, 22,836 relationships, 6,518 testimony records, 6,269 correspondence items, 4,176 legislative actions, 2,180 fee patents, 1,844 taxes, 599 mortgages. Counts reflect the collection as loaded and include the second Part 33 extraction and the two Part 3 sub-section artifacts.

**AIPRC Taylor Report** — same `survey_of_conditions` database, collection `"AIPRC Taylor Report"`. The American Indian Policy Review Commission's *Report on Indian Land Consolidation* (Taylor, 1976), 119 pages of tables on land taken by legislation and eminent domain (1936–1974) and land repurchased under IRA Section 5 (1934–present). Extracted via vision mode (PyMuPDF could not handle the multi-column tables). 43 tables, 366 rows. Key finding: IRA Section 5 recovered only **595,000 acres, or 0.66% of the 90 million lost through allotment**.

**NARA RG 60 — DOJ Index Cards** — database `index_cards`. Department of Justice record slips, 87 PDFs and ~2,400 pages of typed correspondence index cards tracking legal cases involving Indian land, taxes, and allotments from 1920 to 1967. Vision-extracted with a custom `--index-cards` prompt. **24,368 items**: 12,969 record slips, 4,811 legal cases, 6,588 persons. Reveals 408+ named allottees in DOJ litigation, 291 case file numbers, heavy geographic concentration in Oklahoma (Osage, Choctaw, Cherokee, Creek), 175 oil/mineral cases.

**Crow Nation corpus** — database `crow_historical_docs`. 386 documents, 43,000 entities, 959 fee patents.

**Kiowa / KCA corpus** — database `historical_docs`. 256 documents, 180 re-extracted through schema v3.

**Circular 2464** — no dedicated database yet; corpus lives as JSON at `circular_2464_extractions/extractions/sonnet/`. The BIA's 1928 investigation into forced fee patents issued without allottee consent. ~1,100 pages across 13 parts plus three Pine Ridge volumes, covering Pine Ridge, Rosebud, Fort Berthold, Otoe, Pawnee, Ponca, and Shawnee agencies. **Three-layer extraction**: (1) Sonnet text per-allottee with a flat 18-column schema, (2) Kimi v5 per-part with the rich schema, (3) Sonnet and Qwen2.5-VL-72B vision for records where text extraction failed on handwritten elements. **1,043 active per-allottee records** (1,030 named, 911 with allotment number, 38 with vision v5 data). Document types: 414 affidavits, 334 agency narratives, 280 questionnaires, 14 ledger entries. Major 2026 reconciliation work: Fort Berthold ledger replaced (Sonnet had OCR column misalignment; Qwen2.5-VL vision is the production reading), Shawnee master list unbundled into 36 individual records, 34 non-extracted recoveries, 9 multi-allottee bundles split, 26 CAT_1 vision recoveries.

## Architecture

- **Text extraction.** PyMuPDF reads the PDF, splits text into 40K-character chunks with 5K overlap, sends each chunk to the model with the extraction prompt, parses the structured JSON response, loads it to PostgreSQL.
- **Vision extraction.** For tabular documents (Taylor Report) and typed index cards (NARA RG 60), PDF pages are rendered as images and sent to Claude Sonnet or Qwen2.5-VL-72B.
- **Index card extraction.** A specialized `--index-cards` prompt returns record_slips, legal_cases, and persons.
- **Synthesis.** Per-document summaries generated via Claude Opus or Kimi for corpus-wide analytical queries.
- **Interface.** Streamlit app (`ai_analysis_interface_v4.py`) with Discovery, Deep Read, Hybrid, and Corpus Synthesis modes. Deployed to Google Cloud Run with Cloud SQL PostgreSQL.

## Schema evolution

- **v3** (legacy): 7 types — entities, events, financial_transactions, relationships, fee_patents, correspondence, legislative_actions.
- **v4** (current default): 10 types — adds testimony, taxes, mortgages.
- **v5**: enhanced for Circular 2464 work and the Taylor Report's table data; adds document_tables and table_rows.

Fee patents are the atomic unit of dispossession across all schemas. They link allottee, allotment, acreage, patent date, mechanism, buyer, attorney, and mortgage into a single structured record.

## Models — what works for what

The benchmark question across most of 2026 has been: what is the best open-source alternative to Claude Sonnet for the extraction step? Results:

- **Claude Sonnet**: baseline (100%). Irreplaceable for narrative-heavy documents (legislative correspondence, litigation) and for corpus-wide synthesis when used as the analysis model.
- **Kimi K2.5** (Moonshot AI, MoE 1T total / 32B active parameters): the best open-source model. 73% of Claude overall, but **105–159% of Claude on fee patents** (found 268 allottees vs Claude's 169 on the 221-page CCF 56074 benchmark). No hallucinations. Correctly distinguishes dispossession mechanisms. Weaker on legislative correspondence (58%) and long causal chains.
- **Qwen 2.5 72B**: 54% overall, only 15% on fee patents. Not a viable extraction alternative despite needing fewer GPUs than Kimi.
- **Qwen2.5-VL-72B**: vision model. Excellent on tabular and handwritten elements; validated against Sonnet on the Fort Berthold ledger and the CAT_1 affidavit recovery.
- **Llama 3.3 70B**: 46%, superseded by Kimi.
- **Llama 4 Maverick**: 25%, with fabricated names and invented events.
- **Llama 4 Scout**: 0%, complete failure.
- **Fine-tuned Llama 3.3 70B**: 38% — fine-tuning produced a worse model. Negative result documented in `FINE_TUNING_PLAN.md`.
- **Gemma 3 12B**: excellent on bounded template work (NARA index cards specifically).

**Production pipeline.** Kimi K2.5 extraction → Claude Opus analytical synthesis. Widest evidence base read by the most capable interpretive model. The full-page case for this is in `KIMI_K25_RESULTS.md`.

## Where Kimi runs

Three deployments, in order of operational preference:

1. **UVA Research Computing GenAI service** (preferred, launched 2026-03-30). Kimi K2.5 hosted on 8x NVIDIA H200, free to UVA researchers via an API. Use the `--uvarc` flag on extraction scripts.
2. **UVA HPC Rivanna** via the `LawData` allocation. SLURM batch on 8x A100 80GB. Uses Loren Moulds's vLLM Singularity container.
3. **Together AI hosted API**. $0.50/$2.80 per million tokens. Convenient but unreliable at scale (occasional Kimi endpoint failures).

## HPC particulars

- Hostname: `login.hpc.virginia.edu`, user `cwm6w`.
- Project directory: `/project/LawData/kimi-extraction/`.
- The Qwen-VL vLLM server is a separate SLURM job. It must be started explicitly each session before any vision recovery work.
- Default walltime for new SLURM scripts: `--time=2-00:00:00`. Do not copy a walltime from an existing script without thinking about it.
- vLLM clients must default to parallel (ThreadPoolExecutor, around six workers). A single-threaded loop leaves the GPU 90%+ idle.
- I run all SSH, SCP, and rsync commands myself in my own terminal. Claude should never execute remote-HPC commands.

## Working style and collaboration preferences

See the Claude project's Custom Instructions for the full set. Briefly: quality over cost, deep fix over quick fix, narrow scope on corrections, production safety, read the codebase before writing new scripts, no AI speak, and documentation is part of the work.

## Tech stack

- Python with PyMuPDF, psycopg2-binary, anthropic, streamlit, together
- PostgreSQL locally; Cloud SQL PostgreSQL in production
- Streamlit interface deployed to Google Cloud Run, Cloud Build auto-deploy on push to `main`
- UVA HPC (Rivanna) with SLURM for Kimi K2.5 and Qwen2.5-VL-72B batch extraction
- DEVONthink for local document management with `x-devonthink-item://` URL linking
- Git in normal flow; large PDFs are git-ignored

## Connections to the allotment-research project

The two projects overlap conceptually but have distinct data structures.

- **Same researcher and same broad historical scope** — allotment-era land dispossession across the twentieth century.
- **Same production infrastructure.** Both deploy to Google Cloud Run / Cloud SQL in the same GCP project.
- **The forced-fee story straddles both projects.** The `american-indian-allotment` Flask app indexes the 1983 Federal Register forced-fee claims as a population-level record (~35,000 claims, ~10,000 forced-fee or adjacent). The Circular 2464 extraction in this project documents the 1928 BIA investigation into forced-fee patents at the individual-case level (~1,043 per-allottee records). The two together cover the bureaucratic event of 1928 and the legal-remedy aftermath of 1983.
- **Loren Moulds collaboration is shared.** This project's NARA RG 60 work and the planned JOIN of `american-indian-allotment`'s CCF references against Loren's 1.4 million NARA BIA index cards are part of the same broader effort.
- **Distinct deliverables.** This project produces structured research data and an analytical interface. The allotment-research project produces a public-facing research site.

## Currently pending, as of 2026-06-01

- Circular 2464 PostgreSQL loader following the `merge_index_cards.py` precedent. Design plan at `circular_2464_extractions/DATABASE_LOADER_PLAN.md`. Will produce a `circular_2464` database with Streamlit dropdown entry and graph integration.
- Continued model benchmarking; the comparison record is `comparisons/MODEL_COMPARISON_SUMMARY.md`.
