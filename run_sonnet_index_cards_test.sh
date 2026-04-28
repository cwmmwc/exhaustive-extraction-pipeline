#!/bin/bash
# Rerun Claude Sonnet on the same 20 test pages used for the Qwen-VL comparison,
# this time using the --index-cards schema (not the general extraction schema).
# Outputs to comparisons/sonnet_index_cards_test/ for direct diff with Qwen-VL.
set -e

cd ~/projects/exhaustive-extraction-pipeline
source venv/bin/activate

PDF="RG 60 index cards/90-2-5/1935 RG 60, Entry A1 96C, Record Slips, 1935, Class Numbers (Interfiled), Box 487, 90-2-5.pdf"
OUT="comparisons/sonnet_index_cards_test"

python3 extract_single_pdf.py "$PDF" \
    --vision \
    --index-cards \
    --vision-pages 1-20 \
    --vision-batch 1 \
    --output "$OUT"

echo
echo "Done. Compare against Qwen-VL with:"
echo "  cat $OUT/vision_merged.json | python3 -m json.tool | head -40"
