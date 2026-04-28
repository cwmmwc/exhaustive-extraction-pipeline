#!/usr/bin/env python3
"""
Full-corpus Sonnet extraction on all split documents.
Skips documents already extracted. Copies validation sample outputs into
the same directory for a unified corpus.

Usage:
    python3 run_full_corpus_extraction.py
    python3 run_full_corpus_extraction.py --dry-run
"""

import argparse
import csv
import json
import os
import sys
import time

import anthropic
import fitz

SPLIT_DIR = "circular_2464_extractions/split_documents"
MANIFEST = os.path.join(SPLIT_DIR, "manifest.csv")
OUTPUT_DIR = "circular_2464_extractions/extractions/sonnet"
VAL_DIR = "circular_2464_extractions/validation_samples/sonnet"
LEDGER_PDF = "circular_2464_extractions/standalone/fee_patent_ledger_part11.pdf"
PROMPT_DIR = "prompts"

TYPE_SUBDIRS = {
    "affidavit": "affidavits",
    "questionnaire": "questionnaires",
    "agency_narrative": "agency_narratives",
    "ledger": "ledgers",
}


def load_prompt(name):
    with open(os.path.join(PROMPT_DIR, name)) as f:
        return f.read()


def get_document_text(row):
    doc_type = row['type']
    doc_id = row['document_id']
    if doc_type == 'ledger':
        # Ledger pages from the standalone PDF
        # source_pages is the original page number; standalone starts at page 18
        orig_page = int(row['source_pages'].split('-')[0])
        page_idx = orig_page - 18
        doc = fitz.open(LEDGER_PDF)
        if 0 <= page_idx < len(doc):
            return doc[page_idx].get_text()
        # Try reading from the split ledger PDF instead
        pdf_path = os.path.join(SPLIT_DIR, row['output_path'])
        if os.path.exists(pdf_path):
            doc = fitz.open(pdf_path)
            return ''.join(doc[p].get_text() + '\n' for p in range(len(doc)))
        return None
    else:
        subdir = TYPE_SUBDIRS.get(doc_type, '')
        pdf_path = os.path.join(SPLIT_DIR, subdir, f"{doc_id}.pdf")
        if not os.path.exists(pdf_path):
            pdf_path = os.path.join(SPLIT_DIR, row['output_path'])
        if os.path.exists(pdf_path):
            doc = fitz.open(pdf_path)
            return ''.join(doc[p].get_text() + '\n' for p in range(len(doc)))
        return None


def build_prompt(text, doc_type):
    if doc_type == 'ledger':
        template = load_prompt('extraction_ledger.md')
        return f"{template}\n\nLEDGER TEXT:\n{text}"
    else:
        template = load_prompt('extraction_single_document.md')
        type_label = doc_type  # affidavit, questionnaire, agency_narrative
        return f"This document is a {type_label}.\n\n{template}\n\nDOCUMENT TEXT:\n{text}"


def parse_json_response(text):
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
            end = max(text.rfind('}'), text.rfind(']')) + 1
            if end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
    return None


