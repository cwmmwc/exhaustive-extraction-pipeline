#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --partition=standard
#SBATCH --mem=16G
#SBATCH -J "qwen-vl-full-cards"
#SBATCH -o /project/LawData/kimi-extraction/logs/qwen_vl_full_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/qwen_vl_full_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

# Full index card collection through Qwen2.5-VL-72B.
# Requires the qwen-vl-server SLURM job to already be running and writing
# its address to /project/LawData/kimi-extraction/logs/qwen_vl_address.txt
#
# Set INDEX_CARDS_DIR and OUTPUT_DIR via --export when submitting:
#   sbatch --export=INDEX_CARDS_DIR=/path/to/cards,OUTPUT_DIR=/path/out hpc/run_qwen_vl_full_index_cards.slurm

set -euo pipefail

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

ADDR_FILE="/project/LawData/kimi-extraction/logs/qwen_vl_address.txt"

# Wait up to 30 minutes for server to be reachable
for i in $(seq 1 180); do
    if [ -f "$ADDR_FILE" ]; then
        ADDR=$(cat "$ADDR_FILE" | tr -d '\n')
        if curl -s --max-time 5 "http://${ADDR}/health" > /dev/null 2>&1; then
            echo "Qwen-VL server ready at ${ADDR}"
            break
        fi
    fi
    if [ "$i" -eq 180 ]; then
        echo "ERROR: Server not ready after 30 minutes"
        exit 1
    fi
    if [ $((i % 30)) -eq 0 ]; then
        echo "  Waiting for server... ($((i * 10 / 60)) min)"
    fi
    sleep 10
done

: "${INDEX_CARDS_DIR:?Set INDEX_CARDS_DIR via --export}"
: "${OUTPUT_DIR:=/project/LawData/kimi-extraction/outputs/qwen_vl_index_cards}"

echo "═══════════════════════════════════════════════"
echo "Qwen-VL Full Index Card Extraction"
echo "Input:  ${INDEX_CARDS_DIR}"
echo "Output: ${OUTPUT_DIR}"
echo "═══════════════════════════════════════════════"

python3 /project/LawData/exhaustive-extraction-pipeline/run_qwen_vl_index_cards_full.py \
    "${INDEX_CARDS_DIR}" \
    "${OUTPUT_DIR}"
