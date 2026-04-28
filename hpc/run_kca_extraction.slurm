#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "kca-extract"
#SBATCH -o /project/LawData/kimi-extraction/logs/kca_extract_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/kca_extract_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# ─────────────────────────────────────────────────────────
# KCA/Kiowa Re-extraction with Kimi K2.5 via RC GenAI
#
# Re-extracts the full KCA corpus (257 docs, ~9,000 pages)
# using Kimi K2.5 on RC GenAI (H200 GPUs) with v4 schema
# (10 types: entities, events, transactions, relationships,
# fee_patents, correspondence, legislative_actions,
# testimony, taxes, mortgages).
#
# Replaces the original Claude Sonnet v3 extraction.
#
# Usage:
#   sbatch /project/LawData/kimi-extraction/hpc/run_kca_extraction.slurm
# ─────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"
OUTPUT_DIR="${PROJECT_DIR}/outputs/kca"

# RC GenAI API key
export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

mkdir -p "$OUTPUT_DIR"

echo "═══════════════════════════════════════════════"
echo "KCA/Kiowa Re-extraction — Kimi K2.5 via RC GenAI"
echo "Schema: v4 (10 types)"
echo "Output: ${OUTPUT_DIR}"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

# Collect all PDF directories
PDF_DIRS=(
    "${PROJECT_DIR}/pdfs/kca"
)

TOTAL=0
DONE=0
FAILED=0
SKIPPED=0

# Find all PDFs recursively across all directories
PDF_LIST=$(mktemp)
for dir in "${PDF_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        find "$dir" -name "*.pdf" -type f >> "$PDF_LIST"
    fi
done
TOTAL=$(wc -l < "$PDF_LIST")

echo "Total PDFs (recursive): $TOTAL"
echo ""

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
echo "KCA Re-extraction Complete"
echo "Finished: $(date)"
echo "Succeeded: $DONE, Failed: $FAILED, Skipped: $SKIPPED / $TOTAL total"
echo "═══════════════════════════════════════════════"
