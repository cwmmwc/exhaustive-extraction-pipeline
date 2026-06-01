# OPERATIONS.md — Project Runbook

**Purpose.** This file documents the *how-to* for common tasks in this project. README.md and EXPERIMENTS.md describe what exists and why; this file documents what to *run*, in what order, with what arguments, and what gotchas to watch for. It is meant to be read at the start of every working session so operational context isn't rediscovered each time.

**Maintenance rule.** When you discover an operational fact that isn't obvious from script docstrings — naming conventions, undocumented dependencies, gotchas — add it here. The cost of writing it down once is small; the cost of rediscovering it every session is large.

---

## Quick orientation

**Project root:** `/Users/cwm6W/projects/exhaustive-extraction-pipeline/`

**HPC hostname:** `login.hpc.virginia.edu` (UVA Rivanna). User: `cwm6w`. SSH: `ssh cwm6w@login.hpc.virginia.edu`.

**HPC project dir:** `/project/LawData/kimi-extraction/`. Layout:
- `pdfs/circular_2464/` — source PDFs (mirrored from local; recursive structure)
- `hpc/` — slurm scripts (NOT `code/hpc/`)
- `code/` — Python scripts uploaded for HPC use
- `outputs/circular_2464_{v3,v4,v5}/` — Kimi extraction results
- `logs/` — slurm stdout/stderr

**Core corpus:** `circular_2464_extractions/extractions/sonnet/` — one JSON file per allottee record. Primary editable corpus.

**Multi-model parallel extractions** (cross-reference whenever a Sonnet record looks suspect):
- `circular_2464_extractions/v3/RG 75 1929 circular 2464 part N/Kimi K2.5.json` — Kimi schema v3
- `circular_2464_extractions/v4/.../Kimi K2.5.json` — schema v4
- `circular_2464_extractions/v5/.../Kimi K2.5.json` — schema v5 (most recent)
- `circular_2464_extractions/sonnet_corpus/.../claude.json` — Sonnet whole-corpus
- `circular_2464_extractions/circular_2464_affidavit_5k/.../Kimi K2.5.json` — 5k Kimi
- `circular_2464_extractions/circular_2464_affidavit_page/.../Kimi K2.5.json` — page-level Kimi
- `circular_2464_extractions/vision_recovery_sample/qwen/` — Qwen2.5-VL pilot (6 records)
- `circular_2464_extractions/vision_test/qwen_full_ledger/` — Qwen full-ledger

**Source PDFs:** `circular_2464_extractions/circular_2464_affidavit_page/` — directory per part (parts 1, 2, 3, 6, 7, 8, 9, 10, 11 [labeled "2564"], 12, 13). **Parts 4 and 5 are not in this directory by default.**

**Split sub-PDFs:** `circular_2464_extractions/split_documents/{affidavits,questionnaires,agency_narratives,ledgers}/`. Manifest at `split_documents/manifest.csv`.

**Naming convention for record JSONs:** `{partN|pine_ridge_volN}_{type}_{NNN}.json`. Multi-allottee bundle splits: `_{NNN}a.json`, `_{NNN}b.json` (Vanderbloom + Wallace, 2026-04-30).

---

## Task: Add a new part to the corpus (Sonnet local + Kimi HPC)

**Scenario.** A part of the source archive isn't in the corpus yet, and you have the source PDF locally.

### Sonnet local track

**1. Classify pages locally**

```
python3 classify_pages.py "<absolute-pdf-path>" \
  --output-dir circular_2464_extractions/classifications_kimi_corpus \
  --label <LABEL> \
  --sonnet-only
```

`<LABEL>` convention: `RG_75_1929_circular_2464_part_N`. Part 11 uses `2564`.

**2. GOTCHA: rename classification file**

The splitter's `load_classifications` reads `*_classifications_kimi.csv` only. Sonnet writes `_sonnet.csv`. Copy:

```
cp circular_2464_extractions/classifications_kimi_corpus/<LABEL>_classifications_sonnet.csv \
   circular_2464_extractions/classifications_kimi_corpus/<LABEL>_classifications_kimi.csv
```

**3. Add part to `split_corpus.py`**

`LABEL_TO_PDF` and `LABEL_SHORT` dicts are hardcoded. Add to both:

```python
"RG_75_1929_circular_2464_part_N": "/absolute/path/to/RG 75 1929 circular 2464 part N.pdf",
"RG_75_1929_circular_2464_part_N": "partN",
```

The default `PDF_BASE` points to OneDrive. Local-only PDFs need absolute path overrides.

**4. Run the splitter**

```
python3 split_corpus.py --labels <LABEL>
```

**5. Sonnet extraction**

```
python3 run_full_corpus_extraction.py
```

Idempotent for already-processed records.

### Kimi HPC track

**A. Upload PDF**

```
scp "/path/to/RG 75 1929 circular 2464 part N.pdf" \
    cwm6w@login.hpc.virginia.edu:/project/LawData/kimi-extraction/pdfs/circular_2464/Replies\ to\ Circular\ 2464/
```

**B. Submit slurm job**

```
ssh cwm6w@login.hpc.virginia.edu \
    'sbatch /project/LawData/kimi-extraction/hpc/run_circular2464.slurm'
```

The script walks `pdfs/circular_2464/` recursively and skips PDFs that already have `Kimi K2.5.json` output across v3/v4/v5. So adding a new part requires only the upload — no script edits.

Monitor:
```
ssh cwm6w@login.hpc.virginia.edu 'squeue -u cwm6w'
```

**C. Pull results back**

```
for v in v3 v4 v5; do
  rsync -avz \
    "cwm6w@login.hpc.virginia.edu:/project/LawData/kimi-extraction/outputs/circular_2464_${v}/RG 75 1929 circular 2464 part N/" \
    "/Users/cwm6W/projects/exhaustive-extraction-pipeline/circular_2464_extractions/${v}/RG 75 1929 circular 2464 part N/"
done
```

---

## Task: Patch a single record

**Pattern.**

