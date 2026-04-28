#!/usr/bin/env python3
"""
Test Kimi K2.5 vision on RC GenAI for index card extraction.
Sends page images directly to Kimi's vision capability.
Run from HPC compute node.
"""
import json, time, base64, urllib.request, fitz

PDF_PATH = "/project/LawData/exhaustive-extraction-pipeline/1935 RG 60, Entry A1 96C, Record Slips, 1935, Class Numbers (Interfiled), Box 487, 90-2-5.pdf"
PAGES = list(range(1, 21))
KEY = 'sk-d392dfeafc9b4ae08aeafece8e97c837'
URL = 'https://open-webui.rc.virginia.edu/api/chat/completions'

INDEX_CARD_PROMPT = """You are reading scanned images of DOJ record slips — index cards tracking correspondence about legal cases involving Indian land, taxes, and allotments.

Each card has: HEADER (file number | jurisdiction | date), CORRESPONDENT, RE: line (case name and action), FOOTER (division routing, dates, clerk initials).

Extract EVERY card as a separate record. Return JSON:
{
  "record_slips": [
    {"file_number": "90-2-5-49", "jurisdiction": "Montana", "date": "1936-03-17", "correspondent": "Asst. U.S. Atty.", "case_name": "U.S. v. Roosevelt County, et al", "named_individual": "Jessie Eng", "tribe_or_reservation": "Fort Peck", "subject": "Encloses 2 copies of bill of complaint", "routing_division": "Lands", "routing_date": "1936-03-21", "clerk_initials": "rmh"}
  ],
  "legal_cases": [
    {"case_name": "U.S. v. Roosevelt County, et al", "file_number": "90-2-5-49", "jurisdiction": "Montana", "named_individual": "Jessie Eng", "tribe_or_reservation": "Fort Peck"}
  ],
  "persons": [
    {"name": "Jessie Eng", "role": "allottee", "tribe": "Fort Peck"}
  ]
}

Read file numbers EXACTLY. Convert dates to YYYY-MM-DD. Return ONLY valid JSON:"""


def render_page(pdf_path, page_num, dpi=200):
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=matrix)
    png = pix.tobytes("png")
    # Reduce if too large
    cur_dpi = dpi
    while len(png) > 3800000 and cur_dpi > 72:
        cur_dpi -= 25
        m = fitz.Matrix(cur_dpi / 72, cur_dpi / 72)
        pix = page.get_pixmap(matrix=m)
        png = pix.tobytes("png")
    return png


def send_to_kimi_vision(image_bytes, prompt):
    img_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    payload = json.dumps({
        "model": "Kimi K2.5",
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

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + KEY,
    }

    start = time.time()
    req = urllib.request.Request(URL, data=payload, headers=headers)
    resp = urllib.request.urlopen(req, timeout=600)
    raw = resp.read().decode()
    elapsed = time.time() - start

    # Parse SSE streaming response
    content = ""
    reasoning = ""
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

    # Kimi sometimes puts JSON in reasoning instead of content
    if not content and reasoning:
        # Look for JSON in the reasoning
        idx = reasoning.find('{')
        if idx >= 0:
            content = reasoning[idx:]
            # Find the last closing brace
            last = content.rfind('}')
            if last >= 0:
                content = content[:last + 1]

    return {"text": content, "time": elapsed}


def parse_json(text):
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
    print(f"PDF: {PDF_PATH}")
    print(f"Pages: {PAGES[0]}-{PAGES[-1]}")
    print(f"Model: Kimi K2.5 vision via RC GenAI")
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
            result = send_to_kimi_vision(img, INDEX_CARD_PROMPT)
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        total_time += result["time"]
        parsed = parse_json(result["text"])

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

    # Save
    merged = {"record_slips": [], "legal_cases": [], "persons": []}
    for r in all_results:
        for key in merged:
            merged[key].extend(r.get(key, []))

    outpath = "/project/LawData/kimi-extraction/outputs/kimi_vision_index_cards_test.json"
    with open(outpath, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Kimi K2.5 Vision — Index Card Test")
    print(f"  Pages: {len(PAGES)}")
    print(f"  Total time: {total_time:.1f}s ({total_time/len(PAGES):.1f}s/page)")
    print(f"  Record slips: {total_slips}")
    print(f"  Legal cases: {total_cases}")
    print(f"  Persons: {total_persons}")
    print(f"  Results: {outpath}")
    print(f"{'='*60}")
    print(f"\nComparison: Claude Sonnet did 28 slips in 141s on these same 20 pages")


if __name__ == "__main__":
    main()
