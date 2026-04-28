#!/bin/bash
# Push Circular 2464 Pine Ridge affidavits to HPC for extraction.
# Runs both v3 and v5 for comparison against hand-transcribed data.
#
# After this completes, SSH to HPC and run:
#   sbatch /project/LawData/kimi-extraction/hpc/run_circular2464.slurm
set -e

CTL=/tmp/cwm6w-hpc-c2464-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline
SRC="$HOME/Library/CloudStorage/OneDrive-UniversityofVirginia/Circular 2464"

ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

SCP="scp -o ControlPath=$CTL"
SSH="ssh -S $CTL $HOST"
RSYNC="rsync -avz --progress -e 'ssh -o ControlPath=$CTL'"

REMOTE_BASE="/project/LawData/kimi-extraction"

$SSH "mkdir -p $REMOTE_BASE/pdfs/circular_2464 $REMOTE_BASE/outputs/circular_2464_v3 $REMOTE_BASE/outputs/circular_2464_v4 $REMOTE_BASE/outputs/circular_2464_v5 $REMOTE_BASE/hpc"

echo "Pushing code..."
$SCP "$REPO/extract_single_pdf.py" "$HOST:$REMOTE_BASE/code/"

echo "Pushing SLURM script..."
$SCP "$REPO/hpc/run_circular2464.slurm" "$HOST:$REMOTE_BASE/hpc/"

echo "Pushing Pine Ridge affidavit PDFs..."
rsync -avz --progress -e "ssh -o ControlPath=$CTL" \
    "$SRC/Pine Ridge Affidavits in Reply to Circular 2464/" \
    "$HOST:$REMOTE_BASE/pdfs/circular_2464/pine_ridge/"

echo "Pushing Replies to Circular 2464 PDFs (text-readable parts)..."
rsync -avz --progress -e "ssh -o ControlPath=$CTL" \
    "$SRC/Replies to Circular 2464/" \
    "$HOST:$REMOTE_BASE/pdfs/circular_2464/replies/"

echo ""
echo "Done. SSH to HPC and run:"
echo "  ssh cwm6w@login.hpc.virginia.edu"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_circular2464.slurm"
