#!/bin/bash
# Pull Circular 2464 affidavit prompt results from HPC.
set -e

CTL=/tmp/cwm6w-hpc-aff-pull-$$
HOST=cwm6w@login.hpc.virginia.edu

ssh -M -S "$CTL" -o ControlPersist=10m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

REMOTE="$HOST:/project/LawData/kimi-extraction/outputs/circular_2464_affidavit/"
LOCAL="$HOME/projects/exhaustive-extraction-pipeline/circular_2464_extractions/affidavit/"

mkdir -p "$LOCAL"

rsync -avh --progress \
  -e "ssh -o ControlPath=$CTL" \
  --exclude='_raw_failures/' \
  --exclude='*chunk*.json' \
  --exclude='*.txt' \
  --exclude='*.err' \
  --exclude='*.out' \
  "$REMOTE" "$LOCAL"

echo ""
echo "Done. JSONs: $(find "$LOCAL" -name '*.json' | wc -l)"
