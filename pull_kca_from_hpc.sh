#!/bin/bash
# Pull the KCA/Kiowa Kimi K2.5 re-extractions from HPC.
#
# Uses an SSH ControlMaster so you only enter your password once.
set -e

CTL=/tmp/cwm6w-hpc-kca-$$
HOST=cwm6w@login.hpc.virginia.edu
SRC="/project/LawData/kimi-extraction/outputs/kca/"
DST="$HOME/projects/exhaustive-extraction-pipeline/kca_reextraction/"

mkdir -p "$DST"

# Open one master SSH connection
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
echo "Done. Extractions are at:"
echo "  $DST"
echo
echo "Next steps:"
echo "  cd ~/projects/exhaustive-extraction-pipeline"
echo "  source venv/bin/activate"
echo "  python3 load_kca_extractions.py"
