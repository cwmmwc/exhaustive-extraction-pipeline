#!/usr/bin/env python3
"""
Run Qwen2.5-VL-72B on a directory of index card PDFs.

Walks INPUT_DIR for *.pdf files, processes each page with the index card prompt
against the Qwen-VL vLLM server, writes per-PDF merged JSON to OUTPUT_DIR.

Pages within a single PDF are processed CONCURRENTLY using a thread pool —
the vLLM server batches concurrent requests internally, so 6-way parallelism
gives ~6x throughput on the same GPUs without changing the server. The
default of 6 workers keeps GPU KV cache use comfortable (~25%) on 4xA100 80GB.

Skips any PDF whose merged JSON already exists, so re-runs are safe and resumable.

Usage:
    python3 run_qwen_vl_index_cards_full.py INPUT_DIR OUTPUT_DIR [PARALLEL]
    PARALLEL defaults to 6.
"""
import json
import os
import sys
import time
import base64
import urllib.request
import fitz
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

SERVER_ADDR_FILE = "/project/LawData/kimi-extraction/logs/qwen_vl_address.txt"

INDEX_CARD_PROMPT = """You are reading scanned images of DOJ (Department of Justice) record slips — index cards that track correspondence about legal cases involving Indian land, taxes, and allotments. Each page contains one or more typed cards.

Each card has a consistent format:
- HEADER: File number (e.g., 90-2-5-49) | Jurisdiction/District (e.g., Mont., S. Dak., N. Okla.) | Date
- CORRESPONDENT: Who the letter is to/from (e.g., U.S. Atty., First Asst. Secy., Asst. U.S. Atty.)
- RE: LINE: Case name (e.g., U.S. v. Bennett County, et al) and brief description of the action
- FOOTER: Division routing (e.g., Lands Div.), processing dates, clerk initials

Extract EVERY card on each page as a separate record. Return a JSON object:

{
  "record_slips": [
    {
      "file_number": "90-2-5-49",
      "jurisdiction": "Montana",
      "date": "1936-03-17",
      "correspondent": "Asst. U.S. Atty.",
      "case_name": "U.S. v. Roosevelt County, et al",
      "allottee_name": "Jessie Eng",
      "tribe_or_reservation": "Fort Peck",
      "subject": "Encloses 2 copies of bill of complaint",
      "routing_division": "Lands",
      "routing_date": "1936-03-21",
      "clerk_initials": "rmh"
    }
  ],
  "legal_cases": [
    {
      "case_name": "U.S. v. Roosevelt County, et al",
      "file_number": "90-2-5-49",
      "jurisdiction": "Montana",
      "allottee_name": "Jessie Eng",
      "tribe_or_reservation": "Fort Peck"
    }
  ],
  "persons": [
    {"name": "Jessie Eng", "role": "allottee", "tribe": "Fort Peck"}
  ]
}

Read the file number EXACTLY. Convert dates from M-D-YY to YYYY-MM-DD.
Extract ALL cards on each page as separate record_slip entries.
Return ONLY valid JSON, no markdown fencing, no commentary:"""


def get_server_url():
    with open(SERVER_ADDR_FILE) as f:
        addr = f.read().strip()
    return f"http://{addr}"


def render_page(pdf_path, page_num, dpi=200):
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=matrix)
    png = pix.tobytes("png")
    doc.close()
    return png


