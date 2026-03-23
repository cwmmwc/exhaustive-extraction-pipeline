# Model Comparison Summary

**Date:** 2026-03-23
**Purpose:** Evaluate whether open-source models can replace Claude for structured extraction and corpus-wide synthesis in a historical document analysis pipeline.

## Models Tested

| Model | Parameters | Architecture | Provider | Context Window |
|-------|-----------|-------------|----------|---------------|
| Claude Opus 4.6 | undisclosed | — | Anthropic API | 200K tokens |
| Claude Sonnet 4.6 | undisclosed | — | Anthropic API | 200K tokens |
| Llama 4 Maverick | 17B × 128 experts (MoE) | Mixture of Experts | Together AI | 1M tokens |
| Llama 4 Scout | 17B × 16 experts (MoE) | Mixture of Experts | Together AI | 512K tokens |
| Llama 3.3 70B | 70B | Dense | Together AI | 128K tokens |

Claude Opus was used for synthesis; Claude Sonnet for extraction. All open-source models were tested via Together AI's hosted API.

## Test Corpus

- **368 documents** from the Crow Reservation archival collection
- Documents span 1887–1989: BIA administrative records, congressional hearings, correspondence, fee patent files, litigation records
- OCR-digitized historical documents with variable text quality

---

## 1. Extraction Comparison

Three documents were used across all extraction tests (pinned via `--doc-ids 798 811 695`):

| Doc ID | Title | Chunk Size | Type |
|--------|-------|-----------|------|
| 695 | 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing | 40,000 chars | Bureaucratic/administrative |
| 798 | 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters | ~30,000 chars | Legislative/correspondence |
| 811 | 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) | 40,000 chars | Litigation/multi-decade |

### Aggregate Extraction Results

| Model | JSON Valid | Total Items | Entities | Events | Financial | Relationships | Fee Patents | Correspondence | Legislative |
|-------|-----------|-------------|----------|--------|-----------|--------------|-------------|----------------|------------|
| **Claude Sonnet** | 3/3 | **327** | 132 | 66 | 16 | 60 | 5 | 35 | 13 |
| **Llama 3.3 70B** | 3/3 | **171** | 93 | 28 | 10 | 19 | 3 | 10 | 8 |
| **Llama 4 Maverick** | 2/3 | **80** | 38 | 11 | 6 | 9 | 2 | 8 | 6 |
| **Llama 4 Scout** | 0/3 | **0** | — | — | — | — | — | — | — |

### Per-Document Breakdown

#### Document 695: BIA Administrative Records

| Model | Valid JSON | Time | Total Items |
|-------|-----------|------|-------------|
| Claude Sonnet | Yes | 86–92s | 98–106 |
| Llama 3.3 70B | Yes | 10.5s | 48 |
| Llama 4 Maverick | No | 13.2s | 0 |
| Llama 4 Scout | No | 0.2s | 0 |

#### Document 798: George Peters Fee Patent

| Model | Valid JSON | Time | Total Items |
|-------|-----------|------|-------------|
| Claude Sonnet | Yes | 53–61s | 74–86 |
| Llama 3.3 70B | Yes | 13.1s | 64 |
| Llama 4 Maverick | Yes | 42.8s | 34 |
| Llama 4 Scout | No | 0.2s | 0 |

#### Document 811: Illegal Patent Dispossession

| Model | Valid JSON | Time | Total Items |
|-------|-----------|------|-------------|
| Claude Sonnet | Yes | 131–139s | 128–135 |
| Llama 3.3 70B | Yes | 16.5s | 59 |
| Llama 4 Maverick | Yes | 49.0s | 46 |
| Llama 4 Scout | No | 0.2s | 0 |

### Extraction Quality Analysis (Doc 798: George Peters)

Side-by-side comparison on the same document reveals qualitative differences beyond item counts:

**Claude found that other models missed:**
- Secondary actors: George Redfield (intended buyer in 1921), W.P. Marshall (Western Union president), Mills Astin (Chief Clerk), Morris (House report submitter)
- All 10 Senate committee member names with state affiliations
- Exact legal land descriptions (section, township, range, meridian)
- Archival provenance (University of Montana, Mansfield Library, Collection No. 91)
- The 1921 prior sale indication event

**Maverick errors:**
- "Jones E. Murray" instead of "James E. Murray" — a hallucinated name variant
- Fabricated "bill_signed_into_law" event not present in source document
- Correspondence entry with sender listed as "Unknown" when the document clearly identifies Murray
- Multiple "not specified" fields where data is present in the source text

**Llama 3.3 70B** was the strongest open-source performer on Doc 798, extracting 64 items vs Claude's 74 — the closest any model came. Entity counts were nearly equal (35 vs 38). The gap was widest in relationships (6 vs 12) and events (11 vs 12).

---

## 2. Synthesis Comparison

Synthesis used the full corpus (368 documents, ~147,264 tokens per prompt) with three research questions. Claude Opus was the baseline; only Maverick was tested for synthesis (Scout and 3.3 70B were not tested in synthesis mode).

### Questions

