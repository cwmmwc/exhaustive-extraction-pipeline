#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "affidavit-v4"
#SBATCH -o /project/LawData/kimi-extraction/logs/affidavit_v4_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/affidavit_v4_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# ─────────────────────────────────────────────────────────
# Re-extract 73 affidavits with v4 using new OCR'd PDFs.
# The original v4 extraction ran against empty (image-only) PDFs.
# This replaces those empty results.
#
# Usage:
#   sbatch /project/LawData/kimi-extraction/hpc/run_affidavit_v4_reextract.slurm
# ─────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"
OUTPUT_DIR="${PROJECT_DIR}/outputs/kca"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

echo "═══════════════════════════════════════════════"
echo "Affidavit v4 Re-extraction (OCR'd PDFs)"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

# Only process PDFs in the Affidavits subdirectories
PDF_LIST=$(mktemp)
find "${PROJECT_DIR}/pdfs/kca" -path "*/Affidavits*" -name "*.pdf" -type f > "$PDF_LIST"
TOTAL=$(wc -l < "$PDF_LIST")

echo "Affidavit PDFs: $TOTAL"
echo ""

DONE=0
FAILED=0
COUNT=0

while IFS= read -r pdf_file; do
    [ -f "$pdf_file" ] || continue
    COUNT=$((COUNT + 1))
    basename=$(basename "$pdf_file" .pdf)

    # Delete old empty extraction to force re-extraction
    rm -f "${OUTPUT_DIR}/${basename}/kimi-k2.5.json" "${OUTPUT_DIR}/${basename}/Kimi K2.5.json" 2>/dev/null

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
echo "Affidavit v4 Re-extraction Complete"
echo "Finished: $(date)"
echo "Succeeded: $DONE, Failed: $FAILED / $TOTAL total"
echo "═══════════════════════════════════════════════"
