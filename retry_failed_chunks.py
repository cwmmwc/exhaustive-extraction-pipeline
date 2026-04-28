#!/usr/bin/env python3
"""
Retry failed chunks and complete interrupted extractions.

Handles three cases:
  1. Failed chunks (_raw.txt files) — re-sends just those chunks to Together AI
  2. Interrupted extractions (chunk files but no merged JSON) — finds missing
     chunks, extracts them, then merges everything
  3. Already complete — skips

Usage:
    python3 retry_failed_chunks.py                    # fix everything
    python3 retry_failed_chunks.py --dry-run          # just show what needs work
    python3 retry_failed_chunks.py --max-retries 3    # retry each chunk up to 3 times
"""

import argparse
import glob
import json
import os
import re
import sys
import time

from extract_single_pdf import (
    TOGETHER_MODELS,
    build_prompt,
    chunk_text,
    count_items,
    extract_full_text,
    merge_extractions,
    parse_json,
    run_together,
)

EXTRACTION_DIR = "survey_of_conditions_extractions"
PDF_DIR = "/Users/cwm6W/Library/CloudStorage/Box-Box/Survey of Conditions"
MODEL = "kimi-k2.5"


def find_problems(extraction_dir):
    """Find all directories that need work: failed chunks or missing merge.

    Returns dict of subdir -> {"failed": [chunk_nums], "missing": [chunk_nums], "needs_merge": bool}
    """
    safe = MODEL.replace("/", "-")
    problems = {}
    for subdir in sorted(glob.glob(os.path.join(extraction_dir, "*"))):
        if not os.path.isdir(subdir):
            continue

        # Check for failed chunks (_raw.txt files)
        raw_files = sorted(glob.glob(os.path.join(subdir, f"{safe}_chunk_*_raw.txt")))
        failed_nums = []
        for rf in raw_files:
            m = re.search(r"_chunk_(\d+)_raw\.txt$", rf)
            if m:
                failed_nums.append(int(m.group(1)))

        # Check for existing good chunk files
        chunk_files = glob.glob(os.path.join(subdir, f"{safe}_chunk_*.json"))
        existing_nums = set()
        for cf in chunk_files:
            m = re.search(r"_chunk_(\d+)\.json$", cf)
            if m:
                existing_nums.add(int(m.group(1)))

        # Check if merged file exists
        has_merged = os.path.exists(os.path.join(subdir, f"{safe}.json"))

        # If we have chunk files but no merged JSON, this was interrupted
        if existing_nums and not has_merged and not failed_nums:
            problems[subdir] = {
                "failed": [],
                "missing": [],  # will be filled in once we know total chunks
                "needs_merge": True,
                "existing": sorted(existing_nums),
            }
        elif failed_nums:
            problems[subdir] = {
                "failed": failed_nums,
                "missing": [],
                "needs_merge": not has_merged,
                "existing": sorted(existing_nums),
            }

    return problems


def find_pdf_for_dir(subdir_name):
    """Find the matching PDF in the Box folder for an extraction directory."""
    # The directory name was created by tr ' ;:' '___' from the PDF basename
    # Reverse: try common patterns
    for pdf in glob.glob(os.path.join(PDF_DIR, "*.pdf")):
        basename = os.path.splitext(os.path.basename(pdf))[0]
        safe = basename.replace(" ", "_").replace(";", "_").replace(":", "_")
        if safe == subdir_name:
            return pdf
    # Fuzzy fallback: normalize both and compare
    for pdf in glob.glob(os.path.join(PDF_DIR, "*.pdf")):
        basename = os.path.splitext(os.path.basename(pdf))[0]
        safe = re.sub(r"[^a-zA-Z0-9]", "_", basename).lower()
        target = re.sub(r"[^a-zA-Z0-9]", "_", subdir_name).lower()
        if safe == target:
            return pdf
    return None


def rechunk_pdf(pdf_path):
    """Extract and chunk PDF text, returning the chunks list."""
    full_text = extract_full_text(pdf_path)
    chunks = chunk_text(full_text)
    return chunks


def retry_chunk(chunk_text_content, model_id, api_key, max_retries=2):
    """Retry a single chunk, returning parsed JSON or None."""
    prompt = build_prompt(chunk_text_content, version="v4")
    for attempt in range(max_retries):
        if attempt > 0:
            wait = 10 * attempt
            print(f"    Retry {attempt + 1}/{max_retries} (waiting {wait}s)...", end=" ", flush=True)
            time.sleep(wait)
        result = run_together(prompt, model_id, api_key)
        if "error" in result:
            err_msg = result["error"][:200]
            print(f"ERROR: {err_msg}")
            continue
        extraction = parse_json(result["text"])
        if extraction:
            item_count = sum(len(v) for v in extraction.values() if isinstance(v, list))
            print(f"OK ({item_count} items, {result['time']:.1f}s)")
            return extraction, result["text"]
        else:
            print(f"INVALID JSON")
    return None, None


