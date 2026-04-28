#!/bin/bash
# Push the affidavit v4 re-extraction SLURM script to HPC.
set -e
CTL=/tmp/cwm6w-hpc-aff-$$
HOST=cwm6w@login.hpc.virginia.edu
ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT
scp -o "ControlPath=$CTL" \
    ~/projects/exhaustive-extraction-pipeline/hpc/run_affidavit_v4_reextract.slurm \
    "$HOST:/project/LawData/kimi-extraction/hpc/"
echo "Done. SSH to HPC and run:"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_affidavit_v4_reextract.slurm"
