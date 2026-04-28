# Exhaustive Extraction Pipeline

## MANDATORY: Read Before Acting

**Before writing ANY new script, making ANY infrastructure decision, or starting ANY multi-step task:**
1. Read the relevant existing scripts in this repo FIRST. They document the established patterns.
2. For HPC/extraction work: read `hpc/`, `push_to_hpc.sh`, `pull_survey_from_hpc.sh`, `load_survey_extractions.py`
3. For Streamlit/analysis work: read `ai_analysis_interface_v4.py`, `enrich_summaries.py`
4. NEVER run SSH/SCP/rsync scripts directly — always tell the user to run with `!` prefix
5. NEVER call RC GenAI from the local machine — extraction runs on HPC via SLURM
6. NEVER ask the user how something was done if the answer is in the codebase — READ THE CODE
7. After completing a step, immediately do the next step in the established pipeline without waiting to be asked

**The user is a historian who has spent weeks building these procedures. Follow them exactly. Do not improvise.**

**Resources are not a constraint.** The goal is the best possible extraction, not the cheapest. UVA HPC provides ample GPUs at no cost for open-source models. The researcher has funding for Claude Sonnet and Opus when needed. Do NOT optimize for cost or time — optimize for quality. Do not suggest cheaper alternatives, shorter prompts for speed, or skipping steps to save money. If a two-pass extraction produces better results than a single pass, run two passes. If Opus produces better summaries than Kimi, use Opus.

## Project Overview
AI-powered structured extraction from 4,925 historical PDFs (139M words) documenting federal Native American land dispossession, 1880–1990. Built by Christian McMillen, historian at UVA.

## Architecture
- **Text extraction**: PyMuPDF text → 40K-char chunks with 5K overlap → Kimi K2.5 → structured JSON → PostgreSQL
- **Vision extraction**: PDF pages rendered as images → Claude Sonnet vision → structured JSON (for tables, ledgers, index cards)
- **Index card extraction**: `--index-cards` flag with custom DOJ record slip prompt → record_slips, legal_cases, persons
- **Synthesis**: Per-document summaries → Claude Opus for corpus-wide analysis
- **Interface**: Streamlit app with Discovery, Deep Read, Hybrid, and Corpus Synthesis modes
- **Deployment**: Google Cloud Run (auto-deploy on push to main), Cloud SQL PostgreSQL

## Key Files
- `poc_pipeline_chunked_v3.py` — Main extraction pipeline (v3: entities + fee_patents, correspondence, legislative_actions)
- `ai_analysis_interface_v4.py` — Streamlit query interface
- `enrich_summaries.py` — Per-document summary generation (supports Batch API, `--from-extraction` for extraction-based summaries, `--model kimi` for cheap summaries)
- `extract_single_pdf.py` — Standalone single-PDF extraction (Claude, Together AI, vLLM, `--uvarc` for RC GenAI, `--vision` for tables, `--index-cards` for DOJ record slips)
- `load_vision_extractions.py` — Load vision-mode extractions (tables + standard types) into PostgreSQL
- `retry_failed_chunks.py` — Retry failed/truncated chunks and complete interrupted extractions
- `run_survey_extraction.sh` — Batch extraction of all Survey of Conditions PDFs via Together AI
- `load_survey_extractions.py` — Load Survey extraction JSONs into PostgreSQL
- `load_survey_fulltext.py` — Load PDF full text into survey database (needed for full-text summary mode)
- `compare_claude_vs_local_models.py` — Model benchmarking (Ollama, vLLM, Together AI, Fireworks, Groq)
- `schema.sql` — PostgreSQL v3 schema
- `schema_v4.sql` — PostgreSQL v4 schema (adds testimony, taxes, mortgages, document_tables, table_rows)
- `comparisons/MODEL_COMPARISON_SUMMARY.md` — Comprehensive model comparison results
- `hpc/` — SLURM scripts for running Kimi K2.5 on UVA HPC (vLLM server + extraction workers)
- `KIMI_K25_RESULTS.md` — One-page summary of Kimi K2.5 findings for sharing

## Databases
- `survey_of_conditions` — Survey of Conditions hearings (26 of 48 volumes loaded, 158K items, 2,487 fee patents). Extracted by Kimi K2.5. Active campaign.
- `crow_historical_docs` — Crow Nation corpus (386 docs, 43K entities, 959 fee patents)
- `historical_docs` — Kiowa/KCA corpus (256 docs, 180 re-extracted through v3)
- `full_corpus_docs` — Full corpus (planned)

