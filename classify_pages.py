#!/usr/bin/env python3
"""
Classify every page in a PDF into document-type categories.
Runs both Sonnet and Kimi (via RC GenAI) in sequence, produces comparison CSVs.

Usage:
    python3 classify_pages.py path/to/document.pdf --output-dir output/
    python3 classify_pages.py path/to/document.pdf --sonnet-only
"""

import argparse
import csv
import json
import os
import sys
import time

import fitz

try:
    import anthropic
except ImportError:
    anthropic = None  # Not available on HPC; Kimi-only mode

CLASSIFY_PROMPT = """You are a document classifier. Classify this page into one category. Respond with ONLY a JSON object, nothing else.

Categories: affidavit_content, questionnaire_content, agency_narrative_content, ledger_entry_page, transmittal_letter, cover_sheet, other

Rules:
- affidavit_content: Any page containing sworn first-person testimony by an allottee. Includes first pages ("being first duly sworn", "personally appeared", "Deponent further states") AND continuation pages of multi-page affidavits (mid-sentence starts, notary blocks, continued testimony). The allottee is speaking.
- questionnaire_content: Any page containing a printed question form with allottee's answers. Has numbered questions or labeled fields ("Name of Allottee ___", "Date of patent ___"). Includes both the question page and the notary/witness page.
- agency_narrative_content: Any page containing a third-person account written by agency staff about an allottee. Opens with "ALLOTMENT NO. X" or continues a narrative about patent issuance, sales, mortgages, taxes in third person. The agency is writing about the allottee, not the allottee speaking.
- ledger_entry_page: Tabular register with MULTIPLE allottees listed per page. Organized by Township/Range with columns for name, allotment number, year, application status. Many names on one page in a list format.
- transmittal_letter: Agency correspondence to the Commissioner of Indian Affairs. Has letterhead ("DEPARTMENT OF THE INTERIOR / UNITED STATES INDIAN SERVICE"), "Sir:", superintendent signature. Discusses policy or administrative matters.
- cover_sheet: Title page, blank page, routing slip, section divider, or page with minimal/no meaningful content.
- other: Anything not matching the above. Includes pages with garbled OCR that can't be classified.

{"classification": "category_name", "confidence": "high|medium|low"}

PAGE TEXT:
"""


