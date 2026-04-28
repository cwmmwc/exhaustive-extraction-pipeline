#!/bin/bash
set -e
CTL=/tmp/cwm6w-hpc-raw-$$
HOST=cwm6w@login.hpc.virginia.edu
ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT
SSH="ssh -S $CTL $HOST"

DIR="/project/LawData/kimi-extraction/outputs/circular_2464_kimi_targeted_10k/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3]"

echo "=== Files in output dir ==="
$SSH "ls -la '$DIR/' 2>/dev/null || echo '(dir not found)'"
echo ""
echo "=== Chunk 1 raw (first 2000 chars) ==="
$SSH "head -c 2000 '$DIR/Kimi K2.5_chunk_1_raw.txt' 2>/dev/null || echo '(no raw file)'"
echo ""
echo "=== Chunk 2 JSON (first 1000 chars) ==="
$SSH "head -c 1000 '$DIR/Kimi K2.5_chunk_2.json' 2>/dev/null || echo '(no chunk 2)'"