## Extraction Schema
- **v4 (current default)**: 10 types — entities, events, financial_transactions, relationships, fee_patents, correspondence, legislative_actions, testimony, taxes, mortgages
- **v3**: 7 types — entities, events, financial_transactions, relationships, fee_patents, correspondence, legislative_actions (use `--v3` flag)
- Fee patents are the atomic unit of land dispossession — linking allottee, allotment, acreage, patent date, mechanism, buyer, attorney, mortgage
- Testimony captures congressional hearing witnesses and their key claims
- Taxes and mortgages capture two additional mechanisms of dispossession that were previously scattered across other categories

## Model Comparison Results (March 2026)
- Claude Sonnet: baseline, 100% of items. Irreplaceable for narrative-heavy documents (legislative correspondence, litigation) and corpus-wide synthesis
- Kimi K2.5 (Moonshot AI, open-source): best open-source model at 73% of Claude overall. **105–159% of Claude on fee patents** — found 268 allottees vs Claude's 169 on the 221-page CCF 56074. No hallucinations, correctly distinguishes dispossession mechanisms. Weaker on legislative correspondence (58%) and long causal chains
- Qwen 2.5 72B: 54% of Claude overall but only 15% on fee patents (26 vs 169). Not a viable alternative to Kimi despite needing only 2x A100 vs 8x
- Llama 3.3 70B: 46% of Claude overall, largely superseded by Kimi K2.5
- Llama 4 Maverick: 25%, hallucination issues (fabricated names, invented events)
- Llama 4 Scout: 0%, complete failure
- Fine-tuning Llama 3.3 70B: negative result (38%, worse than untuned)
- Gemma 3 12B: excellent on bounded template extraction (NARA index cards)
- Claude Sonnet vision: excellent on tabular documents (Taylor Report: 75 tables, 686 rows from 119 pages) and on DOJ index cards. Full 87-PDF Sonnet `--vision --index-cards` run already exists at `vision_index_cards_full/` (80 PDFs with merged JSON).
- Qwen2.5-VL-72B: tested on HPC (4x A100 80GB, Loren's container `vllm_0.14.1-cu130.sif`, `--tensor-parallel-size 4`). Full corpus run launched 2026-04-10 against the running Qwen-VL vLLM server — duplicate of existing Sonnet data, kept for corpus-scale Sonnet-vs-Qwen comparison. Initial 2-PDF apples-to-apples (66 dense pages, 744 slips): ties Sonnet on slips, **+90% on cases** (per-mention vs deduped), **−70% on persons** (principals only vs all named individuals). Likely a deduplication-strategy difference, not a comprehension gap. See `comparisons/MODEL_COMPARISON_SUMMARY.md` §8 for the full breakdown.
- Optimal pipeline: **Kimi extraction → Claude Opus analysis** (widest evidence base + deepest analytical framing)
- Key finding: fee patent comprehension is Kimi-specific, not a general capability of 70B+ models — both Qwen 72B and Llama 70B fail catastrophically on fee patents while Kimi exceeds Claude

## Index Card Extraction (RG 60)
- 87 PDFs, ~2,400 pages of DOJ record slips from NARA RG 60
- Custom `--index-cards` prompt extracts: record_slips, legal_cases, persons
- Each card = one piece of correspondence about a legal case (tax recovery, quiet title, allotment disputes)
- File number (e.g., 90-2-5-49) is the unique case identifier — case names vary across cards and need post-extraction dedup
- Source files at `RG 60 index cards/` (exported from DEVONthink)
- Tracks the DOJ's involvement in Indian land tax cases: which counties, which allottees, what outcomes

## Environment
- Python venv at `./venv` — activate with `source venv/bin/activate`
- Requires: PyMuPDF, psycopg2-binary, anthropic, streamlit, together
- API keys: `ANTHROPIC_API_KEY`, `TOGETHER_API_KEY` (set in user's shell, may not propagate to Claude Code's Bash sessions)

## Conventions
- Always update README.md and relevant docs when building features
- Commit messages should be descriptive
- The comparison doc at `comparisons/MODEL_COMPARISON_SUMMARY.md` is the canonical record of all model testing
- `FINE_TUNING_PLAN.md` documents the fine-tuning experiment (negative result)

## Important Context
- The user (Christian) is a historian, not a software engineer. Explain technical concepts in plain language.
- OCR quality varies widely across the corpus — this affects extraction quality
- The "Nez Perce paradox" was discovered via Claude's extraction of CCF 56074-21-312 GS (221 pages, Board of Indian Commissioners)
- DEVONthink `x-devonthink-item://` URLs are used for local document linking
- Production Cloud SQL is on `lunar-mercury-397321:us-east1:allotment-db`
