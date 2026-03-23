# Exhaustive Extraction Pipeline

AI-powered structured extraction from 4,925 historical PDF documents (139 million words) documenting federal Native American land dispossession, 1880–1990.

## What This Does

Instead of using Retrieval-Augmented Generation (RAG) to search for "relevant" document chunks at query time, this pipeline **pre-processes every document** and extracts all structured information into a PostgreSQL database. The result is a queryable knowledge base of every person, organization, legal case, financial transaction, land parcel, and relationship mentioned across the entire corpus.

**Why not RAG?** A RAG system retrieves the top-K most relevant chunks for a query. It cannot trace a person across 30 years of documents, aggregate financial transactions to calculate total acreage lost, or discover that the same dispossession pattern recurs across different tribes and decades. Exhaustive extraction can.

## Current Status

- **386 documents processed** across 9 batches (Crow Nation archival materials) with v3 pipeline
- **180 Kiowa documents re-extracted** through v3 pipeline (historical_docs database), producing 598 fee patents, 1,355 correspondence records, 439 legislative actions
- **43,000+ entities**, **6,800+ financial transactions**, **8,700+ relationships**, **7,900+ events** extracted (Crow corpus)
- **959 fee patents**, **5,057 correspondence records**, **2,432 legislative actions** (v3 structured types, Crow corpus)
- Five-mode analysis interface with citation linking to the [Crow Nation Digital Archive](https://github.com/cwmmwc/crow-nation-digital-archive) and DEVONthink 4 (`x-devonthink-item://` URLs for local collections)
- HTML export with preserved document links in all analysis modes
- Production deployment on Google Cloud Run with auto-deploy on push to `main`
- Multi-database support: `crow_historical_docs` (Crow), `historical_docs` (Kiowa/KCA), `full_corpus_docs` (planned)
- Ready for full-corpus deployment on UVA Rivanna/Afton HPC

## Repository Contents

| File | Description |
|------|-------------|
| `poc_pipeline_chunked_v3.py` | **v3 extraction pipeline** — 10 entity types + fee patents, correspondence, legislative actions. Supports `--force` for re-extraction preserving doc IDs and summaries |
| `poc_pipeline_chunked_v2.py` | v2 extraction pipeline using Anthropic API (10 entity types) |
| `poc_pipeline_v2_local.py` | v2 extraction pipeline using Ollama (for HPC deployment, zero API cost) |
| `ai_analysis_interface_v4.py` | Streamlit query interface with four analysis modes, citation linking, v3 data support |
| `enrich_summaries.py` | Generate per-document analytical summaries for corpus-wide synthesis (supports Batch API) |
| `process_crow_batch.sh` | Batch staging helper script |
| `dedup_entities_phase1.py` | Entity deduplication: case normalization + title stripping |
| `compare_claude_vs_local_models.py` | Claude vs. open-source model comparison (Ollama, vLLM, Together AI, Fireworks, Groq) |
| `generate_display_titles.py` | AI-generated archival display titles for all documents |
| `devonthink_uuids.json` | DEVONthink 4 UUID mapping for local document linking (Kiowa/KCA) |
| `schema.sql` | PostgreSQL database schema (v3) |
| `comparisons/` | Baseline and comparison outputs (v2 vs v3 extraction, model comparisons) |

## The Pipeline

### Extraction (poc_pipeline_chunked_v3.py)

Takes a directory of PDFs and produces structured database records:

1. **Text extraction** — PyMuPDF reads OCR'd text from each PDF
2. **Chunking** — 40,000-character chunks with 5,000-character overlap
3. **LLM extraction** — Each chunk sent to LLM with structured prompt returning JSON
4. **Database storage** — Parsed into PostgreSQL with deduplication

### Entity Types (v2) + Structured Types (v3)

| Type | Example | Version |
|------|---------|---------|
| person | Harold Stanton, Paul Fickinger, Guy Bulltail | v2 |
| organization | Bureau of Indian Affairs, Campbell Farming Corporation | v2 |
| location | Crow Reservation, Big Horn County | v2 |
| land_parcel | Allotment 2237, Section 12 T1S R32E | v2 |
| legal_case | Dillon v. Antler Land Co. of Wyola | v2 |
| legislation | Crow Act 1920, H.R. 5477 | v2 |
| acreage_holding | Homer Scott: 90,000 acres | v2 |
| financial_transaction | $32,691.20 oil lease bonus payment | v2 |
| relationship | Stanton represented Crow Tribe as tribal attorney | v2 |
| date_event | March 18, 1940 — House passed H.R. 5477 | v2 |
| **fee_patent** | George Peters, Allotment 1292, 840 acres, sold to Stanton | **v3** |
| **correspondence** | Murray to BIA Commissioner, 1947-06-15, re: Peters fee patent | **v3** |
| **legislative_action** | S. 1385 introduced by Murray, 1947-06, enacted as Private Law 68 | **v3** |

### v3 Extraction Types — Why These Matter

**Fee patents** are the atomic unit of land dispossession. The v2 pipeline scattered fee patent data across `person`, `land_parcel`, `financial_transaction`, and `relationship` entities — forcing the AI to reassemble it at query time. The v3 `fee_patent` type links allottee, allotment number, acreage, patent date, trust-to-fee mechanism (private bill, administrative action), subsequent buyer, sale price, facilitating attorney, and any mortgage into a single record. This enables direct SQL queries like "total acreage patented by decade" or "which attorneys appeared in the most fee patent chains."

**Correspondence** captures the bureaucratic network: sender, recipient, titles/positions, date, subject, action requested, and outcome. Designed to link with Pipeline B (1.4M BIA index cards from the National Archives) via sender/recipient/date matching. This is the cross-corpus integration layer described in the HAVI Level I proposal.

**Legislative actions** track bills through their lifecycle: introduced, reported, amended, passed, vetoed, enacted — with sponsors, vote counts, and committee assignments. The v2 `legislation` entity captured bill names but not their trajectories. The Murray synthesis (which reconstructed 5 major bills across 30+ documents from summaries alone) demonstrated how much analytical leverage structured legislative data provides.

### Analysis Interface (ai_analysis_interface_v4.py)

Streamlit web interface with four modes:

- **Discovery** — Search the entity database across all documents, including v3 structured types (fee patents, correspondence, legislative actions). Evidence browser with tabs for each data type. Best for broad research questions spanning multiple archival collections.
- **Deep Read** — Send a complete document to the AI for close analysis. Replicates single-document depth of DevonThink AI.
- **Discovery → Deep Read** — Run Discovery to find relevant documents, select which ones to deep-read, then send full texts plus cross-collection entity data to the AI. Produces the richest analysis.
- **Corpus Synthesis** — Send analytical summaries of ALL documents to the AI for corpus-wide pattern analysis. No context window limit — the AI sees every document in the collection. Requires summaries to be generated first (see below).

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
python3 enrich_summaries.py                    # summarize all unsummarized docs
python3 enrich_summaries.py --limit 5          # test on 5 documents first
python3 enrich_summaries.py --force            # re-summarize all documents
python3 enrich_summaries.py --batch            # use Batch API (50% cost savings)
python3 enrich_summaries.py --batch --force    # re-summarize all via Batch API
```

**Why summaries?** 386 summaries x ~300 words = ~100K tokens — fits in a single Claude call. 386 full documents x ~50K words each = impossible in any context window. Summaries are the bridge between exhaustive extraction and corpus-wide reasoning.

**Batch API:** The `--batch` flag submits all requests via the Anthropic Message Batches API, which processes them asynchronously at 50% of standard pricing ($2.50/MTok input, $12.50/MTok output for Opus). Batches typically complete within an hour.

## Setup

### Requirements

```bash
pip install pymupdf psycopg2-binary anthropic streamlit markdown
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

`compare_claude_vs_local_models.py` runs the same extraction or synthesis task through Claude and open-source models, saving outputs side by side for human evaluation.

**Supported models:**
- Claude Opus (synthesis) / Claude Sonnet (extraction)
- Llama 4 Maverick / Scout (latest — preferred for new comparisons)
- Llama 3.3 70B (`meta-llama/Llama-3.3-70B-Instruct`) — 2x A100 80GB
- Qwen 2.5 72B (`Qwen/Qwen2.5-72B-Instruct`) — 2x A100 80GB
- Gemma 3 27B (`google/gemma-3-27b-it`) — 1x A100

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
| Together AI | `TOGETHER_API_KEY` | Llama 4 Maverick, Llama 4 Scout, Qwen 2.5 72B |
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
| `hpc/run_comparison.slurm` | SLURM job: launch vLLM + run comparison for one model |
| `hpc/run_all_models.sh` | Submit jobs for all three models in parallel |
| `corpus_context.json` | Pre-dumped corpus data (no DB needed on cluster) |

## Contact

Christian McMillen, Department of History, University of Virginia
