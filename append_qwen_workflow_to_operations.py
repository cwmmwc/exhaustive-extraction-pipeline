#!/usr/bin/env python3
"""
Append session 2026-05-03 (continued) Qwen workflow corrections to OPERATIONS.md.

This patch adds critical missing details about the Qwen vision pipeline
that caused wasted time tonight:

1. The Qwen-VL server is NEVER just running. Every Qwen vision batch
   requires submitting start_qwen_vl_server.slurm FIRST, waiting for the
   address file to refresh, THEN submitting the recovery slurm.

2. The address file at /project/LawData/kimi-extraction/logs/qwen_vl_address.txt
   persists from previous runs. A stale address (old timestamp) does NOT
   indicate the server is running.

3. The full CAT_1 batch workflow (server start → batch upload → recovery
   submit → Sonnet vision parallel → comparison → arbitration).
"""
from pathlib import Path

OPERATIONS_PATH = Path(
    "/Users/cwm6W/projects/exhaustive-extraction-pipeline/OPERATIONS.md"
)

ADDITIONS = """

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
curl -s --max-time 5 "http://$(cat /project/LawData/kimi-extraction/logs/qwen_vl_address.txt | tr -d '\\n')/health" && echo " OK" || echo " UNREACHABLE"
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
scp -r circular_2464_extractions/vision_recovery_cat1 \\
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
sbatch \\
  --export=ALL,INPUT_DIR=/project/LawData/kimi-extraction/code/circular_2464_extractions/vision_recovery_cat1,OUT_DIR=/project/LawData/kimi-extraction/outputs/vision_recovery_cat1 \\
  /project/LawData/kimi-extraction/hpc/run_qwen_vl_recovery.slurm
```

### Step 4 — Pull Qwen results back

```
rsync -avz \\
    "cwm6w@login.hpc.virginia.edu:'/project/LawData/kimi-extraction/outputs/vision_recovery_cat1/'" \\
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
"""

MARKER = "## Qwen-VL server is a separate slurm"


def main():
    if not OPERATIONS_PATH.exists():
        print(f"ERROR: {OPERATIONS_PATH} does not exist.")
        return

    with open(OPERATIONS_PATH) as f:
        existing = f.read()

    if MARKER in existing:
        print(
            f"Additions already present (marker found: '{MARKER}'). "
            "Refusing to duplicate."
        )
        return

    with open(OPERATIONS_PATH, "a") as f:
        f.write(ADDITIONS)

    print(f"Appended {len(ADDITIONS.splitlines())} lines to {OPERATIONS_PATH}")
    print()
    print("New sections added:")
    print("  - Qwen-VL server is a separate slurm — must be started first, EVERY TIME")
    print("  - CAT_1 vision recovery — full batch workflow")


if __name__ == "__main__":
    main()
