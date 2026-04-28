#!/bin/bash
# Pull Kimi targeted affidavit extraction results from HPC (v1 and v2).
set -e

CTL=/tmp/cwm6w-hpc-tgt-pull-$$
HOST=cwm6w@login.hpc.virginia.edu

ssh -M -S "$CTL" -o ControlPersist=10m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

REMOTE_BASE="$HOST:/project/LawData/kimi-extraction/outputs"
LOCAL_BASE="$HOME/projects/exhaustive-extraction-pipeline/circular_2464_extractions"

for DIR in kimi_targeted_10k kimi_targeted_v2_10k; do
    REMOTE="$REMOTE_BASE/circular_2464_${DIR}"
    LOCAL="$LOCAL_BASE/${DIR}"
    mkdir -p "$LOCAL"

    echo "Pulling ${DIR}..."
    rsync -avh --progress \
      -e "ssh -o ControlPath=$CTL" \
      --exclude='*chunk*.json' \
      --exclude='*.txt' \
      --exclude='*.err' \
      --exclude='*.out' \
      "$REMOTE/" "$LOCAL/"
    echo ""
done

echo "Done."
for DIR in kimi_targeted_10k kimi_targeted_v2_10k; do
    echo "  ${DIR}: $(find "$LOCAL_BASE/${DIR}" -name '*.json' 2>/dev/null | wc -l) JSONs"
done
