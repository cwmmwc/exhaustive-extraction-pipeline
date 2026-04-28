# Audit: compare_affidavit_extractions.py

**Date:** 2026-04-18 (revised)
**Auditor:** Claude Code (under review by PI McMillen and Claude Chat)
**Script version:** v2 matcher, verified denominator with assertion, post three bug fixes + matcher upgrade

## Purpose

This script computes recall, field completeness, and deduplication statistics for AI-extracted affidavit records compared against a hand-transcribed ground truth spreadsheet. Its output is the basis for quantitative claims in `MODEL_COMPARISON_SUMMARY.md` Section 12 about how well AI extraction performs relative to human transcription on Circular 2464 affidavits.

**Research claims that depend on this script's output (current verified values):**
- Sonnet recall on Pine Ridge Volume 1: **91%** (87/96 verified allottees)
- Opus recall: **91%** (87/96)
- Kimi recall: **58%** (56/96)
- Allotment number accuracy when populated: **100%** (Sonnet 82/82, Opus 82/82, Kimi 7/7)
- Allotment number capture rate: Sonnet **96%**, Opus **96%**, Kimi **17%**
- Consent completeness: Sonnet **100%**, Opus **100%**, Kimi **93%**
- Outcome completeness: Sonnet **95-97%**, Opus **97%**, Kimi **93%**
- The conclusion that Sonnet/Opus outperform Kimi on structured affidavit extraction

## Inputs

### Ground Truth

**File:** `/Users/cwm6W/Library/CloudStorage/OneDrive-UniversityofVirginia/Circular 2464/Replies to Circular 2464.xlsx`
**Sheet:** `Sheet1`
**Schema:** Row 1 is headers. Each subsequent row is one allottee. Fields used by this script:
- Column 0 (`r[0]`): Name — `str`, stripped. Rows where this is empty or None are skipped.
- Column 1 (`r[1]`): Tribe/Reservation — `str`. Used for filtering (e.g., "Pine Ridge").
- Column 3 (`r[3]`): Allotment number — `str`. **Used in two ways:** (1) to build the verified denominator by cross-referencing against "No." markers in the target volume's PDF text, and (2) for allotment accuracy spot-checks on matched pairs. NOT used in the name matcher itself.
- Column 4 (`r[4]`): Cancelled status — `str`. Not used in matching or quality metrics.
- Column 5 (`r[5]`): Refused/Protested text — `str`. Used for spot-check comparison.
- Column 7 (`r[7]`): Sold/Mortgaged text — `str`. Not used in matching.
- Column 8 (`r[8]`): Buyer text — `str`. Not used in matching.

**Assertion:** `assert os.path.exists(GT_PATH)` — script crashes if the file doesn't exist.

**Known limitation:** The ground truth is filtered by `args.reservation` using substring match (`reservation_filter in r.get('reservation', '')`). "Pine Ridge" matches "Pine Ridge Agency" and "Pine RIdge Agency" (with typo). It would also match a hypothetical "Pine Ridge Sub-Agency" or any other reservation containing the substring "Pine Ridge." In the current spreadsheet, this is not a problem — all Pine Ridge entries use "Pine Ridge Agency" (with two case variants). But the filter is not exact.

### Extraction Results

**Input format:** Each model's output is in a directory containing one or more JSON files. The script looks for files ending in `.json` that do NOT contain "chunk" in the filename (case-insensitive). This means it finds both `claude.json` (Claude models) and `Kimi K2.5.json` (Kimi).

