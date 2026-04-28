#!/bin/bash
# Push updated code to HPC.
# Uses an SSH ControlMaster so you only enter your password ONCE for the
# whole batch. The control socket persists for 5 minutes, so re-runs within
# that window also skip the password prompt.
set -e

CTL=/tmp/cwm6w-hpc-ctl-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline

# Open one master connection and keep it alive in the background.
ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

SCP="scp -o ControlPath=$CTL"

$SCP "$REPO/extract_single_pdf.py" \
    "$HOST:/project/LawData/kimi-extraction/code/"

$SCP "$REPO/hpc/run_kimi_extraction.slurm" \
     "$REPO/hpc/start_qwen_vl_server.slurm" \
     "$REPO/hpc/run_qwen_vl_test.slurm" \
     "$REPO/hpc/run_qwen_vl_full_index_cards.slurm" \
     "$REPO/hpc/check_status.sh" \
    "$HOST:/project/LawData/exhaustive-extraction-pipeline/hpc/"

$SCP "$REPO/run_qwen_vl_index_cards_full.py" \
    "$HOST:/project/LawData/exhaustive-extraction-pipeline/"

echo "Done."
