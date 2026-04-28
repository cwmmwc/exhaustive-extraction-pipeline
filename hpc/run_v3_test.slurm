#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "v3-test"
#SBATCH -o /project/LawData/kimi-extraction/logs/v3_test_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/v3_test_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# ─────────────────────────────────────────────────────────
# Kimi K2.5 v3 vs v4 prompt comparison
#
# Runs the same document through both v3 and v4 prompts
# to measure whether the v4 prompt degrades Kimi's extraction.
#
# Usage:
#   sbatch /project/LawData/kimi-extraction/hpc/run_v3_test.slurm
# ─────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"
PDF_DIR="${PROJECT_DIR}/pdfs/v3_test"
OUTPUT_DIR="${PROJECT_DIR}/outputs/v3_test"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

mkdir -p "$OUTPUT_DIR"

echo "═══════════════════════════════════════════════"
echo "Kimi K2.5 v3 vs v4 Prompt Comparison"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

for pdf_file in "$PDF_DIR"/*.pdf; do
    [ -f "$pdf_file" ] || continue
    basename=$(basename "$pdf_file" .pdf)

    # Run v3
    echo ""
    echo "── v3: ${basename} ──"
    if [ ! -f "${OUTPUT_DIR}/${basename}_v3/kimi-k2.5.json" ] && [ ! -f "${OUTPUT_DIR}/${basename}_v3/Kimi K2.5.json" ]; then
        python3 "${CODE_DIR}/extract_single_pdf.py" \
            "$pdf_file" \
            --uvarc \
            --chunked \
            --v3 \
            --output "${OUTPUT_DIR}/${basename}_v3" \
            && echo "  v3 OK" || echo "  v3 FAILED"
    else
        echo "  v3 SKIP (already done)"
    fi

    # Run v4
    echo ""
    echo "── v4: ${basename} ──"
    if [ ! -f "${OUTPUT_DIR}/${basename}_v4/kimi-k2.5.json" ] && [ ! -f "${OUTPUT_DIR}/${basename}_v4/Kimi K2.5.json" ]; then
        python3 "${CODE_DIR}/extract_single_pdf.py" \
            "$pdf_file" \
            --uvarc \
            --chunked \
            --output "${OUTPUT_DIR}/${basename}_v4" \
            && echo "  v4 OK" || echo "  v4 FAILED"
    else
        echo "  v4 SKIP (already done)"
    fi
done

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "Results in: ${OUTPUT_DIR}"
echo "═══════════════════════════════════════════════"
