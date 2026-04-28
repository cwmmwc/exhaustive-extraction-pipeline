#!/bin/bash
# Run all index card PDFs through vision extraction with custom index card prompt
cd ~/projects/exhaustive-extraction-pipeline
source venv/bin/activate

OUTPUT_BASE="vision_index_cards_full"
mkdir -p "$OUTPUT_BASE"

TOTAL=0
DONE=0
FAILED=0

# Find all PDFs in the RG 60 index cards directory
while IFS= read -r pdf; do
    TOTAL=$((TOTAL + 1))
done < <(find "RG 60 index cards" -name "*.pdf" -type f)

echo "═══════════════════════════════════════════════"
echo "Index Card Extraction — Claude Sonnet Vision"
echo "Total PDFs: $TOTAL"
echo "Output: $OUTPUT_BASE/"
echo "═══════════════════════════════════════════════"

find "RG 60 index cards" -name "*.pdf" -type f | sort | while IFS= read -r pdf; do
    # Create output dir from filename
    basename=$(basename "$pdf" .pdf)
    outdir="$OUTPUT_BASE/$basename"

    # Skip if already extracted
    if [ -f "$outdir/vision_merged.json" ]; then
        echo "SKIP: $basename (already extracted)"
        continue
    fi

    DONE=$((DONE + 1))
    echo ""
    echo "[$DONE] $basename"

    python3 extract_single_pdf.py "$pdf" \
        --index-cards \
        --vision-batch 1 \
        --output "$outdir"
done

echo ""
echo "═══════════════════════════════════════════════"
echo "Done."
echo "═══════════════════════════════════════════════"
