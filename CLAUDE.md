# Exhaustive Extraction Pipeline

## Project Overview
AI-powered structured extraction from 4,925 historical PDFs (139M words) documenting federal Native American land dispossession, 1880–1990. Built by Christian McMillen, historian at UVA.

## Architecture
- **Extraction**: PyMuPDF text → 40K-char chunks with 5K overlap → Claude Sonnet → structured JSON → PostgreSQL
- **Synthesis**: Per-document summaries → Claude Opus for corpus-wide analysis
- **Interface**: Streamlit app with Discovery, Deep Read, Hybrid, and Corpus Synthesis modes
- **Deployment**: Google Cloud Run (auto-deploy on push to main), Cloud SQL PostgreSQL

## Key Files
- `poc_pipeline_chunked_v3.py` — Main extraction pipeline (v3: entities + fee_patents, correspondence, legislative_actions)
- `ai_analysis_interface_v4.py` — Streamlit query interface
- `enrich_summaries.py` — Per-document summary generation (supports Batch API)
- `extract_single_pdf.py` — Standalone single-PDF extraction (Claude and/or Together AI)
- `compare_claude_vs_local_models.py` — Model benchmarking (Ollama, vLLM, Together AI, Fireworks, Groq)
- `schema.sql` — PostgreSQL v3 schema
- `comparisons/MODEL_COMPARISON_SUMMARY.md` — Comprehensive model comparison results

## Databases
- `crow_historical_docs` — Crow Nation corpus (386 docs, 43K entities, 959 fee patents)
- `historical_docs` — Kiowa/KCA corpus (256 docs, 180 re-extracted through v3)
- `full_corpus_docs` — Full corpus (planned)

## v3 Extraction Schema
The v3 prompt extracts: entities, events, financial_transactions, relationships, fee_patents, correspondence, legislative_actions. Fee patents are the atomic unit of land dispossession — linking allottee, allotment, acreage, patent date, mechanism, buyer, attorney, mortgage.

## Model Comparison Results (March 2026)
- Claude Sonnet: baseline, 100% of items
- Llama 3.3 70B: best open-source at 46% of Claude overall, but near-parity on entities/events/financial (80-100%), catastrophic on fee patents (10%)
- Fine-tuning Llama 3.3 70B: negative result (38%, worse than untuned)
- Llama 4 Maverick: 25%, hallucination issues
- Llama 4 Scout: 0%, complete failure
- Gemma 3 12B: excellent on bounded template extraction (NARA index cards)
- Key finding: open-source good at **recognition** (entities, dates, labeled fields), bad at **comprehension** (fee patent narratives, relationships, synthesis)

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
