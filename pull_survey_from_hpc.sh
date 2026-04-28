#!/bin/bash
# Pull the Survey of Conditions Kimi K2.5 extractions from HPC into the
# Mac survey_of_conditions_extractions/ directory, where the loader expects them.
#
# Excludes:
#   - qwen_vl_index_cards/   (a different project's outputs in the same parent dir)
#   - per-chunk JSONs        (we only want the merged per-volume file)
#   - _raw_failures and txt logs
#
# Uses an SSH ControlMaster so you only enter your password once.
set -e

CTL=/tmp/cwm6w-hpc-survey-$$
HOST=cwm6w@login.hpc.virginia.edu
SRC="/project/LawData/kimi-extraction/outputs/"
DST="$HOME/projects/exhaustive-extraction-pipeline/survey_of_conditions_extractions/"

mkdir -p "$DST"

# Open one master SSH connection
ssh -M -S "$CTL" -o ControlPersist=10m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

rsync -avh --progress \
  -e "ssh -o ControlPath=$CTL" \
  --exclude='qwen_vl_index_cards/' \
  --exclude='qwen_vl_index_cards' \
  --exclude='qwen_vl_*' \
  --exclude='_raw_failures/' \
  --exclude='*chunk*.json' \
  --exclude='*.txt' \
  --exclude='*.err' \
  --exclude='*.out' \
  "$HOST:$SRC" "$DST"

echo
echo "Done. New extractions are at:"
echo "  $DST"
echo
echo "Next steps:"
echo "  cd ~/projects/exhaustive-extraction-pipeline"
echo "  source venv/bin/activate"
echo "  python3 load_survey_extractions.py"
