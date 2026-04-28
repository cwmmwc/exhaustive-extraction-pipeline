#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "c2464-exp"
#SBATCH -o /project/LawData/kimi-extraction/logs/circular2464_experiments_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/circular2464_experiments_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# Two experiments on Circular 2464:
#   1. Affidavit prompt with 5K chunks (smaller = fewer affidavits per chunk)
#   2. Affidavit prompt with page-level extraction (one page at a time, no chunking)

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"
PDF_DIR="${PROJECT_DIR}/pdfs/circular_2464"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

echo "═══════════════════════════════════════════════"
echo "Circular 2464 Affidavit Experiments"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

PDF_LIST=$(mktemp)
find "$PDF_DIR" -name "*.pdf" -type f | grep -v "Pull slip" > "$PDF_LIST"
TOTAL=$(wc -l < "$PDF_LIST")

# ── Experiment 1: 5K chunks ──
OUTPUT_5K="${PROJECT_DIR}/outputs/circular_2464_affidavit_5k"
mkdir -p "$OUTPUT_5K"

echo ""
echo "── Experiment 1: Affidavit prompt, 5K chunks ──"
DONE=0; FAILED=0; COUNT=0

while IFS= read -r pdf_file; do
    [ -f "$pdf_file" ] || continue
    COUNT=$((COUNT + 1))
    basename=$(basename "$pdf_file" .pdf)

    echo "[$COUNT/$TOTAL] (5K) ${basename}"
    if python3 "${CODE_DIR}/extract_single_pdf.py" "$pdf_file" --uvarc --chunked --chunk-size 5000 --affidavit --output "${OUTPUT_5K}/${basename}"; then
        DONE=$((DONE + 1))
    else
        FAILED=$((FAILED + 1)); echo "  FAILED"
    fi
done < "$PDF_LIST"
echo "5K chunks: OK=$DONE, Failed=$FAILED / $TOTAL"

# ── Experiment 2: Page-level (1-page chunks) ──
# Use chunk-size of 2000 with 0 overlap to approximate page-level.
# Most affidavit pages are 800-1700 chars, so 2000 gives ~1 page per chunk.
OUTPUT_PAGE="${PROJECT_DIR}/outputs/circular_2464_affidavit_page"
mkdir -p "$OUTPUT_PAGE"

echo ""
echo "── Experiment 2: Affidavit prompt, page-level (~2K chunks) ──"
DONE=0; FAILED=0; COUNT=0

while IFS= read -r pdf_file; do
    [ -f "$pdf_file" ] || continue
    COUNT=$((COUNT + 1))
    basename=$(basename "$pdf_file" .pdf)

    echo "[$COUNT/$TOTAL] (page) ${basename}"
    if python3 "${CODE_DIR}/extract_single_pdf.py" "$pdf_file" --uvarc --chunked --chunk-size 2000 --affidavit --output "${OUTPUT_PAGE}/${basename}"; then
        DONE=$((DONE + 1))
    else
        FAILED=$((FAILED + 1)); echo "  FAILED"
    fi
done < "$PDF_LIST"
echo "Page-level: OK=$DONE, Failed=$FAILED / $TOTAL"

rm -f "$PDF_LIST"

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "═══════════════════════════════════════════════"
