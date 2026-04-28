#!/usr/bin/env python3
"""
Retry failed chunks from the Kimi targeted v2 extraction on Pine Ridge Volume 1.

Identifies failed chunks (INVALID JSON saved as _raw.txt, or missing entirely),
retries each via RC GenAI with the same targeted v2 prompt, and produces a
merged JSON combining original successes with retry successes.

Usage (on HPC):
    python3 retry_kimi_targeted_v2.py --output-dir /path/to/output --pdf /path/to/vol1.pdf

The script:
  1. Scans the output dir for existing chunk files and raw failure files
  2. Re-extracts text from the PDF and re-chunks at 10K
  3. Retries each failed chunk up to 3 times
  4. Merges all successful chunks (original + retry) into a new Kimi K2.5.json
  5. Reports per-chunk outcomes
"""

import argparse
import json
import os
import re
import sys
import time

from extract_single_pdf import (
    build_prompt,
    chunk_text,
    count_items,
    extract_full_text,
    merge_extractions,
    parse_json,
    run_vllm,
)

CHUNK_SIZE = 10000
MODEL_NAME = "Kimi K2.5"


def find_failed_chunks(output_dir):
    """Identify which chunks succeeded and which failed.
    Returns: (succeeded_nums, failed_nums_with_type)
    """
    succeeded = {}  # chunk_num -> filepath
    failed = {}     # chunk_num -> 'invalid_json' | 'empty_sse'

    for f in os.listdir(output_dir):
        # Successful chunk: "Kimi K2.5_chunk_N.json"
        m = re.match(r'Kimi K2\.5_chunk_(\d+)\.json$', f)
        if m:
            succeeded[int(m.group(1))] = os.path.join(output_dir, f)
            continue
        # Failed chunk (invalid JSON): "Kimi K2.5_chunk_N_raw.txt"
        m = re.match(r'Kimi K2\.5_chunk_(\d+)_raw\.txt$', f)
        if m:
            failed[int(m.group(1))] = 'invalid_json'
            continue

    return succeeded, failed


def diagnose_raw_file(filepath):
    """Read a raw failure file and categorize the failure."""
    with open(filepath) as f:
        content = f.read()
    if not content.strip():
        return 'empty_response', ''
    if content.strip().startswith('data: '):
        return 'empty_sse', content[:200]
    if '```json' in content or '```' in content:
        return 'markdown_fenced', content[:200]
    if content.strip().startswith('{'):
        return 'truncated_json', content[:200]
    return 'other', content[:200]


