#!/usr/bin/env python3
"""
Extract structured data from a single PDF using Claude and/or a Together AI model.
Useful for testing extraction on documents not yet in the database.

Usage:
    python3 extract_single_pdf.py path/to/document.pdf
    python3 extract_single_pdf.py path/to/document.pdf --together-model llama3.3-70b
    python3 extract_single_pdf.py path/to/document.pdf --claude-only
    python3 extract_single_pdf.py path/to/document.pdf --together-only --together-model llama3.3-70b
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
}


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


def build_prompt(chunk: str) -> str:
    """Build the v3 extraction prompt."""
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
            max_tokens=16000,
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
    except Exception as e:
        return {"error": str(e), "text": "", "time": time.time() - start}


def parse_json(text: str) -> dict:
    """Try to parse JSON from model output, stripping markdown fences if needed."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        return json.loads(text)
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
    parser.add_argument("--together-model", default=None,
                        help="Together AI model (shortname or full ID)")
    parser.add_argument("--claude-only", action="store_true",
                        help="Only run Claude")
    parser.add_argument("--together-only", action="store_true",
                        help="Only run Together AI model")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: auto-generated)")
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"File not found: {args.pdf}")
        sys.exit(1)

    # Extract text
    print(f"Extracting text from {os.path.basename(args.pdf)}...")
    text = extract_text(args.pdf, args.max_chars)
    print(f"  {len(text):,} chars extracted")

    prompt = build_prompt(text)

    # Set up output directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    basename = os.path.splitext(os.path.basename(args.pdf))[0]
    output_dir = args.output or f"comparisons/single_{timestamp}_{basename}"
    os.makedirs(output_dir, exist_ok=True)

    results = {}

    # Run Claude
    if not args.together_only:
        print("\nRunning Claude Sonnet...")
        result = run_claude(prompt)
        print(f"  Done in {result['time']:.1f}s")
        extraction = parse_json(result["text"])
        if extraction:
            counts = count_items(extraction)
            print(f"  Valid JSON: {counts['total']} items extracted")
            with open(os.path.join(output_dir, "claude.json"), "w") as f:
                json.dump(extraction, f, indent=2)
            results["claude"] = {"counts": counts, "time": result["time"]}
        else:
            print(f"  INVALID JSON")
            with open(os.path.join(output_dir, "claude_raw.txt"), "w") as f:
                f.write(result["text"])
            results["claude"] = {"error": "invalid JSON", "time": result["time"]}

    # Run Together AI model
    if not args.claude_only and args.together_model:
        model_id = TOGETHER_MODELS.get(args.together_model, args.together_model)
        api_key = os.environ.get("TOGETHER_API_KEY")
        if not api_key:
            print("\nTOGETHER_API_KEY not set, skipping Together AI model")
        else:
            print(f"\nRunning {args.together_model} ({model_id})...")
            result = run_together(prompt, model_id, api_key)
            if "error" in result:
                print(f"  ERROR: {result['error']}")
                results[args.together_model] = {"error": result["error"]}
            else:
                print(f"  Done in {result['time']:.1f}s")
                extraction = parse_json(result["text"])
                if extraction:
                    counts = count_items(extraction)
                    print(f"  Valid JSON: {counts['total']} items extracted")
                    safe_name = args.together_model.replace("/", "-")
                    with open(os.path.join(output_dir, f"{safe_name}.json"), "w") as f:
                        json.dump(extraction, f, indent=2)
                    results[args.together_model] = {"counts": counts, "time": result["time"]}
                else:
                    print(f"  INVALID JSON")
                    safe_name = args.together_model.replace("/", "-")
                    with open(os.path.join(output_dir, f"{safe_name}_raw.txt"), "w") as f:
                        f.write(result["text"])
                    results[args.together_model] = {"error": "invalid JSON", "time": result["time"]}

    # Print summary
    print(f"\n{'='*60}")
    print(f"Results for: {os.path.basename(args.pdf)}")
    print(f"Text chunk: {len(text):,} chars")
    print(f"{'='*60}")

    categories = ["entities", "events", "financial_transactions", "relationships",
                   "fee_patents", "correspondence", "legislative_actions", "total"]

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
