#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "c2464-aff"
#SBATCH -o /project/LawData/kimi-extraction/logs/circular2464_affidavit_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/circular2464_affidavit_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# Circular 2464 extraction with affidavit-specific prompt
set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"
PDF_DIR="${PROJECT_DIR}/pdfs/circular_2464"
OUTPUT_DIR="${PROJECT_DIR}/outputs/circular_2464_affidavit"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

mkdir -p "$OUTPUT_DIR"

echo "═══════════════════════════════════════════════"
echo "Circular 2464 — Affidavit-Specific Prompt"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

PDF_LIST=$(mktemp)
find "$PDF_DIR" -name "*.pdf" -type f | grep -v "Pull slip" > "$PDF_LIST"
TOTAL=$(wc -l < "$PDF_LIST")
echo "Total PDFs: $TOTAL"

DONE=0; FAILED=0; SKIPPED=0; COUNT=0

while IFS= read -r pdf_file; do
    [ -f "$pdf_file" ] || continue
    COUNT=$((COUNT + 1))
    basename=$(basename "$pdf_file" .pdf)

    # Delete old results to force re-extraction with new chunk size
    rm -f "${OUTPUT_DIR}/${basename}/kimi-k2.5.json" "${OUTPUT_DIR}/${basename}/Kimi K2.5.json" 2>/dev/null

    echo "[$COUNT/$TOTAL] ${basename}"
    # Smaller chunks (10K) for affidavits — each affidavit is ~500-1500 chars,
    # so 10K gives ~5-10 per chunk. 40K overwhelms Kimi with 25-80 affidavits per chunk.
    if python3 "${CODE_DIR}/extract_single_pdf.py" "$pdf_file" --uvarc --chunked --chunk-size 10000 --affidavit --output "${OUTPUT_DIR}/${basename}"; then
        DONE=$((DONE + 1))
    else
        FAILED=$((FAILED + 1)); echo "  FAILED"
    fi
done < "$PDF_LIST"
rm -f "$PDF_LIST"

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date) | OK=$DONE, Failed=$FAILED, Skipped=$SKIPPED / $TOTAL"
echo "═══════════════════════════════════════════════"
