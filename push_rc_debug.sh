#!/bin/bash
scp ~/projects/exhaustive-extraction-pipeline/test_rc_debug.py \
    cwm6w@login.hpc.virginia.edu:/project/LawData/
scp ~/projects/exhaustive-extraction-pipeline/test_rc_debug2.py \
    cwm6w@login.hpc.virginia.edu:/project/LawData/
scp ~/projects/exhaustive-extraction-pipeline/test_rc_debug3.py \
    cwm6w@login.hpc.virginia.edu:/project/LawData/
scp ~/projects/exhaustive-extraction-pipeline/test_rc_debug4.py \
    cwm6w@login.hpc.virginia.edu:/project/LawData/
echo "Done. Run: python3 /project/LawData/test_rc_debug4.py"
