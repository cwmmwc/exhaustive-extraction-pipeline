#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "c2464-retry"
#SBATCH -o /project/LawData/kimi-extraction/logs/circular2464_retry_targeted_v2_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/circular2464_retry_targeted_v2_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# Retry failed chunks from the Kimi targeted v2 extraction
set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

echo "═══════════════════════════════════════════════"
echo "Retry failed chunks — Kimi Targeted v2"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

python3 "${CODE_DIR}/retry_kimi_targeted_v2.py" \
    --output-dir "${PROJECT_DIR}/outputs/circular_2464_kimi_targeted_v2_10k/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3]" \
    --pdf "${PROJECT_DIR}/pdfs/circular_2464/pine_ridge/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3].pdf" \
    --max-retries 3

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "═══════════════════════════════════════════════"
