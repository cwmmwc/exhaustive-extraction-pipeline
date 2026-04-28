#!/usr/bin/env python3
"""Quick diagnostic: send one classification request to RC GenAI and print the raw response."""
import json, os, sys, urllib.request
import fitz

CLASSIFY_PROMPT = """You are a document classifier. Classify this page into one category. Respond with ONLY a JSON object, nothing else.

Categories: affidavit, questionnaire, agency_narrative, ledger_entry_page, affidavit_continuation, questionnaire_continuation, agency_narrative_continuation, transmittal_letter, cover_sheet, other

{"classification": "category_name", "confidence": "high|medium|low"}

PAGE TEXT:
"""

pdf_path = sys.argv[1] if len(sys.argv) > 1 else '/project/LawData/kimi-extraction/pdfs/circular_2464/pine_ridge/312 Affidavits by Indians who accepted land patents under protest 1928 [1 of 3].pdf'
doc = fitz.open(pdf_path)

# Page 6 — should be an affidavit
text = doc[5].get_text()[:2000]
prompt = CLASSIFY_PROMPT + text

vllm_url = "https://open-webui.rc.virginia.edu"
api_key = os.environ.get("UVARC_GenAI_API")

payload = json.dumps({
    "model": "Kimi K2.5",
    "messages": [
        {"role": "system", "content": "Respond with only a JSON object. Do not explain your reasoning."},
        {"role": "user", "content": prompt},
    ],
    "max_tokens": 500,
    "temperature": 0.1,
}).encode("utf-8")

url = f"{vllm_url}/api/chat/completions"
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
req = urllib.request.Request(url, data=payload, headers=headers)

print("Sending request...")
with urllib.request.urlopen(req, timeout=120) as resp:
    raw = resp.read().decode()

print(f"Response length: {len(raw)}")
print(f"First 500 chars:")
print(raw[:500])
print()
print(f"Last 500 chars:")
print(raw[-500:])
