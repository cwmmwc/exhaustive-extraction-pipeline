#!/bin/bash
# Push updated code (with v5 prompt) and SLURM script to HPC.
# PDFs are already there from the fresh push.
#
# After this completes, SSH to HPC and run:
#   sbatch /project/LawData/kimi-extraction/hpc/run_kca_fresh_v5.slurm
set -e

CTL=/tmp/cwm6w-hpc-v5-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline

ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

SCP="scp -o ControlPath=$CTL"
SSH="ssh -S $CTL $HOST"

REMOTE_BASE="/project/LawData/kimi-extraction"

$SSH "mkdir -p $REMOTE_BASE/outputs/kca_fresh_v5"

echo "Pushing updated code (with v5 prompt)..."
$SCP "$REPO/extract_single_pdf.py" "$HOST:$REMOTE_BASE/code/"

echo "Pushing SLURM script..."
$SCP "$REPO/hpc/run_kca_fresh_v5.slurm" "$HOST:$REMOTE_BASE/hpc/"

echo ""
echo "Done. SSH to HPC and run:"
echo "  ssh cwm6w@login.hpc.virginia.edu"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_kca_fresh_v5.slurm"
