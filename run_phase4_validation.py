#!/usr/bin/env python3
"""
Phase 4: Validation sample extraction with Sonnet and/or Kimi.
Extracts 100 stratified documents from the split corpus using the approved
18-column schema prompts, producing per-document JSON outputs.

Usage:
    python3 run_phase4_validation.py --sonnet         # Sonnet only (local)
    python3 run_phase4_validation.py --kimi           # Kimi only (HPC)
    python3 run_phase4_validation.py --select-sample  # Just select the sample, don't extract
"""

import argparse
import csv
import json
import os
import random
import sys
import time

import fitz

SPLIT_DIR = "circular_2464_extractions/split_documents"
MANIFEST = os.path.join(SPLIT_DIR, "manifest.csv")
SAMPLE_DIR = "circular_2464_extractions/validation_samples"
SAMPLE_IDS = os.path.join(SAMPLE_DIR, "phase4_sample_ids.csv")
LEDGER_PDF = "circular_2464_extractions/standalone/fee_patent_ledger_part11.pdf"

# Load prompts
PROMPT_DIR = "prompts"

def load_prompt(name):
    path = os.path.join(PROMPT_DIR, name)
    if not os.path.exists(path):
        # Try from HPC code dir
        path = os.path.join("/project/LawData/kimi-extraction/code/prompts", name)
    with open(path) as f:
        return f.read()


def select_sample():
    """Select stratified 100-document sample from the manifest."""
    random.seed(2026)

    with open(MANIFEST) as f:
        manifest = list(csv.DictReader(f))

    # Group by type
    by_type = {}
    for row in manifest:
        t = row['type']
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(row)

    sample = []

    # Affidavits: 30 (15 Pine Ridge, 15 Replies)
    affs = by_type.get('affidavit', [])
    pine_ridge_affs = [r for r in affs if 'pine_ridge' in r['document_id']]
    replies_affs = [r for r in affs if 'pine_ridge' not in r['document_id']]
    sample.extend(random.sample(pine_ridge_affs, min(15, len(pine_ridge_affs))))
    sample.extend(random.sample(replies_affs, min(15, len(replies_affs))))

    # Questionnaires: 30 (20 from Parts 12-13, 10 from other Parts)
    quests = by_type.get('questionnaire', [])
    parts_12_13 = [r for r in quests if 'part12' in r['document_id'] or 'part13' in r['document_id']]
    other_quests = [r for r in quests if r not in parts_12_13]
    sample.extend(random.sample(parts_12_13, min(20, len(parts_12_13))))
    sample.extend(random.sample(other_quests, min(10, len(other_quests))))

    # Agency narratives: 30 from Rosebud Parts 1-2, 7-9
    narrs = by_type.get('agency_narrative', [])
    rosebud_narrs = [r for r in narrs if any(p in r['document_id'] for p in ['part1_', 'part2_', 'part7_', 'part8_', 'part9_'])]
    sample.extend(random.sample(rosebud_narrs, min(30, len(rosebud_narrs))))

    # Ledger entries: 10 pages from Fort Berthold ledger
    # We sample 10 individual pages from the 14-page ledger
    ledger_pages = random.sample(range(1, 15), 10)
    for pg in sorted(ledger_pages):
        sample.append({
            'document_id': f'part11_ledger_page_{pg:02d}',
            'type': 'ledger',
            'source_pdf': 'RG 75 1929 circular 2564 part 11.pdf',
            'source_pages': str(pg + 17),  # Original page number (ledger starts at page 18)
            'output_path': f'ledgers/part11_ledger_page_{pg:02d}.pdf',
        })

    # Save sample
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    with open(SAMPLE_IDS, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['document_id', 'type', 'source_pdf', 'source_pages', 'output_path'])
        w.writeheader()
        for row in sample:
            w.writerow({k: row.get(k, '') for k in ['document_id', 'type', 'source_pdf', 'source_pages', 'output_path']})

    print(f"Sample selected: {len(sample)} documents")
    type_counts = {}
    for row in sample:
        t = row['type']
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")
    print(f"Saved to: {SAMPLE_IDS}")
    return sample


