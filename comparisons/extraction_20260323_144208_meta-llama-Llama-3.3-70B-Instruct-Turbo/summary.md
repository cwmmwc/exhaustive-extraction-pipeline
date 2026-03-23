# Model Comparison — Extraction

**Date:** 2026-03-23 14:47
**Models:** claude-sonnet-4-6, meta-llama/Llama-3.3-70B-Instruct-Turbo

## Document 1: 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing (id=695)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-3.3-70B-Instruct-Turbo |
|--------|--------|--------|
| Time | 84.9s | 10.5s |
| Valid JSON | Yes | Yes |
| Entities | 46 | 26 |
| Events | 16 | 7 |
| Financial Transactions | 4 | 3 |
| Relationships | 20 | 8 |
| Fee Patents | 2 | 1 |
| Correspondence | 7 | 2 |
| Legislative Actions | 3 | 1 |
| **Total items** | **98** | **48** |

## Document 2: 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters (id=798)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-3.3-70B-Instruct-Turbo |
|--------|--------|--------|
| Time | 56.4s | 13.1s |
| Valid JSON | Yes | Yes |
| Entities | 38 | 35 |
| Events | 12 | 11 |
| Financial Transactions | 1 | 2 |
| Relationships | 12 | 6 |
| Fee Patents | 1 | 1 |
| Correspondence | 5 | 5 |
| Legislative Actions | 5 | 4 |
| **Total items** | **74** | **64** |

## Document 3: 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) (id=811)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-3.3-70B-Instruct-Turbo |
|--------|--------|--------|
| Time | 136.7s | 16.5s |
| Valid JSON | Yes | Yes |
| Entities | 42 | 32 |
| Events | 31 | 10 |
| Financial Transactions | 10 | 5 |
| Relationships | 17 | 5 |
| Fee Patents | 2 | 1 |
| Correspondence | 21 | 3 |
| Legislative Actions | 5 | 3 |
| **Total items** | **128** | **59** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
