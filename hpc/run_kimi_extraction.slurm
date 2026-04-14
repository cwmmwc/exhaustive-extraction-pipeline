#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "kimi-extract"
#SBATCH -o /project/LawData/kimi-extraction/logs/extract_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/extract_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# ─────────────────────────────────────────────────────────
# Kimi K2.5 Extraction Worker
#
# Runs on a CPU node and sends extraction requests to either:
#   - UVA RC GenAI (H200 GPUs, free) — default
#   - Your own vLLM server (A100 GPUs) — set BACKEND=vllm
#
# Prerequisites:
#   1. PDFs staged in /project/LawData/kimi-extraction/pdfs/
#   2. Code copied to /project/LawData/kimi-extraction/code/
#   3. For vLLM backend: Kimi server running (sbatch hpc/start_kimi_server.slurm)
#
# Usage:
#   # Extract all PDFs via RC GenAI (H200s, default):
#   sbatch --export=PDF=ALL hpc/run_kimi_extraction.slurm
#
#   # Extract all PDFs via your vLLM server (A100s):
#   sbatch --export=PDF=ALL,BACKEND=vllm hpc/run_kimi_extraction.slurm
#
#   # Extract a single PDF:
#   sbatch --export=PDF="1921 CCF 56074-21-312 GS.pdf" hpc/run_kimi_extraction.slurm
# ─────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
PDF_DIR="${PROJECT_DIR}/pdfs"
CODE_DIR="${PROJECT_DIR}/code"
OUTPUT_DIR="${PROJECT_DIR}/outputs"

# The PDF to process — set via --export=PDF="filename.pdf" or PDF=ALL
PDF="${PDF:-ALL}"

# Backend: "rcgenai" (default, H200s) or "vllm" (your A100 server)
BACKEND="${BACKEND:-rcgenai}"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4

# Activate the Python environment
source /scratch/$USER/model-compare-venv/bin/activate

# ── Configure backend ──
if [ "$BACKEND" = "rcgenai" ]; then
    # UVA RC GenAI — Kimi K2.5 on H200 GPUs, free
    # Using 20K chunks to stay under proxy timeout (40K still triggers 502)
    export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"
    EXTRACT_FLAGS="--uvarc --chunked"
    echo "═══════════════════════════════════════════════"
    echo "Kimi K2.5 Extraction Worker — RC GenAI (H200)"
    echo "Backend:  UVA RC GenAI (free H200 GPUs)"
    echo "PDF:      ${PDF}"
    echo "Output:   ${OUTPUT_DIR}"
    echo "═══════════════════════════════════════════════"
else
    # vLLM server on A100s — wait for it to be ready
    echo "Waiting for Kimi server..."
    ADDR_FILE="${PROJECT_DIR}/logs/server_address.txt"

    for i in $(seq 1 360); do
        if [ -f "$ADDR_FILE" ]; then
            ADDR=$(cat "$ADDR_FILE" | tr -d '\n')
            if curl -s --max-time 5 "http://${ADDR}/health" > /dev/null 2>&1; then
                echo "Server ready at ${ADDR}"
                break
            fi
        fi
        if [ "$i" -eq 360 ]; then
            echo "ERROR: Server not ready after 1 hour. Is the server job running?"
            echo "  Check: squeue -u $USER"
            echo "  Logs:  cat ${PROJECT_DIR}/logs/server_*.out"
            exit 1
        fi
        if [ $((i % 30)) -eq 0 ]; then
            echo "  Attempt $i/360 — waiting ($((i * 10 / 60)) min so far)..."
        fi
        sleep 10
    done

    ADDR=$(cat "$ADDR_FILE" | tr -d '\n')
    VLLM_URL="http://${ADDR}"
    EXTRACT_FLAGS="--vllm-url $VLLM_URL --vllm-model kimi-k2.5 --chunked"
    echo "═══════════════════════════════════════════════"
    echo "Kimi K2.5 Extraction Worker — vLLM (A100)"
    echo "Server:   ${VLLM_URL}"
    echo "PDF:      ${PDF}"
    echo "Output:   ${OUTPUT_DIR}"
    echo "═══════════════════════════════════════════════"
fi

mkdir -p "$OUTPUT_DIR"

# ── Run extraction ──
if [ "$PDF" = "ALL" ]; then
    # Process all PDFs in the staging directory
    TOTAL=$(ls "$PDF_DIR"/*.pdf 2>/dev/null | wc -l)
    if [ "$TOTAL" -eq 0 ]; then
        echo "No PDFs found in $PDF_DIR"
        exit 1
    fi
    echo "Processing $TOTAL PDFs (skipping duplicates and already-extracted)..."
    DONE=0
    FAILED=0
    SKIPPED=0
    for pdf_file in "$PDF_DIR"/*.pdf; do
        basename=$(basename "$pdf_file" .pdf)
        # Skip duplicates
        if echo "$basename" | grep -qi "duplicate"; then
            echo "SKIP: ${basename} (duplicate)"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi
        # Skip if already extracted (skip-on-exists) — check both naming conventions
        if [ -f "${OUTPUT_DIR}/${basename}/kimi-k2.5.json" ] || [ -f "${OUTPUT_DIR}/${basename}/Kimi K2.5.json" ]; then
            echo "SKIP: ${basename} (already extracted)"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi
        echo ""
        echo "[$((DONE + FAILED + 1))/$TOTAL] ${basename}"
        python3 "${CODE_DIR}/extract_single_pdf.py" \
            "$pdf_file" \
            $EXTRACT_FLAGS \
            --output "${OUTPUT_DIR}/${basename}" \
            && DONE=$((DONE + 1)) \
            || FAILED=$((FAILED + 1))
    done
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "Done. $DONE succeeded, $FAILED failed, $SKIPPED skipped out of $TOTAL."
    echo "═══════════════════════════════════════════════"
else
    # Process a single PDF
    pdf_file="${PDF_DIR}/${PDF}"
    if [ ! -f "$pdf_file" ]; then
        echo "File not found: $pdf_file"
        exit 1
    fi
    basename=$(basename "$pdf_file" .pdf)
    python3 "${CODE_DIR}/extract_single_pdf.py" \
        "$pdf_file" \
        $EXTRACT_FLAGS \
        --output "${OUTPUT_DIR}/${basename}"
fi