1. Read the record:
   ```
   python3 -c "import json; d = json.load(open('circular_2464_extractions/extractions/sonnet/<filename>.json')); print(json.dumps(d, indent=2))"
   ```

2. **Cross-reference parallel extractions before patching.**
   ```
   python3 << 'EOF'
   import json
   path = "circular_2464_extractions/v5/RG 75 1929 circular 2464 part N/Kimi K2.5.json"
   with open(path) as f:
       data = json.load(f)
   for e in data.get("entities", []):
       if "<name>" in json.dumps(e):
           print(json.dumps(e, indent=2))
   EOF
   ```

3. Render source PDF for confirmation:
   ```
   mkdir -p validation_samples/<name>_check
   pdftoppm -r 150 \
     circular_2464_extractions/split_documents/<type>/<filename>.pdf \
     validation_samples/<name>_check/<filename> -png
   open validation_samples/<name>_check/*.png
   ```

4. Patch script template (drop in project root):
   ```python
   import json
   from pathlib import Path
   PATH = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline/circular_2464_extractions/extractions/sonnet/<filename>.json")
   with open(PATH) as f:
       record = json.load(f)
   e = record["extraction"]
   previous = e.get("<field>", "")
   e["<field>"] = "<new-value>"
   e["NOTES"] = (e.get("NOTES") or "") + " | <CORRECTION_TAG> YYYY-MM-DD: <rationale>"
   record.setdefault("recovery_notes", []).append({
       "date": "YYYY-MM-DD",
       "type": "<task-type>",
       "method": "<source-of-truth>",
       "fields_corrected": ["<field>", "NOTES"],
       "previous_values": {"<field>": previous},
       "corrected_values": {"<field>": "<new-value>"},
       "user_confirmed": True,
   })
   with open(PATH, "w") as f:
       json.dump(record, f, indent=2, ensure_ascii=False)
   ```

---

## Task: Multi-allottee bundle split

**Scenario.** A source PDF contains multiple allottees on sequential pages, captured as one record.

**Pattern (Vanderbloom + Wallace convention, 2026-04-30):**
- New records: `<filename>a.json`, `<filename>b.json`, etc.
- Each record gets full `extraction` content for that one allottee
- `pre_split_sonnet_extraction` field archives the original
- `recovery_notes` contains a `task5_record_split_from_multi_allottee_bundle` entry with `split_origin` pointing to source PDF, page number, sibling record
- Original record file is removed

Reference: `split_part11_questionnaire_002.py`.

---

## Task: Bulk allotment recovery from NOTES regex

Sonnet often captures allotment numbers in NOTES (labeled "document number," "file reference," etc.) instead of the structured field.

**Diagnostic:** `diagnose_notes_vs_allotment_v2.py` enumerates candidates.

**Apply scripts:** `apply_no_pattern_patches_v2.py` (48 records), `apply_phrasing_holdouts.py` (3 records), `apply_holdout_patches.py` (4 records).

**Pattern recognized:** "No. NNNN" / "Document No. NNNN" / "document numbered No. NNNN" / "document reference No. NNNN".

**Pattern NOT recognized (manual review):** "File reference: 5-NNN-N" (CCF case file, not allotment).

---

## Task: Cross-reference Sonnet vs Kimi disagreements

```
grep -l "<name>" circular_2464_extractions/extractions/sonnet/*.json
find /Users/cwm6W/projects/exhaustive-extraction-pipeline -name "*.json" -exec grep -l "<name>" {} + 2>/dev/null
```

Second command catches Kimi v3/v4/v5, sonnet_corpus, and other parallel extractions.

**Known disagreement modes:**
- Sonnet hallucinates fabricated names ("Philadelphia Lightfoot McCauley" for Philomena Leighton)
- Sonnet captures patent number in Allotment field (Anna Blackbird 35918→3518; Hannah Hardin 715412 → real allotment 42)
- Sonnet captures Circular number 2464 as allotment (Nicholas Trombla — real allotment 464)
- Sonnet swaps allotments between adjacent allottees (Mary Julia Neiss 1463 vs Alphonse Charbonneau 1466 — Kimi v5 had it right)
- Both models can fail completely on illegible-claimed pages (Vanderbloom + Wallace — neither captured anything; user source-page review required)
- Qwen tends to mis-spell surnames (Trombley vs Trombla, Wencard vs Menard)

---

## Task: Render a source PDF for review

```
mkdir -p validation_samples/<name>_check
pdftoppm -r 150 \
  circular_2464_extractions/split_documents/<type>/<filename>.pdf \
  validation_samples/<name>_check/<filename> -png
open validation_samples/<name>_check/*.png
```

`<type>`: `affidavits`, `questionnaires`, `agency_narratives`, `ledgers`.

For pages outside `split_documents/`:
```
find circular_2464_extractions/ -name "<filename>*" 2>/dev/null
```

---

## Recurring gotchas

1. **`split_corpus.py` only reads `*_classifications_kimi.csv`.** Copy `_sonnet.csv` to `_kimi.csv` if Sonnet did the classifying.
2. **`split_corpus.py` has hardcoded `LABEL_TO_PDF` and `LABEL_SHORT` dicts.** Add new parts to both.
3. **`split_corpus.py`'s `PDF_BASE` points to OneDrive.** Local-only PDFs need absolute path overrides.
4. **Part 11's directory uses "2564" not "2464"** (source archive typo).
5. **Parts 4 and 5 source PDFs are not in OneDrive by default.** Project root or Desktop.
6. **`extractions/sonnet/` is the corpus; `sonnet_corpus/` and `sonnet_affidavit/` are EARLIER experimental extractions.**
7. **Kimi extractions use `entities + events` schema.** Sonnet uses record-style. Same record looks different in each.
8. **Multi-model search is essential.** Cross-reference Kimi v5 and source PDF before assuming Sonnet is right.
9. **A.W. Leech's cover letter (Shawnee master list) explicitly says many allottees never had detail reports submitted.** Absence from corpus ≠ lookup failure.
10. **BLM URLs are blocked from automated tooling.** User does BLM lookups; pastes results.
11. **`run_circular2464.slurm` walks `pdfs/circular_2464/` recursively and auto-skips processed PDFs across v3/v4/v5.** No edits needed when adding a new part.
12. **HPC hostname is `login.hpc.virginia.edu`, not `rivanna.hpc.virginia.edu`.**
13. **HPC slurm scripts live at `/project/LawData/kimi-extraction/hpc/`, NOT `/code/hpc/`.**

