# Model Comparison — Extraction

**Date:** 2026-03-23 14:23
**Models:** claude-sonnet-4-6, meta-llama/Llama-4-Scout-17B-16E-Instruct

## Document 1: 1950–1956: BIA Files on Turtle Mountain Chippewa Public Domain Allotments in Carter County, Montana (id=691)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Scout-17B-16E-Instruct |
|--------|--------|--------|
| Time | 150.4s | 0.3s |
| Valid JSON | Yes | NO |
| Entities | 93 | — |
| Events | 32 | — |
| Financial Transactions | 10 | — |
| Relationships | 52 | — |
| Fee Patents | 7 | — |
| Correspondence | 10 | — |
| Legislative Actions | 1 | — |
| **Total items** | **205** | **0** |

## Document 2: 1954–1955: Crow Allottee Fee Patent Applications and Supervised Land Sales (id=667)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Scout-17B-16E-Instruct |
|--------|--------|--------|
| Time | 113.9s | 0.3s |
| Valid JSON | Yes | NO |
| Entities | 53 | — |
| Events | 20 | — |
| Financial Transactions | 5 | — |
| Relationships | 24 | — |
| Fee Patents | 11 | — |
| Correspondence | 20 | — |
| Legislative Actions | 1 | — |
| **Total items** | **134** | **0** |

## Document 3: 1957–1961: BIA Correspondence on Crow Reservation Land Sale Acreage Limits (id=23)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Scout-17B-16E-Instruct |
|--------|--------|--------|
| Time | 112.9s | 0.3s |
| Valid JSON | Yes | NO |
| Entities | 51 | — |
| Events | 38 | — |
| Financial Transactions | 3 | — |
| Relationships | 20 | — |
| Fee Patents | 2 | — |
| Correspondence | 14 | — |
| Legislative Actions | 7 | — |
| **Total items** | **135** | **0** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
