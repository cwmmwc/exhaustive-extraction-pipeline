#!/usr/bin/env python3
"""
Compare Claude vs. Local Open-Source Models

Two modes:
  1. SYNTHESIS — Compare corpus-wide analysis quality (default)
  2. EXTRACTION — Compare structured entity extraction from document chunks

Runs the same task through Claude (API) and one or more local models
(via Ollama) and saves all outputs side by side for human evaluation.

Requirements:
  - Anthropic API key (ANTHROPIC_API_KEY env var)
  - Ollama running locally (ollama serve) with models pulled
  - PostgreSQL with crow_historical_docs database

Usage:
    # List available Ollama models
    python3 compare_claude_vs_local_models.py --list-models

    # Compare all three local models against Claude for synthesis
    python3 compare_claude_vs_local_models.py --local-models llama3.3:70b qwen2.5:72b gemma3:27b

    # Compare for extraction (uses sample document chunks)
    python3 compare_claude_vs_local_models.py --mode extraction --local-models llama3.3:70b qwen2.5:72b gemma3:27b

    # Single model comparison
    python3 compare_claude_vs_local_models.py --local-models qwen2.5:72b

    # Custom synthesis question
    python3 compare_claude_vs_local_models.py --question "Tell me about fee patents"

    # Skip Claude (only run local models)
    python3 compare_claude_vs_local_models.py --local-only --local-models llama3.3:70b qwen2.5:72b

    # Skip local (only run Claude)
    python3 compare_claude_vs_local_models.py --claude-only

Output:
    Creates a timestamped directory under comparisons/ with:
      - question_N_claude.md
      - question_N_<model>.md  (one per local model)
      - summary.md  (side-by-side stats for all models)
"""

import anthropic
import psycopg2
import psycopg2.extras
import os
import sys
import json
import time
import re
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


# ─────────────────────────────────────────────────
# Default test questions for SYNTHESIS mode
# ─────────────────────────────────────────────────

DEFAULT_QUESTIONS = [
    # 1. Person tracing across documents (tests cross-document synthesis)
    "Tell me about Harlow Pease and his relationship with the Crow generally "
    "and with Section 2 of the Crow Act specifically.",

    # 2. Mechanism analysis (tests understanding of legal/administrative processes)
    "What were the primary mechanisms of forced fee patent issuance on the "
    "Crow Reservation? Who were the key actors and what were the outcomes?",

    # 3. Quantitative aggregation (tests ability to gather and aggregate numbers)
    "How much Crow land was lost and to whom? Quantify the scale of land "
    "dispossession using specific acreages, dollar amounts, and transaction counts "
    "from the documents.",
]


# ─────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────

DB_NAME = "crow_historical_docs"


def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    return psycopg2.connect(dbname=DB_NAME, host="localhost")


def get_db_stats() -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    stats = {}
    for table in ["documents", "entities", "events", "financial_transactions",
                   "relationships", "fee_patents", "correspondence", "legislative_actions"]:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cur.fetchone()[0]
        except Exception:
            stats[table] = 0
    cur.close()
    conn.close()
    return stats


