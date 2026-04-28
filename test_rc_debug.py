import urllib.request, json, time

key = 'sk-d392dfeafc9b4ae08aeafece8e97c837'
url = 'https://open-webui.rc.virginia.edu/api/chat/completions'

payload = json.dumps({
    'model': 'Kimi K2.5',
    'messages': [{'role': 'user', 'content': 'Hello'}],
}).encode()

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + key,
}

print(f'Sending simple Hello...')
start = time.time()
req = urllib.request.Request(url, data=payload, headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=120)
    elapsed = time.time() - start
    status = resp.status
    raw = resp.read()
    print(f'Status: {status}')
    print(f'Time: {elapsed:.1f}s')
    print(f'Response length: {len(raw)} bytes')
    print(f'First 500 chars: {raw[:500]}')
    try:
        data = json.loads(raw.decode())
        print(f'JSON parsed OK')
        print(f'Content: {data["choices"][0]["message"]["content"][:200]}')
    except Exception as e:
        print(f'JSON parse failed: {e}')
        print(f'Raw bytes: {raw[:200]}')
except urllib.error.HTTPError as e:
    elapsed = time.time() - start
    body = e.read()
    print(f'HTTP Error {e.code} after {elapsed:.1f}s')
    print(f'Body: {body[:500]}')
except Exception as e:
    elapsed = time.time() - start
    print(f'Error after {elapsed:.1f}s: {type(e).__name__}: {e}')
