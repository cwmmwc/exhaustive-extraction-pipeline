#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=2-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=standard
#SBATCH --mem=32G
#SBATCH -J "classify-v1"
#SBATCH -o /project/LawData/kimi-extraction/logs/classify_vol1_kimi_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/classify_vol1_kimi_%j.err
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
echo "Page Classification — Kimi K2.5 (with retry, max_tokens=8000)"
echo "Pine Ridge Volume 1 (148 pages)"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

python3 << 'PYEOF'
import fitz, json, csv, os, sys, time
from collections import Counter

sys.path.insert(0, '/project/LawData/kimi-extraction/code')
from classify_pages import classify_kimi, CLASSIFY_PROMPT

pdf_path = '/project/LawData/kimi-extraction/pdfs/circular_2464/pine_ridge/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3].pdf'
output_dir = '/project/LawData/kimi-extraction/outputs/classifications'

doc = fitz.open(pdf_path)
pages = len(doc)
print(f'Classifying {pages} pages with Kimi K2.5 (max 5 retries per page)')

vllm_url = 'https://open-webui.rc.virginia.edu'
api_key = os.environ['UVARC_GenAI_API']

results = []
all_retry_logs = {}
total_time = 0

first_attempt_ok = 0
retry_ok = 0
retry_distribution = Counter()  # attempt_number -> count
failed_all = 0

for p in range(pages):
    text = doc[p].get_text()
    cls, conf, in_tok, out_tok, elapsed, retry_log = classify_kimi(text, vllm_url, api_key, max_retries=5)
    preview = text[:100].replace('\n', ' | ')
    results.append((p + 1, cls, conf, in_tok, out_tok, elapsed, preview))
    all_retry_logs[p + 1] = retry_log
    total_time += elapsed

    # Classify retry outcome
    attempts_needed = len([r for r in retry_log if r['failure'] is not None]) + (0 if cls == 'error' else 1)
    if retry_log[0]['failure'] is None:
        first_attempt_ok += 1
    elif cls != 'error':
        retry_ok += 1
        retry_distribution[len(retry_log)] += 1
    else:
        failed_all += 1

    if (p + 1) % 10 == 0 or p == 0:
        retries = len(retry_log)
        retry_str = f' (attempt {retries})' if retries > 1 else ''
        print(f'  Page {p+1}/{pages}: {cls} ({conf}){retry_str} [{elapsed:.1f}s]')

# Write CSV
with open(os.path.join(output_dir, 'vol1_classifications_kimi.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['pdf_name', 'page_number', 'classification', 'confidence', 'first_150_chars'])
    for pnum, cls, conf, _, _, _, preview in results:
        w.writerow(['vol1', pnum, cls, conf, preview])

# Summary
counts = Counter(r[1] for r in results)
conf_counts = Counter(r[2] for r in results)

print(f'\n{"="*60}')
print(f'RESULTS')
print(f'{"="*60}')
print(f'Total pages: {pages}')
print(f'First attempt success: {first_attempt_ok}')
print(f'Succeeded after retry: {retry_ok}')
if retry_distribution:
    print(f'  Retry distribution: {dict(retry_distribution)}')
print(f'Failed all 5 retries: {failed_all}')
print(f'Total success rate: {(first_attempt_ok + retry_ok) * 100 / pages:.1f}%')
print(f'Total time: {total_time:.1f}s ({total_time/60:.1f} min)')
print(f'\nClassification summary:')
for cls, count in counts.most_common():
    print(f'  {cls:<35} {count:>5}')
print(f'\nConfidence: {dict(conf_counts)}')

# Save usage
with open(os.path.join(output_dir, 'vol1_kimi_usage.json'), 'w') as f:
    json.dump({
        'pages': pages,
        'first_attempt_ok': first_attempt_ok,
        'retry_ok': retry_ok,
        'failed_all': failed_all,
        'retry_distribution': dict(retry_distribution),
        'total_time_s': round(total_time, 1),
    }, f, indent=2)

# Save failure log for UVARC support ticket
failure_log = []
for page_num, retry_log in sorted(all_retry_logs.items()):
    if any(r['failure'] for r in retry_log):
        failure_log.append({
            'page': page_num,
            'attempts': len(retry_log),
            'final_outcome': results[page_num - 1][1],
            'log': retry_log,
        })

with open(os.path.join(output_dir, 'vol1_kimi_failure_log_maxtokens8000.json'), 'w') as f:
    json.dump({
        'endpoint': 'https://open-webui.rc.virginia.edu/api/chat/completions',
        'model': 'Kimi K2.5',
        'task': 'page classification (single JSON response per page)',
        'date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_pages': pages,
        'first_attempt_failures': pages - first_attempt_ok,
        'recovered_by_retry': retry_ok,
        'unrecoverable': failed_all,
        'failure_pattern': 'Empty SSE content with reasoning-only response or no response',
        'pages_with_failures': failure_log,
    }, f, indent=2)

print(f'\nFailure log saved: {len(failure_log)} pages had at least one failed attempt')
PYEOF

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "═══════════════════════════════════════════════"
