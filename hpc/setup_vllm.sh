#!/bin/bash
# ─────────────────────────────────────────────────────────
# Setup vLLM on UVA Rivanna/Afton
#
# Run this ONCE to pull the vLLM container and install
# Python dependencies. Everything goes in $SCRATCH to
# avoid home directory quota.
#
# Usage:
#   bash hpc/setup_vllm.sh
# ─────────────────────────────────────────────────────────

set -euo pipefail

echo "Setting up vLLM for model comparison on Rivanna..."

# ── Directories ──
CONTAINER_DIR="${SCRATCH}/containers"
HF_DIR="${SCRATCH}/huggingface"
mkdir -p "$CONTAINER_DIR" "$HF_DIR"

# ── Pull vLLM container ──
echo ""
echo "Pulling vLLM container (this takes a few minutes)..."
module load apptainer

VLLM_SIF="${CONTAINER_DIR}/vllm.sif"
if [ -f "$VLLM_SIF" ]; then
    echo "  Container already exists at $VLLM_SIF"
    echo "  Delete it and re-run to update."
else
    apptainer pull "$VLLM_SIF" docker://vllm/vllm-openai:latest
    echo "  Saved to $VLLM_SIF"
fi

# ── Python environment for comparison script ──
echo ""
echo "Setting up Python environment..."

VENV_DIR="${SCRATCH}/model-compare-venv"
if [ -d "$VENV_DIR" ]; then
    echo "  Virtualenv already exists at $VENV_DIR"
else
    module load python/3.11
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    # Only need anthropic if running Claude comparisons from HPC
    # (requires outbound internet — works on Rivanna login nodes)
    pip install anthropic
    echo "  Created virtualenv at $VENV_DIR"
fi

# ── Pre-download models (optional, run on login node) ──
echo ""
echo "═══════════════════════════════════════════════"
echo "Setup complete!"
echo ""
echo "Container: $VLLM_SIF"
echo "Virtualenv: $VENV_DIR"
echo "HF cache: $HF_DIR"
echo ""
echo "Next steps:"
echo "  1. Copy corpus_context.json and compare_claude_vs_local_models.py to your working dir"
echo "  2. Set your allocation in hpc/run_comparison.slurm (-A flag)"
echo "  3. (Optional) Pre-download models:"
echo "     export HF_HOME=$HF_DIR"
echo "     huggingface-cli download meta-llama/Llama-3.3-70B-Instruct"
echo "     huggingface-cli download Qwen/Qwen2.5-72B-Instruct"
echo "     huggingface-cli download google/gemma-3-27b-it"
echo "  4. Submit jobs:"
echo "     sbatch --export=MODEL=meta-llama/Llama-3.3-70B-Instruct hpc/run_comparison.slurm"
echo "     sbatch --export=MODEL=Qwen/Qwen2.5-72B-Instruct hpc/run_comparison.slurm"
echo "     sbatch --export=MODEL=google/gemma-3-27b-it,MODE=extraction --gres=gpu:a100:1 hpc/run_comparison.slurm"
echo "═══════════════════════════════════════════════"
