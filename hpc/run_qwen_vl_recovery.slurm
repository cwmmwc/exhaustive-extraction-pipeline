#!/bin/bash
#SBATCH -A LawData
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --partition=standard
#SBATCH --mem=16G
#SBATCH -J "qwen-vl-recov"
#SBATCH -o /project/LawData/kimi-extraction/logs/qwen_vl_recovery_%j.out
#SBATCH -e /project/LawData/kimi-extraction/logs/qwen_vl_recovery_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=cwm6w@virginia.edu

set -euo pipefail

module purge
module load gcc/11.4.0 openmpi/4.1.4 python/3.11.4
source /scratch/$USER/model-compare-venv/bin/activate

ADDR_FILE="/project/LawData/kimi-extraction/logs/qwen_vl_address.txt"
INPUT_DIR="/project/LawData/kimi-extraction/code/circular_2464_extractions/vision_recovery_sample"
OUT_DIR="/project/LawData/kimi-extraction/outputs/vision_recovery_sample"
mkdir -p "$OUT_DIR"

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
echo "Qwen2.5-VL-72B — Vision Recovery Sample (6 records, 10 pages)"
echo "Server: ${ADDR}"
echo "Input:  ${INPUT_DIR}"
echo "Output: ${OUT_DIR}"
echo "Started: $(date)"
echo "═══════════════════════════════════════════════"

export INPUT_DIR OUT_DIR ADDR

python3 << 'PYEOF'
import os, csv, json, time, base64, urllib.request

INPUT_DIR = os.environ['INPUT_DIR']
OUT_DIR = os.environ['OUT_DIR']
ADDR = os.environ['ADDR']
MANIFEST = os.path.join(INPUT_DIR, 'manifest.csv')

PROMPT = """You are examining a scanned page from a 1928-1929 Bureau of Indian Affairs document — either an "Affidavit" or a "Questions and Answers" questionnaire issued under Circular No. 2464. These documents collected testimony from Native American allottees who had been issued fee patents on their allotments.

A prior text-extraction pipeline successfully captured the printed body content of this document but FAILED to capture the allottee's name and allotment number — both of which appear as handwritten elements rather than printed text. Your task is to recover that handwritten identifying information.

IMPORTANT: The number "2464" is the circular's reference number, not an allotment number. Do not return 2464 as an allotment number. Look for handwritten allotment numbers in margins (typically top-right corner) or in the form field of question 1.

Examine the page CAREFULLY for the following:

1. Allottee name (handwritten signature): typically appears at the bottom of the document on a signature line, above a printed label like "Deponent" or "Allottee" or "Signature of Allottee". The name is the allottee's own handwritten signature. It may also appear handwritten in headers or as marginalia. Some documents have a thumbprint instead of a signature; if so, note that.

2. Allotment number (handwritten): typically handwritten in the top-right corner of the first page, often as "No. ####" or "Allot. No. ####" or just a bare number. Sometimes appears in question 1 of a questionnaire form.

3. Date of document: the "subscribed and sworn before me this ____ day of _______, 19__" line, near the bottom.

4. Notary name (handwritten signature): appears on the notary signature line at the very bottom, typically above a printed "Notary Public" label.

5. Location of swearing: usually printed at the top as "State of ____, County of ____".

Return ONLY valid JSON, no markdown fencing, no commentary. Schema:

{
  "name": "best reading of handwritten allottee name, or null if not present",
  "name_confidence": "high | medium | low | illegible | not_present_on_this_page",
  "name_signature_or_print": "signature | print | thumbprint | other",
  "allotment_number": "best reading of handwritten allotment number, or null",
  "allotment_number_confidence": "high | medium | low | illegible | not_present_on_this_page",
  "date": "subscribed-and-sworn date if recoverable",
  "notary_name": "best reading of notary signature, or null",
  "notary_confidence": "high | medium | low | illegible | not_present_on_this_page",
  "state_of_swearing": "state name, or null if not visible",
  "county_of_swearing": "county name, or null if not visible",
  "notes": "any other handwritten elements worth capturing, or observations about why a field could not be read"
}"""

url = f"http://{ADDR}/v1/chat/completions"

with open(MANIFEST) as f:
    rows = list(csv.DictReader(f))

print(f"Manifest rows: {len(rows)}")

successes = 0
failures = 0

for row in rows:
    record_id = row['record_id']
    page = row['page']
    image_path = os.path.join('/project/LawData/kimi-extraction/code', row['image_path'])
    out_key = f"{record_id}_page-{page}"
    out_path = os.path.join(OUT_DIR, f"{out_key}.json")

    if os.path.exists(out_path):
        print(f"  SKIP {out_key} (already exists)")
        continue

    if not os.path.exists(image_path):
        print(f"  ERROR {out_key}: image not found at {image_path}")
        failures += 1
        continue

    with open(image_path, 'rb') as f:
        img_b64 = base64.standard_b64encode(f.read()).decode('utf-8')

    payload = json.dumps({
        "model": "qwen-vl-72b",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                {"type": "text", "text": PROMPT}
            ]
        }],
        "max_tokens": 1500,
        "temperature": 0.1,
    }).encode('utf-8')

    start = time.time()
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            raw = resp.read().decode()
    except Exception as e:
        print(f"  ERROR {out_key}: {type(e).__name__}: {e}")
        failures += 1
        continue

    elapsed = time.time() - start
    data = json.loads(raw)
    content = data['choices'][0]['message']['content']
    usage = data.get('usage', {})

    text = content.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:])
        if text.rstrip().endswith('```'):
            text = text.rstrip()[:-3]
        text = text.strip()
    if text.lstrip().startswith('json\n'):
        text = text.lstrip()[5:]

    try:
        parsed = json.loads(text)
        parse_ok = True
    except json.JSONDecodeError as e:
        parsed = {"_parse_error": str(e), "_raw_text_excerpt": text[:500]}
        parse_ok = False

    result = {
        "model": "qwen-vl-72b",
        "record_id": record_id,
        "page": int(page),
        "image_path": row['image_path'],
        "known_allotment_from_manifest": row['known_allotment'],
        "agency_hint": row['agency_hint'],
        "elapsed_s": round(elapsed, 1),
        "input_tokens": usage.get('prompt_tokens', 0),
        "output_tokens": usage.get('completion_tokens', 0),
        "extraction": parsed,
        "raw_response": content,
    }

    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    if parse_ok:
        name = parsed.get('name') or '(none)'
        name_conf = parsed.get('name_confidence') or '?'
        allot = parsed.get('allotment_number') or '(none)'
        allot_conf = parsed.get('allotment_number_confidence') or '?'
        print(f"  OK   {out_key}: name='{name}' ({name_conf}) | allot='{allot}' ({allot_conf}) | {elapsed:.1f}s")
    else:
        print(f"  PARSE-FAIL {out_key}: {parsed.get('_parse_error', '?')}")
    successes += 1

print()
print(f"Total: {len(rows)}, succeeded: {successes}, failures: {failures}")

PYEOF

echo ""
echo "═══════════════════════════════════════════════"
echo "Done: $(date)"
echo "═══════════════════════════════════════════════"
