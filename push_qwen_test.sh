#!/bin/bash
# Push Qwen-VL test files to HPC

scp ~/projects/exhaustive-extraction-pipeline/test_qwen_vl_cards.py \
    cwm6w@login.hpc.virginia.edu:/project/LawData/exhaustive-extraction-pipeline/

scp ~/projects/exhaustive-extraction-pipeline/"RG 60 index cards/90-2-5/1935 RG 60, Entry A1 96C, Record Slips, 1935, Class Numbers (Interfiled), Box 487, 90-2-5.pdf" \
    cwm6w@login.hpc.virginia.edu:/project/LawData/exhaustive-extraction-pipeline/

echo "Done. When Qwen-VL server starts, SSH to HPC and run:"
echo "  salloc --partition=standard --time=00:30:00 --cpus-per-task=4"
echo "  python3 /project/LawData/exhaustive-extraction-pipeline/test_qwen_vl_cards.py"
