#!/bin/bash
scp ~/projects/exhaustive-extraction-pipeline/test_rc_40k.py \
    cwm6w@login.hpc.virginia.edu:/project/LawData/
echo "Done. On HPC compute node run: python3 /project/LawData/test_rc_40k.py"
