#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=64G
#SBATCH -J "kimi-download"
#SBATCH -o /project/LawData/kimi-extraction/logs/download_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/download_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# ─────────────────────────────────────────────────────────
# Download Kimi K2.5 model and build fresh vLLM container.
# Run on a compute node because login nodes kill large downloads.
#
# Usage:
#   sbatch hpc/download_kimi.slurm
# ─────────────────────────────────────────────────────────

set -euo pipefail

module purge
module load apptainer

echo "═══════════════════════════════════════════════"
echo "Kimi K2.5 Download Job"
echo "Node:     $(hostname)"
echo "Job ID:   ${SLURM_JOB_ID}"
echo "Started:  $(date)"
echo "═══════════════════════════════════════════════"

# ── 1. Build fresh vLLM container ──
mkdir -p /scratch/$USER/containers
VLLM_SIF="/scratch/$USER/containers/vllm_kimi.sif"
if [ -f "$VLLM_SIF" ]; then
    echo "Container already exists: $VLLM_SIF"
else
    echo ""
    echo "Pulling vLLM container..."
    apptainer pull "$VLLM_SIF" docker://vllm/vllm-openai:latest
    echo "Container saved: $VLLM_SIF"
fi

# ── 2. Download Kimi K2.5 model weights ──
MODEL_DIR="/project/LawData/models/Kimi-K2.5"
mkdir -p "$MODEL_DIR"
mkdir -p /scratch/$USER/fakehome/.cache/huggingface

echo ""
echo "Downloading Kimi K2.5 to $MODEL_DIR..."
echo "This is ~549GB and will take a few hours."

apptainer exec \
    --bind /project/LawData:/project/LawData \
    --bind /scratch/$USER:/scratch/$USER \
    --bind /scratch/$USER/fakehome:/home/$USER \
    --env HOME=/home/$USER \
    --env HF_HOME=/home/$USER/.cache/huggingface \
    "$VLLM_SIF" \
    huggingface-cli download moonshotai/Kimi-K2.5 \
        --local-dir "$MODEL_DIR"

echo ""
echo "═══════════════════════════════════════════════"
echo "Done. $(date)"
echo "Container: $VLLM_SIF"
echo "Model:     $MODEL_DIR"
echo "═══════════════════════════════════════════════"