---

## Reference files

- `README.md` — project overview
- `EXPERIMENTS.md` — research notes
- `CORPUS_METHODOLOGY_entity_resolution.md` — entity resolution methodology (in `/mnt/user-data/outputs/`; not folded into project yet)
- `split_documents/manifest.csv` — record manifest
- `classifications_kimi_corpus/` — page classifications by part
- `hpc/run_circular2464.slurm` — Kimi v3/v4/v5 sweep
- `hpc/run_circular2464_kimi_targeted_v2.slurm` — Kimi targeted single-pass on Pine Ridge Vol 1
- `hpc/run_qwen_vl_recovery.slurm` — Qwen2.5-VL recovery

---

## Database landscape (separate projects)

These are SEPARATE projects with SEPARATE databases. Do not conflate.

- **`allotment_research`** — Federal Register patent claims, BLM patents, Murray tables, Wilson tables. Quantitative datasets behind `land-sales.iath.virginia.edu`. **Not the 2464 corpus.**
- **`crow_historical_docs`** — Crow Act project on Cloud SQL. **Not the 2464 corpus.**
- **`full_corpus_docs`** — proof-of-concept loader target (currently 1 Claude + 1 Kimi POC record).
- **The Circular 2464 extraction corpus has no dedicated database.** It lives only in JSON files at `circular_2464_extractions/extractions/sonnet/` and `circular_2464_extractions/v3/`, `v4/`, `v5/`.

Cross-corpus entity queries (the "who buys what across allotments" analysis) require either:
1. Loading the 2464 JSON corpus into a new database, then `dedup_entities_phase1.py` + `explore_graph.py`
2. Inline Python scripts that walk the v5 Kimi JSON files directly


---

## Vision recovery — dual-model methodology

For records where Sonnet text extraction has failed (handwriting, illegible scans, multi-allottee bundles), the established methodology (Task 4 decision from the pilot) is dual-model: run BOTH Sonnet vision and Qwen vision, then user arbitrates against the source page. Single-model vision can hallucinate (Sonnet hallucinated $7000 NW 1/4 for Charbonneau when source said $2000 partial allotment) or mis-spell (Qwen pilot: Trombley vs Trombla, Wencard vs Menard).

### Sonnet vision

```
python3 extract_single_pdf.py "<absolute-pdf-path>" \
    --claude-only \
    --vision \
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


---

## Qwen-VL server is a separate slurm — must be started first, EVERY TIME

The Qwen vision pipeline has **two required slurm jobs** that must run in order:

1. **`start_qwen_vl_server.slurm`** — starts the Qwen2.5-VL-72B model server on a GPU node. Writes its address (hostname:port) to `/project/LawData/kimi-extraction/logs/qwen_vl_address.txt` once ready. Takes 5-10 min to load model after the GPU allocation comes through.

2. **`run_qwen_vl_recovery.slurm`** (or other batch slurm) — reads the address file, sends pages to the server for processing.

The server is **never just running**. It must be submitted before every batch:

```
sbatch /project/LawData/kimi-extraction/hpc/start_qwen_vl_server.slurm
```

**Stale address file warning.** The address file at `/project/LawData/kimi-extraction/logs/qwen_vl_address.txt` persists from previous runs. After a server job ends, the address file retains the old hostname:port — but no server is responding at that address. Check the file's timestamp:

```
ls -la /project/LawData/kimi-extraction/logs/qwen_vl_address.txt
```

If the timestamp is not today, the address is stale and any recovery slurm submission will sit in the wait loop until the server starts and updates the file. Always submit the server slurm before the recovery slurm; never assume the server is up.

**Verify server is responding:**
```
curl -s --max-time 5 "http://$(cat /project/LawData/kimi-extraction/logs/qwen_vl_address.txt | tr -d '\n')/health" && echo " OK" || echo " UNREACHABLE"
```

Returns " OK" if the server is up. " UNREACHABLE" means submit `start_qwen_vl_server.slurm`.

---

## CAT_1 vision recovery — full batch workflow

For systematic CAT_1 work (records where Sonnet text extraction missed both Name and Allotment), the established workflow is:

### Step 1 — Re-enumerate current CAT_1 candidates

```
python3 enumerate_task5_candidates.py 2>&1 | head -100
```

This walks the corpus and lists CAT_1, CAT_2, CAT_3 records. CAT_1 = both Name and Allotment "not stated".

**Filter administrative correspondence first.** Some CAT_1 records are agency cover letters from superintendents to the Commissioner — these have no allottee Name/Allotment to recover (they're correspondence, not allottee records). Reclassify these to `Document type: agency_correspondence` so they don't get vision-recovered. Tonight 6 such records were caught at this step.

### Step 2 — Build the batch directory locally

```
python3 prep_cat1_vision_batch.py
```

This script:
- Reads CAT_1 candidates from extractions
- Locates each one's sub-PDF in split_documents/
- Renders each page to PNG at 200 DPI
- Writes `circular_2464_extractions/vision_recovery_cat1/manifest.csv`

Records where the source PDF doesn't exist in split_documents/ get reported but skipped. If those are real allottee records (not administrative correspondence), the parent part PDF must be located and the relevant pages extracted manually.

### Step 3 — Run BOTH models in parallel

**Sonnet vision (local):**
```
python3 run_cat1_sonnet_vision.py
```
Sequential, ~30-90s per record. Output: `validation_samples/cat1_sonnet_vision/<rid>/vision_merged.json`. Captures full v5 schema (entities, fee_patents, events, etc.).

**Qwen vision (HPC) — TWO SLURM SUBMISSIONS REQUIRED:**

```
# Step 3a: from laptop, upload the batch
scp -r circular_2464_extractions/vision_recovery_cat1 \
    cwm6w@login.hpc.virginia.edu:/project/LawData/kimi-extraction/code/circular_2464_extractions/

