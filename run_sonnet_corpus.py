#!/usr/bin/env python3
"""
Run Sonnet 4.6 with the affidavit prompt on the remaining Circular 2464 corpus.
Saves per-chunk usage data (input_tokens, output_tokens) to usage.json in each
output directory. Sequential extraction with full error handling.

Usage:
    python3 run_sonnet_corpus.py
    python3 run_sonnet_corpus.py --dry-run    # list PDFs without extracting
"""

import argparse
import json
import os
import sys
import time

import anthropic
import fitz

from extract_single_pdf import (
    build_prompt,
    chunk_text,
    count_items,
    extract_full_text,
    merge_extractions,
    parse_json,
)

MODEL = "claude-sonnet-4-6"
CHUNK_SIZE = 10000
PROMPT_VERSION = "affidavit"
OUTPUT_BASE = "circular_2464_extractions/sonnet_corpus"

# Sonnet 4.6 pricing
INPUT_PRICE = 3.0 / 1_000_000   # $3/MTok
OUTPUT_PRICE = 15.0 / 1_000_000  # $15/MTok

# PDF base directory
PDF_BASE = "/Users/cwm6W/Library/CloudStorage/OneDrive-UniversityofVirginia/Circular 2464"

# PDFs to extract (remaining corpus — Pine Ridge Vols 1-3 already done)
REMAINING_PDFS = [
    os.path.join(PDF_BASE, "Replies to Circular 2464", f)
    for f in [
        "RG 75 1929 Circular 2464 part 1.pdf",
        "RG 75 1929 circular 2464 part 2.pdf",
        "RG 75 1929 circular 2464 part 3.pdf",
        "RG 75 1929 circular 2464 part 6.pdf",
        "RG 75 1929 circular 2464 part 7.pdf",
        "RG 75 1929 circular 2464 part 8.pdf",
        "RG 75 1929 circular 2464 part 9.pdf",
        "RG 75 1929 circular 2464 part 10.pdf",
        "RG 75 1929 circular 2564 part 11.pdf",
        "RG 75 1929 circular 2464 part 12.pdf",
        "RG 75 1929 circular 2464 part 13.pdf",
    ]
] + [
    os.path.join(PDF_BASE, "Circular 2464 text thereof.pdf"),
    os.path.join(PDF_BASE, "Guerue refusal.pdf"),
]