def extract_one(client, prompt, max_tokens):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load manifest
    with open(MANIFEST) as f:
        manifest = list(csv.DictReader(f))

    # Copy validation sample outputs first
    copied = 0
    if os.path.isdir(VAL_DIR):
        for f_name in os.listdir(VAL_DIR):
            if f_name.endswith('.json') and f_name != 'usage_summary.json':
                src = os.path.join(VAL_DIR, f_name)
                dst = os.path.join(OUTPUT_DIR, f_name)
                if not os.path.exists(dst):
                    with open(src) as f:
                        data = json.load(f)
                    with open(dst, 'w') as f:
                        json.dump(data, f, indent=2)
                    copied += 1
    print(f"Copied {copied} validation sample extractions to {OUTPUT_DIR}")

    # Determine what's already done
    done = set()
    for f_name in os.listdir(OUTPUT_DIR):
        if f_name.endswith('.json'):
            done.add(f_name.replace('.json', ''))

    remaining = [r for r in manifest if r['document_id'] not in done]
    print(f"Total manifest: {len(manifest)}")
    print(f"Already extracted: {len(done)}")
    print(f"Remaining: {len(remaining)}")

    if args.dry_run:
        from collections import Counter
        types = Counter(r['type'] for r in remaining)
        for t, c in types.most_common():
            print(f"  {t}: {c}")
        return

    # Extract
    client = anthropic.Anthropic()
    total_in = 0
    total_out = 0
    total_time = 0
    success = 0
    failures = []
    batch_start = time.time()

    for i, row in enumerate(remaining):
        doc_id = row['document_id']
        doc_type = row['type']
        out_path = os.path.join(OUTPUT_DIR, f"{doc_id}.json")

        # Skip if somehow done between check and now
        if os.path.exists(out_path):
            continue

        text = get_document_text(row)
        if text is None:
            print(f"  [{i+1}/{len(remaining)}] {doc_id}: ERROR (no text)")
            failures.append(doc_id)
            continue

        prompt = build_prompt(text, doc_type)
        max_tokens = 16000 if doc_type == 'ledger' else 8000

        try:
            result, usage, elapsed = extract_one(client, prompt, max_tokens)
        except Exception as e:
            print(f"  [{i+1}/{len(remaining)}] {doc_id}: EXCEPTION {e}")
            failures.append(doc_id)
            continue

        total_in += usage['input_tokens']
        total_out += usage['output_tokens']
        total_time += elapsed

        if result is not None:
            output = {
                "document_id": doc_id,
                "type": doc_type,
                "source_pdf": row.get('source_pdf', ''),
                "source_pages": row.get('source_pages', ''),
                "model": "sonnet",
                "extraction": result,
                "usage": usage,
                "elapsed": round(elapsed, 1),
            }
            with open(out_path, 'w') as f:
                json.dump(output, f, indent=2)
            success += 1
            if (i + 1) % 50 == 0 or i == 0:
                cost_so_far = total_in * 3/1e6 + total_out * 15/1e6
                print(f"  [{i+1}/{len(remaining)}] {doc_id}: OK [{elapsed:.1f}s] (${cost_so_far:.2f} so far)")
        else:
            failures.append(doc_id)
            print(f"  [{i+1}/{len(remaining)}] {doc_id}: FAILED [{elapsed:.1f}s]")

    batch_elapsed = time.time() - batch_start

    # Final report
    total_cost = total_in * 3/1e6 + total_out * 15/1e6

    print(f"\n{'='*60}")
    print("FULL-CORPUS EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"New extractions: {success}")
    print(f"Failures: {len(failures)}")
    if failures:
        print(f"  Failed: {failures[:20]}{'...' if len(failures) > 20 else ''}")
    print(f"Copied from validation: {copied}")
    print(f"Total in output dir: {len(done) + success}")
    print(f"Time: {batch_elapsed:.0f}s ({batch_elapsed/60:.1f} min)")
    print(f"Tokens: {total_in:,} in, {total_out:,} out")
    print(f"Cost: ${total_cost:.2f}")

    # Per-type counts in output directory
    print(f"\nPer-type in {OUTPUT_DIR}:")
    from collections import Counter
    type_counts = Counter()
    for f_name in os.listdir(OUTPUT_DIR):
        if f_name.endswith('.json'):
            with open(os.path.join(OUTPUT_DIR, f_name)) as f:
                data = json.load(f)
            type_counts[data.get('type', 'unknown')] += 1
    for t, c in type_counts.most_common():
        print(f"  {t}: {c}")

    # Save usage summary
    with open(os.path.join(OUTPUT_DIR, 'usage_summary.json'), 'w') as f:
        json.dump({
            "new_extractions": success,
            "copied_from_validation": copied,
            "failures": len(failures),
            "failed_ids": failures,
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_cost": round(total_cost, 4),
            "total_time_s": round(batch_elapsed, 1),
        }, f, indent=2)


if __name__ == "__main__":
    main()
