#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --partition=standard
#SBATCH --mem=16G
#SBATCH -J "qwen-vl-p7"
#SBATCH -o /project/LawData/kimi-extraction/logs/qwen_vl_ledger_p7_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/qwen_vl_ledger_p7_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

set -euo pipefail

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

ADDR_FILE="/project/LawData/kimi-extraction/logs/qwen_vl_address.txt"
OUT_DIR="/project/LawData/kimi-extraction/outputs/vision_test"
mkdir -p "$OUT_DIR"

# Wait up to 30 minutes for server
echo "Waiting for Qwen-VL server..."
# Wait up to 6 hours for GPU server to start
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
echo "Qwen2.5-VL-72B — Ledger Page 7 Extraction"
echo "Server: ${ADDR}"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

python3 << 'PYEOF'
import fitz, json, os, time, base64, urllib.request

# Render page 7
ledger_pdf = '/project/LawData/kimi-extraction/code/circular_2464_extractions/standalone/fee_patent_ledger_part11.pdf'
doc = fitz.open(ledger_pdf)
pix = doc[6].get_pixmap(matrix=fitz.Matrix(2, 2))
img_path = '/tmp/ledger_page_07.png'
pix.save(img_path)
print(f"Rendered page 7: {pix.width}x{pix.height}")

with open(img_path, 'rb') as f:
    img_b64 = base64.standard_b64encode(f.read()).decode('utf-8')
print(f"Base64 size: {len(img_b64):,} bytes")

# Load prompt
prompt_path = '/project/LawData/kimi-extraction/code/prompts/extraction_ledger.md'
with open(prompt_path) as f:
    ledger_prompt = f.read()

vision_prefix = """You are viewing a scanned page from a fee patent ledger. The page has columns arranged left-to-right: Name, Allotment Number, Fee Patent Date (year), and Application Status. Rows are organized under Township/Range section headers.

CRITICAL: Read each ROW across the columns. Each name belongs with the allotment number, date, and status on the SAME horizontal line. Do not shift values between rows.

"""
full_prompt = vision_prefix + ledger_prompt

# Get server address
with open('/project/LawData/kimi-extraction/logs/qwen_vl_address.txt') as f:
    addr = f.read().strip()

url = f"http://{addr}/v1/chat/completions"

# Send vision request
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

print(f"Sending request to {url}...")
start = time.time()

req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=600) as resp:
    raw = resp.read().decode()

elapsed = time.time() - start
print(f"Response in {elapsed:.1f}s, {len(raw):,} chars")

# Parse response
data = json.loads(raw)
content = data['choices'][0]['message']['content']
usage = data.get('usage', {})
print(f"Tokens: {usage.get('prompt_tokens',0)} in, {usage.get('completion_tokens',0)} out")

# Parse JSON from content
text = content.strip()
if text.startswith('```'):
    lines = text.split('\n')
    text = '\n'.join(lines[1:])
    if text.rstrip().endswith('```'):
        text = text.rstrip()[:-3]
    text = text.strip()

si = text.find('[')
try:
    result = json.loads(text[si:]) if si >= 0 else None
except json.JSONDecodeError:
    ei = text.rfind(']') + 1
    try:
        result = json.loads(text[si:ei])
    except:
        result = None

if result:
    print(f"Records: {len(result)}")
    for r in result[:3]:
        print(f"  {r.get('Name',''):<30} allot={r.get('Allotment number',''):<10} date={r.get('Fee Patent Date','')}")
else:
    print("PARSE FAILED")
    print(f"First 500 chars: {content[:500]}")

# Save
out_path = '/project/LawData/kimi-extraction/outputs/vision_test/page_07_qwen_vision.json'
with open(out_path, 'w') as f:
    json.dump({
        'model': 'qwen-vl-72b',
        'records': result if result else [],
        'raw_content': content[:2000] if not result else None,
        'usage': usage,
        'elapsed': round(elapsed, 1),
    }, f, indent=2)
print(f"Saved to {out_path}")

PYEOF

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "═══════════════════════════════════════════════"
