#!/bin/bash
# ─────────────────────────────────────────────────────────
# Setup Kimi K2.5 on UVA HPC
#
# Run this ONCE to:
#   1. Create the project directory structure
#   2. Download Kimi K2.5 model weights (~549GB, takes a while)
#   3. Set up the Python environment
#   4. Verify the vLLM container exists
#
# Usage:
#   bash hpc/setup_kimi.sh
#
# This should be run on a login node (it needs internet access
# for the model download). For very large downloads, consider
# submitting as a SLURM job on the standard partition.
# ─────────────────────────────────────────────────────────

set -euo pipefail

echo "Setting up Kimi K2.5 for extraction on UVA HPC..."
echo ""

# ── 1. Directory structure ──
echo "Creating directory structure..."
mkdir -p /project/LawData/kimi-extraction/{logs,pdfs,outputs,code}
mkdir -p /scratch/$USER/fakehome/.cache/{huggingface,vllm,flashinfer,triton}
echo "  /project/LawData/kimi-extraction/logs/     — server + worker logs"
echo "  /project/LawData/kimi-extraction/pdfs/     — stage PDFs here for extraction"
echo "  /project/LawData/kimi-extraction/outputs/  — extraction results (JSON)"
echo "  /project/LawData/kimi-extraction/code/     — copy extract_single_pdf.py here"

# ── 2. Check container ──
echo ""
VLLM_SIF="/project/LawData/models/container/vllm_0.14.1-cu130.sif"
if [ -f "$VLLM_SIF" ]; then
    echo "vLLM container found: $VLLM_SIF"
    echo "  NOTE: Kimi K2.5 requires transformers >= 4.57.1."
    echo "  If the existing container is too old, build a new one:"
    echo "    module load apptainer"
    echo "    apptainer pull /scratch/$USER/containers/vllm_kimi.sif docker://vllm/vllm-openai:latest"
    echo "  Then update VLLM_SIF in start_kimi_server.slurm."
else
    echo "vLLM container NOT found at $VLLM_SIF"
    echo "Building container (this takes ~20 minutes)..."
    module load apptainer
    mkdir -p /project/LawData/models/container
    apptainer pull "$VLLM_SIF" docker://vllm/vllm-openai:latest
    echo "  Saved to $VLLM_SIF"
fi

# ── 3. Python environment ──
echo ""
VENV_DIR="/scratch/$USER/model-compare-venv"
if [ -d "$VENV_DIR" ]; then
    echo "Python virtualenv exists: $VENV_DIR"
else
    echo "Creating Python virtualenv..."
    module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install pymupdf requests
    echo "  Created: $VENV_DIR"
fi

# ── 4. Download Kimi K2.5 ──
echo ""
MODEL_DIR="/project/LawData/models/Kimi-K2.5"
if [ -d "$MODEL_DIR" ] && [ "$(ls -A "$MODEL_DIR" 2>/dev/null)" ]; then
    echo "Kimi K2.5 model already exists at $MODEL_DIR"
else
    echo "Downloading Kimi K2.5 to $MODEL_DIR..."
    echo "  This is a ~549GB model. It will take a significant amount of time."
    echo "  If this times out on the login node, submit as a SLURM job instead."
    echo ""

    module load apptainer
    mkdir -p "$MODEL_DIR"

    # Use huggingface-cli inside the container (has the right dependencies)
    apptainer exec \
        --bind /project/LawData:/project/LawData \
        --bind /scratch/$USER:/scratch/$USER \
        --bind /scratch/$USER/fakehome:/home/$USER \
        --env HOME=/home/$USER \
        --env HF_HOME=/home/$USER/.cache/huggingface \
        "$VLLM_SIF" \
        huggingface-cli download moonshotai/Kimi-K2.5 \
            --local-dir "$MODEL_DIR"

    echo "  Download complete: $MODEL_DIR"
fi

# ── 5. Copy extraction code ──
echo ""
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
if [ -f "$REPO_DIR/extract_single_pdf.py" ]; then
    cp "$REPO_DIR/extract_single_pdf.py" /project/LawData/kimi-extraction/code/
    echo "Copied extract_single_pdf.py to /project/LawData/kimi-extraction/code/"
else
    echo "WARNING: extract_single_pdf.py not found in $REPO_DIR"
    echo "  Copy it manually: cp extract_single_pdf.py /project/LawData/kimi-extraction/code/"
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Stage PDFs:    cp *.pdf /project/LawData/kimi-extraction/pdfs/"
echo "  2. Start server:  sbatch hpc/start_kimi_server.slurm"
echo "  3. Run extraction: sbatch --export=PDF=ALL hpc/run_kimi_extraction.slurm"
echo ""
echo "Or test with a single doc first:"
echo "  sbatch --export=PDF=\"1921 CCF 56074-21-312 GS.pdf\" hpc/run_kimi_extraction.slurm"
echo ""
echo "Monitor:"
echo "  squeue -u \$USER"
echo "  tail -f /project/LawData/kimi-extraction/logs/server_*.out"
echo "═══════════════════════════════════════════════"