**BUG HISTORY (Bug #1):** The initial comparison script used a glob pattern that matched only `Kimi K2.5.json` for all models. Claude writes to `claude.json`. This produced the "Kimi 94, Sonnet 8" error. The current script reads ALL non-chunk JSON files in the directory, which handles both naming conventions. If a directory contains BOTH `claude.json` and `Kimi K2.5.json`, both are loaded and their records are merged — this could produce double-counting if the same model wrote to both files. A WARNING is printed when multiple files are found.

**Assertion:** `assert os.path.isdir(dirpath)` — crashes if directory doesn't exist. `assert candidates` — crashes if no JSON files found, listing what files ARE present.

**Expected JSON schema:**
```json
{
  "affidavits": [
    {
      "name": "string or null",
      "allotment_number": "string, int, or null",
      "consent": "string or null",
      "sold": "string or null",
      "mortgaged": "string or null",
      ...other fields ignored by quality metrics...
    }
  ]
}
```

**Record filtering:** Records are dropped if:
- `a.get('name')` is falsy (None, empty string, 0)
- `str(a['name'])` is in `('full name of the deponent/allottee', '', '...', 'None')`

The first filter catches null/missing names. The second catches template rows where the prompt's example text was returned verbatim.

**Known limitation:** A record with `name: 0` (integer zero) would be dropped by the falsy check. This is unlikely but possible if the JSON parser interprets something as a number.

## Name Normalization

**Function:** `normalize_name(name)`

**Steps:**
1. `str(name).lower().strip()` — convert to string, lowercase, strip whitespace
2. `re.sub(r'\b(n[eé]e|formerly|nee)\b', '', n)` — remove "nee", "née", "formerly" as whole words
3. `re.sub(r'[—\-,\.\(\)\[\]]', ' ', n)` — replace em-dash, hyphen, comma, period, parens, brackets with space
4. `re.sub(r'\s+', ' ', n).strip()` — collapse multiple spaces to one, strip

**What this handles:**
- "Fannie Pilcher, nee Janis" → "fannie pilcher janis"
- "Laura Patton—nee Merrival" → "laura patton merrival"
- "Susie Dixon (nee Sears)" → "susie dixon sears"
- "Frank H. Twiss" → "frank h twiss"

**What this does NOT handle:**
- Name reordering: "Pilcher, Fannie" stays as "pilcher fannie" (last name first), which would NOT match "fannie pilcher" in the `names_match` function because `names_match` assumes the LAST word is the last name.
- Middle names vs maiden names: "fannie pilcher janis" has three parts — `names_match` treats "janis" as the last name and "fannie" as the first. If the ground truth has "Fannie Janis" (married name dropped), last names match. But if the ground truth has "Fannie Pilcher" (maiden name dropped), last names DON'T match. This is a false negative.
- Compound last names: "Mary Little Thunder" — `names_match` treats "thunder" as the last name. "Mary Littlethunder" would not match because "thunder" != "littlethunder".

## Name Matching

**Function:** `names_match(a, b)` (v2 matcher, default since 2026-04-18)

The v2 matcher includes two improvements over v1:

**Fix 1 — Suffix handling:**
- Tokens `jr`, `jr.`, `junior` normalize to `jr`. Tokens `sr`, `sr.`, `senior` normalize to `sr`. `ii`, `iii`, `iv` kept as-is. Defined in `_SUFFIX_MAP`.
- `_split_suffix(parts)` strips the suffix token from the name parts list and returns `(core_parts, suffix)`.
- Suffixes are stripped before last-name comparison.
- If BOTH names had a suffix, the suffixes must agree (jr↔jr, sr↔sr). Jr↔Sr is blocked. This prevents merging father/son pairs like John Cottier Sr. and John Cottier Jr.
- If only ONE name had a suffix, the match is allowed but requires exact first name match. This prevents "Benjamin Janis" (no suffix) matching "Bejmain Janis Jr." (suffix + typo) where these are different people.

**Fix 2 — Fuzzy last name:**
- If last names differ but `SequenceMatcher(a_last, b_last).ratio() > 0.85` AND first names match exactly, allow the match.
- Catches OCR/spelling variants: Mosseau↔Mousseau (0.93), Velandry↔Valandry (0.88).
- The exact-first-name constraint prevents over-matching: two people with similar last names but different first names will not match.

**Full v2 logic:**
1. Split both names by spaces. Apply `_split_suffix` to get core parts and suffix.
2. If either core has fewer than 2 parts: fall back to `SequenceMatcher` on core strings > 0.85.
3. Last name comparison: exact match on core last parts, OR fuzzy > 0.85 with exact first name (Fix 2).
4. Suffix check: if both have a suffix, they must agree. If only one has a suffix, require exact first name (Fix 1).
5. First name comparison: exact, initial (if ≤ 2 chars), or `SequenceMatcher > 0.7`.

**Verification of v2:** Tested against 6 predicted true matches (5 succeeded; 1 — Cottier Jr ↔ Cottier Sr — correctly blocked as father/son) and 2 predicted false positives (both correctly blocked). Also tested against all 96×96 GT-internal pairs: 0 new false positives introduced by v2 beyond what v1 produced.

**Retained:** `names_match_v1(a, b)` is in the code for reproducing earlier results. It uses exact last name match only, no suffix handling, no fuzzy last name.

**Known issue — false positives from initial matching:** Step 5 means that any two people with the same last name and matching first initial will be treated as the same person. This affects both dedup and GT matching.

**Known issue — compound names:** "Frank Bird Necklace" has last part "necklace". Compound-name handling is imperfect.

**This function is used in two contexts:** dedup (within one model's output) and GT matching (AI records against spreadsheet). Both use the same matcher, which is a deliberate design choice.

## Deduplication

**Function:** `dedup_records(records)`

**Algorithm:**
1. For each record, compute `normalize_name(record['name'])`.
2. Skip records where normalized name is empty, "unknown", or "none".
3. For each record, iterate through existing clusters. If `names_match(this_record, cluster_representative)` is True, add to that cluster. Otherwise, create a new cluster.
4. For each cluster, pick the "best" record:
   - Prefer records with a non-empty allotment_number (checked against a list of null-like values).
   - Among equally-allotmented records, prefer the one with the longest consent text.

**Known issue — order dependence:** The clustering is order-dependent. The dedup result depends on the order records appear in the JSON file. Reordering the records could produce different cluster counts.

**Known issue — the "unknown" filter drops real records.** Only records whose normalized name is exactly "unknown" or "none" are dropped. "Unknown (No. 356, female deponent)" is kept.

**Known issue — allotment number not used as dedup key.** Two records for "John Smith, allotment 123" and "John Smith, allotment 456" would be merged into one cluster. If these are actually two different people, this is a false merge. This is a known design limitation that has not yet been addressed.

## Quality Metrics

**Function:** `compute_quality(records)`

**Field presence rules (the `has_field` inner function):**

For `allotment_number`:
- Convert to string: `str(a.get(field, '') or '').strip()`
- Present if: length > 0 AND value (lowercased) is not in `('none', 'not specified', 'n/a', 'unknown', '', 'allotment number')`
- **This accepts any non-empty string, including short values like "18", "85".**
- **BUG HISTORY (Bug #2):** The original version used `len(val) > 5` for ALL fields, which filtered out short allotment numbers. Fixed by adding a special case for `allotment_number`.

For all other fields (`consent`, `sold`, `mortgaged`):
- Convert to string: `str(a.get(field, '') or '').strip()`
- Present if: length > 5 AND value (lowercased) is not in `('none', 'not specified', 'n/a', 'unknown')`
- **The length > 5 threshold means bare values like "Yes", "No", or "Sold" are counted as ABSENT.** This is intentional — a bare "yes" without quoted language is not a useful consent record.

**Known issue — integer allotment numbers:** If a model returns `allotment_number: 18` (integer), `str(18)` produces `'18'`, which passes correctly. Integer 0 would be counted as absent due to `0 or ''` evaluating to `''` in Python. Unlikely in practice.

## Recall Denominator

**Current method (verified cross-reference):** The script computes the denominator by cross-referencing GT allotment numbers against "No." markers in the target volume's PDF text. For each GT allottee filtered by reservation, the allotment number is checked against the set of "No. XXX" values found in the volume's text. Only allottees whose allotment numbers appear in the volume are included in the denominator.

For Pine Ridge Volume 1, this produces **96 verified allottees**. The script enforces this with an assertion:

```python
assert len(gt_filtered) == 96, (
    f"GT filtered to {len(gt_filtered)} records; audit specifies 96 "
    f"verified Volume 1 allottees. Check GT filter logic and verified "
    f"allottee list."
)
```

The `--vol1-pdf` argument provides the path to the Volume 1 PDF for cross-referencing. If no PDF is provided, the script falls back to the full reservation set with a warning about cross-volume contamination risk.

**Superseded method (proportional estimate):** The earlier version used `int(len(gt_filtered) * 148 / 431)` ≈ 126, assuming uniform affidavit distribution across volumes. This was 31% too high and was the source of Bug #4 (denominator drift).

**For Volumes 2 and 3:** The same cross-reference procedure applies. Each volume's PDF is searched for "No." markers, and the GT is filtered to allottees whose allotment numbers appear in that volume. Per-volume assertions should be added as the verified denominators are established.

## Sanity Checks Performed

1. **File existence:** Asserts on GT path, extraction directory, and presence of JSON files.
2. **Multiple-file warning:** Prints WARNING if multiple non-chunk JSON files exist in an extraction directory.
3. **Plausibility — over-extraction:** Warns if unique count exceeds 1.5× denominator.
4. **Plausibility — under-extraction:** Warns if unique count is below 0.3× denominator.
5. **Spot-checks:** Prints N random matched pairs (AI name + allotment vs GT name + allotment, plus consent text comparison) and N random unmatched AI records for manual review.
6. **Verified denominator (resolved 2026-04-18):** Cross-reference GT allotment numbers against "No." markers in the target volume PDF. Enforced by assertion for Pine Ridge Volume 1 (96). Replaces the superseded proportional estimate.
7. **Cross-volume contamination guard (resolved 2026-04-18):** GT is filtered to the verified volume-specific subset before matching. AI records can only match GT allottees whose allotment numbers appear in the target volume.
8. **Allotment number accuracy check (automated 2026-04-18):** `check_allotment_accuracy()` runs on every invocation. For matched pairs where both AI and GT have allotment numbers, values are compared after normalizing (strip "No.", "Allot.", whitespace, leading zeros). Reports exact matches, format-different matches, and mismatches. Any mismatches print the specific pairs. Validation run: Sonnet 85/87 exact + 0 format-different + 2 mismatched; Opus 79/86 exact + 5 format-different + 2 mismatched; Kimi 8/8 exact. The 2 mismatches in Sonnet/Opus are name-variant matches (Benjamin Janis 711↔709, Louis Mosseau 1859↔1856) where the v2 matcher correctly matched names but allotment numbers differ — these are edge cases of the fuzzy matcher, not extraction errors.
9. **repr() type consistency check (automated 2026-04-18):** `print_repr_diagnostic()` runs on every invocation. Prints `repr()` of allotment_number, consent, sold, mortgaged for the first 10 raw records per model. Confirms field types on every run.
10. **False-positive sample (automated 2026-04-18):** `print_false_positive_sample()` runs on every invocation. Prints 5 random matched pairs per model with AI name + allotment, GT name + allotment, and both consent texts for side-by-side review.

## Sanity Checks NOT Performed (Outstanding)

1. **No dedup quality check.** No automated verification that merged clusters are genuinely the same person. This requires a different approach (e.g., sampling merged clusters and verifying they're the same person) and is not blocking current work.

## Completed Changes (formerly "What Would Need to Change for Production Use")

1. **Allotment number accuracy check:** Automated on 2026-04-18 via `check_allotment_accuracy()`. Runs on every invocation. Reports exact, format-different, and mismatched counts. Prints specific mismatched pairs. *(Complete.)*
2. **Volume-specific GT counting:** Implemented via cross-reference of GT allotment numbers against PDF "No." markers. Enforced by assertion for Volume 1. *(Complete.)*
3. **Allotment-number-aware dedup:** Not yet implemented. Two records with same name but different allotment numbers are still merged. *(Outstanding.)*
4. **repr() diagnostic output:** Automated on 2026-04-18 via `print_repr_diagnostic()`. Runs on every invocation, prints first 10 records' key fields with `repr()`. *(Complete.)*
5. **Cross-volume contamination guard:** Implemented via verified denominator. GT is filtered to volume-specific allottees before matching. *(Complete.)*
6. **False-positive sample:** Automated on 2026-04-18 via `print_false_positive_sample()`. Prints 5 random matched pairs per model on every run. *(Complete.)*

## Summary of Bugs Found in This Script (2026-04-18)

| Bug | Effect | How Caught | Fix |
|-----|--------|-----------|-----|
| 1. Glob pattern matched `Kimi K2.5.json` for all models | Sonnet/Opus showed 8 records instead of 150+ | User asked for repr() check; then discovered the file naming | Changed to read all non-chunk JSON files in directory |
| 2. `has_field` used `len(val) > 5` for allotment numbers | Allotment numbers "18", "85" counted as absent | User pushed for careful dedup; post-dedup numbers contradicted pre-dedup | Added special case for allotment_number: `len(val) > 0` |
| 3. Pre-dedup numbers reported as if post-dedup | 96% allotment capture reported (was 155/161 pre-dedup, actually 10% post-dedup with bug #2) | User pointed out dedup was "awfully quick"; re-examination revealed timing issue | Quality metrics now computed on post-dedup records only |
| 4. Denominator drift — script retained proportional ~126 estimate after audit specified 96 | Recall inflated (93% vs actual 91%); cross-volume contamination reintroduced | User caught that 117 matches against 126 denominator was inconsistent with 6 predicted new matches | Replaced proportional estimate with verified cross-reference; added assertion |

All four bugs produced plausible-looking numbers. None were caught by the script's own sanity checks. All were caught by the user questioning the results.
