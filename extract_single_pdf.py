#!/usr/bin/env python3
"""
Extract structured data from a single PDF using Claude, Together AI, or a vLLM server.
Useful for testing extraction on documents not yet in the database.

Usage:
    python3 extract_single_pdf.py path/to/document.pdf
    python3 extract_single_pdf.py path/to/document.pdf --together-model llama3.3-70b
    python3 extract_single_pdf.py path/to/document.pdf --claude-only
    python3 extract_single_pdf.py path/to/document.pdf --together-only --together-model llama3.3-70b
    python3 extract_single_pdf.py path/to/document.pdf --together-model kimi-k2.5 --together-only --chunked

    # vLLM server (e.g., on HPC):
    python3 extract_single_pdf.py path/to/document.pdf --vllm-url http://hostname:8000 --vllm-model kimi-k2.5 --chunked
"""

import argparse
import json
import os
import sys
import time

import fitz  # PyMuPDF

# Model shortcuts for Together AI
TOGETHER_MODELS = {
    "llama3.3-70b": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "llama4-maverick": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "llama4-scout": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "qwen2.5-72b": "Qwen/Qwen2.5-72B-Instruct-Turbo",
    "kimi-k2.5": "moonshotai/Kimi-K2.5",
}


def render_pages_to_images(pdf_path: str, dpi: int = 200, max_bytes: int = 3_800_000) -> list:
    """Render each PDF page as a PNG image. Returns list of (page_num, png_bytes).
    If a page exceeds max_bytes, re-renders at lower DPI until it fits.
    Note: max_bytes accounts for ~33% base64 overhead (3.8MB PNG -> ~5MB base64)."""
    doc = fitz.open(pdf_path)
    pages = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        png_bytes = pix.tobytes("png")
        # If too large, reduce DPI until it fits
        cur_dpi = dpi
        while len(png_bytes) > max_bytes and cur_dpi > 72:
            cur_dpi -= 25
            m = fitz.Matrix(cur_dpi / 72, cur_dpi / 72)
            pix = page.get_pixmap(matrix=m)
            png_bytes = pix.tobytes("png")
        pages.append((page.number + 1, png_bytes))
    return pages


