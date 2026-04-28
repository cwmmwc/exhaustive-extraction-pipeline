#!/usr/bin/env python3
"""
Test Qwen2.5-VL-72B on the same 20 index card pages we tested with Claude Sonnet.
Run from HPC compute node after the Qwen-VL server is running.

Usage:
    python3 test_qwen_vl_cards.py
"""
import json
import time
import base64
import urllib.request
import fitz

# Config
PDF_PATH = "/project/LawData/exhaustive-extraction-pipeline/1935 RG 60, Entry A1 96C, Record Slips, 1935, Class Numbers (Interfiled), Box 487, 90-2-5.pdf"
PAGES = list(range(1, 21))  # Pages 1-20
SERVER_ADDR_FILE = "/project/LawData/kimi-extraction/logs/qwen_vl_address.txt"

# Read the index card prompt from extract_single_pdf.py
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
    return pix.tobytes("png")


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

    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        f"{server_url}/v1/chat/completions",
        data=payload, headers=headers
    )

    start = time.time()
    resp = urllib.request.urlopen(req, timeout=300)
    elapsed = time.time() - start
    data = json.loads(resp.read().decode())
    return {
        "text": data["choices"][0]["message"]["content"],
        "time": elapsed,
        "tokens": data.get("usage", {}),
    }


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


def main():
    server_url = get_server_url()
    print(f"Server: {server_url}")
    print(f"PDF: {PDF_PATH}")
    print(f"Pages: {PAGES[0]}-{PAGES[-1]}")
    print()

    total_slips = 0
    total_cases = 0
    total_persons = 0
    total_time = 0
    all_results = []

    for page_num in PAGES:
        print(f"  Page {page_num}/{PAGES[-1]}...", end=" ", flush=True)
        img = render_page(PDF_PATH, page_num)

        try:
            result = send_to_qwen(server_url, img, INDEX_CARD_PROMPT)
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        total_time += result["time"]
        parsed = parse_json_response(result["text"])

        if parsed:
            slips = len(parsed.get("record_slips", []))
            cases = len(parsed.get("legal_cases", []))
            persons = len(parsed.get("persons", []))
            total_slips += slips
            total_cases += cases
            total_persons += persons
            all_results.append(parsed)
            print(f"Done in {result['time']:.1f}s — {slips} slips, {cases} cases, {persons} persons")
        else:
            print(f"INVALID JSON ({result['time']:.1f}s)")
            with open(f"/project/LawData/kimi-extraction/logs/qwen_vl_page_{page_num}_raw.txt", "w") as f:
                f.write(result["text"])

    # Merge and save
    merged = {"record_slips": [], "legal_cases": [], "persons": []}
    for r in all_results:
        for key in merged:
            merged[key].extend(r.get(key, []))

    outpath = "/project/LawData/kimi-extraction/outputs/qwen_vl_index_cards_test.json"
    with open(outpath, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Qwen2.5-VL-72B Index Card Test")
    print(f"  Pages: {len(PAGES)}")
    print(f"  Total time: {total_time:.1f}s ({total_time/len(PAGES):.1f}s/page)")
    print(f"  Record slips: {total_slips}")
    print(f"  Legal cases: {total_cases}")
    print(f"  Persons: {total_persons}")
    print(f"  Results: {outpath}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
