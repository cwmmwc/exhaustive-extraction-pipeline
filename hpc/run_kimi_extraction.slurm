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
# Runs on a CPU node and sends extraction requests to the
# Kimi vLLM server running on a GPU node.
#
# Prerequisites:
#   1. Kimi server running (sbatch hpc/start_kimi_server.slurm)
#   2. PDFs staged in /project/LawData/kimi-extraction/pdfs/
#   3. Code copied to /project/LawData/kimi-extraction/code/
#
# Usage:
#   # Extract a single PDF (full document, chunked):
#   sbatch --export=PDF="1921 CCF 56074-21-312 GS.pdf" hpc/run_kimi_extraction.slurm
#
#   # Extract all PDFs in the staging directory:
#   sbatch --export=PDF=ALL hpc/run_kimi_extraction.slurm
# ─────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
PDF_DIR="${PROJECT_DIR}/pdfs"
CODE_DIR="${PROJECT_DIR}/code"
OUTPUT_DIR="${PROJECT_DIR}/outputs"

# The PDF to process — set via --export=PDF="filename.pdf" or PDF=ALL
PDF="${PDF:-ALL}"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4

# Activate the Python environment
source /scratch/$USER/model-compare-venv/bin/activate

# ── Wait for the server ──
echo "Waiting for Kimi server..."
ADDR_FILE="${PROJECT_DIR}/logs/server_address.txt"

for i in $(seq 1 60); do
    if [ -f "$ADDR_FILE" ]; then
        ADDR=$(cat "$ADDR_FILE" | tr -d '\n')
        if curl -s --max-time 5 "http://${ADDR}/health" > /dev/null 2>&1; then
            echo "Server ready at ${ADDR}"
            break
        fi
    fi
    if [ "$i" -eq 60 ]; then
        echo "ERROR: Server not ready after 10 minutes. Is the server job running?"
        echo "  Check: squeue -u $USER"
        echo "  Logs:  cat ${PROJECT_DIR}/logs/server_*.out"
        exit 1
    fi
    echo "  Attempt $i/60 — waiting 10s..."
    sleep 10
done

ADDR=$(cat "$ADDR_FILE" | tr -d '\n')
VLLM_URL="http://${ADDR}"

echo "═══════════════════════════════════════════════"
echo "Kimi K2.5 Extraction Worker"
echo "Server:   ${VLLM_URL}"
echo "PDF:      ${PDF}"
echo "Output:   ${OUTPUT_DIR}"
echo "═══════════════════════════════════════════════"

mkdir -p "$OUTPUT_DIR"

# ── Run extraction ──
if [ "$PDF" = "ALL" ]; then
    # Process all PDFs in the staging directory
    TOTAL=$(ls "$PDF_DIR"/*.pdf 2>/dev/null | wc -l)
    if [ "$TOTAL" -eq 0 ]; then
        echo "No PDFs found in $PDF_DIR"
        exit 1
    fi
    echo "Processing $TOTAL PDFs..."
    DONE=0
    FAILED=0
    for pdf_file in "$PDF_DIR"/*.pdf; do
        basename=$(basename "$pdf_file" .pdf)
        # Skip if already extracted (skip-on-exists)
        if [ -f "${OUTPUT_DIR}/${basename}/kimi-k2.5.json" ]; then
            echo "SKIP: ${basename} (already extracted)"
            DONE=$((DONE + 1))
            continue
        fi
        echo ""
        echo "[$((DONE + FAILED + 1))/$TOTAL] ${basename}"
        python3 "${CODE_DIR}/extract_single_pdf.py" \
            "$pdf_file" \
            --vllm-url "$VLLM_URL" \
            --vllm-model kimi-k2.5 \
            --chunked \
            --output "${OUTPUT_DIR}/${basename}" \
            && DONE=$((DONE + 1)) \
            || FAILED=$((FAILED + 1))
    done
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "Done. $DONE succeeded, $FAILED failed out of $TOTAL."
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
        --vllm-url "$VLLM_URL" \
        --vllm-model kimi-k2.5 \
        --chunked \
        --output "${OUTPUT_DIR}/${basename}"
fi
