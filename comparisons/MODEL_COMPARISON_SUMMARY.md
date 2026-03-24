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

| Model | JSON Valid | Total Items | % of Claude | Entities | Events | Financial | Relationships | Fee Patents | Correspondence | Legislative |
|-------|-----------|-------------|-------------|----------|--------|-----------|--------------|-------------|----------------|------------|
| **Claude Sonnet** | 3/3 | **321** | 100% | 134 | 62 | 15 | 55 | 5 | 35 | 15 |
| **Llama 3.3 70B (untuned)** | 3/3 | **148** | 46% | 88 | 16 | 8 | 15 | 5 | 9 | 7 |
| **Llama 3.3 70B (few-shot)** | 3/3 | **148** | 46% | — | — | — | — | — | — | — |
| **Llama 3.3 70B (fine-tuned)** | 3/3 | **122** | **38%** | 69 | 18 | 7 | 10 | 4 | 8 | 6 |
| **Llama 4 Maverick** | 2/3 | **80** | 25% | 38 | 11 | 6 | 9 | 2 | 8 | 6 |
| **Llama 4 Scout** | 0/3 | **0** | 0% | — | — | — | — | — | — | — |

**Note:** Claude Sonnet totals vary slightly between runs due to non-deterministic output. The fine-tuned model row represents `cwm6w_eacd/Llama-3.3-70B-Instruct-Reference-extraction-v1-a3211159`, trained on 109 examples from both Crow and Kiowa corpora.

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

### Deep-Dive: 1921 Board of Indian Commissioners Report (CCF 56074-21-312 GS)

A 221-page document containing Board of Indian Commissioners correspondence and field agent reports on the condition of patent-in-fee Indians across Pawnee, Ponca, Otoe, Kaw, and Tonkawa reservations. This is a document the PI knows well and which Claude's full extraction (all 13 chunks) produced 1,369 items that powered significant analytical findings, including the discovery of what we term the "Nez Perce paradox." Testing on the first 40K-character chunk only:

| Category | Claude Sonnet | Llama 3.3 70B | Llama % of Claude |
|----------|-------------|---------------|-------------------|
| Entities | 173 | 142 | 82% |
| Events | 18 | 17 | 94% |
| Financial transactions | 10 | 10 | 100% |
| Relationships | 34 | 20 | 59% |
| Fee patents | **83** | **8** | **10%** |
| Correspondence | 7 | 10 | 143% |
| Legislative actions | 1 | 6 | 600% |
| **Total** | **326** | **213** | **65%** |

This is Llama's **best overall result** (65% of Claude), and the category-level breakdown reveals where the gap actually lives:

**Near parity (80%+):** Entities, events, financial transactions. Llama correctly identified the Board of Indian Commissioners members, agency superintendents, field farmers, and key events. Both models found the same financial transactions.

**Llama found more:** Correspondence (10 vs 7) and legislative actions (6 vs 1). Llama correctly identified individual letters from each field agent (DeVare, Crim, Thompson, Long, Mitchell, Furry, Collins, Clendening) as separate correspondence records, while Claude grouped some of these.

**The devastating gap — fee patents (8 vs 83):** This document contains dozens of individual allottee case histories — named people, their allotment status, what happened after they received fee patents (lost land, retained land, circumstances). Claude extracted 83 of these as structured fee_patent records with allottee names, acreage details, and outcomes. Llama found only 8, and those 8 had "Unknown" for allotment numbers, acreage, and mechanism. This is the core data that makes the document historically valuable.

**Quality difference in context fields:** Claude included geographic specifics ("Philadelphia, PA," "Mohonk Lake, N.Y.," "Princeton, N.J.") from the letterhead. Llama captured the same people but with generic context ("Member of Board of Indian Commissioners"). Claude's richer context enables better entity resolution across documents.

**Bottom line:** Llama 3.3 70B is competent at identifying *who is in the document* and *what correspondence occurred*. It fails at extracting the repetitive structured records — individual allottee case histories, fee patent details, specific acreages and outcomes — that constitute the historical evidence. For this corpus, that structured data is the entire point.

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

## 3. Fine-Tuning Experiment

