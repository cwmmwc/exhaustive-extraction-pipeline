#!/bin/bash
# Pull v3 vs v4 test results from HPC.
set -e

CTL=/tmp/cwm6w-hpc-v3pull-$$
HOST=cwm6w@login.hpc.virginia.edu
SRC="/project/LawData/kimi-extraction/outputs/v3_test/"
DST="$HOME/projects/exhaustive-extraction-pipeline/comparisons/v3_vs_v4_test/"

mkdir -p "$DST"

ssh -M -S "$CTL" -o ControlPersist=10m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

rsync -avh --progress \
  -e "ssh -o ControlPath=$CTL" \
  --exclude='_raw_failures/' \
  --exclude='*chunk*.json' \
  --exclude='*.txt' \
  --exclude='*.err' \
  --exclude='*.out' \
  "$HOST:$SRC" "$DST"

echo
echo "Done. Results at: $DST"
