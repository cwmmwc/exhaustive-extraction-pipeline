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