We fine-tuned Llama 3.3 70B on 109 training examples (Claude's extraction output as ground truth) using Together AI's LoRA fine-tuning API.

### Training Details

| Parameter | Value |
|-----------|-------|
| Base model | meta-llama/Llama-3.3-70B-Instruct-Reference |
| Training method | LoRA (rank 64, alpha 128) |
| Training examples | 109 (24 Crow + 85 Kiowa) |
| Epochs | 3 |
| Training time | 55 minutes |
| Training cost | $12.89 |
| Truncated examples | 10 (9.17%) at 24,576 token limit |

### Result: Negative

The fine-tuned model extracted **fewer** items than the untuned base model on all three test documents except doc 798:

| Document | Claude | Untuned | Fine-tuned | Fine-tuned % of Claude |
|----------|--------|---------|------------|----------------------|
| 695 | 106 | 59 | 38 | 36% |
| 798 | 78 | 30 | 43 | 55% |
| 811 | 137 | 59 | 41 | 30% |
| **Total** | **321** | **148** | **122** | **38%** |

### Why It Didn't Work

1. **Training data imbalance:** 59% of training examples had empty v3 fields (correspondence, fee_patents, legislative_actions), teaching the model that sparse output is correct.
2. **Truncation:** 10% of the richest examples were cut at Together AI's 24K token sequence limit.
3. **Fundamental capability gap:** Claude's extraction advantage comes from deep comprehension of long, OCR-degraded documents — not from knowing a specific output format. A LoRA adapter cannot bridge that gap with 109 examples.

### Infrastructure Finding

Fine-tuned models on Together AI require **dedicated endpoints** at $0.532/min ($31.92/hr). There is no serverless inference for custom fine-tunes. This eliminates the cost advantage over Claude, which was the primary motivation for fine-tuning.

---

## 4. Conclusions

### Model Ranking for This Pipeline

1. **Claude (Opus for synthesis, Sonnet for extraction)** — dramatically superior on both tasks. 100% JSON reliability, 2–3× more items extracted, qualitatively richer output with specific names, dates, amounts, and archival references. Fine-tuning open-source alternatives did not close the gap.

2. **Llama 3.3 70B (untuned)** — the best open-source option at 46% of Claude's volume. 100% JSON reliability. Competitive on entity identification but weak on relationships, correspondence chains, and events. Fine-tuning this model made it worse, not better.

3. **Llama 4 Maverick** — disappointing given its size. 67% JSON reliability, ~25% of Claude's extraction depth. Slower than 3.3 70B despite MoE efficiency. Hallucination issues (fabricated names, invented events). Not recommended.

4. **Llama 4 Scout** — completely failed extraction (0/3 valid JSON, 0.2s responses indicating the model refused or errored on all inputs). Not viable for this task.

### Should You Run Models Locally?

**For extraction:** Not recommended. The best open-source result (Llama 3.3 70B untuned, 46% of Claude) loses more than half the structured data. Fine-tuning did not improve this — it made it worse. The cost of Claude ($0.50–1.00/doc) is justified by the 2–3× data quality improvement.

**For synthesis:** No. No open-source model tested came close to Claude Opus. The synthesis task requires holding 147K tokens of context and cross-referencing specific details across dozens of documents. This is where Claude's advantage is most pronounced and where local models are not a viable substitute.

### Cost Summary

| Experiment | Cost |
|-----------|------|
| Open-source inference testing (Llama 3.3, Maverick, Scout) | ~$0.25 |
| Fine-tuning job (LoRA, 3 epochs, 109 examples) | $12.89 |
| Together AI credits for dedicated endpoint tier | $50.00 |
| Dedicated endpoint runtime (~15 min) | ~$8.00 |
| **Total open-source experimentation** | **~$71** |

Claude API costs for equivalent extraction are significantly higher per document ($0.50–1.00) but produce 2–3× more structured data. For a full corpus of 5,000 documents, Claude extraction would cost $2,500–5,000 — but with dramatically better results than any open-source alternative tested.

---

## Raw Data Locations

| Run | Directory |
|-----|-----------|
| Synthesis: Claude Opus vs Maverick | `comparisons/synthesis_20260323_132103_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Synthesis: Maverick only | `comparisons/synthesis_20260323_133836_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Extraction: Maverick (fixed docs) | `comparisons/extraction_20260323_142938_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Extraction: Scout (fixed docs) | `comparisons/extraction_20260323_143734_meta-llama-Llama-4-Scout-17B-16E-Instruct/` |
| Extraction: Llama 3.3 70B (fixed docs) | `comparisons/extraction_20260323_144208_meta-llama-Llama-3.3-70B-Instruct-Turbo/` |
| Extraction: Llama 3.3 70B few-shot | `comparisons/extraction_20260323_155714_meta-llama-Llama-3.3-70B-Instruct-Turbo_tuned/` |
| Extraction: Maverick few-shot | `comparisons/extraction_20260323_161751_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8_tuned/` |
| Extraction: Llama 3.3 70B **fine-tuned** | `comparisons/extraction_20260323_182629_cwm6w_eacd-Llama-3.3-70B-Instruct-Reference-extraction-v1-a3211159-eb529166/` |
| Extraction: CCF 56074 deep-dive (Claude vs Llama 3.3) | `comparisons/single_20260324_091852_1921 CCF 56074-21-312 GS/` (Claude) + `comparisons/single_20260324_093343_1921 CCF 56074-21-312 GS/` (Llama) |

### Reproducibility

To re-run the extraction comparison with the same documents:

```bash
export TOGETHER_API_KEY=your_key
python3 compare_claude_vs_local_models.py --provider together --local-models llama4-maverick --mode extraction --doc-ids 798 811 695
python3 compare_claude_vs_local_models.py --provider together --local-models llama4-scout --mode extraction --doc-ids 798 811 695
python3 compare_claude_vs_local_models.py --provider together --local-models llama3.3-70b --mode extraction --doc-ids 798 811 695
```

---

*Comparison and fine-tuning experiment conducted 2026-03-23. Model performance may change with future releases or prompt optimization. Fine-tuning was tested and did not improve results — see Section 3.*
