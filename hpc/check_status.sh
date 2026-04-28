#!/bin/bash
# Quick status check for the in-flight HPC extractions.
# Run on HPC: bash /project/LawData/exhaustive-extraction-pipeline/hpc/check_status.sh

LOGS=/project/LawData/kimi-extraction/logs
QWEN_OUT=/project/LawData/kimi-extraction/outputs/qwen_vl_index_cards

echo "═══════════════════════════════════════════════════════════════"
echo "  RUNNING JOBS"
echo "═══════════════════════════════════════════════════════════════"
squeue -u cwm6w
echo

# ─────────────────────────────────────────────────────────────────
# Survey of Conditions extraction (Kimi K2.5 via RC GenAI)
# ─────────────────────────────────────────────────────────────────
SURVEY_LOG=$(ls -t "$LOGS"/extract_*.out 2>/dev/null | head -1)
if [ -n "$SURVEY_LOG" ]; then
    echo "═══════════════════════════════════════════════════════════════"
    echo "  SURVEY (Kimi K2.5)"
    echo "  Log: $(basename "$SURVEY_LOG")"
    echo "═══════════════════════════════════════════════════════════════"
    # In this slurm script's log, [N/44] headers are printed ONLY for
    # volumes actually being processed (not skipped). SKIPped volumes get
    # a separate "SKIP:" line and no [N/44] header. So the [N/44] count IS
    # the processed count — do NOT subtract SKIPs from it.
    PROCESSED=$(grep -c "^\[" "$SURVEY_LOG" || echo 0)
    SKIPS=$(grep -c "^SKIP:" "$SURVEY_LOG" || echo 0)
    REMAINING=$((44 - PROCESSED - SKIPS))
    echo "Skipped (already done elsewhere): ${SKIPS}"
    echo "Processed/in-progress this run:    ${PROCESSED}"
    echo "Still queued in input list:        ${REMAINING}"
    echo "  (Per README: 26 of 48 Survey volumes done by Together AI; ~23 remaining queued on HPC)"
    echo
    echo "Current volume:"
    grep "^\[" "$SURVEY_LOG" | tail -1 | sed 's/^/  /'
    echo
    echo "Recent chunks:"
    grep "Done in\|ERROR" "$SURVEY_LOG" | tail -5 | sed 's/^/  /'
    echo
fi

# ─────────────────────────────────────────────────────────────────
# Qwen-VL index card extraction
# ─────────────────────────────────────────────────────────────────
QWEN_LOG=$(ls -t "$LOGS"/qwen_vl_full_*.out 2>/dev/null | head -1)
if [ -n "$QWEN_LOG" ]; then
    echo "═══════════════════════════════════════════════════════════════"
    echo "  QWEN-VL INDEX CARDS"
    echo "  Log: $(basename "$QWEN_LOG")"
    echo "═══════════════════════════════════════════════════════════════"
    DONE=$(find "$QWEN_OUT" -name "*.json" 2>/dev/null | wc -l)
    echo "PDFs completed: ${DONE} of 87"
    echo
    echo "Per-PDF results:"
    python3 - <<'PYEOF'
import json, glob, os
out = "/project/LawData/kimi-extraction/outputs/qwen_vl_index_cards"
files = sorted(glob.glob(os.path.join(out, "**/*.json"), recursive=True))
totals = {"slips": 0, "cases": 0, "persons": 0, "pages": 0, "fail": 0}
for p in files:
    try:
        d = json.load(open(p))
    except Exception as e:
        print(f"  ERROR reading {p}: {e}")
        continue
    m = d.get("_meta", {})
    pages = m.get("pages", "?")
    secs = m.get("total_seconds", 0)
    slips = len(d.get("record_slips", []))
    cases = len(d.get("legal_cases", []))
    persons = len(d.get("persons", []))
    fail = len(m.get("failed_pages", []))
    rel = os.path.relpath(p, out)
    print(f"  {pages}p {secs:.0f}s slips={slips} cases={cases} persons={persons} fail={fail}  {rel}")
    if isinstance(pages, int):
        totals["pages"] += pages
    totals["slips"] += slips
    totals["cases"] += cases
    totals["persons"] += persons
    totals["fail"] += fail
print()
print(f"  TOTALS  pages={totals['pages']}  slips={totals['slips']}  cases={totals['cases']}  persons={totals['persons']}  failed_pages={totals['fail']}")
PYEOF
    echo
fi

# ─────────────────────────────────────────────────────────────────
# Qwen-VL server activity (last few requests)
# ─────────────────────────────────────────────────────────────────
SERVER_LOG=$(ls -t "$LOGS"/qwen_vl_*.out 2>/dev/null | grep -v "_full_\|_test_" | head -1)
if [ -n "$SERVER_LOG" ]; then
    echo "═══════════════════════════════════════════════════════════════"
    echo "  QWEN-VL SERVER (last 3 lines)"
    echo "═══════════════════════════════════════════════════════════════"
    tail -3 "$SERVER_LOG" | sed 's/^/  /'
fi
