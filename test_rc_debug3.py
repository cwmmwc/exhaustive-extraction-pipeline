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

print('Sending and parsing SSE stream...')
start = time.time()
req = urllib.request.Request(url, data=payload, headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=300)
    raw = resp.read().decode()
    elapsed = time.time() - start

    # Parse SSE: each line starting with "data: " is a chunk
    content = ""
    reasoning = ""
    usage = {}
    for line in raw.split('\n'):
        line = line.strip()
        if not line.startswith('data: '):
            continue
        data_str = line[6:]  # strip "data: "
        if data_str == '[DONE]':
            break
        try:
            chunk = json.loads(data_str)
            delta = chunk['choices'][0].get('delta', {})
            if 'content' in delta and delta['content']:
                content += delta['content']
            if 'reasoning' in delta and delta['reasoning']:
                reasoning += delta['reasoning']
            if 'usage' in chunk and chunk['usage']:
                usage = chunk['usage']
        except (json.JSONDecodeError, KeyError, IndexError):
            continue

    print(f'SUCCESS in {elapsed:.1f}s')
    print(f'Content: {content[:300]}')
    print(f'Reasoning length: {len(reasoning)} chars')
    print(f'Usage: {usage}')
except Exception as e:
    elapsed = time.time() - start
    print(f'FAILED after {elapsed:.1f}s: {e}')
