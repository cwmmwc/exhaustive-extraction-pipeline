#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "kca-fresh-v4"
#SBATCH -o /project/LawData/kimi-extraction/logs/kca_fresh_v4_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/kca_fresh_v4_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# Fresh KCA extraction: Kimi K2.5 v4 (10 types)
set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"
OUTPUT_DIR="${PROJECT_DIR}/outputs/kca_fresh_v4"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

mkdir -p "$OUTPUT_DIR"

echo "═══════════════════════════════════════════════"
echo "KCA Fresh Extraction — Kimi K2.5 v4 (10 types)"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

PDF_LIST=$(mktemp)
find "${PROJECT_DIR}/pdfs/kca" -name "*.pdf" -type f > "$PDF_LIST"
TOTAL=$(wc -l < "$PDF_LIST")
echo "Total PDFs: $TOTAL"

DONE=0; FAILED=0; SKIPPED=0; COUNT=0

while IFS= read -r pdf_file; do
    [ -f "$pdf_file" ] || continue
    COUNT=$((COUNT + 1))
    basename=$(basename "$pdf_file" .pdf)

    if [ -f "${OUTPUT_DIR}/${basename}/kimi-k2.5.json" ] || [ -f "${OUTPUT_DIR}/${basename}/Kimi K2.5.json" ]; then
        SKIPPED=$((SKIPPED + 1)); continue
    fi

    echo "[$COUNT/$TOTAL] ${basename}"
    if python3 "${CODE_DIR}/extract_single_pdf.py" "$pdf_file" --uvarc --chunked --output "${OUTPUT_DIR}/${basename}"; then
        DONE=$((DONE + 1))
    else
        FAILED=$((FAILED + 1)); echo "  FAILED"
    fi
done < "$PDF_LIST"
rm -f "$PDF_LIST"

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date) | OK: $DONE, Failed: $FAILED, Skipped: $SKIPPED / $TOTAL"
echo "═══════════════════════════════════════════════"