def rescue_truncated_raw_files(subdir):
    """Try to parse existing _raw.txt files using the improved parser.
    Converts any that parse successfully into proper .json chunk files."""
    safe = MODEL.replace("/", "-")
    raw_files = sorted(glob.glob(os.path.join(subdir, f"{safe}_chunk_*_raw.txt")))
    rescued = 0
    for rf in raw_files:
        with open(rf) as f:
            content = f.read()
        if not content:
            continue
        m = re.search(r"_chunk_(\d+)_raw\.txt$", rf)
        if not m:
            continue
        chunk_num = m.group(1)
        parsed = parse_json(content)
        if parsed:
            items = sum(len(v) for v in parsed.values() if isinstance(v, list))
            json_path = os.path.join(subdir, f"{safe}_chunk_{chunk_num}.json")
            with open(json_path, "w") as f:
                json.dump(parsed, f, indent=2)
            os.remove(rf)
            print(f"  Rescued chunk {chunk_num} from truncated response — {items} items")
            rescued += 1
    return rescued


def remerge_document(subdir):
    """Re-merge all per-chunk JSONs in a directory into a single merged file."""
    safe = MODEL.replace("/", "-")
    chunk_files = sorted(
        glob.glob(os.path.join(subdir, f"{safe}_chunk_*.json")),
        key=lambda f: int(re.search(r"_chunk_(\d+)\.json$", f).group(1))
    )
    if not chunk_files:
        return None
    extractions = []
    for cf in chunk_files:
        with open(cf) as f:
            extractions.append(json.load(f))
    merged = merge_extractions(extractions)
    merged_path = os.path.join(subdir, f"{safe}.json")
    with open(merged_path, "w") as f:
        json.dump(merged, f, indent=2)
    return merged


