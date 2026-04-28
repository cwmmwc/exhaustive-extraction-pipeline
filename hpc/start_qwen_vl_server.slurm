#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:a100:4
#SBATCH --constraint=a100_80gb
#SBATCH --partition=gpu
#SBATCH --mem=120G
#SBATCH -J "qwen-vl-server"
#SBATCH -o /project/LawData/kimi-extraction/logs/qwen_vl_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/qwen_vl_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# Qwen2.5-VL-72B vLLM Server — using Loren's proven config
set -euo pipefail

MODEL_PATH="/project/LawData/models/qwen2.5-vl-72b"
VLLM_PORT=8000

# Use Loren's container
VLLM_SIF="/project/LawData/models/container/vllm_0.14.1-cu130.sif"

module purge
module load apptainer

mkdir -p /scratch/$USER/fakehome/.cache/{huggingface,vllm,flashinfer,triton}

echo "═══════════════════════════════════════════════"
echo "Qwen2.5-VL-72B vLLM Server (Loren config)"
echo "Model:    ${MODEL_PATH}"
echo "Container: ${VLLM_SIF}"
echo "GPUs:     4x A100 80GB"
echo "Node:     $(hostname)"
echo "Job ID:   ${SLURM_JOB_ID}"
echo "Port:     ${VLLM_PORT}"
echo "═══════════════════════════════════════════════"

echo "$(hostname):${VLLM_PORT}" > /project/LawData/kimi-extraction/logs/qwen_vl_address.txt
echo "Server address written"

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
        --served-model-name qwen-vl-72b \
        --tensor-parallel-size 4 \
        --dtype auto \
        --host 0.0.0.0 \
        --port "$VLLM_PORT"