def send_to_qwen(server_url, image_bytes, prompt):
    img_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    payload = json.dumps({
        "model": "qwen-vl-72b",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        "max_tokens": 4096,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        f"{server_url}/v1/chat/completions",
        data=payload, headers={"Content-Type": "application/json"}
    )
    start = time.time()
    resp = urllib.request.urlopen(req, timeout=300)
    elapsed = time.time() - start
    data = json.loads(resp.read().decode())
    return {"text": data["choices"][0]["message"]["content"], "time": elapsed}


def parse_json_response(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    first_brace = text.find("{")
    if first_brace > 0:
        text = text[first_brace:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _process_one_page(pdf_path, page_num, server_url, basename, output_dir):
    """Worker for the thread pool: render one page and send it to the server.
    Returns a dict with at least 'page_num', 'parsed' (or None on failure),
    and 'time'. Errors are caught and reported via the dict, never raised.
    """
    result = {"page_num": page_num, "parsed": None, "time": 0.0, "error": None}
    try:
        img = render_page(pdf_path, page_num)
    except Exception as e:
        result["error"] = f"render error: {e}"
        return result

    try:
        resp = send_to_qwen(server_url, img, INDEX_CARD_PROMPT)
    except Exception as e:
        result["error"] = f"server error: {e}"
        return result

    result["time"] = resp.get("time", 0.0)
    parsed = parse_json_response(resp["text"])
    if parsed is not None:
        result["parsed"] = parsed
    else:
        result["error"] = "unparseable JSON"
        # Save the raw text for debugging
        raw_dir = os.path.join(output_dir, "_raw_failures")
        os.makedirs(raw_dir, exist_ok=True)
        try:
            with open(os.path.join(raw_dir, f"{basename}_p{page_num}.txt"), "w") as f:
                f.write(resp["text"])
        except Exception:
            pass
    return result


def process_pdf(pdf_path, output_dir, server_url, input_root, parallel=6):
    """Process every page of a PDF in parallel via a thread pool."""
    # Mirror the input directory structure in output, so PDFs in subdirs
    # like 90-2-5/ and 90-2-11/ don't collide.
    rel = os.path.relpath(pdf_path, input_root)
    rel_no_ext = os.path.splitext(rel)[0]
    out_path = os.path.join(output_dir, f"{rel_no_ext}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    basename = os.path.basename(rel_no_ext)

    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        print(f"  SKIP (already done): {basename}", flush=True)
        return None

    doc = fitz.open(pdf_path)
    num_pages = doc.page_count
    doc.close()

    print(f"  {basename} ({num_pages} pages, parallel={parallel})", flush=True)
    pdf_started = time.time()

    # Submit every page to the thread pool. Results may arrive out of order;
    # we'll collect them all then iterate by page_num to keep slip ordering
    # roughly chronological.
    page_results = {}
    with ThreadPoolExecutor(max_workers=parallel) as ex:
        futures = {
            ex.submit(_process_one_page, pdf_path, p, server_url, basename, output_dir): p
            for p in range(1, num_pages + 1)
        }
        for fut in as_completed(futures):
            r = fut.result()
            page_results[r["page_num"]] = r

    # Aggregate
    merged = {"record_slips": [], "legal_cases": [], "persons": []}
    failed_pages = []
    server_seconds = 0.0
    for p in range(1, num_pages + 1):
        r = page_results.get(p)
        if r is None:
            failed_pages.append(p)
            continue
        server_seconds += r["time"]
        if r["parsed"] is not None:
            # Stamp source_page on every extracted item so the merge step
            # (and any future verification) can trace each slip back to a
            # specific page of the source PDF without rescanning the whole PDF.
            for k in merged:
                for item in r["parsed"].get(k, []):
                    if isinstance(item, dict) and "source_page" not in item:
                        item["source_page"] = p
                    merged[k].append(item)
        else:
            failed_pages.append(p)

    wall_seconds = time.time() - pdf_started
    merged["_meta"] = {
        "pdf": os.path.basename(pdf_path),
        "pages": num_pages,
        "failed_pages": failed_pages,
        "total_seconds": round(wall_seconds, 1),
        "server_seconds": round(server_seconds, 1),
        "parallel": parallel,
        "model": "qwen-vl-72b",
    }
    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2)

    speedup = (server_seconds / wall_seconds) if wall_seconds > 0 else 1.0
    print(f"    -> {len(merged['record_slips'])} slips, "
          f"{len(merged['legal_cases'])} cases, "
          f"{len(merged['persons'])} persons "
          f"({wall_seconds:.0f}s wall / {server_seconds:.0f}s server, "
          f"{speedup:.1f}x speedup, {len(failed_pages)} failed pages)",
          flush=True)
    return merged


def main():
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(f"Usage: {sys.argv[0]} INPUT_DIR OUTPUT_DIR [PARALLEL]")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    parallel = int(sys.argv[3]) if len(sys.argv) == 4 else 6
    os.makedirs(output_dir, exist_ok=True)

    server_url = get_server_url()
    print(f"Server:    {server_url}", flush=True)
    print(f"Input:     {input_dir}", flush=True)
    print(f"Output:    {output_dir}", flush=True)
    print(f"Parallel:  {parallel} concurrent pages per PDF", flush=True)

    pdfs = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, f))
    pdfs.sort()
    print(f"Found {len(pdfs)} PDFs (recursive)\n", flush=True)

    started = time.time()
    for i, pdf in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}]", end=" ", flush=True)
        try:
            process_pdf(pdf, output_dir, server_url, input_dir, parallel=parallel)
        except Exception as e:
            print(f"  FATAL on {os.path.basename(pdf)}: {e}", flush=True)

    print(f"\nDone. Wall time: {(time.time() - started)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
