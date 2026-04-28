# Section 12 Correction Appendix

Structured log of five measurement bugs found and corrected during the Circular 2464 comparison work on 2026-04-18. Each bug produced plausible-looking numbers that were narrated as findings before being caught. Referenced from the final paragraph of MODEL_COMPARISON_SUMMARY.md Section 12.

---

## Bug 1: "Kimi 94, Sonnet 8" — Filename Glob Mismatch

**What the script reported:** Kimi extracted 94 affidavit records from Pine Ridge Volume 1. Sonnet extracted 8. Opus extracted 8. This was narrated as evidence that Kimi excels on repetitive structured extraction — the same pattern as its fee patent advantage on the CCF 56074 document.

**What actually happened:** The comparison script used a glob pattern that matched `Kimi K2.5.json` for every model. Claude models write their output to `claude.json`, not `Kimi K2.5.json`. The glob found the Kimi file in the Kimi directory (94 records) and found nothing in the Sonnet and Opus directories (0 records, but the script loaded a partial file or default). The "8 records" for Sonnet/Opus came from an earlier partial run's output that happened to be in the directory.

**How it was caught:** The user asked for a `repr()` check on allotment number fields. During preparation for that check, the actual filenames in each directory were examined, revealing that `claude.json` existed alongside `Kimi K2.5.json` and the script was reading the wrong one.

**What replaced it:** The script now reads ALL non-chunk JSON files in each extraction directory, handling both naming conventions. A WARNING is printed when multiple files are found. The corrected Sonnet count was 157 records (Volume 1, 10K chunks), not 8.

**Duration of the error:** The incorrect "Kimi 94, Sonnet 8" numbers existed in MODEL_COMPARISON_SUMMARY.md for approximately 3 hours and shaped a full paragraph of analytical interpretation about Kimi's superiority on repetitive forms. The interpretation was completely backwards.

---

## Bug 2: "Sonnet 96% Allotment Capture" — Dedup-Timing Bug

**What the script reported:** Sonnet captured allotment numbers on 96% of records (150/157 on Volume 1). This was narrated as the key quality differentiator between Sonnet and Kimi: "The allotment number gap is the finding that matters most for research use. 18% vs 92-96% is an order-of-magnitude difference."

**What actually happened:** The quality metrics (`with_allotment`, `with_consent`, `with_any_outcome`) were computed on pre-dedup records — the raw 157 records including duplicates from overlapping chunks. High-quality records that appeared in two overlapping chunks were counted twice in the numerator, inflating the field-completeness percentage. After deduplication, the unique count was lower and the percentage changed.

**How it was caught:** The user noted that the deduplication step ran "awfully quickly" and pushed for a more careful fuzzy dedup. When the dedup was redone properly, the post-dedup allotment percentage changed from the pre-dedup figure, revealing that the metrics had been computed at the wrong stage.

**What replaced it:** Quality metrics are now computed on post-dedup unique records only. The corrected allotment capture rate for Sonnet on Volume 1 is 96% (128/132 unique), which happens to be close to the pre-dedup figure — but this is coincidental, and the mechanism of the bug would have produced larger distortions on datasets with higher duplication rates.

**Duration of the error:** Approximately 2 hours. The error was compounded by Bug 3 (below), which was discovered during the same correction cycle.

---

## Bug 3: "0-10% Across All Models, Document-Structure Problem" — Field-Length Filter

**What the script reported:** After the dedup fix (Bug 2), allotment number capture appeared to be 0-10% across ALL models — Kimi, Sonnet, and Opus alike. This was narrated as: "Allotment numbers are missing across all models (0-10%). This was initially reported as a Kimi-specific weakness. After deduplication, the gap nearly disappears. The allotment numbers in these Pine Ridge affidavits are on cover sheets or in document headers that don't consistently make it into the chunked text. This is a document-structure problem, not a model-quality difference."

**What actually happened:** The `has_field()` function in the quality-metrics code used `len(val) > 5` as the threshold for all fields, including `allotment_number`. Pine Ridge allotment numbers are short strings: "18", "85", "211", "709". These have lengths of 2-3 characters, which fail the `> 5` check. The function was correctly counting allotment numbers as "absent" because of the length filter, not because they were actually absent.

**How it was caught:** The user pushed for a `repr()` check on allotment number fields for all models. The `repr()` output showed Sonnet records with `allotment_number='18'`, `allotment_number='85'` — clearly populated, clearly short. The `has_field` function's `len(val) > 5` threshold was then identified as the cause.

**What replaced it:** `has_field` now has a special case for `allotment_number`: present if `len(val) > 0` (not `> 5`) and the value is not a null-like string. The corrected Sonnet allotment capture rate is 96% (Volume 1); Kimi's is 17%. The "document-structure problem" narrative was wrong — it was a measurement bug. The allotment gap between Sonnet and Kimi is real.

**Duration of the error:** Approximately 1 hour. This bug was discovered in the same correction cycle as Bug 2, during the process of verifying the dedup fix.

---

## Bug 4: Denominator Drift — Proportional Estimate Retained After Audit

**What the script reported:** After the v2 matcher was implemented and all three field-level bugs were fixed, the script was rerun and reported Sonnet recall as 93% (117/126). This looked like an improvement from the audited 85% (82/96), suggesting the v2 matcher had found 35 additional matches.

**What actually happened:** The script was still using the proportional denominator (~126 = 369 × 148/431) instead of the verified cross-reference denominator (96). The audit document specified 96 as the correct denominator and included code for an assertion to enforce it. But the assertion had not been added to the script — the audit described intended behavior that the code didn't implement. The 117 matches included cross-volume contamination: AI records from Volume 1 matching GT allottees from Volumes 2 and 3 whose names happened to appear in Volume 1's text.