def run_claude_vision(page_images: list, prompt: str,
                      model: str = "claude-sonnet-4-6") -> dict:
    """Send page images to Claude for vision-based extraction.
    page_images is a list of (page_num, png_bytes). Uses streaming for long requests."""
    import anthropic
    import base64

    client = anthropic.Anthropic()
    start = time.time()

    # Build content blocks: images + prompt
    content = []
    for page_num, png_bytes in page_images:
        img_b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_b64}
        })
    content.append({"type": "text", "text": prompt})

    text = ""
    with client.messages.stream(
        model=model,
        max_tokens=32000,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        for event_text in stream.text_stream:
            text += event_text
    response = stream.get_final_message()
    elapsed = time.time() - start
    return {
        "text": text,
        "time": elapsed,
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }


VISION_EXTRACTION_PROMPT = """Extract ALL structured information from these scanned historical document pages.
Return a single JSON object with these keys:

{
  "entities": [
    {"name": "...", "type": "person|organization|location|land_parcel|legal_case|legislation|acreage_holding", "context": "brief description"}
  ],
  "events": [
    {"type": "...", "date": "YYYY-MM-DD or partial", "location": "...", "description": "..."}
  ],
  "financial_transactions": [
    {"type": "sale|lease|payment|fee|other", "amount": "...", "payer": "...", "payee": "...", "date": "...", "description": "..."}
  ],
  "relationships": [
    {"subject": "...", "type": "represented|employed_by|sold_to|bought_from|related_to|...", "object": "...", "context": "..."}
  ],
  "fee_patents": [
    {"allottee_name": "...", "allotment_number": "...", "acreage": "...", "patent_date": "...", "patent_number": "...", "mechanism": "private_bill|administrative|application|certificate_of_competency", "buyer": "...", "sale_price": "...", "attorney": "...", "mortgage": "..."}
  ],
  "correspondence": [
    {"sender": "...", "sender_title": "...", "recipient": "...", "recipient_title": "...", "date": "...", "subject": "...", "action_requested": "...", "outcome": "..."}
  ],
  "legislative_actions": [
    {"bill_number": "...", "sponsor": "...", "action_type": "introduced|reported|amended|passed|vetoed|enacted", "date": "...", "vote_count": "...", "committee": "...", "outcome": "..."}
  ],
  "testimony": [
    {"witness": "...", "witness_title": "...", "hearing": "...", "committee": "...", "location": "...", "date": "...", "subject": "...", "key_claims": "summary of what the witness stated or alleged", "questioner": "name of committee member or counsel asking questions, if identifiable"}
  ],
  "taxes": [
    {"taxpayer": "...", "land_description": "...", "tax_type": "property|county|state|delinquent|other", "amount": "...", "year": "...", "status": "paid|delinquent|tax_sale|tax_deed|exempt|other", "county": "...", "context": "..."}
  ],
  "mortgages": [
    {"borrower": "...", "lender": "...", "amount": "...", "land_description": "...", "acreage": "...", "date": "...", "interest_rate": "...", "status": "active|foreclosed|paid|default|other", "context": "..."}
  ],
  "tables": [
    {"title": "...", "columns": ["col1", "col2", ...], "rows": [{"col1": "val1", "col2": "val2"}, ...]}
  ]
}

Pay special attention to TABLES — extract every row and column with exact values.
Read numbers carefully: distinguish 3 from 8, 0 from O, 1 from l.
Extract EVERY entity, event, transaction, relationship, fee patent, correspondence record, legislative action, testimony, tax record, mortgage, and table mentioned.
Be thorough — missing data is worse than extra data.

Return ONLY valid JSON, no markdown fencing, no commentary:"""


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
      "correspondent_role": "outgoing",
      "case_name": "U.S. v. Roosevelt County, et al",
      "case_number": "",
      "allottee_name": "Jessie Eng",
      "allottee_number": "",
      "tribe_or_reservation": "Fort Peck",
      "subject": "Encloses 2 copies of bill of complaint prepared in above action",
      "action_type": "filing|acknowledgment|enclosure|request|ruling|settlement|appeal|other",
      "enclosures": "2 copies of bill of complaint",
      "routing_division": "Lands",
      "routing_date": "1936-03-21",
      "clerk_initials": "rmh",
      "processed_date": "1936-03-21"
    }
  ],
  "legal_cases": [
    {
      "case_name": "U.S. v. Roosevelt County, et al",
      "file_number": "90-2-5-49",
      "jurisdiction": "Montana",
      "case_type": "tax_recovery|quiet_title|allotment|termination|other",
      "allottee_name": "Jessie Eng",
      "tribe_or_reservation": "Fort Peck",
      "county": "Roosevelt"
    }
  ],
  "persons": [
    {
      "name": "Jessie Eng",
      "role": "allottee",
      "tribe": "Fort Peck",
      "allottee_number": ""
    }
  ]
}

IMPORTANT:
- Each page may have 1-4 cards. Extract ALL of them as separate record_slip entries.
- Read the file number EXACTLY (e.g., 90-2-5-49, not 90-2-549 or 90-3-5-49).
- Dates are in M-D-YY format (e.g., 3-17-36 = March 17, 1936). Convert to YYYY-MM-DD.
- Many cards reference the same case — extract each card separately even if redundant.
- Allottee names appear in the Re: line (e.g., "Jessie Eng" in "U.S. v. Roosevelt County, et al" for recovery of taxes upon allotment of Jessie Eng).
- "Enc." or "Encl." means enclosures were attached.
- Clerk initials (cam, rmh, ahw, me, ib, jt, etc.) appear at the bottom with dates.
- If text is illegible, transcribe what you can and mark unclear portions with [?].

Return ONLY valid JSON, no markdown fencing, no commentary:"""


def extract_text(pdf_path: str, max_chars: int = 40000) -> str:
    """Extract text from PDF, up to max_chars."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += f"--- Page {page.number + 1} ---\n"
        text += page.get_text() + "\n"
        if len(text) >= max_chars:
            text = text[:max_chars]
            break
    return text


