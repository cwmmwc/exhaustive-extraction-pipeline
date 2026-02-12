# Exhaustive Entity Extraction Pipeline

An AI-powered pipeline for **100% coverage entity extraction** from large historical document collections into PostgreSQL, with a natural language analysis interface.

Built for the **Native American Land Dispossession Research Project** at the University of Virginia, processing federal records related to the allotment era (1887–1970s).

---

## The Problem This Solves

Standard RAG (Retrieval-Augmented Generation) systems retrieve the **top-K most similar documents** to a query — typically 55–65% coverage. For legal and historical research requiring complete evidence, missed documents mean missed patterns.

This pipeline takes the opposite approach: **extract everything first, query later**. Every entity, person, organization, location, and event is extracted from every document and stored in a relational database. Queries then retrieve complete, verified evidence sets.

**Results:**
- Kiowa Agency Records: 253 documents → 3,732 entities, 100% coverage
- Crow Reservation: 364 documents → ~20,000 entities (in progress)
- Congressional Records: 215 spreadsheet rows integrated as structured events

---

## Architecture

```
PDFs → Text Extraction → Chunked LLM Extraction → PostgreSQL → Streamlit Interface
         (PyMuPDF)        (Claude Sonnet 4 API)      (4 tables)   (Natural language Q&A)
```

### Four-Table Schema

```sql
documents   -- full text + metadata for every PDF
entities    -- every person, org, location, land parcel
mentions    -- which entities appear in which documents
events      -- land transactions, hearings, patents, foreclosures
```

### Why Chunked Extraction?

Long documents (100–850 pages) exceed LLM context windows. The pipeline splits documents into overlapping 40,000-character chunks, extracts entities from each independently, then merges and deduplicates. An 850-page document yields ~1,687 entities vs ~20–30 with single-pass extraction.

---

## Files

| File | Description |
|------|-------------|
| `poc_pipeline_chunked.py` | Main extraction pipeline (Anthropic API) |
| `poc_pipeline_local.py` | Local extraction pipeline (Ollama, zero API cost) |
| `ai_analysis_interface.py` | Streamlit natural language query interface |
| `process_crow_batch.sh` | Batch processing helper script |
| `schema.sql` | Database schema |

---

## Requirements

```bash
# Python packages
pip install anthropic pymupdf psycopg2-binary streamlit

# System dependencies
brew install postgresql ollama  # macOS
# or: apt install postgresql    # Linux

# For local (Ollama) pipeline only
ollama pull llama3.1:70b        # 40GB, best quality (needs 64GB RAM)
ollama pull llama3.1:8b         # 8GB, fast (needs 16GB RAM)
```

---

## Quick Start

### 1. Create database
```bash
createdb crow_historical_docs
psql crow_historical_docs < schema.sql
```

### 2. Set API key
```bash
export ANTHROPIC_API_KEY='your-key-here'
# Or add to ~/.zshrc to persist across sessions
```

### 3. Run extraction
```bash
# Single batch
python3 poc_pipeline_chunked.py \
    --input /path/to/pdfs \
    --output results/

# Overnight batch processing (prevents Mac sleep)
caffeinate -i python3 poc_pipeline_chunked.py \
    --input /path/to/pdfs \
    --output results/

# Local pipeline (no API cost)
ollama serve &
python3 poc_pipeline_local.py \
    --input /path/to/pdfs \
    --output results/ \
    --model llama3.1:70b
```

### 4. Launch analysis interface
```bash
streamlit run ai_analysis_interface.py --server.port 8502
# Open http://localhost:8502
```

---

## Batch Processing

For large collections, use the batch helper to process in groups of 50:

```bash
# Prepare batch N (copies files to ~/Desktop/CROW_BATCH_N)
./process_crow_batch.sh 1

# Process batch
caffeinate -i python3 poc_pipeline_chunked.py \
    --input ~/Desktop/CROW_BATCH_1 \
    --output results_batch_1

# Chain batches
caffeinate -i bash -c '
python3 poc_pipeline_chunked.py --input ~/Desktop/CROW_BATCH_1 --output results_1 &&
python3 poc_pipeline_chunked.py --input ~/Desktop/CROW_BATCH_2 --output results_2
'
```