def get_all_summaries() -> List[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, file_name, display_title, collection, summary
        FROM documents
        WHERE summary IS NOT NULL AND summary != ''
        ORDER BY id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_extraction_samples(n: int = 3) -> List[Dict]:
    """Get sample document chunks for extraction comparison."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # Pick documents with varied content — a hearing, a correspondence file, a fee patent doc
    cur.execute("""
        SELECT id, file_name, display_title,
               SUBSTRING(full_text FROM 1 FOR 40000) as chunk
        FROM documents
        WHERE LENGTH(full_text) > 5000
        ORDER BY random()
        LIMIT %s
    """, [n])
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────
# Prompt builders
# ─────────────────────────────────────────────────

def build_corpus_context(summaries: List[Dict]) -> str:
    lines = []
    current_collection = None
    for doc in summaries:
        collection = doc.get('collection') or 'Unknown'
        if collection != current_collection:
            current_collection = collection
            lines.append(f"\n--- Collection: {collection} ---\n")
        name = doc.get('display_title') or doc.get('file_name', '')
        lines.append(f"[Doc {doc['id']}] {name}")
        lines.append(doc['summary'])
        lines.append("")
    return "\n".join(lines)


def build_synthesis_prompt(question: str, summaries: List[Dict], db_stats: Dict) -> str:
    corpus_context = build_corpus_context(summaries)
    collections = set(d.get('collection', 'Unknown') for d in summaries)

    return f"""You are a historian analyzing a complete archival collection about Native American land dispossession, federal Indian policy, and Bureau of Indian Affairs records.

You have analytical summaries of ALL {len(summaries)} documents in this collection, spanning {len(collections)} archival collections. Each summary captures the document type, key parties, specific actions, legal mechanisms, and evidentiary value. This is the ENTIRE corpus — you are seeing everything, not a sample.

DATABASE SCOPE: {db_stats.get('documents', 0)} documents, {db_stats.get('entities', 0)} entities, {db_stats.get('events', 0)} events, {db_stats.get('financial_transactions', 0)} transactions, {db_stats.get('relationships', 0)} relationships, {db_stats.get('fee_patents', 0)} fee patents, {db_stats.get('correspondence', 0)} correspondence records, {db_stats.get('legislative_actions', 0)} legislative actions.

RESEARCH QUESTION: {question}

{corpus_context}

SYNTHESIS GUIDELINES:

1. SURFACE PATTERNS across documents. Identify recurring actors, repeated legal mechanisms, and systematic processes that appear across multiple documents and decades.

2. GROUND EVERYTHING IN EVIDENCE. Every claim must be supported by specific documentary evidence: names, allotment numbers, acreages, dollar amounts, bill numbers, dates.

3. SHOW CONNECTIONS. Trace which actors appear together across documents. Identify sequences of events that recur.

4. QUANTIFY WHERE POSSIBLE. Aggregate total acreages, dollar amounts, numbers of transactions across the corpus.

5. Cite specific documents by their [Doc N] reference. Every substantive claim needs at least one citation.

6. CONCLUDE WITH THREE SECTIONS:
   - **What the Documents Prove**: claims fully supported by the documentary evidence.
   - **What the Documents Suggest**: plausible interpretations the evidence points toward.
   - **Gaps in the Record**: what is poorly represented or unanswerable from this corpus.

Begin your corpus-wide synthesis:"""


def build_extraction_prompt(chunk: str) -> str:
    """Build the v3 extraction prompt for a document chunk."""
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


# ─────────────────────────────────────────────────
# Model runners
# ─────────────────────────────────────────────────

def run_claude(prompt: str, model: str = "claude-opus-4-6",
               max_tokens: int = 16000) -> Dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set", "text": "", "time": 0}

    client = anthropic.Anthropic(api_key=api_key)
    start = time.time()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        elapsed = time.time() - start
        text = response.content[0].text
        return {
            "text": text,
            "time": elapsed,
            "model": model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
    except Exception as e:
        return {"error": str(e), "text": "", "time": time.time() - start}


def run_ollama(prompt: str, model: str = "llama3.3:70b",
               max_tokens: int = 16000) -> Dict:
    """Run a prompt through Ollama's API."""
    import urllib.request
    import urllib.error

    start = time.time()
    try:
        data = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": max_tokens,
                "num_ctx": 131072,
            }
        }).encode()

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=1800) as resp:
            result = json.loads(resp.read().decode())

        elapsed = time.time() - start
        return {
            "text": result.get("response", ""),
            "time": elapsed,
            "model": model,
            "eval_count": result.get("eval_count", 0),
            "prompt_eval_count": result.get("prompt_eval_count", 0),
        }
    except urllib.error.URLError as e:
        return {
            "error": f"Cannot connect to Ollama at localhost:11434. "
                     f"Is 'ollama serve' running? ({e})",
            "text": "", "time": time.time() - start
        }
    except Exception as e:
        return {"error": str(e), "text": "", "time": time.time() - start}


def list_ollama_models() -> List[str]:
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")[1:]
        return [line.split()[0] for line in lines if line.strip()]
    except Exception:
        return []


# ─────────────────────────────────────────────────
# Analysis metrics
# ─────────────────────────────────────────────────

def count_doc_citations(text: str) -> int:
    refs = re.findall(r'\[Doc\s+(\d+)', text)
    return len(set(refs))