def extract_full_text(pdf_path: str) -> str:
    """Extract all text from PDF with no limit."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += f"--- Page {page.number + 1} ---\n"
        text += page.get_text() + "\n"
    return text


def chunk_text(text: str, chunk_size: int = 40000, overlap: int = 5000) -> list:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def merge_extractions(extractions: list) -> dict:
    """Merge multiple chunk extractions into one, concatenating all arrays."""
    merged = {}
    for ext in extractions:
        for key, val in ext.items():
            if isinstance(val, list):
                if key not in merged:
                    merged[key] = []
                merged[key].extend(val)
    return merged


def build_prompt(chunk: str, version: str = "v4") -> str:
    """Build the extraction prompt. v4 adds testimony, taxes, and mortgages."""
    if version == "v3":
        return _build_prompt_v3(chunk)
    return _build_prompt_v4(chunk)


def _build_prompt_v3(chunk: str) -> str:
    """Build the v3 extraction prompt (original 7 types)."""
    return f"""Extract ALL structured information from this historical document text.
Return a single JSON object with these keys:

{{
  "entities": [
    {{"name": "...", "type": "person|organization|location|land_parcel|legal_case|legislation|acreage_holding", "context": "brief description"}}
  ],
  "events": [
    {{"type": "...", "date": "YYYY-MM-DD or partial", "location": "...", "description": "..."}}
  ],
  "financial_transactions": [
    {{"type": "sale|lease|payment|fee|other", "amount": "...", "payer": "...", "payee": "...", "date": "...", "description": "..."}}
  ],
  "relationships": [
    {{"subject": "...", "type": "represented|employed_by|sold_to|bought_from|related_to|...", "object": "...", "context": "..."}}
  ],
  "fee_patents": [
    {{"allottee_name": "...", "allotment_number": "...", "acreage": "...", "patent_date": "...", "patent_number": "...", "mechanism": "private_bill|administrative|application", "buyer": "...", "sale_price": "...", "attorney": "...", "mortgage": "..."}}
  ],
  "correspondence": [
    {{"sender": "...", "sender_title": "...", "recipient": "...", "recipient_title": "...", "date": "...", "subject": "...", "action_requested": "...", "outcome": "..."}}
  ],
  "legislative_actions": [
    {{"bill_number": "...", "sponsor": "...", "action_type": "introduced|reported|amended|passed|vetoed|enacted", "date": "...", "vote_count": "...", "committee": "...", "outcome": "..."}}
  ]
}}

Extract EVERY entity, event, transaction, relationship, fee patent, correspondence record, and legislative action mentioned. Be thorough — missing data is worse than extra data.

DOCUMENT TEXT:
{chunk}

Return ONLY valid JSON, no markdown fencing, no commentary:"""


def _build_prompt_v4(chunk: str) -> str:
    """Build the v4 extraction prompt (10 types: v3 + testimony, taxes, mortgages)."""
    return f"""Extract ALL structured information from this historical document text.
Return a single JSON object with these keys:

{{
  "entities": [
    {{"name": "...", "type": "person|organization|location|land_parcel|legal_case|legislation|acreage_holding", "context": "brief description"}}
  ],
  "events": [
    {{"type": "...", "date": "YYYY-MM-DD or partial", "location": "...", "description": "..."}}
  ],
  "financial_transactions": [
    {{"type": "sale|lease|payment|fee|other", "amount": "...", "payer": "...", "payee": "...", "date": "...", "description": "..."}}
  ],
  "relationships": [
    {{"subject": "...", "type": "represented|employed_by|sold_to|bought_from|related_to|...", "object": "...", "context": "..."}}
  ],
  "fee_patents": [
    {{"allottee_name": "...", "allotment_number": "...", "acreage": "...", "patent_date": "...", "patent_number": "...", "mechanism": "private_bill|administrative|application|certificate_of_competency", "buyer": "...", "sale_price": "...", "attorney": "...", "mortgage": "..."}}
  ],
  "correspondence": [
    {{"sender": "...", "sender_title": "...", "recipient": "...", "recipient_title": "...", "date": "...", "subject": "...", "action_requested": "...", "outcome": "..."}}
  ],
  "legislative_actions": [
    {{"bill_number": "...", "sponsor": "...", "action_type": "introduced|reported|amended|passed|vetoed|enacted", "date": "...", "vote_count": "...", "committee": "...", "outcome": "..."}}
  ],
  "testimony": [
    {{"witness": "...", "witness_title": "...", "hearing": "...", "committee": "...", "location": "...", "date": "...", "subject": "...", "key_claims": "summary of what the witness stated or alleged", "questioner": "name of committee member or counsel asking questions, if identifiable"}}
  ],
  "taxes": [
    {{"taxpayer": "...", "land_description": "...", "tax_type": "property|county|state|delinquent|other", "amount": "...", "year": "...", "status": "paid|delinquent|tax_sale|tax_deed|exempt|other", "county": "...", "context": "..."}}
  ],
  "mortgages": [
    {{"borrower": "...", "lender": "...", "amount": "...", "land_description": "...", "acreage": "...", "date": "...", "interest_rate": "...", "status": "active|foreclosed|paid|default|other", "context": "..."}}
  ]
}}

Extract EVERY entity, event, transaction, relationship, fee patent, correspondence record, legislative action, testimony, tax record, and mortgage mentioned. Be thorough — missing data is worse than extra data. For testimony, extract each distinct witness's statements as a separate record. For taxes and mortgages, extract every specific instance mentioned — these are key mechanisms of land dispossession.

DOCUMENT TEXT:
{chunk}

