#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "kca-v3"
#SBATCH -o /project/LawData/kimi-extraction/logs/kca_v3_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/kca_v3_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# ─────────────────────────────────────────────────────────
# KCA Kimi K2.5 v3 Extraction for v3-vs-v4 comparison
#
# Runs the full KCA corpus through Kimi with the v3 prompt
# (7 types). Results stored separately from the v4 extraction
# so both can be compared side by side.
#
# Also re-extracts the 73 affidavits that now have OCR text.
#
# Usage:
#   sbatch /project/LawData/kimi-extraction/hpc/run_kca_v3_comparison.slurm
# ─────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"
OUTPUT_DIR="${PROJECT_DIR}/outputs/kca_v3"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

mkdir -p "$OUTPUT_DIR"

echo "═══════════════════════════════════════════════"
echo "KCA v3 Extraction — Kimi K2.5 via RC GenAI"
echo "Schema: v3 (7 types) for comparison with v4"
echo "Output: ${OUTPUT_DIR}"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

# Find all PDFs recursively
PDF_DIR="${PROJECT_DIR}/pdfs/kca"
PDF_LIST=$(mktemp)
find "$PDF_DIR" -name "*.pdf" -type f > "$PDF_LIST"
TOTAL=$(wc -l < "$PDF_LIST")

echo "Total PDFs (recursive): $TOTAL"
echo ""

DONE=0
FAILED=0
SKIPPED=0
COUNT=0

while IFS= read -r pdf_file; do
    [ -f "$pdf_file" ] || continue
    COUNT=$((COUNT + 1))
    basename=$(basename "$pdf_file" .pdf)

    # Skip if already extracted
    if [ -f "${OUTPUT_DIR}/${basename}/kimi-k2.5.json" ] || [ -f "${OUTPUT_DIR}/${basename}/Kimi K2.5.json" ]; then
        echo "[$COUNT/$TOTAL] SKIP (done): ${basename}"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    echo ""
    echo "[$COUNT/$TOTAL] ${basename}"
    if python3 "${CODE_DIR}/extract_single_pdf.py" \
        "$pdf_file" \
        --uvarc \
        --chunked \
        --v3 \
        --output "${OUTPUT_DIR}/${basename}"; then
        DONE=$((DONE + 1))
    else
        FAILED=$((FAILED + 1))
        echo "  FAILED: ${basename}"
    fi
done < "$PDF_LIST"
rm -f "$PDF_LIST"

echo ""
echo "═══════════════════════════════════════════════"
echo "KCA v3 Extraction Complete"
echo "Finished: $(date)"
echo "Succeeded: $DONE, Failed: $FAILED, Skipped: $SKIPPED / $TOTAL total"
echo "═══════════════════════════════════════════════"
