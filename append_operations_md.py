#!/usr/bin/env python3
"""
Append session 2026-05-03 methodology findings to OPERATIONS.md.

Adds five new sections covering:
  1. Vision recovery — dual-model methodology
  2. Database landscape (separate projects)
  3. BLM scope clarification
  4. Verify-when-cited workflow
  5. Sonnet vs Kimi v5 cross-extraction scan triage rules

Idempotent: if the additions block is already present, refuses to duplicate.
"""
from pathlib import Path

OPERATIONS_PATH = Path(
    "/Users/cwm6W/projects/exhaustive-extraction-pipeline/OPERATIONS.md"
)

ADDITIONS = """

---

## Vision recovery — dual-model methodology

For records where Sonnet text extraction has failed (handwriting, illegible scans, multi-allottee bundles), the established methodology (Task 4 decision from the pilot) is dual-model: run BOTH Sonnet vision and Qwen vision, then user arbitrates against the source page. Single-model vision can hallucinate (Sonnet hallucinated $7000 NW 1/4 for Charbonneau when source said $2000 partial allotment) or mis-spell (Qwen pilot: Trombley vs Trombla, Wencard vs Menard).

### Sonnet vision

```
python3 extract_single_pdf.py "<absolute-pdf-path>" \\
    --claude-only \\
    --vision \\
    --output validation_samples/<name>_vision/
```

- 30-90 seconds per record. Uses Claude Sonnet 4.6 vision.
- Output: `validation_samples/<name>_vision/vision_merged.json` with full v5 schema (entities, events, fee_patents, financial_transactions, relationships, testimony, etc.)
- Captures **per-allottee detail**: name, allotment, patent date, patent number, mechanism, buyer, sale price, mortgages, testimony content
- Failure mode: can fabricate confident-looking numerical values not in source. Always verify against source for any numeric claim.

### Qwen vision (HPC slurm)

The current slurm at `hpc/run_qwen_vl_recovery.slurm` is **narrow scope**: it only recovers handwritten name + allotment number + date + notary + state/county. It does NOT extract buyers, sale prices, patent numbers, mortgages, or substantive testimony content.

```
# Submit (from HPC):
sbatch /project/LawData/kimi-extraction/hpc/run_qwen_vl_recovery.slurm
```

- Reads `INPUT_DIR/manifest.csv` (currently pinned to the original 6-record pilot)
- Output: per-page JSONs in `/project/LawData/kimi-extraction/outputs/vision_recovery_sample/`
- Useful for: confirming or disputing handwritten name/allotment when Sonnet vision is also run
- NOT useful for: validating substantive case content (buyers, prices, dates) — Sonnet vision is the only tool we currently have that captures those

### When to use each

| Scenario | Tool |
|---|---|
| CAT_1 record (Sonnet text failed Name+Allotment) | BOTH Sonnet vision AND Qwen — name/allotment is what's at stake |
| Multi-allottee bundle splitting | Sonnet vision only — Qwen slurm doesn't capture per-allottee detail |
| Full-content recovery on handwritten record | Sonnet vision only — Qwen slurm prompt doesn't extract content |
| Suspected Sonnet vision hallucination (numerical claims) | User source-page verification — Qwen won't catch this since it doesn't extract those fields |

### Methodology lessons established 2026-05-03

- **Sonnet vision can fabricate numerical values on handwritten content.** Charbonneau case: Sonnet vision reported "$7,000 NW 1/4 sale" when source actually said "$2,000 partial allotment" with no buyer or date. Vision output looks structured and confident but cannot be trusted on specific numbers without source review.
- **Sonnet vision succeeds at multi-allottee bundle splitting.** Tonight's 6 bundles each had `fee_patents: 2` per Sonnet vision, with clean per-allottee names, allotments, patent dates, patent numbers, buyers, sale prices. Source-verified for names/allotments by user; substantive details (buyers, prices) preserved as extracted but not separately verified.
- **Both models can converge on a wrong answer.** Edward Little Eagle: Sonnet text="A0L-" garbled, Kimi v5="404", actual=Standing Rock 1371. Confident-looking convergence is not validation.

---

## Database landscape (separate projects)

These are SEPARATE projects with SEPARATE databases. Do not conflate.

- **`allotment_research`** — Federal Register patent claims, BLM patents, Murray tables, Wilson tables. Quantitative datasets behind `land-sales.iath.virginia.edu`. **Not the 2464 corpus.**
- **`crow_historical_docs`** — Crow Act project on Cloud SQL. **Not the 2464 corpus.**
- **`full_corpus_docs`** — proof-of-concept loader target.
- **The Circular 2464 extraction corpus has no dedicated database yet.** Lives in JSON only at `circular_2464_extractions/extractions/sonnet/` and `circular_2464_extractions/v3,v4,v5/`.

Future load (Path B per user decision 2026-05-03): per-record Sonnet documents linked to per-part Kimi entities via mentions table. Streamlit app waits until cleanup is complete.

---

## BLM scope clarification

BLM holds **patent issuance data only** — patent number, allottee name, acreage, date issued. Does NOT contain:
- Sale prices
- Buyer names
- Mortgage details
- Subsequent transactions

Sale prices and buyers live in **county deed records**, not BLM. Don't propose BLM lookups to resolve transaction-detail discrepancies — they can't.

BLM cross-reference IS appropriate for: confirming an allottee's allotment number when corpus extraction is uncertain; finding the patent issuance date; confirming acreage. User does these manually because BLM URLs are blocked from automated tooling.

---

## Verify-when-cited workflow

The corpus is a **research tool, not a forensic transcription** (user decision 2026-05-03). The book makes Role 2 (pattern-level) claims primarily, with selective Role 1 (atmospheric/illustrative) and Role 4 (network like Valandra) work. Role 3 (precise quantitative claims) is not the load-bearing analytical move.

**Implication:** corpus-wide cleanup is not a goal in itself. The records that matter are the ones cited in the book. Per-record source verification is required for those records (and was done for tonight's named individuals: Vanderbloom, Wallace, Hardin, Charbonneau, Mary Julia Neiss, the 12 split bundle records).

**What still requires systematic work:**
- Records where someone is hidden — multi-allottee bundles, missing-name records (CAT_1). Completion has value beyond per-record analytical use because someone shouldn't be missed if they're recoverable.
- Network actor name normalization (recurring buyers/lenders/recorders) — for Valandra-style searches across the corpus.

**What does NOT require systematic work:**
- Bulk patches from Sonnet/Kimi cross-reference disagreement scans. Both models can be wrong (Edward Little Eagle case). Use the scan as a triage tool, not a patch tool.
- 100-record sampling study or full BLM verification pass. Save for projects making Role 3 claims.

---

## Sonnet vs Kimi v5 cross-extraction scan

Script: `scan_sonnet_kimi_v5_disagreements.py`. Output: `sonnet_vs_kimi_v5_disagreements.tsv`.

Last run 2026-05-03: 647 records scanned (excluding 392 Pine Ridge), 210 agree, 112 disagree, 325 no Kimi match.

**Disagreement categories (sorted by analytical risk):**

1. Both models wrong (silent risk) — Edward Little Eagle case. Cannot be detected by the scan. Mitigation: source-verify any record before citing.
2. Real disagreements (both captured a value, values differ) — render source, decide.
3. Sonnet missing, Kimi has value — DO NOT auto-patch from Kimi. Both might be wrong. Treat as triage flag for source review.
4. Sonnet has value, Kimi missing — common; usually fine; spot-check if record matters.
5. Surname collision false matches (e.g., Sonnet=Henry Black, Kimi=Henry Chapman) — scan artifact, not a real disagreement. Filter or ignore.
6. Name variant differences (Philomena Beauvais Leighton vs Philomena Leighton née Beauvais) — same person, different spelling. Benign.

The scan is a **triage tool, not a patch tool**.
"""

MARKER = "## Vision recovery — dual-model methodology"


def main():
    if not OPERATIONS_PATH.exists():
        print(f"ERROR: {OPERATIONS_PATH} does not exist.")
        return

    with open(OPERATIONS_PATH) as f:
        existing = f.read()

    if MARKER in existing:
        print(
            f"Additions already present in OPERATIONS.md (marker found: '{MARKER}'). "
            "Refusing to duplicate."
        )
        return

    with open(OPERATIONS_PATH, "a") as f:
        f.write(ADDITIONS)

    print(f"Appended {len(ADDITIONS.splitlines())} lines to {OPERATIONS_PATH}")
    print()
    print("New sections:")
    print("  - Vision recovery — dual-model methodology (Sonnet + Qwen)")
    print("  - Database landscape (separate projects)")
    print("  - BLM scope clarification")
    print("  - Verify-when-cited workflow")
    print("  - Sonnet vs Kimi v5 cross-extraction scan (triage tool, not patch tool)")


if __name__ == "__main__":
    main()
