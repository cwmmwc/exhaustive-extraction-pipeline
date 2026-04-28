#!/bin/bash
# Pull fresh KCA v3 and v4 extraction results from HPC.
set -e

CTL=/tmp/cwm6w-hpc-fresh-pull-$$
HOST=cwm6w@login.hpc.virginia.edu

ssh -M -S "$CTL" -o ControlPersist=10m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

REMOTE_BASE="/project/LawData/kimi-extraction/outputs"
LOCAL_BASE="$HOME/projects/exhaustive-extraction-pipeline/kca_reextraction"

echo "Pulling v3 results..."
mkdir -p "$LOCAL_BASE/fresh_v3"
rsync -avh --progress \
  -e "ssh -o ControlPath=$CTL" \
  --exclude='_raw_failures/' \
  --exclude='*chunk*.json' \
  --exclude='*.txt' \
  --exclude='*.err' \
  --exclude='*.out' \
  "$HOST:$REMOTE_BASE/kca_fresh_v3/" "$LOCAL_BASE/fresh_v3/"

echo ""
echo "Pulling v4 results..."
mkdir -p "$LOCAL_BASE/fresh_v4"
rsync -avh --progress \
  -e "ssh -o ControlPath=$CTL" \
  --exclude='_raw_failures/' \
  --exclude='*chunk*.json' \
  --exclude='*.txt' \
  --exclude='*.err' \
  --exclude='*.out' \
  "$HOST:$REMOTE_BASE/kca_fresh_v4/" "$LOCAL_BASE/fresh_v4/"

echo ""
echo "Pulling v5 results..."
mkdir -p "$LOCAL_BASE/fresh_v5"
rsync -avh --progress \
  -e "ssh -o ControlPath=$CTL" \
  --exclude='_raw_failures/' \
  --exclude='*chunk*.json' \
  --exclude='*.txt' \
  --exclude='*.err' \
  --exclude='*.out' \
  "$HOST:$REMOTE_BASE/kca_fresh_v5/" "$LOCAL_BASE/fresh_v5/" 2>/dev/null || echo "  (v5 not ready yet)"

echo ""
echo "Done. Results at:"
echo "  v3: $LOCAL_BASE/fresh_v3/"
echo "  v4: $LOCAL_BASE/fresh_v4/"
echo "  v5: $LOCAL_BASE/fresh_v5/"
echo ""
echo "v3 JSONs: $(find "$LOCAL_BASE/fresh_v3" -name '*.json' 2>/dev/null | wc -l)"
echo "v4 JSONs: $(find "$LOCAL_BASE/fresh_v4" -name '*.json' 2>/dev/null | wc -l)"
echo "v5 JSONs: $(find "$LOCAL_BASE/fresh_v5" -name '*.json' 2>/dev/null | wc -l)"
