# Sonnet vs Kimi K2.5: Survey of Conditions Part 33

**Date:** 2026-04-13
**Document:** Part 33 — San Diego & San Francisco, CA (June–July 1934)
**Doc ID:** 91
**Pages:** 205 | **Characters:** 722,044 | **Chunks:** 21 (40K chars, 5K overlap)
**Document type:** Congressional hearing testimony (Senate Subcommittee on Indian Affairs)

## Purpose

The entire Survey of Conditions corpus (41 parts) was extracted with Kimi K2.5 via UVA RC GenAI. No Claude comparison existed for Survey documents. This test runs Claude Sonnet on Part 33 under identical chunking conditions to establish how the two models perform on hearing testimony — a document type not represented in the original Crow benchmark.

## Raw Extraction Counts (apples-to-apples, pre-dedup)

| Category | Kimi K2.5 | Claude Sonnet | Kimi % of Sonnet |
|----------|----------:|--------------:|:----------------:|
| entities | 1,022 | 1,376 | 74% |
| events | 156 | 398 | 39% |
| financial_transactions | 90 | 297 | 30% |
| relationships | 163 | 455 | 36% |
| fee_patents | 5 | 0 | — (Kimi wins) |
| correspondence | 52 | 106 | 49% |
| legislative_actions | 43 | 92 | 47% |
| testimony | 50 | 130 | 38% |
| taxes | 2 | 2 | 100% |
| mortgages | 0 | 3 | — |
| **total** | **1,583** | **2,859** | **55%** |

## Context: How This Compares to the Crow Benchmarks

The original model comparison (March 2026, documented in `MODEL_COMPARISON_SUMMARY.md`) tested three Crow Nation documents. Kimi's performance varied dramatically by document type:

| Document type | Kimi % of Claude | Notes |
|---------------|:----------------:|-------|
| Fee patent records (CCF 56074) | **125–159%** | Kimi found 268 allottees vs Claude's 169 |
| BIA administrative (Doc 695) | **~99%** | Effectively tied |
| Legislative correspondence (Doc 798) | **~70%** | Weaker on multi-party narrative chains |
| Multi-decade litigation (Doc 811) | **~66%** | Weakest on long causal sequences |
| **Crow overall (3-doc average)** | **~73%** | |
| **Survey Part 33 (hearing testimony)** | **55%** | New result — this test |

The 55% result is **consistent with the established pattern**: Kimi is weakest on narrative-heavy, testimony-rich documents where extraction requires following conversational exchanges, tracking who said what to whom, and identifying implicit relationships across pages of dialogue. Congressional hearing transcripts are the purest form of this document type.

The 73% headline from the Crow benchmarks was an average pulled up by fee patent documents, where Kimi exceeds Claude.

## Qualitative Differences

### Testimony
- **Witnesses found:** Kimi 41 unique, Sonnet 94 unique, 31 overlap
- Sonnet creates ~1.4 testimony entries per witness (multiple topics per witness). Kimi creates ~1.2 (typically one entry per witness covering their entire testimony).
- Sonnet captures more secondary witnesses and brief exchanges. Kimi focuses on substantial testimony.

### Events
- Sonnet finds 2.6x more events. The gap is in recognizing discrete actions within testimony: delegation trips, tribal votes, agency decisions described by witnesses.
- Kimi's events focus on the hearing sessions themselves and major documented actions.

### Financial Transactions
- The 3.3x gap (297 vs 90) is the largest category difference. Hearing testimony references many small transactions (lease payments, wages, per capita distributions) that Sonnet extracts individually. Kimi captures the larger, more explicit transactions.
- **Unlike the Crow benchmark**, Kimi does NOT appear to be over-extracting in this category. The CCF 56074 test showed Kimi inflating events and financial_transactions by creating one per allottee; that pattern is absent here.

### Fee Patents
- Kimi found 5; Sonnet found 0. The 5 Kimi found are real — brief references to fee patent issuance in witness testimony. Sonnet apparently did not classify these as fee_patents, likely categorizing the same information under events or financial_transactions.
- This is consistent with the Crow finding: Kimi has a specific, superior ability to recognize fee patent case histories even when they appear as passing references.

### Entities
- Closest category at 74% (1,022 vs 1,376). Both models identify the core cast of characters. Sonnet picks up more minor figures mentioned once in passing testimony.

## What This Means for the Survey Corpus

The Survey of Conditions is 41 volumes of congressional hearing testimony — precisely the document type where Sonnet outperforms Kimi most. Kimi extracted ~55% of what Sonnet would find on this representative volume.

However, three considerations:

1. **Kimi found the fee patents Sonnet missed.** Even in a testimony-heavy document, Kimi's fee patent recognition caught 5 that Sonnet classified differently. Across 41 volumes, those add up.

2. **The 55% is on raw item counts, not analytical value.** Many of the additional Sonnet items are minor events, secondary witnesses, and small financial transactions. The core narrative — who testified, what they said, what policy actions were described — is captured by both models.

3. **Cost:** Kimi extraction via RC GenAI is free (university HPC allocation). Sonnet extraction of the full 41-volume Survey at ~$3-5 per volume would be ~$125-200.

## Recommendation

For research questions that depend on **comprehensive extraction** (e.g., counting every financial transaction, mapping every witness relationship), a Sonnet re-extraction of high-priority Survey volumes would capture significantly more. For questions about **major testimony, policy actions, and fee patents**, the existing Kimi extraction is sufficient and actually superior on the fee patent dimension.

The optimal approach would be selective: identify the 5-10 Survey volumes most critical to the monograph argument and re-extract those with Sonnet, rather than re-extracting all 41.
