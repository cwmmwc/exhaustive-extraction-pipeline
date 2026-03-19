#!/bin/bash
# ─────────────────────────────────────────────────────────
# Submit comparison jobs for all three models
#
# Usage:
#   bash hpc/run_all_models.sh            # extraction mode (default)
#   MODE=synthesis bash hpc/run_all_models.sh  # synthesis mode
#
# Edit the -A allocation below before running.
# ─────────────────────────────────────────────────────────

set -euo pipefail

ALLOCATION="${ALLOCATION:-<your_allocation>}"
MODE="${MODE:-extraction}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f corpus_context.json ]; then
    echo "ERROR: corpus_context.json not found in current directory."
    echo "Generate it locally: python3 compare_claude_vs_local_models.py --dump-context"
    exit 1
fi

echo "Submitting ${MODE} comparison jobs for all three models..."
echo ""

# Gemma 3 27B — fits on 1 GPU
JOB1=$(sbatch --parsable \
    -A "$ALLOCATION" \
    --gres=gpu:a100:1 \
    --mem=64G \
    --export=MODEL=google/gemma-3-27b-it,MODE=$MODE \
    "${SCRIPT_DIR}/run_comparison.slurm")
echo "Gemma 3 27B:     Job $JOB1 (1x A100)"

# Qwen 2.5 72B — needs 2 GPUs
JOB2=$(sbatch --parsable \
    -A "$ALLOCATION" \
    --gres=gpu:a100:2 \
    --constraint=a100_80gb \
    --mem=128G \
    --export=MODEL=Qwen/Qwen2.5-72B-Instruct,MODE=$MODE \
    "${SCRIPT_DIR}/run_comparison.slurm")
echo "Qwen 2.5 72B:    Job $JOB2 (2x A100 80GB)"

# Llama 3.3 70B — needs 2 GPUs
JOB3=$(sbatch --parsable \
    -A "$ALLOCATION" \
    --gres=gpu:a100:2 \
    --constraint=a100_80gb \
    --mem=128G \
    --export=MODEL=meta-llama/Llama-3.3-70B-Instruct,MODE=$MODE \
    "${SCRIPT_DIR}/run_comparison.slurm")
echo "Llama 3.3 70B:   Job $JOB3 (2x A100 80GB)"

echo ""
echo "Monitor with: squeue -u \$USER"
echo "Results will appear in comparisons/ when jobs complete."
