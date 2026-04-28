#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --partition=standard
#SBATCH --mem=16G
#SBATCH -J "qwen-vl-ledger"
#SBATCH -o /project/LawData/kimi-extraction/logs/qwen_vl_full_ledger_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/qwen_vl_full_ledger_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

set -euo pipefail

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

ADDR_FILE="/project/LawData/kimi-extraction/logs/qwen_vl_address.txt"
OUT_DIR="/project/LawData/kimi-extraction/hpc/qwen_full_ledger_output"
mkdir -p "$OUT_DIR"

# Wait up to 6 hours for GPU server to start
echo "Waiting for Qwen-VL server..."
for i in $(seq 1 2160); do
    if [ -f "$ADDR_FILE" ]; then
        ADDR=$(cat "$ADDR_FILE" | tr -d '\n')
        if curl -s --max-time 5 "http://${ADDR}/health" > /dev/null 2>&1; then
            echo "Server ready at ${ADDR}"
            break
        fi
    fi
    if [ "$i" -eq 2160 ]; then
        echo "ERROR: Server not ready after 6 hours"
        exit 1
    fi
    if [ $((i % 30)) -eq 0 ]; then
        echo "  Waiting... ($((i * 10 / 60)) min)"
    fi
    sleep 10
done

echo "═══════════════════════════════════════════════"
echo "Qwen2.5-VL-72B — Full Ledger Extraction (14 pages)"
echo "Server: ${ADDR}"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

python3 << 'PYEOF'
import fitz, json, os, time, base64, urllib.request, datetime

LEDGER_PDF = '/project/LawData/kimi-extraction/code/circular_2464_extractions/standalone/fee_patent_ledger_part11.pdf'
PROMPT_PATH = '/project/LawData/kimi-extraction/code/prompts/extraction_ledger.md'
OUT_DIR = '/project/LawData/kimi-extraction/hpc/qwen_full_ledger_output'

# Load prompt — verbatim from page-7 run
with open(PROMPT_PATH) as f:
    ledger_prompt = f.read()

vision_prefix = """You are viewing a scanned page from a fee patent ledger. The page has columns arranged left-to-right: Name, Allotment Number, Fee Patent Date (year), and Application Status. Rows are organized under Township/Range section headers.

CRITICAL: Read each ROW across the columns. Each name belongs with the allotment number, date, and status on the SAME horizontal line. Do not shift values between rows.

"""
full_prompt = vision_prefix + ledger_prompt

# Get server address
with open('/project/LawData/kimi-extraction/logs/qwen_vl_address.txt') as f:
    addr = f.read().strip()
url = f"http://{addr}/v1/chat/completions"

# Open the 14-page ledger PDF
doc = fitz.open(LEDGER_PDF)
total_pages = len(doc)
assert total_pages == 14, f"Expected 14 pages, got {total_pages}"

run_start = time.time()
log_rows = []
total_records = 0
succeeded = 0
failed_pages = []

