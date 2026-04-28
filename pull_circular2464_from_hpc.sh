#!/bin/bash
# Pull Circular 2464 v3/v4/v5 extraction results from HPC.
set -e

CTL=/tmp/cwm6w-hpc-c2464-pull-$$
HOST=cwm6w@login.hpc.virginia.edu

ssh -M -S "$CTL" -o ControlPersist=10m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

REMOTE_BASE="/project/LawData/kimi-extraction/outputs"
LOCAL_BASE="$HOME/projects/exhaustive-extraction-pipeline/circular_2464_extractions"

for VERSION in v3 v4 v5; do
    echo "Pulling ${VERSION} results..."
    mkdir -p "$LOCAL_BASE/${VERSION}"
    rsync -avh --progress \
      -e "ssh -o ControlPath=$CTL" \
      --exclude='_raw_failures/' \
      --exclude='*chunk*.json' \
      --exclude='*.txt' \
      --exclude='*.err' \
      --exclude='*.out' \
      "$HOST:$REMOTE_BASE/circular_2464_${VERSION}/" "$LOCAL_BASE/${VERSION}/"
    echo ""
done

echo "Done. Results at: $LOCAL_BASE"
for VERSION in v3 v4 v5; do
    echo "  ${VERSION}: $(find "$LOCAL_BASE/${VERSION}" -name '*.json' 2>/dev/null | wc -l) JSONs"
done