1. Tell me about Harlow Pease and his relationship with the Crow generally and with Section 2 of the Crow Act specifically.
2. What were the primary mechanisms of forced fee patent issuance on the Crow Reservation? Who were the key actors and what were the outcomes?
3. How much Crow land was lost and to whom? Quantify the scale of land dispossession using specific acreages, dollar amounts, and transaction counts from the documents.

### Results

| Metric | Claude Opus | Maverick |
|--------|------------|----------|
| **Q1: Word count** | 2,826 | 708 |
| **Q1: Document citations** | 23 | 2 |
| **Q1: Specific dates** | 19 | 1 |
| **Q1: Acreage mentions** | 21 | 1 |
| **Q2: Word count** | 4,024 | 846 |
| **Q2: Document citations** | 72 | 17 |
| **Q2: Dollar amounts** | 18 | 0 |
| **Q2: Specific dates** | 24 | 0 |
| **Q3: Word count** | 4,508 | 857 |
| **Q3: Document citations** | 80 | 13 |
| **Q3: Dollar amounts** | 97 | 2 |
| **Q3: Acreage mentions** | 71 | 4 |
| **Q3: Specific dates** | 13 | 0 |

### Synthesis Quality Assessment

Claude Opus produced deeply evidence-grounded historical analysis — reconstructing Harlow Pease's 35-year biography from documentary fragments across dozens of sources, tracing specific allotment numbers and patent dates through chains of transactions, and assembling named dollar amounts and acreages into a quantified account of dispossession.

Maverick produced competent thematic summaries that correctly identified the major topics (fee patents, acreage limitations, Section 2 violations) but could not populate specifics. Its output followed the requested three-part structure (Prove/Suggest/Gaps) — demonstrating prompt compliance — but the content was generic. Where Claude identified missing records by specific file number, Maverick cited "OCR quality issues" and "gaps exist."

The synthesis gap is wider than extraction. Maverick can recognize what a document is about; Claude can tell you what the document says.

---

## 3. Conclusions

### Model Ranking for This Pipeline

1. **Claude (Opus for synthesis, Sonnet for extraction)** — dramatically superior on both tasks. 100% JSON reliability, 2–3× more items extracted, qualitatively richer output with specific names, dates, amounts, and archival references.

2. **Llama 3.3 70B** — the best open-source option. 100% JSON reliability, roughly 50% of Claude's extraction depth. Competitive on entity identification but weak on relationships, correspondence chains, and events. Could potentially serve as a first-pass extractor if cost were a concern. **This is the model most likely to be useful running locally on a 128GB MacBook.**

3. **Llama 4 Maverick** — disappointing given its size. 67% JSON reliability, ~25% of Claude's extraction depth. Slower than 3.3 70B despite MoE efficiency. Hallucination issues (fabricated names, invented events). Not recommended.

4. **Llama 4 Scout** — completely failed extraction (0/3 valid JSON, 0.2s responses indicating the model refused or errored on all inputs). Not viable for this task.

### Should You Run Models Locally?

**For extraction:** Llama 3.3 70B on a 128GB MacBook via Ollama would give you ~50% of Claude Sonnet's extraction depth at zero marginal API cost. Whether that tradeoff is worth it depends on volume: if you're processing hundreds of documents, running locally saves money but loses significant detail. A hybrid approach — local 3.3 70B for first-pass extraction, Claude Sonnet for high-value documents — could be practical.

**For synthesis:** No open-source model tested came close to Claude Opus. The synthesis task requires holding 147K tokens of context and cross-referencing specific details across dozens of documents. This is where Claude's advantage is most pronounced and where local models are not a viable substitute.

### Cost Context

All open-source model testing via Together AI cost approximately $0.15 total. Claude API costs for equivalent work are significantly higher but produce significantly better results.

---

## Raw Data Locations

| Run | Directory |
|-----|-----------|
| Synthesis: Claude Opus vs Maverick | `comparisons/synthesis_20260323_132103_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Synthesis: Maverick only | `comparisons/synthesis_20260323_133836_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Extraction: Maverick (fixed docs) | `comparisons/extraction_20260323_142938_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Extraction: Scout (fixed docs) | `comparisons/extraction_20260323_143734_meta-llama-Llama-4-Scout-17B-16E-Instruct/` |
| Extraction: Llama 3.3 70B (fixed docs) | `comparisons/extraction_20260323_144208_meta-llama-Llama-3.3-70B-Instruct-Turbo/` |

### Reproducibility

To re-run the extraction comparison with the same documents:

```bash
export TOGETHER_API_KEY=your_key
python3 compare_claude_vs_local_models.py --provider together --local-models llama4-maverick --mode extraction --doc-ids 798 811 695
python3 compare_claude_vs_local_models.py --provider together --local-models llama4-scout --mode extraction --doc-ids 798 811 695
python3 compare_claude_vs_local_models.py --provider together --local-models llama3.3-70b --mode extraction --doc-ids 798 811 695
```

---

*Comparison conducted 2026-03-23. Model performance may change with future releases, fine-tuning, or prompt optimization.*
