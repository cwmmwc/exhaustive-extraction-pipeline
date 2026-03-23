# Model Comparison — Extraction

**Date:** 2026-03-23 15:46
**Models:** claude-sonnet-4-6, meta-llama/Llama-3.3-70B-Instruct-Turbo

## Document 1: 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing (id=695)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-3.3-70B-Instruct-Turbo |
|--------|--------|--------|
| Time | 85.9s | 28.4s |
| Valid JSON | Yes | Yes |
| Entities | 49 | 20 |
| Events | 17 | 2 |
| Financial Transactions | 5 | 0 |
| Relationships | 17 | 3 |
| Fee Patents | 2 | 0 |
| Correspondence | 7 | 2 |
| Legislative Actions | 3 | 1 |
| **Total items** | **100** | **28** |

## Document 2: 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters (id=798)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-3.3-70B-Instruct-Turbo |
|--------|--------|--------|
| Time | 53.5s | 9.0s |
| Valid JSON | Yes | Yes |
| Entities | 37 | 10 |
| Events | 12 | 2 |
| Financial Transactions | 1 | 0 |
| Relationships | 12 | 2 |
| Fee Patents | 1 | 1 |
| Correspondence | 5 | 2 |
| Legislative Actions | 5 | 1 |
| **Total items** | **73** | **18** |

## Document 3: 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) (id=811)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-3.3-70B-Instruct-Turbo |
|--------|--------|--------|
| Time | 134.6s | 11.1s |
| Valid JSON | Yes | Yes |
| Entities | 43 | 20 |
| Events | 34 | 4 |
| Financial Transactions | 10 | 1 |
| Relationships | 19 | 2 |
| Fee Patents | 2 | 1 |
| Correspondence | 19 | 1 |
| Legislative Actions | 5 | 0 |
| **Total items** | **132** | **29** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
