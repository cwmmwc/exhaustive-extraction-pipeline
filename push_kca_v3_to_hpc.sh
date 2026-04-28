#!/bin/bash
# Push updated KCA PDFs (with new OCR'd affidavits) and v3 comparison SLURM script to HPC.
#
# After this completes, SSH to HPC and run:
#   sbatch /project/LawData/kimi-extraction/hpc/run_kca_v3_comparison.slurm
set -e

CTL=/tmp/cwm6w-hpc-v3-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline

ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

SCP="scp -o ControlPath=$CTL"
SSH="ssh -S $CTL $HOST"
RSYNC="rsync -avz --progress -e 'ssh -o ControlPath=$CTL'"

REMOTE_BASE="/project/LawData/kimi-extraction"

$SSH "mkdir -p $REMOTE_BASE/outputs/kca_v3 $REMOTE_BASE/hpc"

echo "Pushing code..."
$SCP "$REPO/extract_single_pdf.py" "$HOST:$REMOTE_BASE/code/"

echo "Pushing SLURM script..."
$SCP "$REPO/hpc/run_kca_v3_comparison.slurm" "$HOST:$REMOTE_BASE/hpc/"

# Push KCA PDFs (including new OCR'd affidavits replacing old empty ones)
echo "Pushing KCA PDFs (rsync, updating OCR'd affidavits)..."
eval $RSYNC "$REPO/corpora/KIOWA/" "$HOST:$REMOTE_BASE/pdfs/kca/"

echo ""
echo "Done. Now SSH to HPC and run:"
echo "  ssh cwm6w@login.hpc.virginia.edu"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_kca_v3_comparison.slurm"
