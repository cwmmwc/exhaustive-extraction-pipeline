# Model Comparison — Extraction

**Date:** 2026-03-23 14:42
**Models:** claude-sonnet-4-6, meta-llama/Llama-4-Scout-17B-16E-Instruct

## Document 1: 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing (id=695)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Scout-17B-16E-Instruct |
|--------|--------|--------|
| Time | 86.6s | 0.2s |
| Valid JSON | Yes | NO |
| Entities | 49 | — |
| Events | 19 | — |
| Financial Transactions | 4 | — |
| Relationships | 18 | — |
| Fee Patents | 2 | — |
| Correspondence | 8 | — |
| Legislative Actions | 3 | — |
| **Total items** | **103** | **0** |

## Document 2: 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters (id=798)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Scout-17B-16E-Instruct |
|--------|--------|--------|
| Time | 52.3s | 0.2s |
| Valid JSON | Yes | NO |
| Entities | 37 | — |
| Events | 12 | — |
| Financial Transactions | 1 | — |
| Relationships | 14 | — |
| Fee Patents | 1 | — |
| Correspondence | 5 | — |
| Legislative Actions | 5 | — |
| **Total items** | **75** | **0** |

## Document 3: 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) (id=811)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Scout-17B-16E-Instruct |
|--------|--------|--------|
| Time | 130.2s | 0.2s |
| Valid JSON | Yes | NO |
| Entities | 43 | — |
| Events | 32 | — |
| Financial Transactions | 8 | — |
| Relationships | 16 | — |
| Fee Patents | 2 | — |
| Correspondence | 23 | — |
| Legislative Actions | 4 | — |
| **Total items** | **128** | **0** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
