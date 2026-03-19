#!/bin/bash
#SBATCH --job-name=model-compare
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a100:2
#SBATCH --constraint=a100_80gb
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=6:00:00
#SBATCH --output=comparison_%j.out
#SBATCH --error=comparison_%j.err
#SBATCH -A <your_allocation>

# ─────────────────────────────────────────────────────────
# Model Comparison on UVA Rivanna/Afton
#
# This script launches a vLLM server on a GPU node, then runs
# the comparison script against it.
#
# Prerequisites:
#   1. Copy corpus_context.json to your working directory
#      (generate with: python3 compare_claude_vs_local_models.py --dump-context)
#   2. Set your allocation group above (-A flag)
#   3. Build the vLLM Apptainer image (see hpc/setup_vllm.sh)
#
# Usage:
#   # Compare Llama 3.3 70B
#   sbatch --export=MODEL=meta-llama/Llama-3.3-70B-Instruct hpc/run_comparison.slurm
#
#   # Compare Qwen 2.5 72B
#   sbatch --export=MODEL=Qwen/Qwen2.5-72B-Instruct hpc/run_comparison.slurm
#
#   # Compare Gemma 3 27B (only needs 1 GPU)
#   sbatch --export=MODEL=google/gemma-3-27b-it --gres=gpu:a100:1 hpc/run_comparison.slurm
#
# Note: 70B+ models need 2x A100 80GB with tensor parallelism.
#       27B models fit on 1x A100 80GB.
# ─────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ──
MODEL="${MODEL:-meta-llama/Llama-3.3-70B-Instruct}"
MODE="${MODE:-extraction}"
VLLM_PORT=8000
NUM_GPUS=$(echo $SLURM_JOB_GPUS | tr ',' '\n' | wc -l)

# HuggingFace cache — store models in scratch to avoid home quota
export HF_HOME="${SCRATCH}/huggingface"
export TRANSFORMERS_CACHE="${SCRATCH}/huggingface"
mkdir -p "$HF_HOME"

# You need a HuggingFace token for gated models (Llama, Gemma)
# Set in your ~/.bashrc or pass via --export=HF_TOKEN=...
export HF_TOKEN="${HF_TOKEN:-}"

echo "═══════════════════════════════════════════════"
echo "Model:    ${MODEL}"
echo "Mode:     ${MODE}"
echo "GPUs:     ${NUM_GPUS}"
echo "Node:     $(hostname)"
echo "Job ID:   ${SLURM_JOB_ID}"
echo "═══════════════════════════════════════════════"

# ── Load modules ──
module load apptainer

VLLM_SIF="${SCRATCH}/containers/vllm.sif"
if [ ! -f "$VLLM_SIF" ]; then
    echo "ERROR: vLLM container not found at $VLLM_SIF"
    echo "Run: bash hpc/setup_vllm.sh"
    exit 1
fi

# ── Start vLLM server ──
echo "Starting vLLM server for ${MODEL} on ${NUM_GPUS} GPUs..."
apptainer exec --nv \
    --bind "${HF_HOME}:/root/.cache/huggingface" \
    "$VLLM_SIF" \
    python -m vllm.entrypoints.openai.api_server \
        --model "$MODEL" \
        --tensor-parallel-size "$NUM_GPUS" \
        --max-model-len 32768 \
        --port "$VLLM_PORT" \
        --trust-remote-code \
    &
VLLM_PID=$!

# Wait for server to be ready
echo "Waiting for vLLM server to start..."
for i in $(seq 1 120); do
    if curl -s "http://localhost:${VLLM_PORT}/v1/models" > /dev/null 2>&1; then
        echo "vLLM server ready after ${i}s"
        break
    fi
    if ! kill -0 $VLLM_PID 2>/dev/null; then
        echo "ERROR: vLLM server process died"
        exit 1
    fi
    sleep 5
done

# Verify it's actually serving
curl -s "http://localhost:${VLLM_PORT}/v1/models" | python3 -m json.tool

# ── Run comparison ──
echo ""
echo "Running comparison..."

# Use a short model name for output filenames
SHORT_MODEL=$(echo "$MODEL" | sed 's|.*/||')

python3 compare_claude_vs_local_models.py \
    --backend vllm \
    --vllm-url "http://localhost:${VLLM_PORT}" \
    --context-file corpus_context.json \
    --local-only \
    --local-models "$MODEL" \
    --mode "$MODE"

echo ""
echo "═══════════════════════════════════════════════"
echo "Done. Results in comparisons/"
echo "═══════════════════════════════════════════════"

# Cleanup
kill $VLLM_PID 2>/dev/null || true
wait $VLLM_PID 2>/dev/null || true
