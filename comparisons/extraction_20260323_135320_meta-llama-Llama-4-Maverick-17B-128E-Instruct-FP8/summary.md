# Model Comparison — Extraction

**Date:** 2026-03-23 14:01
**Models:** claude-sonnet-4-6, meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8

## Document 1: 1960: Sen. Mansfield Correspondence on Northern Cheyenne Land Development and School Construction (id=734)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 113.8s | 57.0s |
| Valid JSON | NO | Yes |
| Entities | — | 25 |
| Events | — | 7 |
| Financial Transactions | — | 3 |
| Relationships | — | 4 |
| Fee Patents | — | 0 |
| Correspondence | — | 4 |
| Legislative Actions | — | 2 |
| **Total items** | **0** | **45** |

## Document 2: 1987–1989: Litigation File, Crow Tribe of Montana v. United States — Section 2 Land Purchase Violations (id=736)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 109.0s | 47.7s |
| Valid JSON | NO | Yes |
| Entities | — | 43 |
| Events | — | 6 |
| Financial Transactions | — | 2 |
| Relationships | — | 4 |
| Fee Patents | — | 1 |
| Correspondence | — | 3 |
| Legislative Actions | — | 2 |
| **Total items** | **0** | **61** |

## Document 3: 1956: House Subcommittee Hearing on Bills to Amend the Crow Allotment Act of 1920 (id=281)

| Metric | claude-sonnet-4-6 | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|--------|
| Time | 97.1s | 35.1s |
| Valid JSON | Yes | Yes |
| Entities | 57 | 25 |
| Events | 17 | 6 |
| Financial Transactions | 5 | 0 |
| Relationships | 22 | 5 |
| Fee Patents | 3 | 1 |
| Correspondence | 3 | 1 |
| Legislative Actions | 10 | 4 |
| **Total items** | **117** | **42** |

---

## How to Evaluate

1. **Valid JSON** — Can the output be parsed? This is pass/fail.
2. **Completeness** — Open the source document and spot-check: did the model find the same people, transactions, and dates?
3. **v3 types** — Did it extract fee patents, correspondence, and legislative actions as structured records (not just entities)?
4. **Accuracy** — Are the extracted values correct? Check names, dates, dollar amounts against the source text.
5. **Hallucination** — Did it invent entities or events not in the source text?
