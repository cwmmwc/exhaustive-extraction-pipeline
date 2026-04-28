#!/usr/bin/env python3
"""Diagnose raw failure files from Kimi targeted v2 extraction."""
import json
import os
import sys

base = '/project/LawData/kimi-extraction/outputs/circular_2464_kimi_targeted_v2_10k/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3]'

for c in [1, 4, 13, 17, 20, 23]:
    path = os.path.join(base, f'Kimi K2.5_chunk_{c}_raw.txt')
    try:
        text = open(path).read()
    except FileNotFoundError:
        print(f'Chunk {c}: NO FILE')
        continue

    print(f'Chunk {c}: len={len(text)}, repr[:30]={repr(text[:30])}')
    s = text.strip()

    # Try stripping markdown fences
    fence = '```'
    if s.startswith(fence):
        lines = s.split('\n')
        inner = '\n'.join(lines[1:])
        if inner.rstrip().endswith(fence):
            inner = inner.rstrip()[:-3]
        inner = inner.strip()
        try:
            d = json.loads(inner)
            print(f'  PARSES OK after fence strip: {len(d.get("affidavits", []))} affidavits')
        except json.JSONDecodeError as e:
            print(f'  PARSE FAIL after fence strip: {e}')
            print(f'  around pos {e.pos}: {repr(inner[max(0,e.pos-40):e.pos+40])}')
    elif '{' in s:
        idx = s.index('{')
        j = s[idx:]
        try:
            d = json.loads(j)
            print(f'  PARSES OK from offset {idx}: {len(d.get("affidavits", []))} affidavits')
        except json.JSONDecodeError as e:
            print(f'  PARSE FAIL from offset {idx}: {e}')
            print(f'  around pos {e.pos}: {repr(j[max(0,e.pos-40):e.pos+40])}')
    else:
        print(f'  NO JSON FOUND')
    print()