for page_idx in range(total_pages):
    page_num = page_idx + 1
    page_label = f"{page_num:02d}"

    print(f"\n--- Page {page_num}/{total_pages} ---")
    page_start = time.time()

    # Render at 2x (144 DPI) — matching page-7 exactly
    pix = doc[page_idx].get_pixmap(matrix=fitz.Matrix(2, 2))
    img_path = f'/tmp/ledger_page_{page_label}.png'
    pix.save(img_path)
    print(f"  Rendered: {pix.width}x{pix.height}")

    with open(img_path, 'rb') as f:
        img_b64 = base64.standard_b64encode(f.read()).decode('utf-8')

    # Send request — same payload structure as page-7
    payload = json.dumps({
        "model": "qwen-vl-72b",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                },
                {
                    "type": "text",
                    "text": full_prompt
                }
            ]
        }],
        "max_tokens": 16000,
        "temperature": 0.1,
    }).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            raw = resp.read().decode()

        elapsed = time.time() - page_start

        # Parse response
        data = json.loads(raw)
        content = data['choices'][0]['message']['content']
        usage = data.get('usage', {})
        in_tok = usage.get('prompt_tokens', 0)
        out_tok = usage.get('completion_tokens', 0)

        # Parse JSON from content — same logic as page-7
        text = content.strip()
        if text.startswith('```'):
            lines = text.split('\n')
            text = '\n'.join(lines[1:])
            if text.rstrip().endswith('```'):
                text = text.rstrip()[:-3]
            text = text.strip()

        si = text.find('[')
        result = None
        if si >= 0:
            try:
                result = json.loads(text[si:])
            except json.JSONDecodeError:
                ei = text.rfind(']') + 1
                if ei > si:
                    try:
                        result = json.loads(text[si:ei])
                    except json.JSONDecodeError:
                        pass

        if result and isinstance(result, list):
            record_count = len(result)
            total_records += record_count
            succeeded += 1
            status = "OK"
            notes = ""

            # Save — same output schema as page-7
            out_path = os.path.join(OUT_DIR, f'part11_ledger_page_{page_label}.json')
            with open(out_path, 'w') as f:
                json.dump({
                    'model': 'qwen-vl-72b',
                    'records': result,
                    'usage': usage,
                    'elapsed': round(elapsed, 1),
                }, f, indent=2)

            print(f"  OK: {record_count} records in {elapsed:.1f}s (in={in_tok}, out={out_tok})")
            for r in result[:2]:
                print(f"    {r.get('Name',''):<28} allot={r.get('Allotment number',''):<10} date={r.get('Fee Patent Date','')}")

        else:
            record_count = 0
            status = "FAILED"
            notes = f"JSON parse failed; raw content length={len(content)}"
            failed_pages.append(page_num)

            # Save failure placeholder
            out_path = os.path.join(OUT_DIR, f'part11_ledger_page_{page_label}.FAILED.json')
            with open(out_path, 'w') as f:
                json.dump({
                    'model': 'qwen-vl-72b',
                    'error': notes,
                    'raw_content': content[:5000],
                    'elapsed': round(elapsed, 1),
                }, f, indent=2)

            print(f"  FAILED: {notes}")

    except Exception as e:
        elapsed = time.time() - page_start
        record_count = 0
        status = "ERROR"
        notes = f"{type(e).__name__}: {str(e)[:200]}"
        failed_pages.append(page_num)

        out_path = os.path.join(OUT_DIR, f'part11_ledger_page_{page_label}.FAILED.json')
        with open(out_path, 'w') as f:
            json.dump({
                'model': 'qwen-vl-72b',
                'error': notes,
                'elapsed': round(elapsed, 1),
            }, f, indent=2)

        print(f"  ERROR: {notes}")

    log_rows.append({
        'page': page_label,
        'status': status,
        'elapsed': round(elapsed, 1),
        'records': record_count,
        'notes': notes if status != "OK" else "",
    })

run_elapsed = time.time() - run_start

# Write structured log
log_path = os.path.join(OUT_DIR, 'run_log.md')
with open(log_path, 'w') as f:
    f.write(f"# Qwen full ledger run — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"## Server\n")
    f.write(f"- Address: {addr}\n")
    f.write(f"- Model: qwen-vl-72b\n")
    f.write(f"- Container: vllm_0.14.1-cu130.sif\n\n")
    f.write(f"## Per-page results\n")
    f.write(f"| Page | Status | Elapsed (s) | Records | Notes |\n")
    f.write(f"|------|--------|-------------|---------|-------|\n")
    for row in log_rows:
        f.write(f"| {row['page']} | {row['status']} | {row['elapsed']} | {row['records']} | {row['notes']} |\n")
    f.write(f"\n## Summary\n")
    f.write(f"- Pages attempted: {total_pages}\n")
    f.write(f"- Pages succeeded: {succeeded}\n")
    f.write(f"- Pages failed: {len(failed_pages)}")
    if failed_pages:
        f.write(f" ({failed_pages})")
    f.write(f"\n- Total elapsed: {run_elapsed:.1f}s ({run_elapsed/60:.1f} min)\n")
    f.write(f"- Total records produced: {total_records}\n")

print(f"\n{'='*60}")
print(f"COMPLETE: {succeeded}/{total_pages} pages, {total_records} records, {run_elapsed:.1f}s")
if failed_pages:
    print(f"FAILED: {failed_pages}")
print(f"Output: {OUT_DIR}/")

PYEOF

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "═══════════════════════════════════════════════"
