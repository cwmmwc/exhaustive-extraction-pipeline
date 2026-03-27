#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=3:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:a100:2
#SBATCH --constraint=a100_80gb
#SBATCH --partition=gpu
#SBATCH --mem=256G
#SBATCH -J "qwen-benchmark"
#SBATCH -o /project/LawData/kimi-extraction/logs/qwen_bench_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/qwen_bench_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# ─────────────────────────────────────────────────────────
# Qwen 2.5 72B Benchmark
#
# Starts vLLM server with Qwen 2.5 72B on 2x A100, then runs:
#   1. 3-doc extraction benchmark (docs 798, 811, 695)
#   2. Full CCF 56074 chunked extraction (221 pages)
#
# Prerequisites:
#   - corpus_context.json in /project/LawData/kimi-extraction/
#   - CCF 56074 PDF in /project/LawData/kimi-extraction/pdfs/
#   - extract_single_pdf.py + compare_claude_vs_local_models.py
#     in /project/LawData/exhaustive-extraction-pipeline/
#
# Usage:
#   sbatch hpc/benchmark_qwen.slurm
# ─────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
REPO_DIR="/project/LawData/exhaustive-extraction-pipeline"
MODEL_PATH="/project/LawData/models/Qwen2.5-72B-Instruct"
VLLM_SIF="/scratch/$USER/containers/vllm_kimi.sif"
VLLM_PORT=8000
NUM_GPUS=2

module purge
module load apptainer

mkdir -p /scratch/$USER/fakehome/.cache/{huggingface,vllm,flashinfer,triton}

echo "═══════════════════════════════════════════════"
echo "Qwen 2.5 72B Benchmark"
echo "Model:    ${MODEL_PATH}"
echo "GPUs:     ${NUM_GPUS}x A100 80GB"
echo "Node:     $(hostname)"
echo "Job ID:   ${SLURM_JOB_ID}"
echo "Started:  $(date)"
echo "═══════════════════════════════════════════════"

# ── Start vLLM server ──
echo ""
echo "Starting vLLM server..."

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
        --served-model-name qwen2.5-72b \
        --tensor-parallel-size "$NUM_GPUS" \
        --trust-remote-code \
        --dtype auto \
        --max-model-len 32768 \
        --gpu-memory-utilization 0.95 \
        --host 0.0.0.0 \
        --port "$VLLM_PORT" \
    &
VLLM_PID=$!

# Wait for server
echo "Waiting for vLLM server..."
for i in $(seq 1 120); do
    if curl -s "http://localhost:${VLLM_PORT}/v1/models" > /dev/null 2>&1; then
        echo "Server ready after ${i} attempts (~$((i*5))s)"
        break
    fi
    if ! kill -0 $VLLM_PID 2>/dev/null; then
        echo "ERROR: vLLM server died"
        exit 1
    fi
    sleep 5
done

curl -s "http://localhost:${VLLM_PORT}/v1/models" | python3 -m json.tool
VLLM_URL="http://localhost:${VLLM_PORT}"

# ── Set up Python environment ──
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate
cd "$REPO_DIR"

# ── Benchmark 1: 3-doc extraction (798, 811, 695) ──
echo ""
echo "═══════════════════════════════════════════════"
echo "Benchmark 1: 3-doc extraction (798, 811, 695)"
echo "═══════════════════════════════════════════════"

python3 compare_claude_vs_local_models.py \
    --backend vllm \
    --vllm-url "$VLLM_URL" \
    --context-file "${PROJECT_DIR}/corpus_context.json" \
    --local-only \
    --local-models "qwen2.5-72b" \
    --mode extraction \
    --doc-ids 798 811 695

# ── Benchmark 2: CCF 56074 full document ──
echo ""
echo "═══════════════════════════════════════════════"
echo "Benchmark 2: CCF 56074 full document (chunked)"
echo "═══════════════════════════════════════════════"

python3 extract_single_pdf.py \
    "${PROJECT_DIR}/pdfs/1921 CCF 56074-21-312 GS.pdf" \
    --vllm-url "$VLLM_URL" \
    --vllm-model "qwen2.5-72b" \
    --chunked \
    --output "${PROJECT_DIR}/outputs/qwen_benchmark_ccf56074"

# ── Done ──
echo ""
echo "═══════════════════════════════════════════════"
echo "Benchmark complete. $(date)"
echo "Results:"
echo "  3-doc: comparisons/ (latest qwen directory)"
echo "  CCF 56074: ${PROJECT_DIR}/outputs/qwen_benchmark_ccf56074/"
echo "═══════════════════════════════════════════════"

kill $VLLM_PID 2>/dev/null || true
wait $VLLM_PID 2>/dev/null || true
