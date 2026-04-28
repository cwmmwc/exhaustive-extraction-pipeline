#!/bin/bash
# Pull the completed Qwen-VL index card extractions from HPC into the Mac
# qwen_vl_index_cards_full/ directory, where the merge script will read them.
#
# Mirrors the directory structure from HPC. Excludes raw failure dumps.
#
# Uses an SSH ControlMaster so you only enter your password once.
set -e

CTL=/tmp/cwm6w-hpc-qwen-$$
HOST=cwm6w@login.hpc.virginia.edu
SRC="/project/LawData/kimi-extraction/outputs/qwen_vl_index_cards/"
DST="$HOME/projects/exhaustive-extraction-pipeline/qwen_vl_index_cards_full/"

mkdir -p "$DST"

# Open one master SSH connection
ssh -M -S "$CTL" -o ControlPersist=10m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

rsync -avh --progress \
  -e "ssh -o ControlPath=$CTL" \
  --exclude='_raw_failures/' \
  "$HOST:$SRC" "$DST"

echo
echo "Done. Qwen-VL index card extractions are at:"
echo "  $DST"
echo
echo "Counts:"
find "$DST" -name "*.json" | wc -l | xargs echo "  JSON files:"
du -sh "$DST" | awk '{print "  Total size:", $1}'
