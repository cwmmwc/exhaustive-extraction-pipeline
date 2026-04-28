#!/bin/bash
set -e
CTL=/tmp/cwm6w-hpc-raw-$$
HOST=cwm6w@login.hpc.virginia.edu
ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT

REMOTE_DIR="/project/LawData/kimi-extraction/outputs/circular_2464_kimi_targeted_v2_10k/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3]"
LOCAL_DIR="$HOME/projects/exhaustive-extraction-pipeline/circular_2464_extractions/kimi_targeted_v2_10k/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3]"

echo "Pulling raw failure files..."
scp -o ControlPath="$CTL" "$HOST":"'${REMOTE_DIR}'"/*_raw.txt "$LOCAL_DIR/"

echo ""
echo "Done."
ls -la "$LOCAL_DIR/"*_raw.txt 2>/dev/null || echo "(no raw files found)"
