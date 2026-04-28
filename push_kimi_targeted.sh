#!/bin/bash
# Push updated code (with targeted affidavit prompts v1+v2) and SLURM scripts to HPC.
# PDFs are already there from the previous push.
set -e

CTL=/tmp/cwm6w-hpc-tgt-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline

ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

SCP="scp -o ControlPath=$CTL"
SSH="ssh -S $CTL $HOST"

REMOTE_BASE="/project/LawData/kimi-extraction"

$SSH "mkdir -p $REMOTE_BASE/outputs/circular_2464_kimi_targeted_10k $REMOTE_BASE/outputs/circular_2464_kimi_targeted_v2_10k"

echo "Pushing updated code..."
$SCP "$REPO/extract_single_pdf.py" \
     "$REPO/retry_kimi_targeted_v2.py" \
     "$HOST:$REMOTE_BASE/code/"

echo "Pushing SLURM scripts..."
$SCP "$REPO/hpc/run_circular2464_kimi_targeted.slurm" \
     "$REPO/hpc/run_circular2464_kimi_targeted_v2.slurm" \
     "$REPO/hpc/run_retry_kimi_targeted_v2.slurm" \
     "$HOST:$REMOTE_BASE/hpc/"

echo ""
echo "Done. SSH to HPC and run:"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_retry_kimi_targeted_v2.slurm"