def extract_one_pdf(pdf_path, output_dir, client):
    """Extract one PDF with usage tracking. Returns (record_count, usage_data, failures)."""
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    os.makedirs(output_dir, exist_ok=True)

    # Check if already extracted
    merged_path = os.path.join(output_dir, "claude.json")
    if os.path.exists(merged_path):
        with open(merged_path) as f:
            data = json.load(f)
        affs = data.get("affidavits", [])
        print(f"  SKIP (already extracted: {len(affs)} records)")
        return len(affs), None, []

    # Extract and chunk text
    full_text = extract_full_text(pdf_path)
    chunks = chunk_text(full_text, chunk_size=CHUNK_SIZE)
    print(f"  {len(full_text):,} chars, {len(chunks)} chunks")

    all_extractions = []
    usage_log = []
    failures = []

    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1}/{len(chunks)} ({len(chunk):,} chars)...", end=" ", flush=True)
        prompt = build_prompt(chunk, version=PROMPT_VERSION)

        try:
            text = ""
            with client.messages.stream(
                model=MODEL,
                max_tokens=32000,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for event_text in stream.text_stream:
                    text += event_text
            response = stream.get_final_message()
            elapsed = 0  # timing not critical here
            usage = response.usage

            chunk_usage = {
                "chunk": i + 1,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
            }
            usage_log.append(chunk_usage)

            extraction = parse_json(text)
            if extraction:
                item_count = sum(len(v) for v in extraction.values() if isinstance(v, list))
                print(f"OK, {item_count} items (in={usage.input_tokens}, out={usage.output_tokens})")
                all_extractions.append(extraction)
                with open(os.path.join(output_dir, f"claude_chunk_{i+1}.json"), "w") as f:
                    json.dump(extraction, f, indent=2)
            else:
                print(f"INVALID JSON (in={usage.input_tokens}, out={usage.output_tokens})")
                with open(os.path.join(output_dir, f"claude_chunk_{i+1}_raw.txt"), "w") as f:
                    f.write(text)
                failures.append(i + 1)

        except Exception as e:
            print(f"EXCEPTION: {e}")
            failures.append(i + 1)
            usage_log.append({"chunk": i + 1, "error": str(e)})

    # Save usage log
    with open(os.path.join(output_dir, "usage.json"), "w") as f:
        json.dump(usage_log, f, indent=2)

    # Merge and save
    if all_extractions:
        merged = merge_extractions(all_extractions)
        with open(merged_path, "w") as f:
            json.dump(merged, f, indent=2)

        # Verify output
        affs = merged.get("affidavits", [])
        if not affs:
            print(f"  WARNING: merged JSON has no affidavits array")
            failures.append("empty_merge")

        return len(affs), usage_log, failures
    else:
        print(f"  ERROR: no valid extractions")
        return 0, usage_log, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-base", default=OUTPUT_BASE)
    args = parser.parse_args()

    # Verify all PDFs exist
    print("=" * 70)
    print("Sonnet 4.6 Corpus Extraction — Circular 2464 Remaining")
    print("=" * 70)
    print()

    missing = [p for p in REMAINING_PDFS if not os.path.exists(p)]
    if missing:
        print("ERROR: Missing PDFs:")
        for p in missing:
            print(f"  {p}")
        sys.exit(1)

    # List PDFs
    total_chars = 0
    total_chunks = 0
    print(f"{'PDF':<65} {'Chars':>10} {'Chunks':>7}")
    print("-" * 85)
    for p in REMAINING_PDFS:
        text = extract_full_text(p)
        chunks = chunk_text(text, chunk_size=CHUNK_SIZE)
        total_chars += len(text)
        total_chunks += len(chunks)
        print(f"{os.path.basename(p):<65} {len(text):>10,} {len(chunks):>7}")
    print("-" * 85)
    print(f"{'TOTAL':<65} {total_chars:>10,} {total_chunks:>7}")
    print()

    if args.dry_run:
        proj_cost = total_chunks * 3561 * INPUT_PRICE + total_chunks * 2496 * OUTPUT_PRICE
        print(f"Projected cost: ${proj_cost:.2f}")
        print(f"Projected time: {total_chunks * 45 / 60:.0f} minutes")
        print("(dry run — not extracting)")
        return

    # Extract
    client = anthropic.Anthropic()
    grand_records = 0
    grand_input = 0
    grand_output = 0
    grand_failures = []
    start_time = time.time()

    for pdf_idx, pdf_path in enumerate(REMAINING_PDFS):
        basename = os.path.splitext(os.path.basename(pdf_path))[0]
        output_dir = os.path.join(args.output_base, basename)
        print(f"\n[{pdf_idx+1}/{len(REMAINING_PDFS)}] {basename}")

        records, usage_log, failures = extract_one_pdf(pdf_path, output_dir, client)
        grand_records += records

        if usage_log:
            for u in usage_log:
                if "error" not in u:
                    grand_input += u["input_tokens"]
                    grand_output += u["output_tokens"]

        if failures:
            grand_failures.append((basename, failures))

    elapsed = time.time() - start_time

    # Final report
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"PDFs processed: {len(REMAINING_PDFS)}")
    print(f"Total records: {grand_records}")
    print(f"Total time: {elapsed/60:.1f} minutes")
    print()
    print(f"Token usage:")
    print(f"  Input tokens:  {grand_input:,}")
    print(f"  Output tokens: {grand_output:,}")
    input_cost = grand_input * INPUT_PRICE
    output_cost = grand_output * OUTPUT_PRICE
    total_cost = input_cost + output_cost
    print(f"  Input cost:  ${input_cost:.3f}")
    print(f"  Output cost: ${output_cost:.3f}")
    print(f"  Total cost:  ${total_cost:.3f}")

    if grand_failures:
        print(f"\nFailures ({len(grand_failures)} PDFs):")
        for name, chunks in grand_failures:
            print(f"  {name}: chunks {chunks}")
    else:
        print("\nNo failures.")


if __name__ == "__main__":
    main()
