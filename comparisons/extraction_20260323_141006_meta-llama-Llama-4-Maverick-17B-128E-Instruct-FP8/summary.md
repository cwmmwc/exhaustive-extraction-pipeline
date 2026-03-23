# Model Comparison — Extraction

**Date:** 2026-03-23 14:17
**Models:** claude-sonnet-4-6, meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8

## Document 1: 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters (id=798)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 56.1s | 52.0s |
| Valid JSON | Yes | Yes |
| Entities | 37 | 14 |
| Events | 13 | 6 |
| Financial Transactions | 1 | 0 |
| Relationships | 22 | 3 |
| Fee Patents | 1 | 1 |
| Correspondence | 6 | 5 |
| Legislative Actions | 5 | 4 |
| **Total items** | **85** | **33** |

## Document 2: 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) (id=811)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 131.5s | 59.9s |
| Valid JSON | Yes | Yes |
| Entities | 40 | 24 |
| Events | 34 | 5 |
| Financial Transactions | 10 | 5 |
| Relationships | 19 | 5 |
| Fee Patents | 2 | 1 |
| Correspondence | 19 | 3 |
| Legislative Actions | 4 | 4 |
| **Total items** | **128** | **47** |

## Document 3: 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing (id=695)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 83.5s | 36.7s |
| Valid JSON | Yes | Yes |
| Entities | 45 | 18 |
| Events | 19 | 3 |
| Financial Transactions | 3 | 2 |
| Relationships | 17 | 3 |
| Fee Patents | 2 | 1 |
| Correspondence | 8 | 3 |
| Legislative Actions | 3 | 1 |
| **Total items** | **97** | **31** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