# Step 3b: SSH to HPC interactively
ssh cwm6w@login.hpc.virginia.edu

# Step 3c: from HPC, start the server FIRST
sbatch /project/LawData/kimi-extraction/hpc/start_qwen_vl_server.slurm

# Step 3d: wait for server. Check periodically:
squeue -u cwm6w
ls -la /project/LawData/kimi-extraction/logs/qwen_vl_address.txt

# When the address file timestamp is today AND `curl /health` returns OK, proceed.

# Step 3e: from HPC, submit the recovery batch (parameterized for new dir)
sbatch \
  --export=ALL,INPUT_DIR=/project/LawData/kimi-extraction/code/circular_2464_extractions/vision_recovery_cat1,OUT_DIR=/project/LawData/kimi-extraction/outputs/vision_recovery_cat1 \
  /project/LawData/kimi-extraction/hpc/run_qwen_vl_recovery.slurm
```

### Step 4 — Pull Qwen results back

```
rsync -avz \
    "cwm6w@login.hpc.virginia.edu:'/project/LawData/kimi-extraction/outputs/vision_recovery_cat1/'" \
    circular_2464_extractions/vision_recovery_cat1/qwen_outputs/
```

### Step 5 — Compare and arbitrate

```
python3 compare_cat1_vision.py
```

Produces `cat1_vision_comparison.tsv`. Verdicts:
- `agree` — both models read the same name + allotment. Most reliable.
- `disagree_name` / `disagree_allot` — models read different values. Source verification required.
- `sonnet_only` / `qwen_only` — one model captured nothing. Source verification required.
- `qwen_has_X_sonnet_missing` / `sonnet_has_X_qwen_missing` — partial matches. Triage.
- `neither_has_data` — both models missed. Source review may reveal it's a non-allottee document (cover letter, index, etc.) that should be reclassified.

For each non-`agree` verdict: render source page, decide which value (if either) is correct, patch the corpus record.

**Don't trust agreement alone.** Edward Little Eagle case shows both models can converge on a wrong answer. Even `agree` verdicts deserve spot-checking when the record will be cited in the book.


---

## Three-extraction architecture (clarified 2026-05-04)

The Circular 2464 corpus has been processed by three parallel extraction layers, each with different units of analysis and different schemas. Understanding the distinction matters for cleanup decisions and for the eventual database load.

**Layer 1 — Sonnet text (per-allottee, flat schema)**
- Location: `circular_2464_extractions/extractions/sonnet/*.json`
- ~1040 records, one per allottee sub-PDF
- Schema: flat `extraction` object with `Name`, `Allotment number`, `Tribe/Reservation`, `Post Office Address`, `Date`, `Document type`, `NOTES`
- Per-allottee retrieval is clean: grep by name, get the record
- Cross-allottee structured queries are not supported; buyer/transaction/mortgage data lives in `NOTES` as free text

**Layer 2 — Kimi text v3/v4/v5 (per-part, v5 schema)**
- Location: `circular_2464_extractions/v3/`, `v4/`, `v5/`
- ~13 records per version, one per whole-part PDF (each part PDF contains many allottees)
- Schema: rich v5 with structured tables (`entities`, `fee_patents`, `financial_transactions`, `events`, `relationships`, `correspondence`, `legislative_actions`, `testimony`, `mortgages`)
- Cross-allottee structured queries work natively (e.g., aggregate `subsequent_buyer` across the corpus)
- Per-allottee retrieval requires entity-level filtering and join back to source pages

**Layer 3 — Sonnet vision (per-record, v5 schema)**
- Location: `validation_samples/<stem>_vision/vision_merged.json` and `validation_samples/cat1_sonnet_vision/<stem>/vision_merged.json`
- ~38 records (multi-allottee bundle splits + CAT_1 recovery batch)
- Schema: rich v5 (same as Kimi), but generated per-allottee via `extract_single_pdf.py --vision --claude-only`
- Combines per-allottee retrieval with structured cross-allottee data

**Important methodology consequence:** when patching a record, we now check all three layers where applicable. The Sonnet text layer is the canonical corpus record. The Kimi v5 layer provides cross-corpus cross-checks. The Sonnet vision layer provides structured per-record data.

---

## Vision extraction retrofit (2026-05-04)

After running Sonnet vision recovery on the 12 multi-allottee bundles (2026-05-03) and 26 CAT_1 records (2026-05-04), the structured v5 data was initially collapsed into the corpus records' `NOTES` field as free text — losing the structured fee_patents, financial_transactions, mortgages, etc.

The retrofit script (`retrofit_sonnet_vision_v2.py`) walks corpus records and adds the structured v5 data as a new top-level key `vision_extraction_v5` on each record. The flat `extraction` object remains unchanged for backwards compatibility; the structured data is available alongside it for database load and analytical queries.

For multi-allottee bundle records (`_NNNa.json` / `_NNNb.json`), the retrofit filters relevant tables (fee_patents, financial_transactions, mortgages, relationships, testimony, taxes) by allottee name match — so each sibling record only carries data about its own allottee.

A `_retrofit_filter_note` field on each retrofitted record's `vision_extraction_v5` documents what was filtered.

Usage notes:
- The retrofit is idempotent for non-bundle records (skipped if already present)
- For bundle records, it always re-filters (so the latest filter logic takes effect)
- Re-run `retrofit_sonnet_vision_v2.py` if vision content is updated for any record

---

## New document type: agency_buyer_report

Established 2026-05-04 for `part11_agency_narrative_003` (M.B. Gregg, Frank Ktilienk, authored by Supt. H.E. Wright).

**Purpose:** distinguishes agency narrative records that report on land buyers/lessors from those that report on allottees, and from administrative correspondence.

**Distinction from related types:**
- `agency_narrative` — agency report on an allottee's case
- `agency_correspondence` — superintendent transmittal letter to Commissioner of Indian Affairs (the 6 records reclassified 2026-05-03)
- `agency_buyer_report` — agency narrative describing buyers/lessors as the primary subject (no allottee Name/Allotment to recover; named actors are the data)

When patching `agency_buyer_report` records, set:
- `Name` = "(buyer report — see NOTES for named actors)"
- `Allotment number` = "(not applicable — non-allottee record)"
- `Tribe/Reservation` = the reservation context (e.g., "Crow Creek")
- `Document type` = "agency_buyer_report"
- NOTES enriched with per-actor details (name, role, location, agency context)

This type supports future Valandra-style buyer-network queries by giving them a discoverable filter.

---

## Continuation page convention

Some splitter cuts produced two corpus records for the same source document — typically a lead record with the main content and a continuation record with the trailing biographical/health/signature page.

**Examples (2026-05-04):**
- `part1_questionnaire_020` (Louise Drapeau, pages 1-3 of her 5-page Form 5-105) and `part1_questionnaire_021` (page 5, the trailing page)
- `part1_questionnaire_013` (Margaret DeCory main questionnaire) and `part1_questionnaire_022` (continuation page with biographical/health section)

**Decision rule:** retain BOTH records as separate corpus entries (do NOT delete the continuation page). Patch the continuation page with the same Name/Allotment/Tribe as the lead. Cross-reference both directions in NOTES.

**Distinguish from duplicates:** if the continuation page's content is genuinely a duplicate of pages already in the lead (overlapping/repeated content, not a different page section), delete it as a duplicate. Example: `part1_questionnaire_016` (Anna Shuck) was a partial duplicate of `part1_questionnaire_015` and was deleted with q016 content archived in q015's recovery_notes. Different from continuation pages where each record covers different page content.

---

## CAT_1 batch — completion summary (2026-05-03 and 2026-05-04)

Original CAT_1 list (from `enumerate_task5_candidates.py`): 34 records (Sonnet missed both Name and Allotment).

**Pre-batch reclassifications (2026-05-03):**
- 6 administrative cover letters → `agency_correspondence`
- 1 known answer (Mrs. Addie Easton Payne) patched directly from Shawnee master list
- 1 record (`part10_affidavit_004`) excluded as likely Hannah Hardin signature page (her main record at part10_questionnaire_012)

**Vision recovery batch (2026-05-04):** 26 records processed
- Sonnet vision (local): 26/26 succeeded
- Qwen vision (HPC): 49/49 pages succeeded (after server-job-then-recovery-job dual-submit pattern)
- Comparison via `compare_cat1_vision.py` produced verdict TSV: 8 agree, 11 disagree_name, 2 disagree_allot, 5 partial/empty

**Resolutions (all 26):**
- 23 records patched with verified Name/Allotment/Tribe (mix of dual-model agreement, user verification of disagreements, and cross-references to records elsewhere in the corpus)
- 1 duplicate removed (`part1_questionnaire_016`)
- 1 reclassified to `agency_buyer_report` (`part11_agency_narrative_003`)
- 1 left as blank Circular 2464 template (`part3_questionnaire_022`)

**Methodology lessons established:**
- Dual-model vision recovery (Sonnet + Qwen) does work, but each model has distinct failure modes (Sonnet over-confident on numerical content; Qwen prone to surname mis-spellings and place-name confabulation)
- User source-page verification is essential where models disagree — the disagreement is the signal, not the answer
- Cross-references across the corpus (master lists, sibling records, prior project research) often resolve disagreements without further source review
- Continuation pages and duplicates are distinct situations requiring different patches

---

## Pending workstream: Sonnet + Kimi merge for database loader

**Architecture (per Claude Code design note 2026-05-04, following `merge_index_cards.py` precedent):**

Three extraction layers merge at the per-allottee row, with provenance preserved:
1. Per-allottee Sonnet records → canonical rows (one per allottee)
2. Per-part Kimi v5 entities/fee_patents/transactions → join to canonical rows by name+allotment matching
3. Sonnet vision structured fields (~38 records) → already retrofitted onto canonical rows as `vision_extraction_v5`

**Output:** new `circular_2464` PostgreSQL database with its own schema, dropdown entry in Streamlit, graph support via `explore_graph.py --db circular_2464`.

**Open design questions to resolve before implementation:**

1. **Name+allotment matching has known failure modes.** The Sonnet vs Kimi v5 disagreement scan found 112 disagreements in 647 records. Where Sonnet has Allot=A and Kimi has Allot=B for the same person, the join either fails or produces duplicates. Need: confidence-scored fuzzy matching, plus a manual override table for known mismatches (e.g., Edward Little Eagle = 1371 not 404).

2. **Per-part Kimi entities don't always carry allotment context.** Many Kimi `entities` of type "person" have no allotment in their context string. Either accept partial joins (some Kimi entities never link to a Sonnet row) or run an enrichment pass pulling allotments from adjacent Kimi `fee_patents` rows mentioning the same name.

3. **Vision retrofit covers 38 records; ~1002 don't have vision data.** The merge needs a precedence rule for which extraction layer's value wins when multiple sources disagree.

4. **Multi-allottee bundle handling.** The bundle splits we did (Decory/Whiting, Real Rider/Peters, etc.) created `_NNNa.json` / `_NNNb.json` records — each has filtered vision data, but the underlying source PDF was the same. The Kimi v5 entities might list both allottees in the same part-level extraction. Need: clear linkage from Kimi entities back to the correct sibling record.

5. **Continuation pages.** Records like `part1_questionnaire_021` (Drapeau continuation) and `part1_questionnaire_022` (DeCory continuation) share an allottee with their lead records. The merge needs to consolidate them into a single canonical row (or carry them as separate rows with a `continuation_of` link).

**Reference:** `comparisons/UNIFIED_INDEX_CARDS_MERGE.md` and `merge_index_cards.py` worked through equivalent issues for the slips corpus. Same reasoning applies here. Read those before designing the loader.

**Status:** design only. No implementation yet. Loader writes to a new database, doesn't modify existing corpus records.


---

## NO QUICK FIXES — academic-historian principles (2026-05-04)

This is not a business project, a startup, or a resource-constrained
sprint. It is an academic historian's research apparatus, where the
deliverable is scholarly argument grounded in defensible source-level
evidence. The standards that apply:

**Correctness over speed.** When a data question has multiple plausible
answers, the answer is "render the source and verify" — not "pick the
likeliest one and move on." Speed is not a goal. Coverage is not a
goal. Defensibility is the goal.

**Complexity is preserved, not collapsed.** Real historical records
contain ambiguity, partial information, contradictions across sources,
and edge cases that don't fit clean schemas. The job is to capture
that complexity, not paper over it. When two records appear to be
about the same person but disagree, that disagreement is data — not
something to resolve by picking one and discarding the other.

**Detail is preserved.** Substantive content (a quoted phrase, a
buyer's name, a sale price, a marginal note) goes into the record
even if it doesn't fit a column. NOTES exists for this. Vision
extractions preserve the full v5 schema even when the flat schema
doesn't have a column for a given field.

**Resources are not constraints unless explicitly asked.** Do not
propose decisions framed by:
  - Time ("we should do X tonight rather than wait for Y")
  - Money / API spend ("X costs $0.05 per record so we should batch")
  - Compute ("the queue is deep so let's defer this")
  - Convenience ("X is faster, even though Y is more rigorous")

If a tradeoff between rigor and resources is genuinely material,
state it explicitly and ask. Do not preemptively choose the cheap
or fast option.

**No quick fixes for complex problems.** The disagreement scan
(Sonnet vs Kimi v5) is a triage tool, not a patch tool. Both models
can be wrong (Edward Little Eagle case). Bulk patches that replace
visibly-garbled values with confident-looking-but-unverified values
remove the signal of failure and replace it with silent error. This
is not acceptable. Per-record source verification is the workflow,
even when slow.

**The corpus is a research tool, not a forensic database.** Pattern-
level claims (Role 2) and atmospheric/illustrative evidence (Role 1)
are the load-bearing analytical moves. Precise quantitative claims
(Role 3) are not. But within the records that are kept, the standard
is correctness — including capturing what is unknown as unknown,
not as "not stated" when it should be "not visible on this page" or
"contradicted by another source."

**Default behaviors that follow from these principles:**

- Always render the source page when there is genuine doubt
- Always preserve original extraction artifacts (`pre_split_sonnet_extraction`,
  `recovery_notes`) before patching — never silently overwrite
- Always record the methodology used (which models, which sources,
  which user verifications) so the audit trail is intact
- When in doubt about which of two interpretations is correct, say so
  in NOTES rather than committing to one
- When two records appear redundant, distinguish duplicates (delete)
  from continuation pages (keep both, cross-reference)
- Never propose `agency_correspondence` or any other umbrella reclass-
  ification when a more specific type captures the analytical reality
  (e.g., `agency_buyer_report`)


---

## Shawnee Indian Agency master list — workstream complete (2026-05-04)

The 36 rows in `circular_2464_extractions/extractions/sonnet/part10_shawnee_*.json` represent the Shawnee Indian Agency master list of allottees flagged for Circular 2464 investigation (transmitted by Supt. A.W. Leech, March 20, 1929). All 36 rows have explicit data state.

**Schema decision (option A):** The `Tribe/Reservation` field carries the actual tribe (e.g., 'Citizen Potawatomie'), not the agency name. Agency context ('Shawnee Indian Agency') is recoverable from the filename pattern (`part10_shawnee_*`) and preserved in NOTES. This treats the agency administrative structure and the actual tribal affiliation as separate analytical facts.

**Workstream results:**

- **30 rows resolved** with allotment + actual tribe:
  - 12 rows backfilled from matched affidavit/questionnaire records elsewhere in the corpus (10 via automated triage, 2 via manual triage for married-name and deceased-filing variants)
  - 18 rows backfilled from Christian's federal-register-app patents database (https://federal-register-app-996830241007.us-east1.run.app/patents)
  - All 30 confirmed allottees are **Citizen Potawatomie**

- **6 rows marked unresolved** with `Allotment number = "(not in patents database)"` and `Tribe/Reservation = "Shawnee Indian Agency (actual tribe unknown)"`:
  - Julia Bourasa Riley (row 04)
  - Nellie Bourasa (row 07)
  - R. DeGraff (row 10)
  - Josephine DeGraff (row 11)
  - Mrs. Jos. Nedeau (row 26)
  - Julia C. Pierson (row 29)

**Analytically significant findings:**

1. **"Shawnee" is agency, not tribe.** Every resolvable row on this master list turned out to be Citizen Potawatomie. The Shawnee Indian Agency administered Citizen Potawatomie, Iowa, Sac & Fox, and Eastern Shawnee allottees, but the master list itself happens to be entirely Citizen Potawatomie. The misclassification of `Tribe/Reservation = "Shawnee"` in the original Sonnet extraction reflects literal transcription of the master list header, not the actual tribal affiliations.

2. **Name variants between 1929 master list and modern patents database are routine.** Documented variants include:
   - Bourbonais (master list) vs Bourbonnais (database, double-n)
   - Joseph C. Cummings (master list) vs Joseph H. Cummings (database, middle initial)
   - Sophie Johnson (master list) vs Sophia Johnson (database)
   - Benis A. Mars (master list) vs Dennis A. Mars (database — master list misread 'D' as 'B')

3. **Married-name and deceased-filing variants required manual triage.** The automated normalize-name triage missed:
   - Lizzie Hartman (master list maiden name) ↔ Lizzie Lyons née Hartman (part10_questionnaire_011, married name in corpus)
   - James J. Sweeney 'for his deceased wife' (master list petitioner) ↔ Laura Dean (part10_questionnaire_017, the actual deceased allottee)
   Future master-list backfills should manually verify residual rows against the corpus, looking for these patterns.

4. **Absence from patents database is itself data.** The 6 unresolved rows may indicate cases where Circular 2464 investigation began but no forced fee patent was consummated, or patent records under different names not indexed in the current database. Marking these rows as explicitly unresolved (rather than leaving them indistinguishable from unprocessed rows) preserves the analytical signal.

**Patches and audit trail:**

- `backfill_shawnee_master_list.py` — 10 corpus cross-references
- `backfill_shawnee_master_list_manual_triage.py` — 2 manual matches (Hartman, Sweeney)
- `backfill_shawnee_final.py` — 18 patents-database confirmations + 6 not-in-database
- Each patched record's `recovery_notes` documents: source (patents database URL or corpus cross-reference), name variant if any, schema rationale, agency context, user confirmation

Total of 36 master list rows now have complete data state. The 6 unresolved rows remain candidates for future research (different databases, family history sources, NARA records).


---

## Task 5 CAT_2 / CAT_3 campaign — complete (2026-05-04)

The Task 5 candidate campaign (records where Sonnet text extraction
failed to capture identifying fields) is complete. Final enumeration:
CAT_1 = 0, CAT_2 = 0, CAT_3 = 0. Two records are deliberately left
unpatched (Hannah Hardin signature page part10_affidavit_004; blank
Circular 2464 instruction template part3_questionnaire_022).

**Category definitions** (from enumerate_task5_candidates.py):
- CAT_1: both Name and Allotment missing (hardest — no anchor)
- CAT_2: Name missing, Allotment captured (anchor by allotment)
- CAT_3: Name captured, Allotment missing (anchor by name + lookup)

**CAT_3 resolution — 76 records, worked by tribe:**

The CAT_3 records were grouped by tribe and resolved primarily through
Christian's federal-register-app patents database
(https://federal-register-app-996830241007.us-east1.run.app/patents),
which is keyed by allottee name and returns allotment + tribe.

- Rosebud-area: 22 records (21 patents-database backfills + 1 name
  correction — see Helena Larvie below)
- Pine Ridge / Oglala Lakota: 6 patents-database backfills + 1
  duplicate removed (Tay Sander = garbled duplicate of Nora Tway
  Sandery)
- Crow Creek / Big Bend District: 6 records (Joe and Peter St John,
  Cleveland Fallis — who is Lower Brule not Crow Creek despite the
  district label — and three William Walker records that are one
  person across pages 2-5 of part 12)
- Scattered single-tribe: 5 records (Crow Creek, Pawnee, Ponca,
  Sioux→Rosebud Sioux, Shannon-County→Oglala Lakota)
- Tribe-not-stated: 36 records (29 allotment backfills, 1
  not-in-database, 1 non-allottee witness, 2 non-allottee
  reclassifications, plus same-person cross-reference cases)

**CAT_2 resolution — 2 records:**

Both were E. W. Jermark cover letters from Pine Ridge Agency
acknowledging Circular 2464, misclassified as CAT_2 because a stray
'112' was read as an allotment number. Reclassified as
agency_correspondence; the spurious allotment cleared. page060's
aggregate patent counts (333 issued 1918-04-13, 344 issued 1919-09-29)
preserved in NOTES for the 'floor not ceiling' framing.

**New document type: non_allottee_record**

Established for records whose named individuals are neither allottees
nor land buyers:
- part6_affidavit_002 (T. C. Montgomery, J. D. Keller — affiants,
  not allottees)
- part7_agency_narrative_page056 (Eugene Sturdevant — white, no
  allotment; note Sturdevant is also the married name of allottee
  Lucy DuBray Sturdevant, a different person)

Distinct from agency_buyer_report (specifically about land buyers/
lessors) and agency_correspondence (transmittal letters). The
non_allottee_record type is the general bucket for documents retained
for evidentiary value whose subjects are not allottees.

William J. Bordeaux (part6_questionnaire_021) was marked
'(non-allottee record — witness)' in the allotment field rather than
reclassified, because he appears as a recurring witness on others'
affidavits — worth keeping discoverable as a witness-network actor.

**Methodologically significant findings:**

1. **Helena Larvie name correction (Hazel -> Helena).** Sonnet text
   extraction read degraded handwriting on part9_questionnaire_010 as
   'Hazel (last name not fully legible)'. The correct name is Helena
   Larvie. This was caught NOT by model comparison but by page-sequence
   reasoning: every allottee in part 9 has both an agency_narrative and
   a questionnaire on consecutive pages; pages 31-32 (the 'Hazel'
   questionnaire) fall exactly between Helena Larvie's agency narrative
   (page 30) and Peter Larvie's (page 33), so the 'Hazel' questionnaire
   is Helena Larvie's. User source-page review confirmed. The part 9
   narrative+questionnaire pairing pattern is itself a verification
   tool. Allotment 3432 from BLM General Land Office records
   (accession SD2610__.247) — Helena Larvie was not in the patents
   database.

2. **Jesse / Jasper Ellston — conservative separation.** Jesse
   Ellston's affidavit (part2_questionnaire_001) contains his own
   statement: 'My name is known also as Jasper J. Ellston, and I am
   sometimes called Jay Ellston.' The patents database has a Jesse
   Ellston (allotment 241) and a separate Jasper Ellston (allotment
   243, own record part2_agency_narrative_004). DECISION: treat them
   as two separate people — two names, two allotment numbers. Why
   Jesse stated he is 'also known as Jasper' is unresolved and
   deliberately not collapsed. The affidavit statement is preserved
   verbatim in NOTES as data, not resolved into an identity claim.
   This is the conservative, evidence-respecting treatment.

3. **Same-person cross-reference cases.** Several allottees have
   multiple corpus records, cross-referenced rather than merged:
   - Josephine Collins: 3 records, allotment 2862.5
     (part2_agency_narrative_page059, part6_agency_narrative_page046,
     part2_questionnaire_020)
   - Mary Dillon: 2 records, allotment 481 (part7_affidavit_005,
     part7_questionnaire_016)
   - George Menard: 2 records, allotment 548 (part2_questionnaire_016,
     part2_questionnaire_017)
   - Joseph/Joe St John: questionnaire + agency narrative, allotment
     547 (part11_questionnaire_012, part11_agency_narrative_005)

4. **Tribe-label normalization.** 'Rosebud' normalized to 'Rosebud
   Sioux'; generic 'Sioux' and the county label 'Shannon County (South
   Dakota)' replaced with actual tribes; 'Big Bond District' (OCR
   error) corrected to Big Bend / Crow Creek Sioux; 'Ponca' on Jesse
   Ellston (derived from a 'Ponca station' mention) corrected to
   Rosebud Sioux. Tribe field carries the actual tribe; agency/district
   context goes in NOTES.

5. **Name variants between 1929 records and the modern database** are
   routine and were documented per-record (e.g., Annie Desersa /
   Annie Deserea; Nora Tway / Nora Sanders / 'Nora Tway Sandery').

6. **Not-in-database records.** Hattie Whiting Whitcher could not be
   located in the patents database; marked '(not in patents database)'
   / '(actual tribe unknown)' per the option-3 convention. Absence is
   recorded as data.

**Provenance recorded per record.** Each patched record's
recovery_notes captures the source (patents database URL, BLM GLO
accession, corpus cross-reference, or source-page review), any name
variant, the tribe-normalization rationale, and user confirmation.

**Reusable scripts from this campaign** (in project root):
- enumerate_task5_candidates_v4.py (current categorization filter)
- triage_shawnee_master_list.py (corpus surname-match triage)
- presort_tribe_not_stated.py (surname -> likely tribe pre-sort)
- the various patch_*.py and backfill_*.py batch patchers


---

## Integrity-pass methodology (reusable verification pattern)

After a long writing session, the corpus needs an integrity check.
`integrity_pass_20260504.py` is the template: it walks every record
patched on a given date (identified by a date string in recovery_notes)
and verifies four things:

1. **Structural integrity** — extraction is a dict, not a list or
   missing; NOTES is non-empty and contains a marker matching the
   session date (catches NOTES clobbering, the failure mode where a
   later patch overwrites instead of appending).
2. **Double-patch detection** — flags any record with two or more
   recovery_notes of the SAME type on the same date. Type-aware, not
   just date-aware: a correction following an initial patch is
   legitimate (different types), but two patches of the same type
   indicate a bug or accidental re-run.
3. **Special-value checks** — the fractional ('.5') allotments
   (Louise Anderson Ernst 12.5, Josephine Collins 2862.5, Jennie
   Wright 1504.5) and the same-person cross-reference groups (matching
   allotments within group; differing allotments preserved across
   sibling-but-distinct groups like the Charbonneau cluster) are
   intact.
4. **Spot-check vision_extraction_v5** — dump structured fee_patents
   and financial_transactions for known-good clusters (Charbonneau,
   DuBray) to confirm the retrofit preserved real data, not just
   placeholders.

Run after any large patching session. Cheap insurance.

---

## Buyer-network names surfaced by the vision retrofit

The vision_extraction_v5 retrofit (38 records) yields structured buyer
and transaction data that the original Sonnet text extraction had
captured only as NOTES prose. The 2026-05-04 spot-check surfaced
the following named non-allottee actors in the DuBray cluster alone:

- Charles Burtz (bought from John DuBray Boyd, allotment 2338, $2000)
- Charles W. Marley (bought from Lucy DuBray Sturdevant, allotment
  2341, '$1.00 and other valuable consideration')
- R. L. Hinn (Lucy DuBray Sturdevant paid $800)
- Ray C. Wynn (Lucy DuBray Sturdevant and husband paid $800)
- H. D. Haskell (Lily Rice DuBray paid $75)

The phrase '$1.00 and other valuable consideration' is the classic
nominal-consideration language that masks real-value transfers — the
kind of phrasing that's evidentially important and that the structured
fields now make queryable across the corpus.

These are real data points already sitting in the corpus, waiting for
the eventual database loader to aggregate them across all 38 retrofit
records (and eventually merge with Kimi v5's per-part buyer data).
This is exactly the Role 4 (network analysis) layer the corpus was
designed to support — Valandra-style queries on recurring buyers,
lessors, lenders, and witnesses across the forced-fee patent cases.

---

## Multi-document allottees are common — and they are NOT duplicates

Several allottees appear in MULTIPLE legitimate corpus records that
document different stages of the same fee-patent case. The
2026-05-04 George Menard verification confirmed the pattern:

- `part2_questionnaire_016` (pages 48-51) — George Menard's Form 5-105
  Application for Patent in Fee (the formal application document, ca.
  1918-1920)
- `part2_questionnaire_017` (page 52) — George Menard's Circular 2464
  questionnaire response (the 1928 follow-up survey), containing his
  statement that he 'asked for patent on one quarter only' but the
  patent was issued for the whole half section.

Same person, same allotment 548, consecutive but non-overlapping
pages, different document types serving different evidentiary
purposes. NOT a duplicate.

**Decision rule** (already in use through 2026-05-04):

- **Duplicate** — same source pages split into two corpus records, OR
  one record's content is wholly contained in the other (Anna Shuck
  q015/q016, Tay Sander as garbled twin of Nora Tway Sandery).
  → DELETE one record, archive its content in the canonical record's
  recovery_notes.

- **Continuation page** — different pages of the same form
  (Louise Drapeau q020/q021, Margaret DeCory q013/q022).
  → KEEP BOTH, cross-reference in NOTES.

- **Multi-document allottee** — different document types about the
  same allottee, often at different points in the timeline
  (application + later questionnaire; agency narrative + questionnaire;
  affidavit + agency narrative). George Menard q016/q017,
  Joe/Joseph St John part11_an005/q012, the DuBray bundle cases
  (agency narrative + questionnaire for John DuBray Boyd and Lucy
  DuBray Sturdevant), the Helena Larvie pair (page 30 agency
  narrative + pages 31-32 questionnaire after the 'Hazel' correction).
  → KEEP BOTH, cross-reference, often with the same allotment.

The default assumption when finding two records that share an
allottee should be 'multi-document allottee' (legitimate, keep both),
not 'duplicate' (delete one). The Anna Shuck / Tay Sander cases
were the exceptions, identified by content comparison of the source
pages themselves.