def load_sample():
    """Load previously selected sample."""
    with open(SAMPLE_IDS) as f:
        return list(csv.DictReader(f))


def get_document_text(row):
    """Extract text from a sample document."""
    doc_type = row['type']
    doc_id = row['document_id']

    if doc_type == 'ledger':
        # Extract single page from the standalone ledger PDF
        page_num = int(row['source_pages']) - 18  # Convert to 0-indexed within standalone PDF
        doc = fitz.open(LEDGER_PDF)
        return doc[page_num].get_text()
    else:
        # Read from split document PDF
        pdf_path = os.path.join(SPLIT_DIR, row['output_path'])
        if not os.path.exists(pdf_path):
            return None
        doc = fitz.open(pdf_path)
        return ''.join(doc[p].get_text() + '\n' for p in range(len(doc)))


def build_extraction_prompt(text, doc_type):
    """Build the full extraction prompt for a document."""
    if doc_type == 'ledger':
        prompt_template = load_prompt('extraction_ledger.md')
    else:
        prompt_template = load_prompt('extraction_single_document.md')

    # For single-document prompt, prepend the document type
    if doc_type != 'ledger':
        type_label = {
            'affidavit': 'affidavit',
            'questionnaire': 'questionnaire',
            'agency_narrative': 'agency_narrative',
        }.get(doc_type, 'affidavit')
        return f"This document is a {type_label}.\n\n{prompt_template}\n\nDOCUMENT TEXT:\n{text}"
    else:
        return f"{prompt_template}\n\nLEDGER TEXT:\n{text}"