def main():
    parser = argparse.ArgumentParser(description="Retry failed chunks and complete interrupted extractions")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be retried without running")
    parser.add_argument("--max-retries", type=int, default=2,
                        help="Max retries per chunk (default: 2)")
    parser.add_argument("--dir", default=EXTRACTION_DIR,
                        help=f"Extraction directory (default: {EXTRACTION_DIR})")
    args = parser.parse_args()

    api_key = os.environ.get("TOGETHER_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: TOGETHER_API_KEY not set")
        print("  export TOGETHER_API_KEY=your_key")
        sys.exit(1)

    model_id = TOGETHER_MODELS[MODEL]

    # Find all problems
    problems = find_problems(args.dir)
    if not problems:
        print("Nothing to fix. All extractions are complete!")
        return

    # For each problem dir, figure out what chunks are missing by checking the PDF
    for subdir, info in problems.items():
        dirname = os.path.basename(subdir)
        pdf = find_pdf_for_dir(dirname)
        if pdf:
            chunks = rechunk_pdf(pdf)
            total_chunks = len(chunks)
            existing = set(info["existing"])
            failed = set(info["failed"])
            all_needed = set(range(1, total_chunks + 1))
            missing = sorted(all_needed - existing - failed)
            info["missing"] = missing
            info["total_chunks"] = total_chunks
        else:
            info["total_chunks"] = 0

    total_failed = sum(len(info["failed"]) for info in problems.values())
    total_missing = sum(len(info["missing"]) for info in problems.values())
    total_needs_merge = sum(1 for info in problems.values() if info["needs_merge"] and not info["failed"] and not info["missing"])
    total_work = total_failed + total_missing

    print(f"{'='*60}")
    print(f"Fix Extractions — {len(problems)} documents need work")
    print(f"  Failed chunks to retry:  {total_failed}")
    print(f"  Missing chunks to extract: {total_missing}")
    print(f"  Just need merge:         {total_needs_merge}")
    print(f"Model: {MODEL} ({model_id})")
    print(f"{'='*60}\n")

    if args.dry_run:
        for subdir, info in problems.items():
            dirname = os.path.basename(subdir)
            pdf = find_pdf_for_dir(dirname)
            pdf_status = "PDF found" if pdf else "PDF NOT FOUND"
            existing_count = len(info["existing"])
            total = info.get("total_chunks", "?")
            print(f"  {dirname}")
            print(f"    Chunks: {existing_count}/{total} done ({pdf_status})")
            if info["failed"]:
                print(f"    Failed (retry):  {info['failed']}")
            if info["missing"]:
                print(f"    Missing (extract): {info['missing']}")
            if not info["failed"] and not info["missing"] and info["needs_merge"]:
                print(f"    Just needs merge")
        print(f"\nTotal: {total_failed} retries + {total_missing} new extractions across {len(problems)} documents")
        return

    fixed_total = 0
    still_failed_total = 0

    for subdir, info in problems.items():
        dirname = os.path.basename(subdir)
        pdf = find_pdf_for_dir(dirname)
        if not pdf:
            print(f"\nSKIP: {dirname} — cannot find source PDF")
            continue

        print(f"\n{'─'*60}")
        print(f"{dirname}")

        # First, try to rescue truncated raw files without any API calls
        rescued = rescue_truncated_raw_files(subdir)
        if rescued > 0:
            fixed_total += rescued
            # Re-scan: some "failed" chunks may now be fixed
            remaining_raw = glob.glob(os.path.join(subdir, f"{MODEL.replace('/', '-')}_chunk_*_raw.txt"))
            remaining_failed = []
            for rf in remaining_raw:
                m = re.search(r"_chunk_(\d+)_raw\.txt$", rf)
                if m:
                    remaining_failed.append(int(m.group(1)))
            info["failed"] = sorted(remaining_failed)
            # Re-check existing chunks
            existing = set()
            for cf in glob.glob(os.path.join(subdir, f"{MODEL.replace('/', '-')}_chunk_*.json")):
                m = re.search(r"_chunk_(\d+)\.json$", cf)
                if m:
                    existing.add(int(m.group(1)))
            total_chunks = info["total_chunks"]
            all_needed = set(range(1, total_chunks + 1))
            info["missing"] = sorted(all_needed - existing - set(info["failed"]))

        chunks_to_do = sorted(set(info["failed"] + info["missing"]))
        total_chunks = info["total_chunks"]

        if info["failed"]:
            print(f"  Failed chunks: {info['failed']}")
        if info["missing"]:
            print(f"  Missing chunks: {info['missing']}")
        if not chunks_to_do and info["needs_merge"]:
            print(f"  All chunks present — merging")
            merged = remerge_document(subdir)
            if merged:
                counts = count_items(merged)
                print(f"  Merged: {counts['total']} total items")
            continue

        # Re-chunk the PDF to get the original chunk text
        chunks = rechunk_pdf(pdf)
        print(f"  PDF has {len(chunks)} chunks, {len(info['existing'])} already done, {len(chunks_to_do)} to do")

        fixed = 0
        still_failed = 0
        safe = MODEL.replace("/", "-")

        for chunk_num in chunks_to_do:
            idx = chunk_num - 1  # chunk numbers are 1-based
            if idx >= len(chunks):
                print(f"  Chunk {chunk_num}: OUT OF RANGE (PDF only has {len(chunks)} chunks)")
                still_failed += 1
                continue

            print(f"  Chunk {chunk_num}/{len(chunks)} ({len(chunks[idx]):,} chars)...", end=" ", flush=True)
            extraction, raw_text = retry_chunk(chunks[idx], model_id, api_key, args.max_retries)

            raw_path = os.path.join(subdir, f"{safe}_chunk_{chunk_num}_raw.txt")
            json_path = os.path.join(subdir, f"{safe}_chunk_{chunk_num}.json")

            if extraction:
                # Save the good JSON and remove the raw file if it exists
                with open(json_path, "w") as f:
                    json.dump(extraction, f, indent=2)
                if os.path.exists(raw_path):
                    os.remove(raw_path)
                fixed += 1
            else:
                # Save raw text so we know this chunk failed
                if raw_text:
                    with open(raw_path, "w") as f:
                        f.write(raw_text)
                still_failed += 1

        # Re-merge the document (even partial is better than nothing)
        if fixed > 0 or info["needs_merge"]:
            merged = remerge_document(subdir)
            if merged:
                counts = count_items(merged)
                print(f"  Re-merged: {counts['total']} total items")

        fixed_total += fixed
        still_failed_total += still_failed
        print(f"  Result: {fixed} fixed, {still_failed} still failed")

    print(f"\n{'='*60}")
    print(f"Done. {fixed_total} chunks fixed, {still_failed_total} still failed.")
    if still_failed_total > 0:
        print(f"Run again to retry remaining failures.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
