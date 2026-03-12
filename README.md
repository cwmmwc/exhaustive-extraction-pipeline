# Exhaustive Extraction Pipeline

AI-powered structured extraction from 4,925 historical PDF documents (139 million words) documenting federal Native American land dispossession, 1880–1990.

## What This Does

Instead of using Retrieval-Augmented Generation (RAG) to search for "relevant" document chunks at query time, this pipeline **pre-processes every document** and extracts all structured information into a PostgreSQL database. The result is a queryable knowledge base of every person, organization, legal case, financial transaction, land parcel, and relationship mentioned across the entire corpus.

**Why not RAG?** A RAG system retrieves the top-K most relevant chunks for a query. It cannot trace a person across 30 years of documents, aggregate financial transactions to calculate total acreage lost, or discover that the same dispossession pattern recurs across different tribes and decades. Exhaustive extraction can.

## Current Status

- **345 documents processed** across 9 batches (Crow Nation archival materials)
- **15,000+ entities**, **600+ financial transactions**, **1,200+ relationships**, **1,200+ events** extracted
- v2 extraction validated with 10 entity types
- Three-mode analysis interface tested and producing publishable historical analysis
- Ready for full-corpus deployment on UVA Rivanna/Afton HPC

## Repository Contents

| File | Description |
|------|-------------|
| `poc_pipeline_chunked_v2.py` | v2 extraction pipeline using Anthropic API (10 entity types) |
| `poc_pipeline_v2_local.py` | v2 extraction pipeline using Ollama (for HPC deployment, zero API cost) |
| `ai_analysis_interface_v4.py` | Streamlit query interface with three analysis modes |
| `process_crow_batch.sh` | Batch staging helper script |
| `schema.sql` | PostgreSQL database schema |

## The Pipeline

### Extraction (poc_pipeline_chunked_v2.py / poc_pipeline_v2_local.py)

Takes a directory of PDFs and produces structured database records:

1. **Text extraction** — PyMuPDF reads OCR'd text from each PDF
2. **Chunking** — 40,000-character chunks with 5,000-character overlap
3. **LLM extraction** — Each chunk sent to LLM with structured prompt returning JSON
4. **Database storage** — Parsed into PostgreSQL with deduplication

### Entity Types (v2)

| Type | Example |
|------|---------|
| person | Harold Stanton, Paul Fickinger, Guy Bulltail |
| organization | Bureau of Indian Affairs, Campbell Farming Corporation |
| location | Crow Reservation, Big Horn County |
| land_parcel | Allotment 2237, Section 12 T1S R32E |
| legal_case | Dillon v. Antler Land Co. of Wyola |
| legislation | Crow Act 1920, H.R. 5477 |
| acreage_holding | Homer Scott: 90,000 acres |
| financial_transaction | $32,691.20 oil lease bonus payment |
| relationship | Stanton represented Crow Tribe as tribal attorney |
| date_event | March 18, 1940 — House passed H.R. 5477 |

### Analysis Interface (ai_analysis_interface_v4.py)

Streamlit web interface with three modes:

- **Discovery** — Search the entity database across all documents. Best for broad research questions spanning multiple archival collections.
- **Deep Read** — Send a complete document to the AI for close analysis. Replicates single-document depth of DevonThink AI.
- **Discovery → Deep Read** — Run Discovery to find relevant documents, select which ones to deep-read, then send full texts plus cross-collection entity data to the AI. Produces the richest analysis.

```bash
streamlit run ai_analysis_interface_v4.py
```

Requires: PostgreSQL with extracted data, Anthropic API key.

## Setup

### Requirements

```bash
pip install pymupdf psycopg2-binary anthropic streamlit
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

**With Anthropic API:**
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

The Streamlit analysis interface is deployed on Google Cloud Run at `https://extraction-pipeline-996830241007.us-east1.run.app`. Auto-deploys on push to `main` via Cloud Build.

- **Database**: Cloud SQL via `DATABASE_URL` env var
- **PDF source**: `gs://crow-archive-pdfs/` (shared with the archive site)
- **API key**: Stored in Secret Manager (`anthropic-api-key`), injected at runtime
- **Memory**: 1 GiB (Streamlit + Anthropic API calls)

## Database Schema

Six tables in PostgreSQL:

- **documents** — One row per PDF (full text, metadata, archival provenance)
- **entities** — Unique entities with type, context, acres, land_type
- **mentions** — Junction table linking entities to source documents
- **events** — Dated historical events with location and description
- **financial_transactions** — Dollar amounts with payer, payee, purpose, date
- **relationships** — Structured triples (subject → type → object)

## Architecture Document

A detailed architecture document (`Extraction_Pipeline_Architecture_v3.docx`) describes the full system design, HPC deployment plan, Ollama/API hybrid strategy, and validation approach. Prepared for UVA Research Computing / Data Analytics Center.

## Corpus

The research corpus is a DevonThink 4 database containing:

- 4,925 OCR'd PDFs (139 million words, ~82 GB)
- Bureau of Indian Affairs Central Classified Files
- Congressional papers (Murray, Mansfield)
- Court records, tribal collections, personal papers
- 1,252 researcher annotations, 340 topical tags

## HPC Deployment (Planned)

The `poc_pipeline_v2_local.py` script is designed for deployment on UVA Rivanna/Afton:

- Ollama with Llama 3.1 70B on A100 80GB GPUs
- SLURM job arrays processing ~100 documents per job
- Estimated 60–100 GPU-hours for full corpus (3–5 days wall-clock)
- Zero API cost after model download

## Contact

Christian McMillen, Department of History, University of Virginia
