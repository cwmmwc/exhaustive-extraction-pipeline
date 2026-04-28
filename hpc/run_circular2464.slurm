#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "c2464"
#SBATCH -o /project/LawData/kimi-extraction/logs/circular2464_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/circular2464_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# ─────────────────────────────────────────────────────────
# Circular 2464 extraction — human vs AI comparison
#
# Extracts Pine Ridge affidavits and Replies with both v3 and v5
# prompts for comparison against hand-transcribed spreadsheet.
# ─────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"
PDF_DIR="${PROJECT_DIR}/pdfs/circular_2464"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

echo "═══════════════════════════════════════════════"
echo "Circular 2464 Extraction — Human vs AI Comparison"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

# Find all PDFs recursively
PDF_LIST=$(mktemp)
find "$PDF_DIR" -name "*.pdf" -type f | grep -v "Pull slip" > "$PDF_LIST"
TOTAL=$(wc -l < "$PDF_LIST")
echo "Total PDFs: $TOTAL"

for VERSION in v3 v4 v5; do
    OUTPUT_DIR="${PROJECT_DIR}/outputs/circular_2464_${VERSION}"
    mkdir -p "$OUTPUT_DIR"

    V_FLAG=""
    if [ "$VERSION" = "v3" ]; then
        V_FLAG="--v3"
    elif [ "$VERSION" = "v5" ]; then
        V_FLAG="--v5"
    fi
    # v4 is the default — no flag needed

    echo ""
    echo "── Running ${VERSION} ──"

    DONE=0; FAILED=0; SKIPPED=0; COUNT=0

    while IFS= read -r pdf_file; do
        [ -f "$pdf_file" ] || continue
        COUNT=$((COUNT + 1))
        basename=$(basename "$pdf_file" .pdf)

        if [ -f "${OUTPUT_DIR}/${basename}/kimi-k2.5.json" ] || [ -f "${OUTPUT_DIR}/${basename}/Kimi K2.5.json" ]; then
            SKIPPED=$((SKIPPED + 1)); continue
        fi

        echo "[$COUNT/$TOTAL] (${VERSION}) ${basename}"
        if python3 "${CODE_DIR}/extract_single_pdf.py" "$pdf_file" --uvarc --chunked $V_FLAG --output "${OUTPUT_DIR}/${basename}"; then
            DONE=$((DONE + 1))
        else
            FAILED=$((FAILED + 1)); echo "  FAILED"
        fi
    done < "$PDF_LIST"

    echo "${VERSION}: OK=$DONE, Failed=$FAILED, Skipped=$SKIPPED / $TOTAL"
done

rm -f "$PDF_LIST"

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "═══════════════════════════════════════════════"