def parse_json_response(text):
    """Parse JSON from model response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()
    start = text.find('{')
    arr_start = text.find('[')
    if arr_start >= 0 and (start < 0 or arr_start < start):
        start = arr_start
    if start >= 0:
        try:
            return json.loads(text[start:])
        except json.JSONDecodeError:
            # Try to find the end
            end = max(text.rfind('}'), text.rfind(']')) + 1
            if end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
    return None


def extract_sonnet(prompt, max_tokens=4000):
    """Extract with Sonnet. Returns (result_dict, usage, elapsed)."""
    import anthropic
    client = anthropic.Anthropic()
    start = time.time()
    text = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for t in stream.text_stream:
            text += t
    response = stream.get_final_message()
    elapsed = time.time() - start
    u = response.usage
    result = parse_json_response(text)
    return result, {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens}, elapsed


def extract_kimi(prompt, max_tokens=8000):
    """Extract with Kimi via RC GenAI, with retry. Returns (result_dict, usage, elapsed, retry_count)."""
    import urllib.request
    vllm_url = "https://open-webui.rc.virginia.edu"
    api_key = os.environ.get("UVARC_GenAI_API")

    max_retries = 5
    total_elapsed = 0

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            time.sleep(2 ** (attempt - 1))

        start = time.time()
        payload = json.dumps({
            "model": "Kimi K2.5",
            "messages": [
                {"role": "system", "content": "Respond with valid JSON only. Do not explain your reasoning."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }).encode("utf-8")

        url = f"{vllm_url}/api/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        req = urllib.request.Request(url, data=payload, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                raw = resp.read().decode()
            elapsed = time.time() - start
            total_elapsed += elapsed

            # Parse SSE
            content = ""
            reasoning = ""
            if raw.startswith("data: "):
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
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

                if not content and reasoning:
                    idx = reasoning.find('{')
                    arr_idx = reasoning.find('[')
                    if arr_idx >= 0 and (idx < 0 or arr_idx < idx):
                        idx = arr_idx
                    if idx >= 0:
                        content = reasoning[idx:]
                        last = max(content.rfind('}'), content.rfind(']')) + 1
                        if last > 0:
                            content = content[:last]
            else:
                try:
                    data = json.loads(raw)
                    content = data["choices"][0]["message"]["content"] or ""
                except (json.JSONDecodeError, KeyError):
                    pass

            if content:
                result = parse_json_response(content)
                if result is not None:
                    return result, {"input_tokens": 0, "output_tokens": 0}, total_elapsed, attempt

        except Exception as e:
            total_elapsed += time.time() - start

    return None, {"input_tokens": 0, "output_tokens": 0}, total_elapsed, max_retries


def run_extraction(sample, model, output_dir):
    """Run extraction on all sample documents."""
    os.makedirs(output_dir, exist_ok=True)

    results = []
    total_in = 0
    total_out = 0
    total_time = 0
    failures = []

    for i, row in enumerate(sample):
        doc_id = row['document_id']
        doc_type = row['type']

        # Skip if already extracted
        out_path = os.path.join(output_dir, f"{doc_id}.json")
        if os.path.exists(out_path):
            print(f"  [{i+1}/{len(sample)}] {doc_id}: SKIP (exists)")
            with open(out_path) as f:
                results.append(json.load(f))
            continue

        text = get_document_text(row)
        if text is None:
            print(f"  [{i+1}/{len(sample)}] {doc_id}: ERROR (no text)")
            failures.append(doc_id)
            continue

        prompt = build_extraction_prompt(text, doc_type)

        if model == "sonnet":
            # Ledger pages produce many records — need more output tokens
            max_tok = 16000 if doc_type == "ledger" else 4000
            result, usage, elapsed = extract_sonnet(prompt, max_tokens=max_tok)
            retry_count = 1
        else:
            # Kimi: ledger pages need 16K for the same reason as Sonnet
            kimi_max_tok = 16000 if doc_type == "ledger" else 8000
            result, usage, elapsed, retry_count = extract_kimi(prompt, max_tokens=kimi_max_tok)

        total_in += usage.get("input_tokens", 0)
        total_out += usage.get("output_tokens", 0)
        total_time += elapsed

        if result is not None:
            # Save result with metadata
            output = {
                "document_id": doc_id,
                "type": doc_type,
                "source_pdf": row.get('source_pdf', ''),
                "source_pages": row.get('source_pages', ''),
                "model": model,
                "extraction": result,
                "usage": usage,
                "elapsed": round(elapsed, 1),
                "retry_count": retry_count if model == "kimi" else 1,
            }
            with open(out_path, 'w') as f:
                json.dump(output, f, indent=2)
            results.append(output)
            retry_str = f" (attempt {retry_count})" if retry_count > 1 else ""
            print(f"  [{i+1}/{len(sample)}] {doc_id}: OK{retry_str} [{elapsed:.1f}s]")
        else:
            failures.append(doc_id)
            print(f"  [{i+1}/{len(sample)}] {doc_id}: FAILED [{elapsed:.1f}s]")

    # Summary
    print(f"\n{'='*60}")
    print(f"{model.upper()} EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total: {len(sample)} documents")
    print(f"Success: {len(results)}")
    print(f"Failures: {len(failures)}")
    if failures:
        print(f"  Failed: {failures}")
    print(f"Time: {total_time:.1f}s ({total_time/60:.1f} min)")
    if model == "sonnet":
        print(f"Tokens: {total_in:,} in, {total_out:,} out")
        cost = total_in * 3/1e6 + total_out * 15/1e6
        print(f"Cost: ${cost:.3f}")

    # Save usage summary
    with open(os.path.join(output_dir, "usage_summary.json"), 'w') as f:
        json.dump({
            "model": model,
            "documents": len(sample),
            "success": len(results),
            "failures": len(failures),
            "total_time_s": round(total_time, 1),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
        }, f, indent=2)

    return results, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--select-sample", action="store_true")
    parser.add_argument("--sonnet", action="store_true")
    parser.add_argument("--kimi", action="store_true")
    args = parser.parse_args()

    if args.select_sample or not os.path.exists(SAMPLE_IDS):
        sample = select_sample()
        if args.select_sample:
            return
    else:
        sample = load_sample()
        print(f"Loaded sample: {len(sample)} documents")

    if args.sonnet:
        print(f"\n{'='*60}")
        print("SONNET EXTRACTION")
        print(f"{'='*60}")
        run_extraction(sample, "sonnet", os.path.join(SAMPLE_DIR, "sonnet"))

    if args.kimi:
        print(f"\n{'='*60}")
        print("KIMI EXTRACTION")
        print(f"{'='*60}")
        run_extraction(sample, "kimi", os.path.join(SAMPLE_DIR, "kimi"))


if __name__ == "__main__":
    main()
