#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "phase4-kimi"
#SBATCH -o /project/LawData/kimi-extraction/logs/phase4_kimi_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/phase4_kimi_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

echo "═══════════════════════════════════════════════"
echo "Phase 4 — Kimi K2.5 Validation Extraction"
echo "100-document stratified sample"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

cd "${CODE_DIR}"
python3 run_phase4_validation.py --kimi

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "═══════════════════════════════════════════════"
