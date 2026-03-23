# Model Comparison — Extraction

**Date:** 2026-03-23 16:02
**Models:** claude-sonnet-4-6, meta-llama/Llama-3.3-70B-Instruct-Turbo

## Document 1: 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing (id=695)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-3.3-70B-Instruct-Turbo |
|--------|--------|--------|
| Time | 81.8s | 16.3s |
| Valid JSON | Yes | Yes |
| Entities | 48 | 41 |
| Events | 17 | 6 |
| Financial Transactions | 4 | 2 |
| Relationships | 17 | 5 |
| Fee Patents | 2 | 1 |
| Correspondence | 7 | 2 |
| Legislative Actions | 3 | 2 |
| **Total items** | **98** | **59** |

## Document 2: 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters (id=798)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-3.3-70B-Instruct-Turbo |
|--------|--------|--------|
| Time | 57.7s | 12.2s |
| Valid JSON | Yes | Yes |
| Entities | 35 | 12 |
| Events | 12 | 5 |
| Financial Transactions | 1 | 1 |
| Relationships | 25 | 4 |
| Fee Patents | 1 | 1 |
| Correspondence | 6 | 3 |
| Legislative Actions | 5 | 4 |
| **Total items** | **85** | **30** |

## Document 3: 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) (id=811)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-3.3-70B-Instruct-Turbo |
|--------|--------|--------|
| Time | 133.9s | 22.3s |
| Valid JSON | Yes | Yes |
| Entities | 40 | 35 |
| Events | 33 | 5 |
| Financial Transactions | 10 | 5 |
| Relationships | 15 | 6 |
| Fee Patents | 2 | 3 |
| Correspondence | 20 | 4 |
| Legislative Actions | 5 | 1 |
| **Total items** | **125** | **59** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
