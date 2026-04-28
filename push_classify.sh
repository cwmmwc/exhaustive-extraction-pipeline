#!/bin/bash
# Push classification code to HPC
set -e
CTL=/tmp/cwm6w-hpc-cls-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline
ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT
SCP="scp -o ControlPath=$CTL"
SSH="ssh -S $CTL $HOST"
REMOTE_BASE="/project/LawData/kimi-extraction"

$SSH "mkdir -p $REMOTE_BASE/outputs/classifications"

echo "Pushing code..."
$SCP "$REPO/classify_pages.py" "$HOST:$REMOTE_BASE/code/"

echo "Pushing SLURM script..."
$SCP "$REPO/hpc/run_classify_vol1_kimi.slurm" "$HOST:$REMOTE_BASE/hpc/"

echo ""
echo "Done. SSH to HPC and run:"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_classify_vol1_kimi.slurm"
