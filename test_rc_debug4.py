import urllib.request, json, time

key = 'sk-d392dfeafc9b4ae08aeafece8e97c837'
url = 'https://open-webui.rc.virginia.edu/api/chat/completions'

# Build a ~40K char prompt like real extraction
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

print(f'Sending {len(msg)} chars, parsing SSE...')
start = time.time()
req = urllib.request.Request(url, data=payload, headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=600)
    raw = resp.read().decode()
    elapsed = time.time() - start

    content = ""
    reasoning = ""
    usage = {}
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
            if 'usage' in chunk and chunk['usage']:
                usage = chunk['usage']
        except (json.JSONDecodeError, KeyError, IndexError):
            continue

    print(f'SUCCESS in {elapsed:.1f}s')
    print(f'Content length: {len(content)} chars')
    print(f'Reasoning length: {len(reasoning)} chars')
    print(f'Usage: {usage}')
    print(f'First 300 chars: {content[:300]}')
except Exception as e:
    elapsed = time.time() - start
    print(f'FAILED after {elapsed:.1f}s: {e}')
