#!/bin/bash
# Pull Circular 2464 Kimi 5K and page-level experiment results from HPC.
set -e

CTL=/tmp/cwm6w-hpc-exp-pull-$$
HOST=cwm6w@login.hpc.virginia.edu

ssh -M -S "$CTL" -o ControlPersist=10m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

REMOTE="$HOST:/project/LawData/kimi-extraction/outputs"
LOCAL="$HOME/projects/exhaustive-extraction-pipeline/circular_2464_extractions"

for DIR in circular_2464_affidavit_5k circular_2464_affidavit_page; do
    echo "Pulling ${DIR}..."
    mkdir -p "$LOCAL/${DIR}"
    rsync -avh --progress \
      -e "ssh -o ControlPath=$CTL" \
      --exclude='_raw_failures/' \
      --exclude='*chunk*.json' \
      --exclude='*.txt' \
      --exclude='*.err' \
      --exclude='*.out' \
      "$REMOTE/${DIR}/" "$LOCAL/${DIR}/"
    echo ""
done

echo "Done."
for DIR in circular_2464_affidavit_5k circular_2464_affidavit_page; do
    echo "  ${DIR}: $(find "$LOCAL/${DIR}" -name '*.json' 2>/dev/null | wc -l) JSONs"
done