def main():
    parser = argparse.ArgumentParser(description="Retry failed chunks from Kimi targeted v2")
    parser.add_argument("--output-dir", required=True, help="Output directory with chunk files")
    parser.add_argument("--pdf", required=True, help="Path to the PDF file")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries per chunk")
    parser.add_argument("--dry-run", action="store_true", help="Just report failures, don't retry")
    args = parser.parse_args()

    assert os.path.isdir(args.output_dir), f"Output dir not found: {args.output_dir}"
    assert os.path.exists(args.pdf), f"PDF not found: {args.pdf}"

    # Step 1: Identify failures
    print("=" * 60)
    print("Step 1: Identifying failed chunks")
    print("=" * 60)

    succeeded, failed = find_failed_chunks(args.output_dir)

    # Re-chunk the PDF to determine total chunk count and identify empty-SSE failures
    # (chunks that produced no file at all)
    full_text = extract_full_text(args.pdf)
    chunks = chunk_text(full_text, chunk_size=CHUNK_SIZE)
    total_chunks = len(chunks)
    print(f"PDF: {len(full_text):,} chars, {total_chunks} chunks at {CHUNK_SIZE}")

    # Chunks with no file at all = empty SSE (no raw.txt saved either)
    for i in range(1, total_chunks + 1):
        if i not in succeeded and i not in failed:
            failed[i] = 'empty_sse'

    print(f"\nSucceeded: {len(succeeded)} chunks: {sorted(succeeded.keys())}")
    print(f"Failed: {len(failed)} chunks:")

    # Diagnose raw files
    for chunk_num in sorted(failed.keys()):
        raw_path = os.path.join(args.output_dir, f"Kimi K2.5_chunk_{chunk_num}_raw.txt")
        if os.path.exists(raw_path):
            failure_type, preview = diagnose_raw_file(raw_path)
            char_start = (chunk_num - 1) * CHUNK_SIZE
            char_end = min(chunk_num * CHUNK_SIZE, len(full_text))
            print(f"  Chunk {chunk_num:>2} (chars {char_start:>7}-{char_end:>7}): {failure_type}")
            if preview:
                print(f"           Preview: {preview[:100]}...")
        else:
            char_start = (chunk_num - 1) * CHUNK_SIZE
            char_end = min(chunk_num * CHUNK_SIZE, len(full_text))
            print(f"  Chunk {chunk_num:>2} (chars {char_start:>7}-{char_end:>7}): empty_sse (no file)")

    if args.dry_run:
        print("\n(dry run — not retrying)")
        return

    # Step 2: Retry failed chunks
    print("\n" + "=" * 60)
    print("Step 2: Retrying failed chunks")
    print("=" * 60)

    vllm_url = "https://open-webui.rc.virginia.edu"
    api_key = os.environ.get("UVARC_GenAI_API")
    assert api_key, "UVARC_GenAI_API not set"

    # Per-chunk retry log: chunk_num -> list of attempt dicts
    # Each attempt dict: {'attempt': N, 'outcome': 'success'|'error'|'invalid_json'|'empty_sse'|'empty_response',
    #                      'failure_type': str, 'raw_preview': str, 'time': float, 'items': int}
    retry_log = {}
    retry_extractions = {}  # chunk_num -> extraction dict

    def classify_failure(result_text):
        """Classify why a response failed to parse."""
        raw = str(result_text or '')
        if not raw.strip():
            return 'empty_response', ''
        if raw.strip().startswith('data: '):
            # SSE format — check if content is empty across all chunks
            return 'empty_sse', raw[:300]
        if '```json' in raw or '```' in raw:
            return 'markdown_fenced', raw[:300]
        if raw.strip().startswith('{'):
            return 'truncated_json', raw[:300]
        # Reasoning/thinking preamble before JSON
        brace = raw.find('{')
        if brace > 0:
            return 'reasoning_preamble', raw[:300]
        return 'unknown', raw[:300]

    for chunk_num in sorted(failed.keys()):
        chunk_text_content = chunks[chunk_num - 1]  # 0-indexed
        prompt = build_prompt(chunk_text_content, version="affidavit-targeted-v2")
        retry_log[chunk_num] = []

        for attempt in range(1, args.max_retries + 1):
            print(f"  Chunk {chunk_num:>2}, attempt {attempt}/{args.max_retries}...", end=" ", flush=True)
            attempt_record = {'attempt': attempt}

            result = run_vllm(prompt, MODEL_NAME, vllm_url, api_key=api_key)
            attempt_record['time'] = result.get('time', 0)

            if "error" in result:
                err = str(result['error'])
                failure_type, raw_preview = classify_failure(result.get('text', ''))
                # Override: if run_vllm returned an error dict, classify from error message
                if 'Unparseable' in err:
                    failure_type = 'empty_sse'
                    raw_preview = err[:300]
                elif 'HTTP' in err:
                    failure_type = f'http_error'
                    raw_preview = err[:300]
                attempt_record.update({
                    'outcome': 'error',
                    'failure_type': failure_type,
                    'raw_preview': raw_preview,
                })
                retry_log[chunk_num].append(attempt_record)
                print(f"ERROR [{failure_type}]: {err[:100]}")
                continue

            extraction = parse_json(result["text"])
            if extraction:
                item_count = sum(len(v) for v in extraction.values() if isinstance(v, list))
                attempt_record.update({
                    'outcome': 'success',
                    'failure_type': None,
                    'raw_preview': None,
                    'items': item_count,
                })
                retry_log[chunk_num].append(attempt_record)
                print(f"OK in {result['time']:.1f}s, {item_count} items")
                retry_extractions[chunk_num] = extraction
                # Save the successful retry chunk
                safe_path = os.path.join(args.output_dir, f"Kimi K2.5_chunk_{chunk_num}.json")
                with open(safe_path, 'w') as f:
                    json.dump(extraction, f, indent=2)
                break
            else:
                failure_type, raw_preview = classify_failure(result.get("text", ""))
                attempt_record.update({
                    'outcome': 'invalid_json',
                    'failure_type': failure_type,
                    'raw_preview': raw_preview,
                })
                retry_log[chunk_num].append(attempt_record)
                print(f"INVALID JSON [{failure_type}] (attempt {attempt})")
                # Save raw for diagnosis
                raw_path = os.path.join(args.output_dir, f"Kimi K2.5_chunk_{chunk_num}_retry{attempt}_raw.txt")
                with open(raw_path, 'w') as f:
                    f.write(result.get("text", ""))
                continue
        else:
            print(f"  Chunk {chunk_num:>2}: FAILED after {args.max_retries} attempts")

    # Step 3: Report and merge
    print("\n" + "=" * 60)
    print("Step 3: Results")
    print("=" * 60)

    retry_ok = sum(1 for k in retry_log if k in retry_extractions)
    retry_fail = sum(1 for k in retry_log if k not in retry_extractions)
    print(f"Retried: {len(failed)} chunks")
    print(f"  Succeeded on retry: {retry_ok}")
    print(f"  Failed again: {retry_fail}")

    # Detailed per-chunk report
    print(f"\n  {'Chunk':>5}  {'Original':>15}  {'Retry Outcomes':>50}")
    print(f"  {'-'*75}")
    for chunk_num in sorted(retry_log.keys()):
        original_type = failed.get(chunk_num, '?')
        attempts = retry_log[chunk_num]
        attempt_strs = []
        for a in attempts:
            if a['outcome'] == 'success':
                attempt_strs.append(f"OK({a['items']} items)")
            else:
                attempt_strs.append(f"{a['failure_type']}")
        retry_str = ' → '.join(attempt_strs)
        final = '✓' if chunk_num in retry_extractions else '✗'
        print(f"  {chunk_num:>5}  {original_type:>15}  {retry_str:<48} {final}")

    # Stability analysis: did failures repeat the same way?
    if retry_fail > 0:
        still_failed = [k for k in retry_log if k not in retry_extractions]
        print(f"\n  Still-failed chunks: {still_failed}")
        print(f"\n  Failure stability analysis:")
        for chunk_num in still_failed:
            original_type = failed.get(chunk_num, '?')
            retry_types = [a['failure_type'] for a in retry_log[chunk_num]]
            all_same = len(set(retry_types)) == 1
            matches_original = all(t == original_type for t in retry_types)
            if matches_original:
                verdict = "CONTENT-SPECIFIC (same failure type every time, matches original)"
            elif all_same:
                verdict = f"CONSISTENT but DIFFERENT from original ({retry_types[0]} vs {original_type})"
            else:
                verdict = f"TRANSIENT (varies: {retry_types})"
            print(f"    Chunk {chunk_num}: original={original_type}, retries={retry_types} → {verdict}")
            # Show raw preview from last attempt
            last_attempt = retry_log[chunk_num][-1]
            if last_attempt.get('raw_preview'):
                print(f"      Last raw preview: {last_attempt['raw_preview'][:150]}...")

    # Merge all successful extractions (original + retry)
    print("\nMerging all successful chunks...")
    all_extractions = []

    for chunk_num in range(1, total_chunks + 1):
        chunk_path = os.path.join(args.output_dir, f"Kimi K2.5_chunk_{chunk_num}.json")
        if os.path.exists(chunk_path):
            with open(chunk_path) as f:
                ext = json.load(f)
            all_extractions.append(ext)

    if all_extractions:
        merged = merge_extractions(all_extractions)
        merged_path = os.path.join(args.output_dir, "Kimi K2.5.json")
        with open(merged_path, 'w') as f:
            json.dump(merged, f, indent=2)
        counts = count_items(merged)
        total_ok = len(succeeded) + retry_ok
        print(f"  Merged {total_ok}/{total_chunks} chunks")
        print(f"  Total records: {counts.get('total', 0)}")
        print(f"  Saved to: {merged_path}")
    else:
        print("  No successful extractions to merge!")


if __name__ == "__main__":
    main()
