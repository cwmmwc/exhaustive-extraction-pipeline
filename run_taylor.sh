#!/bin/bash
cd ~/projects/exhaustive-extraction-pipeline
python3 extract_single_pdf.py \
  "/Users/cwm6W/Desktop/1976 Taylor REPORT ON PURCHASE OF INDIAN LAND.pdf" \
  --vision \
  --vision-batch 3 \
  --output vision_taylor_full
