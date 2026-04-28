#!/usr/bin/env python3
"""Debug: show raw Kimi vision response for one index card page."""
import json, time, base64, urllib.request, fitz

PDF_PATH = "/project/LawData/exhaustive-extraction-pipeline/1935 RG 60, Entry A1 96C, Record Slips, 1935, Class Numbers (Interfiled), Box 487, 90-2-5.pdf"
KEY = 'sk-d392dfeafc9b4ae08aeafece8e97c837'
URL = 'https://open-webui.rc.virginia.edu/api/chat/completions'

PROMPT = """You are reading a scanned DOJ record slip. Extract all cards as JSON:
{"record_slips": [{"file_number": "", "jurisdiction": "", "date": "", "correspondent": "", "case_name": "", "subject": ""}]}
Return ONLY valid JSON:"""

# Render page 2 (one of the failed pages)
doc = fitz.open(PDF_PATH)
page = doc[1]
matrix = fitz.Matrix(200 / 72, 200 / 72)
pix = page.get_pixmap(matrix=matrix)
img = pix.tobytes("png")
img_b64 = base64.standard_b64encode(img).decode("utf-8")

payload = json.dumps({
    "model": "Kimi K2.5",
    "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
        {"type": "text", "text": PROMPT}
    ]}],
    "max_tokens": 4096,
}).encode()

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + KEY,
}

print("Sending page 2 to Kimi vision...")
start = time.time()
req = urllib.request.Request(URL, data=payload, headers=headers)
resp = urllib.request.urlopen(req, timeout=600)
raw = resp.read().decode()
elapsed = time.time() - start

# Parse SSE
content = ""
reasoning = ""
for line in raw.split('\n'):
    line = line.strip()
    if not line.startswith('data: '):
        continue
    data_str = line[6:]
    if data_str == '[DONE]':
        break
    try:
        chunk = json.loads(data_str)
        delta = chunk['choices'][0].get('delta', {})
        if 'content' in delta and delta['content']:
            content += delta['content']
        if 'reasoning' in delta and delta['reasoning']:
            reasoning += delta['reasoning']
    except:
        continue

print(f"Time: {elapsed:.1f}s")
print(f"Reasoning ({len(reasoning)} chars): {reasoning[:500]}")
print(f"Content ({len(content)} chars): {content[:1000]}")
print()

# Try to parse
try:
    data = json.loads(content)
    print("JSON PARSED OK")
    print(json.dumps(data, indent=2)[:500])
except json.JSONDecodeError as e:
    print(f"JSON PARSE FAILED: {e}")
    # Try stripping markdown
    c = content.strip()
    if c.startswith("```"):
        lines = c.split("\n")
        c = "\n".join(lines[1:])
        if c.endswith("```"):
            c = c[:-3]
        c = c.strip()
    # Try finding first brace
    idx = c.find("{")
    if idx > 0:
        c = c[idx:]
    try:
        data = json.loads(c)
        print("JSON PARSED after cleanup")
        print(json.dumps(data, indent=2)[:500])
    except:
        print("STILL FAILED after cleanup")
        print(f"Cleaned content: {c[:500]}")
