import urllib.request, json, time

key = 'sk-d392dfeafc9b4ae08aeafece8e97c837'
url = 'https://open-webui.rc.virginia.edu/api/chat/completions'

# Build a ~40K char prompt
base = 'John Clendening reported on Kaw Indians. '
base += 'Abby Conn age 43 land sold. '
base += 'Ralph Pepper age 26 land sold. '
base += 'Robert Sands land sold nothing left. '
msg = 'Extract all entities as JSON: ' + (base * 250)

payload = json.dumps({
    'model': 'Kimi K2.5',
    'messages': [{'role': 'user', 'content': msg}],
    'max_tokens': 8192,
}).encode()

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + key,
}

print(f'Sending {len(msg)} chars...')
start = time.time()
req = urllib.request.Request(url, data=payload, headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=600)
    elapsed = time.time() - start
    data = json.loads(resp.read().decode())
    print(f'SUCCESS in {elapsed:.1f}s')
    print(f'Tokens: {data.get("usage", {})}')
except Exception as e:
    elapsed = time.time() - start
    print(f'FAILED after {elapsed:.1f}s: {e}')