def count_specific_evidence(text: str) -> Dict:
    return {
        "dollar_amounts": len(re.findall(r'\$[\d,]+(?:\.\d{2})?', text)),
        "acreage_mentions": len(re.findall(r'[\d,]+\s*acres?', text, re.IGNORECASE)),
        "dates": len(re.findall(
            r'\b(?:January|February|March|April|May|June|July|August|September|'
            r'October|November|December)\s+\d{1,2},?\s+\d{4}', text)),
        "bill_numbers": len(re.findall(r'[SH]\.?\s*(?:R\.)?\s*\d+', text)),
        "allotment_numbers": len(re.findall(
            r'(?:allot(?:ment|tee)?|No\.)\s*#?\s*\d+', text, re.IGNORECASE)),
    }


def analyze_synthesis_output(result: Dict) -> Dict:
    text = result.get("text", "")
    if not text:
        return {"word_count": 0, "doc_citations": 0, "evidence": {}, "sections": {}}
    return {
        "word_count": len(text.split()),
        "doc_citations": count_doc_citations(text),
        "evidence": count_specific_evidence(text),
        "sections": {
            "has_prove": "what the documents prove" in text.lower(),
            "has_suggest": "what the documents suggest" in text.lower(),
            "has_gaps": "gaps in the record" in text.lower(),
        }
    }


def analyze_extraction_output(result: Dict) -> Dict:
    """Analyze extraction output — count entities, valid JSON, etc."""
    text = result.get("text", "")
    if not text:
        return {"valid_json": False, "counts": {}}

    # Try to parse JSON
    try:
        # Strip markdown fencing if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        data = json.loads(cleaned)
        counts = {}
        for key in ["entities", "events", "financial_transactions", "relationships",
                     "fee_patents", "correspondence", "legislative_actions"]:
            items = data.get(key, [])
            counts[key] = len(items) if isinstance(items, list) else 0
        return {"valid_json": True, "counts": counts, "data": data}
    except (json.JSONDecodeError, Exception) as e:
        return {"valid_json": False, "error": str(e), "counts": {}}


# ─────────────────────────────────────────────────
# Synthesis comparison
# ─────────────────────────────────────────────────

