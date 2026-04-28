import urllib.request, json, time

key = 'sk-d392dfeafc9b4ae08aeafece8e97c837'
url = 'https://open-webui.rc.virginia.edu/api/chat/completions'

payload = json.dumps({
    'model': 'Kimi K2.5',
    'messages': [{'role': 'user', 'content': 'Hello'}],
    'stream': False,
}).encode()

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + key,
}

print('Sending with stream=false...')
start = time.time()
req = urllib.request.Request(url, data=payload, headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=120)
    elapsed = time.time() - start
    raw = resp.read().decode()
    data = json.loads(raw)
    content = data['choices'][0]['message']['content']
    tokens = data.get('usage', {})
    print(f'SUCCESS in {elapsed:.1f}s')
    print(f'Tokens: {tokens}')
    print(f'Content: {content[:300]}')
except Exception as e:
    elapsed = time.time() - start
    print(f'FAILED after {elapsed:.1f}s: {e}')
