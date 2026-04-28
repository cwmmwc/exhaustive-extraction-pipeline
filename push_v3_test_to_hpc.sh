#!/bin/bash
# Push a single PDF + code to HPC for a Kimi v3 vs v4 comparison test.
# Usage: ./push_v3_test_to_hpc.sh
#
# After this completes, SSH to HPC and run:
#   sbatch /project/LawData/kimi-extraction/hpc/run_v3_test.slurm
set -e

CTL=/tmp/cwm6w-hpc-v3test-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline

ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

SCP="scp -o ControlPath=$CTL"
SSH="ssh -S $CTL $HOST"

REMOTE_BASE="/project/LawData/kimi-extraction"

$SSH "mkdir -p $REMOTE_BASE/pdfs/v3_test $REMOTE_BASE/outputs/v3_test $REMOTE_BASE/hpc"

echo "Pushing code..."
$SCP "$REPO/extract_single_pdf.py" "$HOST:$REMOTE_BASE/code/"

echo "Pushing SLURM script..."
$SCP "$REPO/hpc/run_v3_test.slurm" "$HOST:$REMOTE_BASE/hpc/"

echo "Pushing Part 33 PDF..."
$SCP "$REPO/survey_pdfs/1934; San Diego, CA; San Francisco, CA; Part 33.pdf" \
     "$HOST:$REMOTE_BASE/pdfs/v3_test/"

echo ""
echo "Done. Now SSH to HPC and run:"
echo "  ssh cwm6w@login.hpc.virginia.edu"
echo "  sbatch /project/LawData/kimi-extraction/hpc/run_v3_test.slurm"
