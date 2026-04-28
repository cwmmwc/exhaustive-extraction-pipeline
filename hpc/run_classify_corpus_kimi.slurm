#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "classify-all"
#SBATCH -o /project/LawData/kimi-extraction/logs/classify_corpus_kimi_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/classify_corpus_kimi_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

set -euo pipefail

PROJECT_DIR="/project/LawData/kimi-extraction"
CODE_DIR="${PROJECT_DIR}/code"
OUTPUT_DIR="${PROJECT_DIR}/outputs/classifications"

export UVARC_GenAI_API="sk-a9f6eea852fb4de8b178bf5937cf4937"

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

mkdir -p "$OUTPUT_DIR"

echo "═══════════════════════════════════════════════"
echo "Full Corpus Page Classification — Kimi K2.5"
echo "Collapsed categories, max_tokens=8000, retry wrapper"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

python3 << 'PYEOF'
import fitz, json, csv, os, sys, time, glob
from collections import Counter

sys.path.insert(0, '/project/LawData/kimi-extraction/code')
from classify_pages import classify_kimi, CLASSIFY_PROMPT

vllm_url = 'https://open-webui.rc.virginia.edu'
api_key = os.environ['UVARC_GenAI_API']
output_dir = '/project/LawData/kimi-extraction/outputs/classifications'

# PDFs to classify
pdf_base = '/project/LawData/kimi-extraction/pdfs/circular_2464'
pdfs = []

# Pine Ridge Vols 2 and 3 (Vol 1 already done)
for vol in ['[2 of 3]', '[3 of 3]']:
    path = f'{pdf_base}/pine_ridge/312 Affidavits by Indians who accepted land patents under protest 1928 {vol}.pdf'
    if os.path.exists(path):
        label = f'vol{vol[1]}'
        pdfs.append((path, label))

# Replies parts
replies_dir = f'{pdf_base}/replies'
if os.path.isdir(replies_dir):
    for f in sorted(os.listdir(replies_dir)):
        if f.endswith('.pdf'):
            label = f.replace('.pdf', '').replace(' ', '_')
            pdfs.append((os.path.join(replies_dir, f), label))

# Check alternate location for replies
if not os.path.isdir(replies_dir):
    # They might be directly in pdf_base or a different subdir
    for f in sorted(glob.glob(f'{pdf_base}/*.pdf')) + sorted(glob.glob(f'{pdf_base}/**/*.pdf', recursive=True)):
        basename = os.path.basename(f)
        if 'pine_ridge' in f and '[1 of 3]' in basename:
            continue  # Skip Vol 1 (already done)
        if basename in [os.path.basename(p) for p, _ in pdfs]:
            continue  # Skip duplicates
        label = basename.replace('.pdf', '').replace(' ', '_')
        pdfs.append((f, label))

print(f'Found {len(pdfs)} PDFs to classify:')
for path, label in pdfs:
    doc = fitz.open(path)
    print(f'  {label}: {len(doc)} pages')

# Classify each PDF
corpus_counts = Counter()
corpus_total_pages = 0
corpus_total_time = 0

for pdf_path, label in pdfs:
    doc = fitz.open(pdf_path)
    pages = len(doc)
    print(f'\n{"="*60}')
    print(f'{label} ({pages} pages)')
    print(f'{"="*60}')

    results = []
    pdf_time = 0
    first_ok = 0
    retry_ok = 0
    failed = 0

    for p in range(pages):
        text = doc[p].get_text()
        cls, conf, in_tok, out_tok, elapsed, retry_log = classify_kimi(text, vllm_url, api_key, max_retries=5)
        preview = text[:100].replace('\n', ' | ')
        results.append((p + 1, cls, conf, preview))
        pdf_time += elapsed
        corpus_counts[cls] += 1

        if retry_log[0]['failure'] is None:
            first_ok += 1
        elif cls != 'error':
            retry_ok += 1
        else:
            failed += 1

        if (p + 1) % 20 == 0 or p == 0 or p == pages - 1:
            retries = len(retry_log)
            retry_str = f' (attempt {retries})' if retries > 1 else ''
            print(f'  Page {p+1}/{pages}: {cls} ({conf}){retry_str} [{elapsed:.1f}s]')

    # Write CSV
    csv_path = os.path.join(output_dir, f'{label}_classifications_kimi.csv')
    with open(csv_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['pdf_name', 'page_number', 'classification', 'confidence', 'first_150_chars'])
        for pnum, cls, conf, preview in results:
            w.writerow([label, pnum, cls, conf, preview])

    counts = Counter(r[1] for r in results)
    print(f'\n  Summary: {dict(counts.most_common())}')
    print(f'  First attempt: {first_ok}, Retry: {retry_ok}, Failed: {failed}')
    print(f'  Time: {pdf_time:.1f}s ({pdf_time/60:.1f} min)')

    corpus_total_pages += pages
    corpus_total_time += pdf_time

# Corpus summary
print(f'\n{"="*60}')
print(f'CORPUS SUMMARY')
print(f'{"="*60}')
print(f'Total PDFs: {len(pdfs)}')
print(f'Total pages: {corpus_total_pages}')
print(f'Total time: {corpus_total_time:.1f}s ({corpus_total_time/60:.1f} min)')
print(f'\nClassification counts:')
for cls, count in corpus_counts.most_common():
    pct = count * 100 / corpus_total_pages
    print(f'  {cls:<30} {count:>5} ({pct:>5.1f}%)')
PYEOF

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "═══════════════════════════════════════════════"
