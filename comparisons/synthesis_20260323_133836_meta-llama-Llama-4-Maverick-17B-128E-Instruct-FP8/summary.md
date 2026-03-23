# Model Comparison — Synthesis

**Date:** 2026-03-23 13:40
**Models:** meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8
**Corpus:** 368 documents, ~147,264 tokens per prompt
**Database:** 388 docs, 36892 entities, 960 fee patents

## Question 1

> Tell me about Harlow Pease and his relationship with the Crow generally and with Section 2 of the Crow Act specifically.

| Metric | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|
| Time | 26.1s |
| Word count | 708 |
| Unique [Doc N] citations | 2 |
| Dollar amounts cited | 0 |
| Acreage mentions | 1 |
| Specific dates | 1 |
| Bill/statute refs | 0 |
| Has 'Prove' section | True |
| Has 'Suggest' section | True |
| Has 'Gaps' section | True |

## Question 2

> What were the primary mechanisms of forced fee patent issuance on the Crow Reservation? Who were the key actors and what were the outcomes?

| Metric | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|
| Time | 38.6s |
| Word count | 846 |
| Unique [Doc N] citations | 17 |
| Dollar amounts cited | 0 |
| Acreage mentions | 1 |
| Specific dates | 0 |
| Bill/statute refs | 2 |
| Has 'Prove' section | True |
| Has 'Suggest' section | True |
| Has 'Gaps' section | True |

## Question 3

> How much Crow land was lost and to whom? Quantify the scale of land dispossession using specific acreages, dollar amounts, and transaction counts from the documents.

| Metric | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 |
|--------|--------|
| Time | 35.9s |
| Word count | 857 |
| Unique [Doc N] citations | 13 |
| Dollar amounts cited | 2 |
| Acreage mentions | 4 |
| Specific dates | 0 |
| Bill/statute refs | 0 |
| Has 'Prove' section | True |
| Has 'Suggest' section | True |
| Has 'Gaps' section | True |

---

## How to Evaluate

Read the full outputs side by side. The metrics above are suggestive but the real test is qualitative:

1. **Evidence grounding** — Does every claim cite specific documents with specific facts?
2. **Cross-document synthesis** — Does it connect information across multiple documents, or just summarize?
3. **Analytical depth** — Does it distinguish proven vs. suggested vs. unknown?
4. **Accuracy** — Spot-check citations against the archive.
5. **Gaps analysis** — Does it identify what's missing, not just what's there?
