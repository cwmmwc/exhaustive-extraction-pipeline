#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "c2464-tgt"
#SBATCH -o /project/LawData/kimi-extraction/logs/circular2464_kimi_targeted_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/circular2464_kimi_targeted_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# Circular 2464 — Three-step targeted affidavit prompt on Kimi K2.5
# Pine Ridge Volume 1 ONLY (10K chunks)
set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"
PDF_DIR="${PROJECT_DIR}/pdfs/circular_2464"
OUTPUT_DIR="${PROJECT_DIR}/outputs/circular_2464_kimi_targeted_10k"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

mkdir -p "$OUTPUT_DIR"

echo "═══════════════════════════════════════════════"
echo "Circular 2464 — Kimi Targeted Affidavit Prompt"
echo "Pine Ridge Volume 1 only, 10K chunks"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

PDF_FILE="$PDF_DIR/pine_ridge/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3].pdf"
BASENAME="312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3]"

if [ ! -f "$PDF_FILE" ]; then
    echo "ERROR: PDF not found: $PDF_FILE"
    exit 1
fi

# Clear old results to force fresh extraction
rm -f "${OUTPUT_DIR}/${BASENAME}/kimi-k2.5.json" "${OUTPUT_DIR}/${BASENAME}/Kimi K2.5.json" 2>/dev/null

echo "Extracting: ${BASENAME}"
if python3 "${CODE_DIR}/extract_single_pdf.py" "$PDF_FILE" \
    --uvarc --chunked --chunk-size 10000 \
    --affidavit-targeted \
    --output "${OUTPUT_DIR}/${BASENAME}"; then
    echo "  OK"
else
    echo "  FAILED"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "═══════════════════════════════════════════════"