def run_synthesis_comparison(
    questions: List[str],
    summaries: List[Dict],
    db_stats: Dict,
    local_models: List[str],
    claude_model: str = "claude-opus-4-6",
    run_claude_flag: bool = True,
    run_local_flag: bool = True,
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_label = "_".join(m.replace(":", "-").replace("/", "-") for m in local_models)
    out_dir = Path("comparisons") / f"synthesis_{timestamp}_{model_label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt_tokens = None
    all_results = []
    all_models = []
    if run_claude_flag:
        all_models.append(("claude", claude_model))
    if run_local_flag:
        for m in local_models:
            all_models.append(("local", m))

    for i, question in enumerate(questions, 1):
        print(f"\n{'='*60}")
        print(f"Question {i}/{len(questions)}:")
        print(f"  {question[:80]}...")
        print(f"{'='*60}")

        prompt = build_synthesis_prompt(question, summaries, db_stats)

        if prompt_tokens is None:
            prompt_tokens = len(prompt.split()) * 1.33
            print(f"\nPrompt size: ~{int(prompt_tokens):,} tokens ({len(prompt):,} chars)")

        result = {"question": question, "outputs": {}}

        for kind, model in all_models:
            safe_name = model.replace(":", "-").replace("/", "-")
            print(f"\nRunning {model}...")
            if kind == "claude":
                output = run_claude(prompt, model=model)
            else:
                print(f"  (This may take a while with ~{int(prompt_tokens):,} tokens of context)")
                output = run_ollama(prompt, model=model)

            if output.get("error"):
                print(f"  ERROR: {output['error']}")
            else:
                tokens_out = output.get('output_tokens') or output.get('eval_count', '?')
                print(f"  Done in {output['time']:.1f}s ({tokens_out} output tokens)")

            result["outputs"][model] = output

            # Save individual output
            with open(out_dir / f"question_{i}_{safe_name}.md", "w") as f:
                f.write(f"# Question {i} — {model}\n\n")
                f.write(f"**Question:** {question}\n\n")
                f.write(f"**Time:** {output['time']:.1f}s\n\n")
                if output.get("input_tokens"):
                    f.write(f"**Tokens:** {output['input_tokens']:,} in, "
                            f"{output['output_tokens']:,} out\n\n")
                elif output.get("eval_count"):
                    f.write(f"**Tokens generated:** {output['eval_count']:,}\n\n")
                f.write("---\n\n")
                f.write(output.get("text", output.get("error", "")))

        all_results.append(result)

    # Write summary comparison
    _write_synthesis_summary(out_dir, all_results, all_models, summaries,
                             db_stats, prompt_tokens)
    _print_output_list(out_dir, all_results, all_models, "synthesis")
    return out_dir


def _write_synthesis_summary(out_dir, all_results, all_models, summaries,
                              db_stats, prompt_tokens):
    model_names = [m for _, m in all_models]

    with open(out_dir / "summary.md", "w") as f:
        f.write(f"# Model Comparison — Synthesis\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Models:** {', '.join(model_names)}\n")
        f.write(f"**Corpus:** {len(summaries)} documents, "
                f"~{int(prompt_tokens):,} tokens per prompt\n")
        f.write(f"**Database:** {db_stats.get('documents', 0)} docs, "
                f"{db_stats.get('entities', 0)} entities, "
                f"{db_stats.get('fee_patents', 0)} fee patents\n\n")

        for i, result in enumerate(all_results, 1):
            f.write(f"## Question {i}\n\n")
            f.write(f"> {result['question']}\n\n")

            # Build header
            header = "| Metric |"
            separator = "|--------|"
            for name in model_names:
                short = name.split(":")[0] if ":" in name else name
                header += f" {short} |"
                separator += "--------|"
            f.write(header + "\n" + separator + "\n")

            # Analyze each model's output
            analyses = {}
            for name in model_names:
                output = result["outputs"].get(name, {})
                analyses[name] = analyze_synthesis_output(output)

            def row(label, key, subkey=None):
                line = f"| {label} |"
                for name in model_names:
                    a = analyses.get(name, {})
                    if subkey:
                        v = a.get(key, {}).get(subkey, "—")
                    else:
                        v = a.get(key, "—")
                    if isinstance(v, float):
                        v = f"{v:.1f}"
                    line += f" {v} |"
                return line

            def time_row():
                line = "| Time |"
                for name in model_names:
                    t = result["outputs"].get(name, {}).get("time", 0)
                    line += f" {t:.1f}s |"
                return line

            f.write(time_row() + "\n")
            f.write(row("Word count", "word_count") + "\n")
            f.write(row("Unique [Doc N] citations", "doc_citations") + "\n")
            f.write(row("Dollar amounts cited", "evidence", "dollar_amounts") + "\n")
            f.write(row("Acreage mentions", "evidence", "acreage_mentions") + "\n")
            f.write(row("Specific dates", "evidence", "dates") + "\n")
            f.write(row("Bill/statute refs", "evidence", "bill_numbers") + "\n")
            f.write(row("Has 'Prove' section", "sections", "has_prove") + "\n")
            f.write(row("Has 'Suggest' section", "sections", "has_suggest") + "\n")
            f.write(row("Has 'Gaps' section", "sections", "has_gaps") + "\n")
            f.write("\n")

        f.write("---\n\n")
        f.write("## How to Evaluate\n\n")
        f.write("Read the full outputs side by side. The metrics above are suggestive "
                "but the real test is qualitative:\n\n")
        f.write("1. **Evidence grounding** — Does every claim cite specific documents "
                "with specific facts?\n")
        f.write("2. **Cross-document synthesis** — Does it connect information across "
                "multiple documents, or just summarize?\n")
        f.write("3. **Analytical depth** — Does it distinguish proven vs. suggested "
                "vs. unknown?\n")
        f.write("4. **Accuracy** — Spot-check citations against the archive.\n")
        f.write("5. **Gaps analysis** — Does it identify what's missing, not just "
                "what's there?\n")


# ─────────────────────────────────────────────────
# Extraction comparison
# ─────────────────────────────────────────────────

def run_extraction_comparison(
    local_models: List[str],
    claude_model: str = "claude-sonnet-4-6",
    n_samples: int = 3,
    run_claude_flag: bool = True,
    run_local_flag: bool = True,
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_label = "_".join(m.replace(":", "-").replace("/", "-") for m in local_models)
    out_dir = Path("comparisons") / f"extraction_{timestamp}_{model_label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {n_samples} sample document chunks...")
    samples = get_extraction_samples(n_samples)
    if not samples:
        print("ERROR: No documents with text found.")
        sys.exit(1)

    all_models = []
    if run_claude_flag:
        all_models.append(("claude", claude_model))
    if run_local_flag:
        for m in local_models:
            all_models.append(("local", m))

    all_results = []

    for i, sample in enumerate(samples, 1):
        doc_name = sample.get('display_title') or sample.get('file_name', '')
        chunk = sample['chunk']
        print(f"\n{'='*60}")
        print(f"Document {i}/{len(samples)}: {doc_name}")
        print(f"  Chunk: {len(chunk):,} chars")
        print(f"{'='*60}")

        prompt = build_extraction_prompt(chunk)
        result = {"document": doc_name, "doc_id": sample["id"], "outputs": {}}

        for kind, model in all_models:
            safe_name = model.replace(":", "-").replace("/", "-")
            print(f"\nRunning {model}...")
            if kind == "claude":
                output = run_claude(prompt, model=model, max_tokens=8000)
            else:
                output = run_ollama(prompt, model=model, max_tokens=8000)

            if output.get("error"):
                print(f"  ERROR: {output['error']}")
            else:
                print(f"  Done in {output['time']:.1f}s")
                analysis = analyze_extraction_output(output)
                if analysis["valid_json"]:
                    counts = analysis["counts"]
                    total = sum(counts.values())
                    print(f"  Valid JSON: {total} items extracted "
                          f"({counts.get('entities', 0)} entities, "
                          f"{counts.get('fee_patents', 0)} fee patents, "
                          f"{counts.get('correspondence', 0)} correspondence)")
                else:
                    print(f"  INVALID JSON: {analysis.get('error', 'unknown')}")

            result["outputs"][model] = output

            # Save individual output
            with open(out_dir / f"doc_{i}_{safe_name}.json", "w") as f:
                f.write(output.get("text", output.get("error", "")))

        all_results.append(result)

    # Write summary
    _write_extraction_summary(out_dir, all_results, all_models)
    _print_output_list(out_dir, all_results, all_models, "extraction")
    return out_dir


def _write_extraction_summary(out_dir, all_results, all_models):
    model_names = [m for _, m in all_models]

    with open(out_dir / "summary.md", "w") as f:
        f.write(f"# Model Comparison — Extraction\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Models:** {', '.join(model_names)}\n\n")

        for i, result in enumerate(all_results, 1):
            f.write(f"## Document {i}: {result['document']} (id={result['doc_id']})\n\n")

            # Header
            header = "| Metric |"
            separator = "|--------|"
            for name in model_names:
                short = name.split(":")[0] if ":" in name else name
                header += f" {short} |"
                separator += "--------|"
            f.write(header + "\n" + separator + "\n")

            # Analyze each
            analyses = {}
            for name in model_names:
                output = result["outputs"].get(name, {})
                analyses[name] = analyze_extraction_output(output)

            # Time row
            line = "| Time |"
            for name in model_names:
                t = result["outputs"].get(name, {}).get("time", 0)
                line += f" {t:.1f}s |"
            f.write(line + "\n")

            # Valid JSON
            line = "| Valid JSON |"
            for name in model_names:
                v = analyses.get(name, {}).get("valid_json", False)
                line += f" {'Yes' if v else 'NO'} |"
            f.write(line + "\n")

            # Entity counts
            for key in ["entities", "events", "financial_transactions", "relationships",
                         "fee_patents", "correspondence", "legislative_actions"]:
                label = key.replace("_", " ").title()
                line = f"| {label} |"
                for name in model_names:
                    c = analyses.get(name, {}).get("counts", {}).get(key, "—")
                    line += f" {c} |"
                f.write(line + "\n")

            # Total
            line = "| **Total items** |"
            for name in model_names:
                counts = analyses.get(name, {}).get("counts", {})
                total = sum(counts.values()) if counts else 0
                line += f" **{total}** |"
            f.write(line + "\n\n")

        f.write("---\n\n")
        f.write("## How to Evaluate\n\n")
        f.write("1. **Valid JSON** — Can the output be parsed? This is pass/fail.\n")
        f.write("2. **Completeness** — Open the source document and spot-check: "
                "did the model find the same people, transactions, and dates?\n")
        f.write("3. **v3 types** — Did it extract fee patents, correspondence, and "
                "legislative actions as structured records (not just entities)?\n")
        f.write("4. **Accuracy** — Are the extracted values correct? Check names, "
                "dates, dollar amounts against the source text.\n")
        f.write("5. **Hallucination** — Did it invent entities or events not in "
                "the source text?\n")


# ─────────────────────────────────────────────────
# Common utilities
# ─────────────────────────────────────────────────

def _print_output_list(out_dir, all_results, all_models, mode):
    print(f"\n{'='*60}")
    print(f"Results saved to: {out_dir}/")
    print(f"  - summary.md")
    ext = ".md" if mode == "synthesis" else ".json"
    prefix = "question" if mode == "synthesis" else "doc"
    for i in range(1, len(all_results) + 1):
        for _, model in all_models:
            safe = model.replace(":", "-").replace("/", "-")
            print(f"  - {prefix}_{i}_{safe}{ext}")
    print(f"{'='*60}")


# ─────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compare Claude vs. local models for synthesis and extraction"
    )
    parser.add_argument("--mode", choices=["synthesis", "extraction"],
                        default="synthesis",
                        help="Comparison mode (default: synthesis)")
    parser.add_argument("--local-models", nargs="+",
                        default=["llama3.3:70b"],
                        help="Ollama model names (default: llama3.3:70b). "
                             "Example: --local-models llama3.3:70b qwen2.5:72b gemma3:27b")
    parser.add_argument("--claude-model", default=None,
                        help="Claude model (default: opus for synthesis, sonnet for extraction)")
    parser.add_argument("--question", type=str,
                        help="Run a single custom question (synthesis mode only)")
    parser.add_argument("--n-samples", type=int, default=3,
                        help="Number of document samples (extraction mode only)")
    parser.add_argument("--claude-only", action="store_true",
                        help="Only run Claude (skip local models)")
    parser.add_argument("--local-only", action="store_true",
                        help="Only run local models (skip Claude)")
    parser.add_argument("--list-models", action="store_true",
                        help="List available Ollama models and exit")
    args = parser.parse_args()

    if args.list_models:
        models = list_ollama_models()
        if models:
            print("Available Ollama models:")
            for m in models:
                print(f"  {m}")
        else:
            print("No Ollama models found. Install with: ollama pull <model>")
            print("\nRecommended models for comparison:")
            print("  ollama pull llama3.3:70b    # ~40GB, needs 48GB+ RAM")
            print("  ollama pull qwen2.5:72b     # ~40GB, needs 48GB+ RAM")
            print("  ollama pull gemma3:27b      # ~16GB, needs 24GB+ RAM")
        return

    # Set default Claude model based on mode
    if args.claude_model is None:
        args.claude_model = ("claude-opus-4-6" if args.mode == "synthesis"
                             else "claude-sonnet-4-6")

    run_claude_flag = not args.local_only
    run_local_flag = not args.claude_only

    if run_local_flag and not args.claude_only:
        available = list_ollama_models()
        missing = [m for m in args.local_models if m not in available]
        if missing and available:
            print(f"\nWARNING: These models are not in Ollama: {', '.join(missing)}")
            print(f"Available: {', '.join(available)}")
            print(f"Pull with: ollama pull <model>")
            present = [m for m in args.local_models if m in available]
            if present:
                print(f"\nContinuing with available models: {', '.join(present)}")
                args.local_models = present
            else:
                if run_claude_flag:
                    print("No local models available. Running Claude only.")
                    run_local_flag = False
                else:
                    sys.exit(1)

    if args.mode == "synthesis":
        print("Loading document summaries...")
        summaries = get_all_summaries()
        if not summaries:
            print("ERROR: No document summaries found. Run enrich_summaries.py first.")
            sys.exit(1)
        print(f"  {len(summaries)} documents with summaries")

        db_stats = get_db_stats()
        print(f"  {db_stats.get('entities', 0)} entities, "
              f"{db_stats.get('fee_patents', 0)} fee patents, "
              f"{db_stats.get('correspondence', 0)} correspondence")

        questions = [args.question] if args.question else DEFAULT_QUESTIONS

        run_synthesis_comparison(
            questions=questions,
            summaries=summaries,
            db_stats=db_stats,
            local_models=args.local_models,
            claude_model=args.claude_model,
            run_claude_flag=run_claude_flag,
            run_local_flag=run_local_flag,
        )

    elif args.mode == "extraction":
        run_extraction_comparison(
            local_models=args.local_models,
            claude_model=args.claude_model,
            n_samples=args.n_samples,
            run_claude_flag=run_claude_flag,
            run_local_flag=run_local_flag,
        )


if __name__ == "__main__":
    main()
