#!/bin/bash
# Push KCA/Kiowa PDFs and updated code to HPC for Kimi K2.5 re-extraction.
#
# After this completes, SSH to HPC and run:
#   sbatch /project/LawData/kimi-extraction/hpc/run_kca_extraction.slurm
#
set -e

CTL=/tmp/cwm6w-hpc-ctl-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline

# Open one master connection (you enter password once).
ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

SCP="scp -o ControlPath=$CTL"
SSH="ssh -S $CTL $HOST"
RSYNC="rsync -avz --progress -e 'ssh -o ControlPath=$CTL'"

REMOTE_BASE="/project/LawData/kimi-extraction"

# Create directories on HPC
$SSH "mkdir -p $REMOTE_BASE/pdfs/kca $REMOTE_BASE/outputs/kca $REMOTE_BASE/logs $REMOTE_BASE/code $REMOTE_BASE/hpc"

# Push updated extraction code
echo "Pushing code..."
$SCP "$REPO/extract_single_pdf.py" "$HOST:$REMOTE_BASE/code/"

# Push updated SLURM script
echo "Pushing SLURM scripts..."
$SCP "$REPO/hpc/run_kca_extraction.slurm" "$HOST:$REMOTE_BASE/hpc/"

# Push KCA PDFs (recursive, includes Affidavits subdirs) — rsync skips existing
echo "Pushing KCA PDFs (rsync, skipping existing)..."
eval $RSYNC "$REPO/corpora/KIOWA/" "$HOST:$REMOTE_BASE/pdfs/kca/"

echo ""
echo "Done. Now SSH to HPC and run:"
echo "  ssh cwm6w@login.hpc.virginia.edu"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_kca_extraction.slurm"
