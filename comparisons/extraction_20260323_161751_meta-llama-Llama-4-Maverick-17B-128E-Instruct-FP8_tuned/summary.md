# Model Comparison — Extraction

**Date:** 2026-03-23 16:24
**Models:** claude-sonnet-4-6, meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8

## Document 1: 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing (id=695)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 88.7s | 21.8s |
| Valid JSON | Yes | Yes |
| Entities | 52 | 14 |
| Events | 17 | 5 |
| Financial Transactions | 4 | 0 |
| Relationships | 18 | 4 |
| Fee Patents | 2 | 0 |
| Correspondence | 8 | 3 |
| Legislative Actions | 3 | 1 |
| **Total items** | **104** | **27** |

## Document 2: 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters (id=798)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 60.5s | 25.2s |
| Valid JSON | Yes | Yes |
| Entities | 39 | 12 |
| Events | 12 | 5 |
| Financial Transactions | 1 | 0 |
| Relationships | 22 | 3 |
| Fee Patents | 1 | 1 |
| Correspondence | 6 | 5 |
| Legislative Actions | 5 | 5 |
| **Total items** | **86** | **31** |

## Document 3: 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) (id=811)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 129.2s | 55.0s |
| Valid JSON | Yes | Yes |
| Entities | 41 | 20 |
| Events | 35 | 7 |
| Financial Transactions | 10 | 4 |
| Relationships | 16 | 5 |
| Fee Patents | 2 | 1 |
| Correspondence | 20 | 3 |
| Legislative Actions | 4 | 3 |
| **Total items** | **128** | **43** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
