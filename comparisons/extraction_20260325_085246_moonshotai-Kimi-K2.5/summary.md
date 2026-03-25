# Model Comparison — Extraction

**Date:** 2026-03-25 09:03
**Models:** claude-sonnet-4-6, moonshotai/Kimi-K2.5

## Document 1: 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing (id=695)

| Metric | claude-sonnet-4-6 | moonshotai/Kimi-K2.5 |
|--------|--------|--------|
| Time | 84.8s | 59.8s |
| Valid JSON | Yes | Yes |
| Entities | 50 | 54 |
| Events | 17 | 15 |
| Financial Transactions | 3 | 5 |
| Relationships | 16 | 12 |
| Fee Patents | 2 | 1 |
| Correspondence | 7 | 7 |
| Legislative Actions | 2 | 2 |
| **Total items** | **97** | **96** |

## Document 2: 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters (id=798)

| Metric | claude-sonnet-4-6 | moonshotai/Kimi-K2.5 |
|--------|--------|--------|
| Time | 62.8s | 169.9s |
| Valid JSON | Yes | Yes |
| Entities | 42 | 28 |
| Events | 12 | 5 |
| Financial Transactions | 1 | 1 |
| Relationships | 23 | 7 |
| Fee Patents | 1 | 1 |
| Correspondence | 6 | 5 |
| Legislative Actions | 5 | 5 |
| **Total items** | **90** | **52** |

## Document 3: 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) (id=811)

| Metric | claude-sonnet-4-6 | moonshotai/Kimi-K2.5 |
|--------|--------|--------|
| Time | 151.7s | 122.7s |
| Valid JSON | Yes | Yes |
| Entities | 41 | 37 |
| Events | 34 | 14 |
| Financial Transactions | 10 | 8 |
| Relationships | 22 | 10 |
| Fee Patents | 2 | 3 |
| Correspondence | 23 | 14 |
| Legislative Actions | 5 | 4 |
| **Total items** | **137** | **90** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
