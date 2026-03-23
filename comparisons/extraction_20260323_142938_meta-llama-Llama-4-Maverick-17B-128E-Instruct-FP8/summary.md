# Model Comparison — Extraction

**Date:** 2026-03-23 14:36
**Models:** claude-sonnet-4-6, meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8

## Document 1: 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing (id=695)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 92.0s | 13.2s |
| Valid JSON | Yes | NO |
| Entities | 50 | — |
| Events | 19 | — |
| Financial Transactions | 6 | — |
| Relationships | 18 | — |
| Fee Patents | 2 | — |
| Correspondence | 8 | — |
| Legislative Actions | 3 | — |
| **Total items** | **106** | **0** |

## Document 2: 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters (id=798)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 60.6s | 42.8s |
| Valid JSON | Yes | Yes |
| Entities | 37 | 13 |
| Events | 12 | 6 |
| Financial Transactions | 1 | 0 |
| Relationships | 24 | 4 |
| Fee Patents | 1 | 1 |
| Correspondence | 6 | 5 |
| Legislative Actions | 5 | 5 |
| **Total items** | **86** | **34** |

## Document 3: 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) (id=811)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 138.8s | 49.0s |
| Valid JSON | Yes | Yes |
| Entities | 45 | 25 |
| Events | 35 | 5 |
| Financial Transactions | 9 | 6 |
| Relationships | 18 | 5 |
| Fee Patents | 2 | 1 |
| Correspondence | 21 | 3 |
| Legislative Actions | 5 | 1 |
| **Total items** | **135** | **46** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
