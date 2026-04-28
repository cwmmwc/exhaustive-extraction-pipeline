#!/bin/bash
set -e
CTL=/tmp/cwm6w-hpc-log-$$
HOST=cwm6w@login.hpc.virginia.edu
ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT
SSH="ssh -S $CTL $HOST"

echo "=== STDOUT ==="
$SSH "cat /project/LawData/kimi-extraction/logs/circular2464_kimi_targeted_11801232.out 2>/dev/null || echo '(no stdout log)'"
echo ""
echo "=== STDERR ==="
$SSH "cat /project/LawData/kimi-extraction/logs/circular2464_kimi_targeted_11801232.err 2>/dev/null || echo '(no stderr log)'"