Return ONLY valid JSON, no markdown fencing, no commentary:"""


def run_claude(prompt: str, model: str = "claude-sonnet-4-6") -> dict:
    """Run extraction via Claude API using streaming for long requests."""
    import anthropic
    client = anthropic.Anthropic()
    start = time.time()
    text = ""
    input_tokens = 0
    output_tokens = 0
    with client.messages.stream(
        model=model,
        max_tokens=32000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for event_text in stream.text_stream:
            text += event_text
    response = stream.get_final_message()
    elapsed = time.time() - start
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    return {
        "text": text,
        "time": elapsed,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def run_together(prompt: str, model: str, api_key: str) -> dict:
    """Run extraction via Together AI API using the together library."""
    from together import Together

    start = time.time()
    try:
        client = Together(api_key=api_key, timeout=600.0)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=32000,
            temperature=0.3,
        )
        elapsed = time.time() - start
        return {
            "text": response.choices[0].message.content,
            "time": elapsed,
            "model": model,
            "input_tokens": getattr(response.usage, "prompt_tokens", 0),
            "output_tokens": getattr(response.usage, "completion_tokens", 0),
        }
    except KeyboardInterrupt:
        raise  # Let Ctrl+C propagate
    except BaseException as e:
        # Catch everything including httpx errors, SDK internal errors, etc.
        err_msg = str(e)
        if len(err_msg) > 200:
            err_msg = err_msg[:200] + "..."
        return {"error": f"Error code: {type(e).__name__} - {err_msg}", "text": "", "time": time.time() - start}


def run_vllm(prompt: str, model: str, base_url: str, api_key: str = None) -> dict:
    """Run extraction via a vLLM/OpenAI-compatible server (e.g., HPC or UVA RC GenAI)."""
    import urllib.request
    import urllib.error

    start = time.time()
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8192,
        "temperature": 0.3,
    }).encode("utf-8")
    # Determine endpoint path: UVA RC GenAI uses /api/chat/completions,
    # standard vLLM uses /v1/chat/completions
    if "open-webui" in base_url:
        url = f"{base_url.rstrip('/')}/api/chat/completions"
    else:
        url = f"{base_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            raw = resp.read().decode()
        elapsed = time.time() - start
        # Try regular JSON first
        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            if content is not None:
                return {
                    "text": content,
                    "time": elapsed,
                    "model": model,
                    "input_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("completion_tokens", 0),
                }
        except (json.JSONDecodeError, KeyError, TypeError, IndexError):
            pass
        # Parse SSE streaming response (RC GenAI returns this format)
        if raw.startswith("data: "):
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
                idx = reasoning.find('{')
                if idx >= 0:
                    content = reasoning[idx:]
                    last = content.rfind('}')
                    if last >= 0:
                        content = content[:last + 1]
            if content:
                return {
                    "text": content,
                    "time": elapsed,
                    "model": model,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
        return {"error": f"Unparseable response: {raw[:200]}", "text": "", "time": elapsed}
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {body[:500]}", "text": "", "time": time.time() - start}
    except Exception as e:
        return {"error": str(e), "text": "", "time": time.time() - start}


def parse_json(text: str) -> dict:
    """Try to parse JSON from model output, stripping markdown fences, thinking
    preamble, and repairing truncated JSON if needed."""
    text = text.strip()
    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip thinking/reasoning preamble — find the first { that starts the JSON
    first_brace = text.find("{")
    if first_brace > 0:
        json_text = text[first_brace:]
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            # Try repair on the extracted JSON portion
            repaired = _repair_truncated_json(json_text)
            if repaired:
                return repaired
    # Attempt to repair truncated JSON by closing open structures
    if text.startswith("{") and len(text) > 100:
        repaired = _repair_truncated_json(text)
        if repaired:
            return repaired
    return None


def _repair_truncated_json(text: str) -> dict:
    """Try to salvage truncated JSON by finding the last complete item
    and closing all open brackets/braces."""
    # Find the last complete JSON object in an array (ends with })
    # by looking for },\n or }\n near the end
    # Walk backwards to find the last complete object boundary
    last_good = text.rfind("},")
    if last_good == -1:
        last_good = text.rfind("}")
    if last_good == -1:
        return None
    truncated = text[:last_good + 1]
    # Count open brackets and braces to close them
    open_brackets = truncated.count("[") - truncated.count("]")
    open_braces = truncated.count("{") - truncated.count("}")
    closing = "]" * open_brackets + "}" * open_braces
    try:
        result = json.loads(truncated + closing)
        return result
    except json.JSONDecodeError:
        return None


def count_items(extraction: dict) -> dict:
    """Count items per category."""
    counts = {}
    total = 0
    for key, val in extraction.items():
        if isinstance(val, list):
            counts[key] = len(val)
            total += len(val)
    counts["total"] = total
    return counts


def main():
    parser = argparse.ArgumentParser(description="Extract from a single PDF")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--max-chars", type=int, default=40000,
                        help="Max chars to extract from PDF (default: 40000)")
    parser.add_argument("--chunk-size", type=int, default=40000,
                        help="Chunk size in chars for chunked extraction (default: 40000)")
    parser.add_argument("--together-model", default=None,
                        help="Together AI model (shortname or full ID)")
    parser.add_argument("--claude-only", action="store_true",
                        help="Only run Claude")
    parser.add_argument("--together-only", action="store_true",
                        help="Only run Together AI model")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: auto-generated)")
    parser.add_argument("--chunked", action="store_true",
                        help="Process full document in 40K-char chunks with 5K overlap")
    parser.add_argument("--vllm-url", default=None,
                        help="vLLM server URL (e.g., http://hostname:8000)")
    parser.add_argument("--vllm-model", default=None,
                        help="Model name served by vLLM (shortname or as shown in /v1/models)")
    parser.add_argument("--uvarc", action="store_true",
                        help="Use UVA RC GenAI (Kimi K2.5). Requires UVARC_GenAI_API env var.")
    parser.add_argument("--vision", action="store_true",
                        help="Use vision mode: render pages as images, send to Claude for extraction. "
                             "Best for tabular documents, financial ledgers, allotment schedules.")
    parser.add_argument("--vision-pages", default=None,
                        help="Page range for vision mode (e.g., '1-10', '5,8,12-15'). Default: all pages.")
    parser.add_argument("--vision-batch", type=int, default=5,
                        help="Number of pages to send per API call in vision mode (default: 5)")
    parser.add_argument("--index-cards", action="store_true",
                        help="Use index card prompt (DOJ record slips). Implies --vision.")
    parser.add_argument("--v3", action="store_true",
                        help="Use v3 prompt (7 types). Default is v4 (10 types: +testimony, taxes, mortgages)")
    args = parser.parse_args()

    # UVA RC GenAI shortcut: sets vllm-url and vllm-model automatically
    if args.uvarc:
        args.vllm_url = "https://open-webui.rc.virginia.edu"
        args.vllm_model = "Kimi K2.5"

    if not os.path.exists(args.pdf):
        print(f"File not found: {args.pdf}")
        sys.exit(1)

    # Index cards mode implies vision
    if args.index_cards:
        args.vision = True

    # Vision mode: render pages and send to Claude vision
    if args.vision:
        print(f"Rendering pages from {os.path.basename(args.pdf)}...")
        all_pages = render_pages_to_images(args.pdf)
        print(f"  {len(all_pages)} pages rendered")

        # Parse page range if specified
        if args.vision_pages:
            selected = set()
            for part in args.vision_pages.split(","):
                if "-" in part:
                    start, end = part.split("-", 1)
                    selected.update(range(int(start), int(end) + 1))
                else:
                    selected.add(int(part))
            all_pages = [(n, img) for n, img in all_pages if n in selected]
            print(f"  Selected {len(all_pages)} pages: {sorted(p[0] for p in all_pages)}")

        # Set up output directory
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        basename = os.path.splitext(os.path.basename(args.pdf))[0]
        output_dir = args.output or f"comparisons/vision_{timestamp}_{basename}"
        os.makedirs(output_dir, exist_ok=True)

        # Process in batches
        batch_size = args.vision_batch
        all_extractions = []
        total_time = 0
        failed_batches = []

        num_batches = (len(all_pages) + batch_size - 1) // batch_size
        print(f"\nRunning Claude vision extraction ({num_batches} batches of up to {batch_size} pages)...")

        for i in range(0, len(all_pages), batch_size):
            batch = all_pages[i:i + batch_size]
            batch_num = i // batch_size + 1
            page_range = f"{batch[0][0]}-{batch[-1][0]}"
            print(f"  Batch {batch_num}/{num_batches} (pages {page_range})...", end=" ", flush=True)

            try:
                prompt = INDEX_CARD_PROMPT if args.index_cards else VISION_EXTRACTION_PROMPT
                result = run_claude_vision(batch, prompt)
            except Exception as e:
                print(f"EXCEPTION: {e}")
                failed_batches.append(batch_num)
                continue

            total_time += result["time"]
            extraction = parse_json(result["text"])
            if extraction:
                # Stamp source_page on every extracted item so the merge step
                # (and any future verification) can trace each item back to a
                # specific page of the source PDF without rescanning the whole PDF.
                # When batch_size == 1, the page number is exact. Otherwise we
                # store a range string and the consumer can decide what to do.
                page_start = batch[0][0]
                page_end = batch[-1][0]
                if page_start == page_end:
                    page_tag = page_start  # int, exact page
                else:
                    page_tag = f"{page_start}-{page_end}"  # range string
                for k, v in extraction.items():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict) and "source_page" not in item:
                                item["source_page"] = page_tag
                item_count = sum(len(v) for v in extraction.values() if isinstance(v, list))
                print(f"Done in {result['time']:.1f}s, {item_count} items")
                all_extractions.append(extraction)
                with open(os.path.join(output_dir, f"vision_batch_{batch_num}.json"), "w") as f:
                    json.dump(extraction, f, indent=2)
            else:
                print(f"INVALID JSON (batch {batch_num})")
                with open(os.path.join(output_dir, f"vision_batch_{batch_num}_raw.txt"), "w") as f:
                    f.write(result["text"])
                failed_batches.append(batch_num)

        if all_extractions:
            merged = merge_extractions(all_extractions)
            with open(os.path.join(output_dir, "vision_merged.json"), "w") as f:
                json.dump(merged, f, indent=2)
            counts = count_items(merged)
            print(f"\n{'='*60}")
            print(f"Vision extraction complete: {os.path.basename(args.pdf)}")
            print(f"  Pages: {len(all_pages)}, Batches: {num_batches}")
            print(f"  Total time: {total_time:.1f}s")
            if failed_batches:
                print(f"  Failed batches: {failed_batches}")
            for cat in sorted(counts.keys()):
                print(f"  {cat:<30} {counts[cat]:>8}")
            print(f"  Results saved to: {output_dir}/")
        else:
            print("\nNo valid extractions from vision mode.")
        sys.exit(0)

    # Extract text
    print(f"Extracting text from {os.path.basename(args.pdf)}...")
    if args.chunked:
        full_text = extract_full_text(args.pdf)
        chunks = chunk_text(full_text, chunk_size=args.chunk_size)
        print(f"  {len(full_text):,} chars extracted, split into {len(chunks)} chunks")
    else:
        text = extract_text(args.pdf, args.max_chars)
        chunks = [text]
        print(f"  {len(text):,} chars extracted")

    # Set up output directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    basename = os.path.splitext(os.path.basename(args.pdf))[0]
    suffix = "_chunked" if args.chunked else ""
    output_dir = args.output or f"comparisons/single_{timestamp}_{basename}{suffix}"
    os.makedirs(output_dir, exist_ok=True)

    results = {}

    def run_model_on_chunks(model_name, run_fn, chunks):
        """Run a model on all chunks and merge results. Continues on error."""
        all_extractions = []
        total_time = 0
        failed_chunks = []
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                print(f"  Chunk {i+1}/{len(chunks)} ({len(chunk):,} chars)...", end=" ", flush=True)
            prompt = build_prompt(chunk, version="v3" if args.v3 else "v4")
            try:
                result = run_fn(prompt)
            except Exception as e:
                print(f"EXCEPTION: {e}")
                failed_chunks.append(i + 1)
                continue
            if "error" in result:
                # Truncate long error messages (e.g., HTML from Cloudflare)
                err_msg = result["error"]
                if len(err_msg) > 200:
                    err_msg = err_msg[:200] + "..."
                print(f"ERROR: {err_msg}")
                failed_chunks.append(i + 1)
                continue
            total_time += result["time"]
            extraction = parse_json(result["text"])
            if extraction:
                item_count = sum(len(v) for v in extraction.values() if isinstance(v, list))
                if len(chunks) > 1:
                    print(f"Done in {result['time']:.1f}s, {item_count} items")
                all_extractions.append(extraction)
                # Save per-chunk output
                safe = model_name.replace("/", "-")
                with open(os.path.join(output_dir, f"{safe}_chunk_{i+1}.json"), "w") as f:
                    json.dump(extraction, f, indent=2)
            else:
                if len(chunks) > 1:
                    print(f"INVALID JSON (chunk {i+1})")
                safe = model_name.replace("/", "-")
                with open(os.path.join(output_dir, f"{safe}_chunk_{i+1}_raw.txt"), "w") as f:
                    f.write(result["text"])
                failed_chunks.append(i + 1)
        if not all_extractions:
            return None, {"error": "no valid extractions", "time": total_time}
        merged = merge_extractions(all_extractions)
        info = {"time": total_time, "chunks_ok": len(all_extractions), "chunks_total": len(chunks)}
        if failed_chunks:
            info["failed_chunks"] = failed_chunks
            print(f"  WARNING: {len(failed_chunks)} chunks failed ({failed_chunks}), merged {len(all_extractions)}/{len(chunks)} chunks")
        return merged, info

    # Run Claude (skip if using together-only or vllm-only)
    vllm_only = args.vllm_url and args.vllm_model and not args.together_model
    if not args.together_only and not vllm_only:
        print(f"\nRunning Claude Sonnet ({len(chunks)} chunk{'s' if len(chunks) > 1 else ''})...")
        merged, info = run_model_on_chunks("claude", lambda p: run_claude(p), chunks)
        if merged:
            counts = count_items(merged)
            print(f"  Total: {counts['total']} items in {info['time']:.1f}s")
            with open(os.path.join(output_dir, "claude.json"), "w") as f:
                json.dump(merged, f, indent=2)
            results["claude"] = {"counts": counts, "time": info["time"]}
        else:
            print(f"  FAILED: {info.get('error', 'unknown')}")
            results["claude"] = {"error": info.get("error", "unknown"), "time": info.get("time", 0)}

    # Run Together AI model
    if not args.claude_only and args.together_model:
        model_id = TOGETHER_MODELS.get(args.together_model, args.together_model)
        api_key = os.environ.get("TOGETHER_API_KEY")
        if not api_key:
            print("\nTOGETHER_API_KEY not set, skipping Together AI model")
        else:
            print(f"\nRunning {args.together_model} ({model_id}, {len(chunks)} chunk{'s' if len(chunks) > 1 else ''})...")
            merged, info = run_model_on_chunks(
                args.together_model,
                lambda p: run_together(p, model_id, api_key),
                chunks,
            )
            if merged:
                counts = count_items(merged)
                print(f"  Total: {counts['total']} items in {info['time']:.1f}s")
                safe_name = args.together_model.replace("/", "-")
                with open(os.path.join(output_dir, f"{safe_name}.json"), "w") as f:
                    json.dump(merged, f, indent=2)
                results[args.together_model] = {"counts": counts, "time": info["time"]}
            else:
                print(f"  FAILED: {info.get('error', 'unknown')}")
                results[args.together_model] = {"error": info.get("error", "unknown")}

    # Run vLLM model (also used for UVA RC GenAI)
    if args.vllm_url and args.vllm_model:
        model_id = args.vllm_model  # Use the served model name directly, not Together AI mapping
        display_name = args.vllm_model
        vllm_api_key = os.environ.get("UVARC_GenAI_API") if getattr(args, "uvarc", False) else None
        if getattr(args, "uvarc", False) and not vllm_api_key:
            print("\nUVARC_GenAI_API not set, skipping UVA RC GenAI")
        else:
            label = "UVA RC GenAI" if getattr(args, "uvarc", False) else f"vLLM at {args.vllm_url}"
            print(f"\nRunning {display_name} via {label} ({len(chunks)} chunk{'s' if len(chunks) > 1 else ''})...")
            merged, info = run_model_on_chunks(
                display_name,
                lambda p: run_vllm(p, model_id, args.vllm_url, api_key=vllm_api_key),
                chunks,
        )
        if merged:
            counts = count_items(merged)
            print(f"  Total: {counts['total']} items in {info['time']:.1f}s")
            safe_name = display_name.replace("/", "-")
            with open(os.path.join(output_dir, f"{safe_name}.json"), "w") as f:
                json.dump(merged, f, indent=2)
            results[display_name] = {"counts": counts, "time": info["time"]}
        else:
            print(f"  FAILED: {info.get('error', 'unknown')}")
            results[display_name] = {"error": info.get("error", "unknown")}

    # Print summary
    print(f"\n{'='*60}")
    print(f"Results for: {os.path.basename(args.pdf)}")
    total_chars = len(full_text) if args.chunked else len(chunks[0])
    chunk_info = f" ({len(chunks)} chunks)" if args.chunked else ""
    print(f"Text: {total_chars:,} chars{chunk_info}")
    print(f"{'='*60}")

    categories = ["entities", "events", "financial_transactions", "relationships",
                   "fee_patents", "correspondence", "legislative_actions",
                   "testimony", "taxes", "mortgages", "total"]

    header = f"{'Category':<30}"
    for model_name in results:
        header += f" {model_name:>15}"
    print(header)
    print("-" * len(header))

    for cat in categories:
        row = f"{cat:<30}"
        for model_name, data in results.items():
            if "counts" in data:
                row += f" {data['counts'].get(cat, 0):>15}"
            else:
                row += f" {'ERROR':>15}"
        print(row)

    print(f"\nResults saved to: {output_dir}/")


if __name__ == "__main__":
    main()
