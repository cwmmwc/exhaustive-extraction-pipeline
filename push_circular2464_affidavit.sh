#!/bin/bash
# Push updated code (with affidavit prompt) and SLURM script to HPC.
# PDFs are already there from the previous push.
set -e

CTL=/tmp/cwm6w-hpc-aff-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline

ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

SCP="scp -o ControlPath=$CTL"
SSH="ssh -S $CTL $HOST"

REMOTE_BASE="/project/LawData/kimi-extraction"

$SSH "mkdir -p $REMOTE_BASE/outputs/circular_2464_affidavit $REMOTE_BASE/outputs/circular_2464_affidavit_5k $REMOTE_BASE/outputs/circular_2464_affidavit_page"

echo "Pushing updated code (with affidavit prompt)..."
$SCP "$REPO/extract_single_pdf.py" "$HOST:$REMOTE_BASE/code/"

echo "Pushing SLURM scripts..."
$SCP "$REPO/hpc/run_circular2464_affidavit.slurm" \
     "$REPO/hpc/run_circular2464_affidavit_experiments.slurm" \
     "$HOST:$REMOTE_BASE/hpc/"

echo ""
echo "Done. SSH to HPC and run:"
echo "  ssh cwm6w@login.hpc.virginia.edu"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_circular2464_affidavit_experiments.slurm"
