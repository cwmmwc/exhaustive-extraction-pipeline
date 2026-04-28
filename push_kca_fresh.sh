#!/bin/bash
# Fresh start: push all KCA PDFs and code to HPC for clean v3 + v4 extraction.
#
# Wipes old outputs and pushes the full corpus with OCR'd affidavits.
#
# After this completes, SSH to HPC and run:
#   sbatch /project/LawData/kimi-extraction/hpc/run_kca_fresh_v3.slurm
#   sbatch /project/LawData/kimi-extraction/hpc/run_kca_fresh_v4.slurm
set -e

CTL=/tmp/cwm6w-hpc-fresh-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline

ssh -M -S "$CTL" -o ControlPersist=10m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

SCP="scp -o ControlPath=$CTL"
SSH="ssh -S $CTL $HOST"
RSYNC="rsync -avz --progress -e 'ssh -o ControlPath=$CTL'"

REMOTE_BASE="/project/LawData/kimi-extraction"

# Clean old outputs and create fresh directories
echo "Cleaning old KCA outputs on HPC..."
$SSH "rm -rf $REMOTE_BASE/outputs/kca $REMOTE_BASE/outputs/kca_v3 $REMOTE_BASE/pdfs/kca && mkdir -p $REMOTE_BASE/outputs/kca_fresh_v3 $REMOTE_BASE/outputs/kca_fresh_v4 $REMOTE_BASE/pdfs/kca $REMOTE_BASE/hpc $REMOTE_BASE/code"

# Push code
echo "Pushing code..."
$SCP "$REPO/extract_single_pdf.py" "$HOST:$REMOTE_BASE/code/"

# Push SLURM scripts
echo "Pushing SLURM scripts..."
$SCP "$REPO/hpc/run_kca_fresh_v3.slurm" \
     "$REPO/hpc/run_kca_fresh_v4.slurm" \
     "$HOST:$REMOTE_BASE/hpc/"

# Push all KCA PDFs (including OCR'd affidavits)
echo "Pushing all KCA PDFs..."
eval $RSYNC --delete "$REPO/corpora/KIOWA/" "$HOST:$REMOTE_BASE/pdfs/kca/"

echo ""
echo "Done. Now SSH to HPC and run both jobs:"
echo "  ssh cwm6w@login.hpc.virginia.edu"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_kca_fresh_v3.slurm"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_kca_fresh_v4.slurm"
