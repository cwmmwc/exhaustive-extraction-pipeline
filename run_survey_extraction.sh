#!/bin/bash
# ─────────────────────────────────────────────────────────
# Batch Kimi K2.5 extraction of Survey of Conditions PDFs
#
# Runs all non-duplicate PDFs through Kimi K2.5 via Together AI
# with v4 chunked extraction (40K chars, 5K overlap).
# v4 extracts 10 types: entities, events, financial_transactions,
# relationships, fee_patents, correspondence, legislative_actions,
# testimony, taxes, mortgages.
#
# Usage:
#   export TOGETHER_API_KEY=your_key
#   bash run_survey_extraction.sh
#
# Results go to: survey_of_conditions_extractions/
# Skip-on-exists: safe to re-run if interrupted.
# ─────────────────────────────────────────────────────────

set -euo pipefail

PDF_DIR="/Users/cwm6W/Library/CloudStorage/Box-Box/Survey of Conditions"
OUTPUT_DIR="survey_of_conditions_extractions"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "${TOGETHER_API_KEY:-}" ]; then
    echo "ERROR: TOGETHER_API_KEY not set"
    echo "  export TOGETHER_API_KEY=your_key"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# Count non-duplicate, non-partial PDFs
TOTAL=0
while IFS= read -r -d '' pdf; do
    TOTAL=$((TOTAL + 1))
done < <(find "$PDF_DIR" -name "*.pdf" -not -iname "*duplicate*" -not -iname "*partial*" -print0)

echo "═══════════════════════════════════════════════"
echo "Survey of Conditions — Kimi K2.5 v4 Extraction"
echo "Types: entities, events, financial, relationships, fee_patents,"
echo "       correspondence, legislative, testimony, taxes, mortgages"
echo "PDFs: $TOTAL (excluding duplicates/partials)"
echo "Output: $OUTPUT_DIR/"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"
echo ""

DONE=0
FAILED=0
SKIPPED=0

while IFS= read -r -d '' pdf; do
    basename=$(basename "$pdf" .pdf)
    safe_name=$(echo "$basename" | tr ' ;:' '___')
    output_subdir="${OUTPUT_DIR}/${safe_name}"

    # Skip if already extracted
    if [ -f "${output_subdir}/kimi-k2.5.json" ]; then
        SKIPPED=$((SKIPPED + 1))
        echo "SKIP [$((DONE + FAILED + SKIPPED))/$TOTAL]: ${basename} (already done)"
        continue
    fi

    echo ""
    echo "────────────────────────────────────────────"
    echo "[$((DONE + FAILED + SKIPPED + 1))/$TOTAL] ${basename}"
    echo "────────────────────────────────────────────"

    if python3 "${SCRIPT_DIR}/extract_single_pdf.py" \
        "$pdf" \
        --together-model kimi-k2.5 \
        --together-only \
        --chunked \
        --output "$output_subdir"; then
        DONE=$((DONE + 1))
    else
        FAILED=$((FAILED + 1))
        echo "FAILED: ${basename}"
    fi

done < <(find "$PDF_DIR" -name "*.pdf" -not -iname "*duplicate*" -not -iname "*partial*" -print0 | sort -z)

echo ""
echo "═══════════════════════════════════════════════"
echo "Complete. $(date)"
echo "  Succeeded: $DONE"
echo "  Failed:    $FAILED"
echo "  Skipped:   $SKIPPED"
echo "  Total:     $TOTAL"
echo "Results: $OUTPUT_DIR/"
echo "═══════════════════════════════════════════════"
