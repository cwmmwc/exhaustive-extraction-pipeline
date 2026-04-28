#!/bin/bash
set -e
CTL=/tmp/cwm6w-hpc-ls-$$
HOST=cwm6w@login.hpc.virginia.edu
ssh -M -S "$CTL" -o ControlPersist=5m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT
SSH="ssh -S $CTL $HOST"

echo "=== circular_2464 directory ==="
$SSH "ls -la /project/LawData/kimi-extraction/pdfs/circular_2464/ 2>/dev/null || echo '(directory not found)'"
echo ""
echo "=== All pdf dirs ==="
$SSH "ls -d /project/LawData/kimi-extraction/pdfs/*/ 2>/dev/null || echo '(no pdfs dir)'"
echo ""
echo "=== Find any 312 Affidavit PDFs ==="
$SSH "find /project/LawData/kimi-extraction/pdfs/ -name '*312*' -o -name '*Affidavit*' -o -name '*affidavit*' -o -name '*pine*' -o -name '*Pine*' 2>/dev/null | head -20"
