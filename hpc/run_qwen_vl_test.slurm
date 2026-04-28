#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --partition=standard
#SBATCH --mem=16G
#SBATCH -J "qwen-vl-test"
#SBATCH -o /project/LawData/kimi-extraction/logs/qwen_vl_test_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/qwen_vl_test_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

set -euo pipefail

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

ADDR_FILE="/project/LawData/kimi-extraction/logs/qwen_vl_address.txt"

# Wait up to 30 minutes for server to be ready
for i in $(seq 1 180); do
    if [ -f "$ADDR_FILE" ]; then
        ADDR=$(cat "$ADDR_FILE" | tr -d '\n')
        if curl -s --max-time 5 "http://${ADDR}/health" > /dev/null 2>&1; then
            echo "Server ready at ${ADDR}"
            break
        fi
    fi
    if [ "$i" -eq 180 ]; then
        echo "ERROR: Server not ready after 30 minutes"
        exit 1
    fi
    if [ $((i % 30)) -eq 0 ]; then
        echo "  Waiting... ($((i * 10 / 60)) min)"
    fi
    sleep 10
done

echo "Running Qwen-VL index card test..."
python3 /project/LawData/exhaustive-extraction-pipeline/test_qwen_vl_cards.py
