#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=3-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --gres=gpu:a100:8
#SBATCH --constraint=a100_80gb
#SBATCH --partition=gpu
#SBATCH --mem=500G
#SBATCH -J "kimi-k2.5-server"
#SBATCH -o /project/LawData/kimi-extraction/logs/server_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/server_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# ─────────────────────────────────────────────────────────
# Kimi K2.5 vLLM Server
#
# Starts Kimi K2.5 (1T MoE, 32B active) on 8x A100 80GB.
# The server exposes an OpenAI-compatible API that worker
# jobs connect to for extraction.
#
# Prerequisites:
#   1. Run setup_kimi.sh first (downloads model + container)
#   2. mkdir -p /project/LawData/kimi-extraction/logs
#
# Usage:
#   sbatch hpc/start_kimi_server.slurm
#
# Then submit worker jobs — they read the server address
# from /project/LawData/kimi-extraction/logs/server_address.txt
# ─────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ──
MODEL_PATH="/project/LawData/models/Kimi-K2.5"
VLLM_PORT=8000
NUM_GPUS=8

# Container — use the shared one, or your own if you built a newer version
VLLM_SIF="/scratch/$USER/containers/vllm_kimi.sif"

module purge
module load apptainer

# Create cache directories
mkdir -p /scratch/$USER/fakehome/.cache/{huggingface,vllm,flashinfer,triton}

echo "═══════════════════════════════════════════════"
echo "Kimi K2.5 vLLM Server"
echo "Model:    ${MODEL_PATH}"
echo "GPUs:     ${NUM_GPUS}x A100 80GB"
echo "Node:     $(hostname)"
echo "Job ID:   ${SLURM_JOB_ID}"
echo "Port:     ${VLLM_PORT}"
echo "═══════════════════════════════════════════════"

# Write the server address so worker jobs can find it
echo "$(hostname):${VLLM_PORT}" > /project/LawData/kimi-extraction/logs/server_address.txt
echo "Server address written to /project/LawData/kimi-extraction/logs/server_address.txt"

# Start vLLM server
# Kimi K2.5 requires: --trust-remote-code
# The tool-call and reasoning parsers are optional (only needed for agentic use)
apptainer exec --nv \
    --no-home \
    --bind /project/LawData:/project/LawData \
    --bind /scratch/$USER:/scratch/$USER \
    --bind /scratch/$USER/fakehome:/home/$USER \
    --env HOME=/home/$USER \
    --env XDG_CACHE_HOME=/home/$USER/.cache \
    --env HF_HOME=/home/$USER/.cache/huggingface \
    --env VLLM_DO_NOT_TRACK=1 \
    "$VLLM_SIF" \
    vllm serve "$MODEL_PATH" \
        --served-model-name kimi-k2.5 \
        --tensor-parallel-size "$NUM_GPUS" \
        --trust-remote-code \
        --dtype auto \
        --max-model-len 32768 \
        --gpu-memory-utilization 0.95 \
        --host 0.0.0.0 \
        --port "$VLLM_PORT"
