#!/bin/bash
scp ~/projects/exhaustive-extraction-pipeline/test_kimi_vision_cards.py \
    cwm6w@login.hpc.virginia.edu:/project/LawData/exhaustive-extraction-pipeline/

scp ~/projects/exhaustive-extraction-pipeline/hpc/start_qwen_vl_server.slurm \
    cwm6w@login.hpc.virginia.edu:/project/LawData/exhaustive-extraction-pipeline/hpc/

scp ~/projects/exhaustive-extraction-pipeline/hpc/run_qwen_vl_test.slurm \
    cwm6w@login.hpc.virginia.edu:/project/LawData/exhaustive-extraction-pipeline/hpc/

echo "Done. On HPC:"
echo "  1. Kimi vision test (run now from compute node):"
echo "     python3 /project/LawData/exhaustive-extraction-pipeline/test_kimi_vision_cards.py"
echo "  2. Qwen-VL on A100 (submit and check start time):"
echo "     cd /project/LawData/exhaustive-extraction-pipeline"
echo "     sbatch hpc/start_qwen_vl_server.slurm"
echo "     scontrol show job JOBID | grep StartTime"
