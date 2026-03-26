#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=4:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "qwen-download"
#SBATCH -o /project/LawData/kimi-extraction/logs/qwen_download_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/qwen_download_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=$USER@virginia.edu

# Download Qwen 2.5 72B for benchmarking (~140GB, ~30 min)

set -euo pipefail
module purge
module load apptainer

echo "Downloading Qwen 2.5 72B..."
echo "Started: $(date)"

mkdir -p /project/LawData/models/Qwen2.5-72B-Instruct
mkdir -p /scratch/$USER/fakehome/.cache/huggingface

apptainer exec \
    --bind /project/LawData:/project/LawData \
    --bind /scratch/$USER:/scratch/$USER \
    --bind /scratch/$USER/fakehome:/home/$USER \
    --env HOME=/home/$USER \
    --env HF_HOME=/home/$USER/.cache/huggingface \
    /scratch/$USER/containers/vllm_kimi.sif \
    hf download Qwen/Qwen2.5-72B-Instruct \
        --local-dir /project/LawData/models/Qwen2.5-72B-Instruct

echo "Done. $(date)"
echo "Model: /project/LawData/models/Qwen2.5-72B-Instruct"
