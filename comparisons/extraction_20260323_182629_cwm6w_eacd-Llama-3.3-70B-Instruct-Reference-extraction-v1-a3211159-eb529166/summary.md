# Model Comparison — Extraction

**Date:** 2026-03-23 18:32
**Models:** claude-sonnet-4-6, cwm6w_eacd/Llama-3.3-70B-Instruct-Reference-extraction-v1-a3211159-eb529166

## Document 1: 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing (id=695)

| Metric | claude-sonnet-4-6 | cwm6w_eacd/Llama-3.3-70B-Instruct-Reference-extraction-v1-a3211159-eb529166 |
|--------|--------|--------|
| Time | 88.3s | 18.6s |
| Valid JSON | Yes | Yes |
| Entities | 51 | 21 |
| Events | 16 | 6 |
| Financial Transactions | 4 | 3 |
| Relationships | 22 | 4 |
| Fee Patents | 2 | 1 |
| Correspondence | 8 | 2 |
| Legislative Actions | 3 | 1 |
| **Total items** | **106** | **38** |

## Document 2: 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters (id=798)

| Metric | claude-sonnet-4-6 | cwm6w_eacd/Llama-3.3-70B-Instruct-Reference-extraction-v1-a3211159-eb529166 |
|--------|--------|--------|
| Time | 53.2s | 19.3s |
| Valid JSON | Yes | Yes |
| Entities | 39 | 26 |
| Events | 12 | 5 |
| Financial Transactions | 1 | 1 |
| Relationships | 15 | 3 |
| Fee Patents | 1 | 1 |
| Correspondence | 5 | 3 |
| Legislative Actions | 5 | 4 |
| **Total items** | **78** | **43** |

## Document 3: 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) (id=811)

| Metric | claude-sonnet-4-6 | cwm6w_eacd/Llama-3.3-70B-Instruct-Reference-extraction-v1-a3211159-eb529166 |
|--------|--------|--------|
| Time | 140.4s | 22.3s |
| Valid JSON | Yes | Yes |
| Entities | 44 | 22 |
| Events | 34 | 7 |
| Financial Transactions | 10 | 3 |
| Relationships | 20 | 3 |
| Fee Patents | 2 | 2 |
| Correspondence | 22 | 3 |
| Legislative Actions | 5 | 1 |
| **Total items** | **137** | **41** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