**How it was caught:** The user noted that 117 matches against a 126 denominator was inconsistent with the v2 matcher diff table, which predicted only 6 new matches (82 baseline + 6 = 88, not 117). The 29-match discrepancy could not be explained by the matcher change alone, pointing to a denominator or GT-set problem.

**What replaced it:** The script now computes the verified denominator by cross-referencing GT allotment numbers against "No." markers in the target volume's PDF text. For Pine Ridge Volume 1, this produces 96 allottees, enforced by an assertion:

```python
assert len(gt_filtered) == 96, (
    f"GT filtered to {len(gt_filtered)} records; audit specifies 96 "
    f"verified Volume 1 allottees."
)
```

The `--vol1-pdf` argument provides the PDF path for the cross-reference. If no PDF is provided, the script falls back to the full reservation set with a warning.

The corrected recall with the v2 matcher against the verified 96 denominator is 87/96 = 91% for Sonnet (5 new matches from v2, not 35).

**Duration of the error:** Approximately 30 minutes. This was the fourth bug of the session and was caught faster than the others because the user had developed a pattern of checking match counts against predictions.

---

## Bug 5: Kimi Targeted Prompt — Infrastructure vs Model Signal

**What the first experiment showed:** A three-step targeted prompt (Step 1: find allotment numbers, Step 2: find deponent names, Step 3: extract fields) was designed to address Kimi's 17% allotment capture rate. On Pine Ridge Volume 1 at 10K chunks via RC GenAI, only 2 of 25 chunks produced valid output. The two successful chunks showed correct allotment capture — the prompt worked when Kimi finished. But 23 chunks returned empty SSE responses.

**What actually happened:** The stepwise instruction structure ("Step 1... Step 2... Step 3...") triggered Kimi's chain-of-thought reasoning mode. In reasoning mode, Kimi spends its token budget on internal reasoning before producing output. The RC GenAI endpoint timed out or returned empty content before Kimi finished reasoning. This was an infrastructure interaction, not a prompt quality problem.

**The v2 revision:** A single-pass prompt was written with the same allotment-number emphasis but no stepwise structure. The opening instruction — "Respond with valid JSON only. Do not explain your reasoning." — suppressed reasoning mode. The v2 prompt produced 43 records from 16 of 25 chunks on first run. The 9 failed chunks exhibited six distinct failure modes:

- Chunks 1, 4: **Truncated JSON** (111 and 774 chars) — Kimi started correct JSON but RC GenAI cut the response short
- Chunks 13, 17: **Ellipsis placeholders** — Kimi returned `{...}` schema shapes instead of actual data
- Chunk 20: **Template placeholder** — `{"affidavits": [...]}` with literal `[...]`
- Chunk 23: **Reasoning mode** — placeholder followed by "Let me analyze the document text..."
- Chunks 7, 12, 21: **Empty SSE** — no response content at all

**Retry results:** A retry wrapper (up to 3 attempts per chunk) recovered all 9 failed chunks. 6 succeeded on first retry, 2 on second, 1 on third. All failures were transient — no chunk failed consistently in the same way, confirming these were RC GenAI infrastructure issues, not content-specific extraction failures.

**Final numbers with retry:** 25/25 chunks merged, 70 raw records, 69 unique, 50 matched against 96 GT = 52% recall. 100% allotment capture, 49/50 allotment accuracy (98%), 100% consent and outcome completeness.

**What the investigation revealed:** Kimi's per-record quality on this document type is competitive with Sonnet when prompt engineering addresses the allotment-linking failure mode. Kimi's recall is not competitive at 10K chunks on this infrastructure. The recall gap (52% vs Sonnet's 91%) is not a prompt problem — it reflects how many distinct deponents Kimi identifies per chunk. The targeted prompt transforms every record Kimi does extract into a complete, accurate record. It does not help Kimi find more records.

**Duration of the investigation:** Approximately 4 hours across two prompt versions, one full extraction, one retry run, and six diagnostic steps.

---

## Pattern

All five bugs share the same structure:

1. A script computed a number.
2. The number looked plausible.
3. The number was reported.
4. A narrative was built around the number.
5. The user questioned the number.
6. Investigation revealed a measurement error.
7. The narrative was wrong.

The bugs differed in severity (Bug 1 reversed the direction of a finding; Bug 3 changed a model-specific finding into a structural claim; Bugs 2 and 4 inflated percentage figures by moderate amounts; Bug 5 initially appeared to be a model limitation but was an infrastructure interaction) but shared the same failure mode: the system produced output that looked reasonable, and the output was accepted without verifying the mechanism that produced it.

The corrective — the audit document with enforced assertions — converts several of these bugs from silent failures to loud failures. Bug 4 specifically would be caught by the denominator assertion. Bugs 1 and 3 would require different safeguards (input-file verification and field-threshold specification, respectively). Bug 2 would require an assertion on the timing of quality-metric computation relative to deduplication. Bug 5 required a retry wrapper with per-attempt failure classification to distinguish infrastructure transients from content-specific failures.

The methodological lesson for AI-assisted historical research: the measurement layer — the scripts that count extraction results, compute recall rates, and generate comparisons — is the most bug-prone layer in the system, more bug-prone than the extraction layer itself. The extraction models produce consistent output; the scripts that evaluate that output produce inconsistent evaluations depending on implementation details that aren't visible in the output.
