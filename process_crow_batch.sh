#!/bin/bash
# process_crow_batch.sh
# Prepares batches of 50 PDFs for overnight processing
#
# Usage:
#   ./process_crow_batch.sh 1    # prepare batch 1 (files 1-50)
#   ./process_crow_batch.sh 2    # prepare batch 2 (files 51-100)
#   etc.

BATCH_NUM=$1
BATCH_SIZE=50
CROW_DIR="/Users/cwm6W/Library/CloudStorage/Box-Box/Crow for Jeremy/Crow"
BATCH_DIR="$HOME/Desktop/CROW_BATCH_${BATCH_NUM}"

if [ -z "$BATCH_NUM" ]; then
    echo "Usage: $0 <batch_number>"
    echo "Example: $0 1"
    exit 1
fi

START=$(( ($BATCH_NUM - 1) * $BATCH_SIZE + 1 ))
END=$(( $BATCH_NUM * $BATCH_SIZE ))

echo "Processing Crow Batch $BATCH_NUM (files $START to $END)"

# Create batch directory
mkdir -p "$BATCH_DIR"

# Find and copy files
find "$CROW_DIR" -name "*.pdf" | sort | sed -n "${START},${END}p" > /tmp/batch_files_$BATCH_NUM.txt

COUNT=0
while IFS= read -r file; do
    cp "$file" "$BATCH_DIR/"
    COUNT=$((COUNT + 1))
done < /tmp/batch_files_$BATCH_NUM.txt

echo "✓ Batch $BATCH_NUM ready: $COUNT files"
echo ""
echo "To process this batch, run:"
echo "  export ANTHROPIC_API_KEY='your-key-here'"
echo "  python3 poc_pipeline_chunked.py --input '$BATCH_DIR' --output 'results_crow_batch_$BATCH_NUM'"
echo ""
echo "To run overnight without sleep:"
echo "  caffeinate -i python3 poc_pipeline_chunked.py --input '$BATCH_DIR' --output 'results_crow_batch_$BATCH_NUM'"