def parse_response(text):
    """Parse JSON from model response, handling markdown fencing."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()
    # Try to find JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            result = json.loads(text[start:end])
            return result.get("classification", "parse_error"), result.get("confidence", "unknown")
        except json.JSONDecodeError:
            pass
    return "parse_error", "unknown"


def classify_sonnet(page_text, client):
    """Classify one page with Sonnet."""
    prompt = CLASSIFY_PROMPT + page_text[:2000]
    start = time.time()
    resp_text = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=50,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for t in stream.text_stream:
            resp_text += t
    response = stream.get_final_message()
    elapsed = time.time() - start
    cls, conf = parse_response(resp_text)
    return cls, conf, response.usage.input_tokens, response.usage.output_tokens, elapsed


def _classify_kimi_single(prompt, vllm_url, api_key):
    """Single attempt to classify via Kimi. Returns (cls, conf, in_tok, out_tok, elapsed, failure_reason).
    failure_reason is None on success, or a string describing the failure."""
    import urllib.request
    start = time.time()

    payload = json.dumps({
        "model": "Kimi K2.5",
        "messages": [
            {"role": "system", "content": "Respond with only a JSON object. Do not explain your reasoning."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 8000,
        "temperature": 0.1,
    }).encode("utf-8")

    url = f"{vllm_url.rstrip('/')}/api/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    req = urllib.request.Request(url, data=payload, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()

        elapsed = time.time() - start

        # Parse SSE or JSON response
        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            if content:
                cls, conf = parse_response(content)
                if cls != "parse_error":
                    in_tok = data.get("usage", {}).get("prompt_tokens", 0)
                    out_tok = data.get("usage", {}).get("completion_tokens", 0)
                    return cls, conf, in_tok, out_tok, elapsed, None
                return None, None, 0, 0, elapsed, f"parse_error: {content[:100]}"
        except (json.JSONDecodeError, KeyError, TypeError, IndexError):
            pass

        # Parse SSE
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

            if not content and reasoning:
                idx = reasoning.find('{')
                if idx >= 0:
                    content = reasoning[idx:]
                    last = content.rfind('}')
                    if last >= 0:
                        content = content[:last + 1]

            if content:
                cls, conf = parse_response(content)
                if cls != "parse_error":
                    return cls, conf, 0, 0, elapsed, None
                return None, None, 0, 0, elapsed, f"parse_error_sse: {content[:100]}"

            # Check finish_reason from the last SSE chunk
            finish_reason = "unknown"
            for line in reversed(raw.split('\n')):
                line = line.strip()
                if line.startswith('data: ') and line != 'data: [DONE]':
                    try:
                        chunk = json.loads(line[6:])
                        fr = chunk['choices'][0].get('finish_reason')
                        if fr:
                            finish_reason = fr
                            break
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass

            # Empty content and no usable reasoning
            reason_len = len(reasoning)
            return None, None, 0, 0, elapsed, f"empty_sse (reasoning={reason_len} chars, finish_reason={finish_reason})"

        return None, None, 0, 0, elapsed, f"unparseable_response ({len(raw)} chars)"

    except Exception as e:
        elapsed = time.time() - start
        return None, None, 0, 0, elapsed, f"exception: {type(e).__name__}: {str(e)[:100]}"


def classify_kimi(page_text, vllm_url, api_key, max_retries=5):
    """Classify one page with Kimi via RC GenAI, with retry on failure.
    Returns (cls, conf, in_tok, out_tok, total_elapsed, retry_log).
    retry_log is a list of dicts: {'attempt': N, 'elapsed': T, 'failure': reason_or_None}
    """
    prompt = CLASSIFY_PROMPT + page_text[:2000]
    retry_log = []
    total_elapsed = 0

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            backoff = 2 ** (attempt - 1)  # 2, 4, 8, 16, 32
            time.sleep(backoff)

        cls, conf, in_tok, out_tok, elapsed, failure = _classify_kimi_single(prompt, vllm_url, api_key)
        total_elapsed += elapsed
        retry_log.append({
            'attempt': attempt,
            'elapsed': round(elapsed, 1),
            'failure': failure,
        })

        if failure is None:
            return cls, conf, in_tok, out_tok, total_elapsed, retry_log

    # All retries exhausted
    return "error", "unknown", 0, 0, total_elapsed, retry_log


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="Path to PDF")
    parser.add_argument("--output-dir", default="classifications")
    parser.add_argument("--sonnet-only", action="store_true")
    parser.add_argument("--label", default=None, help="Label for the PDF in output")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    doc = fitz.open(args.pdf)
    pages = len(doc)
    label = args.label or os.path.splitext(os.path.basename(args.pdf))[0]
    print(f"Classifying {label}: {pages} pages")

    # Sonnet classification
    client = anthropic.Anthropic()
    sonnet_results = []
    sonnet_total_in = 0
    sonnet_total_out = 0
    sonnet_total_time = 0

    print(f"\n--- Sonnet classification ({pages} pages) ---")
    for p in range(pages):
        text = doc[p].get_text()
        cls, conf, in_tok, out_tok, elapsed = classify_sonnet(text, client)
        preview = text[:150].replace('\n', ' | ')
        sonnet_results.append((p + 1, cls, conf, in_tok, out_tok, elapsed, preview[:100]))
        sonnet_total_in += in_tok
        sonnet_total_out += out_tok
        sonnet_total_time += elapsed
        if (p + 1) % 10 == 0 or p == 0:
            print(f"  Page {p+1}/{pages}: {cls} ({conf}) [{elapsed:.1f}s]")

    # Write Sonnet CSV
    sonnet_csv = os.path.join(args.output_dir, f"{label}_classifications_sonnet.csv")
    with open(sonnet_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pdf_name", "page_number", "classification", "confidence", "first_150_chars"])
        for pnum, cls, conf, _, _, _, preview in sonnet_results:
            w.writerow([label, pnum, cls, conf, preview])

    print(f"\n  Sonnet done: {sonnet_total_in:,} in, {sonnet_total_out:,} out, {sonnet_total_time:.1f}s total")
    sonnet_cost = sonnet_total_in * 3 / 1e6 + sonnet_total_out * 15 / 1e6
    print(f"  Sonnet cost: ${sonnet_cost:.3f}")

    # Kimi classification
    kimi_results = []
    kimi_total_in = 0
    kimi_total_out = 0
    kimi_total_time = 0

    if not args.sonnet_only:
        vllm_url = "https://open-webui.rc.virginia.edu"
        api_key = os.environ.get("UVARC_GenAI_API")
        if not api_key:
            print("\n  UVARC_GenAI_API not set — skipping Kimi classification")
        else:
            print(f"\n--- Kimi classification ({pages} pages) ---")
            for p in range(pages):
                text = doc[p].get_text()
                cls, conf, in_tok, out_tok, elapsed, _retry_log = classify_kimi(text, vllm_url, api_key)
                preview = text[:150].replace('\n', ' | ')
                kimi_results.append((p + 1, cls, conf, in_tok, out_tok, elapsed, preview[:100]))
                kimi_total_in += in_tok
                kimi_total_out += out_tok
                kimi_total_time += elapsed
                if (p + 1) % 10 == 0 or p == 0:
                    print(f"  Page {p+1}/{pages}: {cls} ({conf}) [{elapsed:.1f}s]")

            kimi_csv = os.path.join(args.output_dir, f"{label}_classifications_kimi.csv")
            with open(kimi_csv, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["pdf_name", "page_number", "classification", "confidence", "first_150_chars"])
                for pnum, cls, conf, _, _, _, preview in kimi_results:
                    w.writerow([label, pnum, cls, conf, preview])

            print(f"\n  Kimi done: {kimi_total_in:,} in, {kimi_total_out:,} out, {kimi_total_time:.1f}s total")

    # Comparison CSV (if both models ran)
    if kimi_results:
        comp_csv = os.path.join(args.output_dir, f"{label}_comparison.csv")
        with open(comp_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["pdf_name", "page_number", "sonnet_class", "sonnet_confidence",
                         "kimi_class", "kimi_confidence", "agreement"])
            agree = 0
            for s, k in zip(sonnet_results, kimi_results):
                s_cls = s[1]
                k_cls = k[1]
                match = "YES" if s_cls == k_cls else "NO"
                if match == "YES":
                    agree += 1
                w.writerow([label, s[0], s_cls, s[2], k_cls, k[2], match])

        print(f"\n--- Comparison ---")
        print(f"  Agreement: {agree}/{pages} ({agree*100//pages}%)")

        # Disagreement breakdown
        from collections import Counter
        disagree = Counter()
        for s, k in zip(sonnet_results, kimi_results):
            if s[1] != k[1]:
                disagree[(s[1], k[1])] += 1
        if disagree:
            print(f"  Disagreements:")
            for (s_cls, k_cls), count in disagree.most_common():
                print(f"    Sonnet={s_cls}, Kimi={k_cls}: {count}")

    # Summary table
    print(f"\n--- Sonnet classification summary ---")
    from collections import Counter
    sonnet_counts = Counter(r[1] for r in sonnet_results)
    for cls, count in sonnet_counts.most_common():
        print(f"  {cls:<35} {count:>5}")

    sonnet_conf = Counter(r[2] for r in sonnet_results)
    print(f"\n  Confidence: {dict(sonnet_conf)}")

    if kimi_results:
        print(f"\n--- Kimi classification summary ---")
        kimi_counts = Counter(r[1] for r in kimi_results)
        for cls, count in kimi_counts.most_common():
            print(f"  {cls:<35} {count:>5}")
        kimi_conf = Counter(r[2] for r in kimi_results)
        print(f"\n  Confidence: {dict(kimi_conf)}")

    # Save usage data
    usage = {
        "sonnet": {
            "input_tokens": sonnet_total_in,
            "output_tokens": sonnet_total_out,
            "total_time_s": round(sonnet_total_time, 1),
            "cost": round(sonnet_cost, 4),
            "pages": pages,
        }
    }
    if kimi_results:
        usage["kimi"] = {
            "input_tokens": kimi_total_in,
            "output_tokens": kimi_total_out,
            "total_time_s": round(kimi_total_time, 1),
            "cost": 0,  # RC GenAI is free
            "pages": pages,
        }
    with open(os.path.join(args.output_dir, f"{label}_usage.json"), "w") as f:
        json.dump(usage, f, indent=2)


if __name__ == "__main__":
    main()