**Cost estimate:** ~$0.18/document × 364 documents = ~$65 total (Anthropic API)
**Local pipeline:** $0 after one-time model download

---

## Example Queries

```sql
-- Most mentioned people
SELECT name, COUNT(*) as mentions
FROM entities e JOIN mentions m ON e.id = m.entity_id
WHERE e.type = 'person'
GROUP BY name ORDER BY mentions DESC LIMIT 20;

-- Documents mentioning acreage violations
SELECT file_name, COUNT(*) as hits
FROM documents d
JOIN mentions m ON d.id = m.document_id
JOIN entities e ON m.entity_id = e.id
WHERE e.context ILIKE '%violat%' AND e.context ILIKE '%acre%'
GROUP BY file_name ORDER BY hits DESC;

-- All contexts for a specific person
SELECT d.file_name, LEFT(m.context, 300)
FROM mentions m
JOIN entities e ON m.entity_id = e.id
JOIN documents d ON m.document_id = d.id
WHERE e.name = 'Robert Yellowtail'
ORDER BY d.file_name;

-- Find documents by full-text search
SELECT file_name,
    SUBSTRING(full_text FROM POSITION('section 2' IN LOWER(full_text)) - 100 FOR 400)
FROM documents
WHERE LOWER(full_text) LIKE '%acreage limitation%'
LIMIT 10;
```

---

## Key Research Findings (Sample)

Running this pipeline on 145 Crow Reservation documents revealed:

- **BIA complicity:** "conducted supervised sales that violated acreage limitations between 1920–1955" — the agency's own records
- **Charlie Bair fraud:** 125,000 sheep on reservation paying for only 35,000
- **Murphy Land & Cattle:** 3,160 acres owned, 22,000 leased — far exceeding 640/1,280 acre limits
- **Crow Reservation Association:** Non-Indian ranchers self-taxed 10¢/acre to fund Congressional lobby protecting illegal holdings
- **1940 Amendment:** Contrary to its title, explicitly preserved non-Indian acreage limits while helping Crow people consolidate fragmented heirship lands

---

## Local Pipeline (Zero API Cost)

`poc_pipeline_local.py` is a drop-in replacement using Ollama:

```python
# Replaces Anthropic client with local Ollama HTTP API
# Same PostgreSQL schema — databases are fully compatible
# Quality: ~85–90% of Claude Sonnet 4 with llama3.1:70b

python3 poc_pipeline_local.py \
    --input /path/to/pdfs \
    --output results/ \
    --model llama3.1:70b \
    --db crow_historical_docs
```

Hardware requirements: 16GB RAM (8b model) or 64GB RAM (70b model)

---

## Scaling

```python
# Parallel processing skeleton
from multiprocessing import Pool

all_pdfs = glob.glob("/path/to/collection/**/*.pdf", recursive=True)
batches = [all_pdfs[i:i+50] for i in range(0, len(all_pdfs), 50)]

with Pool(processes=10) as pool:
    pool.map(process_batch, batches)

# Full-text search index
CREATE INDEX idx_fulltext ON documents
    USING gin(to_tsvector('english', full_text));
```

**Estimated costs at scale:**
- 5,000 documents: ~$900, ~3 hours (10 workers)
- 50,000 documents: ~$9,000, ~30 hours (10 workers)
- 50,000 documents (local): ~$0, ~150 hours (single machine)

---

## Project Context

This pipeline was developed for research into Native American land dispossession during the allotment era. Collections processed include:

- **Kiowa Agency Records** — affidavits, complaints, fee patent records (Oklahoma, 1900–1940)
- **Crow Reservation Documents** — CCF files, Congressional hearings, court records (Montana, 1907–1993)
- **Congressional Records** — 215 land transaction records (1932–1984)

The system demonstrates that exhaustive extraction enables historical pattern recognition impossible with RAG: coordinated family land transfers, systematic BIA policy violations, corporate lobbying networks, and individual victim identification across thousands of archival documents.

---

## License

MIT License — free to use, modify, and distribute with attribution.

---

## Citation

If you use this pipeline in research, please cite:

```
Exhaustive Entity Extraction Pipeline for Historical Document Analysis
University of Virginia Data Analytics Center, 2026
https://github.com/[your-username]/exhaustive-extraction-pipeline
```
