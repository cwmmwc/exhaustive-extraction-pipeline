#!/usr/bin/env python3
"""
Compare Claude vs. Local Open-Source Models for Corpus Synthesis

Runs the same research questions through Claude (API) and a local model
(via Ollama) and saves both outputs side by side for human evaluation.

Requirements:
  - Anthropic API key (ANTHROPIC_API_KEY env var)
  - Ollama running locally (ollama serve) with a model pulled
  - PostgreSQL with crow_historical_docs database

Usage:
    # List available Ollama models
    python3 compare_claude_vs_local_models.py --list-models

    # Run comparison with default models
    python3 compare_claude_vs_local_models.py

    # Specify a local model
    python3 compare_claude_vs_local_models.py --local-model llama3.3:70b

    # Run a single specific question
    python3 compare_claude_vs_local_models.py --question "Tell me about fee patents on the Crow Reservation"

    # Skip Claude (only run local model, e.g. if you already have Claude output)
    python3 compare_claude_vs_local_models.py --local-only

    # Skip local (only run Claude)
    python3 compare_claude_vs_local_models.py --claude-only

Output:
    Creates a timestamped directory under comparisons/ with:
      - question_N_claude.md
      - question_N_local.md
      - summary.md  (side-by-side stats)
"""

import anthropic
import psycopg2
import psycopg2.extras
import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


# ─────────────────────────────────────────────────
# Default test questions — designed to test different capabilities
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
    for table, col in [
        ("documents", "documents"), ("entities", "entities"),
        ("events", "events"), ("financial_transactions", "financial_transactions"),
        ("relationships", "relationships"),
    ]:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            stats[col] = cur.fetchone()[0]
        except Exception:
            stats[col] = 0
    for table in ["fee_patents", "correspondence", "legislative_actions"]:
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


def build_prompt(question: str, summaries: List[Dict], db_stats: Dict) -> str:
    corpus_context = build_corpus_context(summaries)
    collections = set(d.get('collection', 'Unknown') for d in summaries)

    return f"""You are a historian analyzing a complete archival collection about Native American land dispossession, federal Indian policy, and Bureau of Indian Affairs records.

You have analytical summaries of ALL {len(summaries)} documents in this collection, spanning {len(collections)} archival collections. Each summary captures the document type, key parties, specific actions, legal mechanisms, and evidentiary value. This is the ENTIRE corpus — you are seeing everything, not a sample.

DATABASE SCOPE: {db_stats.get('documents', 0)} documents, {db_stats.get('entities', 0)} entities, {db_stats.get('events', 0)} events, {db_stats.get('financial_transactions', 0)} transactions, {db_stats.get('relationships', 0)} relationships, {db_stats.get('fee_patents', 0)} fee patents, {db_stats.get('correspondence', 0)} correspondence records, {db_stats.get('legislative_actions', 0)} legislative actions.

RESEARCH QUESTION: {question}

{corpus_context}

SYNTHESIS GUIDELINES:

1. SURFACE PATTERNS across documents. Identify recurring actors, repeated legal mechanisms, and systematic processes that appear across multiple documents and decades. This is corpus-wide synthesis — prioritize cross-document patterns over summarizing individual documents.

2. GROUND EVERYTHING IN EVIDENCE. Every claim must be supported by specific documentary evidence: names, allotment numbers, acreages, dollar amounts, bill numbers, dates, vote counts, patent numbers, legal descriptions. Do not make assertions without citing the specific details from the documents that support them.

3. SHOW CONNECTIONS. Trace which actors appear together across documents. Identify sequences of events that recur. Show how specific mechanisms (fee patenting, private bills, administrative trust-to-fee conversion) operated across time and place, citing the specific cases that demonstrate each pattern.

4. QUANTIFY WHERE POSSIBLE. Aggregate total acreages, dollar amounts, numbers of transactions, vote tallies, and other numerical evidence across the corpus. When exact totals aren't possible, provide ranges or lower bounds based on what the documents contain.

5. Cite specific documents by their [Doc N] reference (where N is the document ID number shown in the summaries above). Use the exact ID numbers. When multiple documents support a claim, list them: [Doc 42, 55, 103]. Every substantive claim needs at least one citation.

6. CONCLUDE WITH THREE SECTIONS:
   - **What the Documents Prove**: claims fully supported by the documentary evidence, with citations.
   - **What the Documents Suggest**: plausible interpretations that the evidence points toward but does not definitively establish.
   - **Gaps in the Record**: what topics, time periods, actors, or questions are poorly represented or unanswerable from this corpus.

Begin your corpus-wide synthesis:"""


# ─────────────────────────────────────────────────
# Claude API
# ─────────────────────────────────────────────────

def run_claude(prompt: str, model: str = "claude-opus-4-6") -> Dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set", "text": "", "time": 0}

    client = anthropic.Anthropic(api_key=api_key)
    start = time.time()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=16000,
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


# ─────────────────────────────────────────────────
# Ollama (local models)
# ─────────────────────────────────────────────────

def list_ollama_models() -> List[str]:
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")[1:]  # skip header
        return [line.split()[0] for line in lines if line.strip()]
    except Exception as e:
        print(f"Error listing Ollama models: {e}")
        return []


def run_ollama(prompt: str, model: str = "llama3.3:70b") -> Dict:
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
                "num_predict": 16000,
                "num_ctx": 131072,  # request max context
            }
        }).encode()

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        # Long timeout — large context + long generation
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
            "error": f"Cannot connect to Ollama at localhost:11434. Is 'ollama serve' running? ({e})",
            "text": "", "time": time.time() - start
        }
    except Exception as e:
        return {"error": str(e), "text": "", "time": time.time() - start}


# ─────────────────────────────────────────────────
# Comparison
# ─────────────────────────────────────────────────

def count_doc_citations(text: str) -> int:
    """Count unique [Doc N] references in output."""
    import re
    refs = re.findall(r'\[Doc\s+(\d+)', text)
    return len(set(refs))


def count_specific_evidence(text: str) -> Dict:
    """Count markers of specific evidence grounding."""
    import re
    return {
        "dollar_amounts": len(re.findall(r'\$[\d,]+(?:\.\d{2})?', text)),
        "acreage_mentions": len(re.findall(r'[\d,]+\s*acres?', text, re.IGNORECASE)),
        "dates": len(re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', text)),
        "bill_numbers": len(re.findall(r'[SH]\.?\s*(?:R\.)?\s*\d+', text)),
        "allotment_numbers": len(re.findall(r'(?:allot(?:ment|tee)?|No\.)\s*#?\s*\d+', text, re.IGNORECASE)),
    }


def analyze_output(result: Dict) -> Dict:
    """Compute comparison metrics for a model's output."""
    text = result.get("text", "")
    if not text:
        return {"word_count": 0, "doc_citations": 0, "evidence": {}}
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


def run_comparison(
    questions: List[str],
    summaries: List[Dict],
    db_stats: Dict,
    local_model: str,
    claude_model: str = "claude-opus-4-6",
    run_claude_flag: bool = True,
    run_local_flag: bool = True,
) -> Path:
    """Run all questions through both models and save results."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("comparisons") / f"{timestamp}_{local_model.replace(':', '-')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt_tokens = None
    all_results = []

    for i, question in enumerate(questions, 1):
        print(f"\n{'='*60}")
        print(f"Question {i}/{len(questions)}:")
        print(f"  {question[:80]}...")
        print(f"{'='*60}")

        prompt = build_prompt(question, summaries, db_stats)

        if prompt_tokens is None:
            prompt_tokens = len(prompt.split()) * 1.33  # rough estimate
            print(f"\nPrompt size: ~{int(prompt_tokens):,} tokens ({len(prompt):,} chars)")

        result = {"question": question, "claude": None, "local": None}

        # Run Claude
        if run_claude_flag:
            print(f"\nRunning Claude ({claude_model})...")
            claude_result = run_claude(prompt, model=claude_model)
            if claude_result.get("error"):
                print(f"  ERROR: {claude_result['error']}")
            else:
                print(f"  Done in {claude_result['time']:.1f}s "
                      f"({claude_result.get('output_tokens', '?')} output tokens)")
            result["claude"] = claude_result

            # Save Claude output
            with open(out_dir / f"question_{i}_claude.md", "w") as f:
                f.write(f"# Question {i} — Claude ({claude_model})\n\n")
                f.write(f"**Question:** {question}\n\n")
                f.write(f"**Time:** {claude_result['time']:.1f}s\n\n")
                if claude_result.get("input_tokens"):
                    f.write(f"**Tokens:** {claude_result['input_tokens']:,} in, "
                            f"{claude_result['output_tokens']:,} out\n\n")
                f.write("---\n\n")
                f.write(claude_result.get("text", claude_result.get("error", "")))

        # Run local model
        if run_local_flag:
            print(f"\nRunning Ollama ({local_model})...")
            print(f"  (This may take a while with ~{int(prompt_tokens):,} tokens of context)")
            local_result = run_ollama(prompt, model=local_model)
            if local_result.get("error"):
                print(f"  ERROR: {local_result['error']}")
            else:
                print(f"  Done in {local_result['time']:.1f}s "
                      f"({local_result.get('eval_count', '?')} tokens generated)")
            result["local"] = local_result

            # Save local output
            with open(out_dir / f"question_{i}_local.md", "w") as f:
                f.write(f"# Question {i} — {local_model}\n\n")
                f.write(f"**Question:** {question}\n\n")
                f.write(f"**Time:** {local_result['time']:.1f}s\n\n")
                if local_result.get("eval_count"):
                    f.write(f"**Tokens generated:** {local_result['eval_count']:,}\n\n")
                f.write("---\n\n")
                f.write(local_result.get("text", local_result.get("error", "")))

        all_results.append(result)

    # Write summary comparison
    with open(out_dir / "summary.md", "w") as f:
        f.write(f"# Model Comparison: Claude ({claude_model}) vs. {local_model}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Corpus:** {len(summaries)} documents, ~{int(prompt_tokens):,} tokens per prompt\n")
        f.write(f"**Database:** {db_stats.get('documents', 0)} docs, "
                f"{db_stats.get('entities', 0)} entities, "
                f"{db_stats.get('fee_patents', 0)} fee patents\n\n")

        for i, result in enumerate(all_results, 1):
            f.write(f"## Question {i}\n\n")
            f.write(f"> {result['question']}\n\n")

            f.write("| Metric | Claude | Local |\n")
            f.write("|--------|--------|-------|\n")

            for label, key in [("Claude", "claude"), ("Local", "local")]:
                pass  # just building the table below

            claude_analysis = analyze_output(result["claude"]) if result.get("claude") else {}
            local_analysis = analyze_output(result["local"]) if result.get("local") else {}

            def val(analysis, key, subkey=None):
                if not analysis:
                    return "—"
                if subkey:
                    return str(analysis.get(key, {}).get(subkey, "—"))
                return str(analysis.get(key, "—"))

            c, l = claude_analysis, local_analysis
            ct = result.get("claude", {}).get("time", 0)
            lt = result.get("local", {}).get("time", 0)

            f.write(f"| Time | {ct:.1f}s | {lt:.1f}s |\n")
            f.write(f"| Word count | {val(c, 'word_count')} | {val(l, 'word_count')} |\n")
            f.write(f"| Unique [Doc N] citations | {val(c, 'doc_citations')} | {val(l, 'doc_citations')} |\n")
            f.write(f"| Dollar amounts cited | {val(c, 'evidence', 'dollar_amounts')} | {val(l, 'evidence', 'dollar_amounts')} |\n")
            f.write(f"| Acreage mentions | {val(c, 'evidence', 'acreage_mentions')} | {val(l, 'evidence', 'acreage_mentions')} |\n")
            f.write(f"| Specific dates | {val(c, 'evidence', 'dates')} | {val(l, 'evidence', 'dates')} |\n")
            f.write(f"| Bill/statute references | {val(c, 'evidence', 'bill_numbers')} | {val(l, 'evidence', 'bill_numbers')} |\n")
            f.write(f"| Has 'Prove' section | {val(c, 'sections', 'has_prove')} | {val(l, 'sections', 'has_prove')} |\n")
            f.write(f"| Has 'Suggest' section | {val(c, 'sections', 'has_suggest')} | {val(l, 'sections', 'has_suggest')} |\n")
            f.write(f"| Has 'Gaps' section | {val(c, 'sections', 'has_gaps')} | {val(l, 'sections', 'has_gaps')} |\n")
            f.write("\n")

        f.write("---\n\n")
        f.write("## How to Evaluate\n\n")
        f.write("Read the full outputs side by side. The metrics above are suggestive but\n")
        f.write("the real test is qualitative:\n\n")
        f.write("1. **Evidence grounding** — Does every claim cite specific documents with "
                "specific facts (names, dates, dollar amounts, allotment numbers)?\n")
        f.write("2. **Cross-document synthesis** — Does it connect information across "
                "multiple documents, or just summarize individual ones?\n")
        f.write("3. **Analytical depth** — Does it distinguish what's proven vs. suggested "
                "vs. unknown? Does it identify patterns?\n")
        f.write("4. **Accuracy** — Do the citations match what the documents actually say? "
                "(Spot-check a few against the archive.)\n")
        f.write("5. **Gaps analysis** — Does it identify what's missing from the record, "
                "not just what's there?\n")

    print(f"\n{'='*60}")
    print(f"Results saved to: {out_dir}/")
    print(f"  - summary.md          (comparison metrics)")
    for i in range(1, len(questions) + 1):
        if run_claude_flag:
            print(f"  - question_{i}_claude.md")
        if run_local_flag:
            print(f"  - question_{i}_local.md")
    print(f"{'='*60}")

    return out_dir


# ─────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compare Claude vs. local models for corpus synthesis"
    )
    parser.add_argument("--local-model", default="llama3.3:70b",
                        help="Ollama model name (default: llama3.3:70b)")
    parser.add_argument("--claude-model", default="claude-opus-4-6",
                        help="Claude model (default: claude-opus-4-6)")
    parser.add_argument("--question", type=str,
                        help="Run a single custom question instead of defaults")
    parser.add_argument("--claude-only", action="store_true",
                        help="Only run Claude (skip local model)")
    parser.add_argument("--local-only", action="store_true",
                        help="Only run local model (skip Claude)")
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
            print("No Ollama models found. Install one with: ollama pull llama3.3:70b")
        return

    # Load data
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

    run_claude_flag = not args.local_only
    run_local_flag = not args.claude_only

    if run_local_flag:
        models = list_ollama_models()
        if args.local_model not in models and models:
            print(f"\nWARNING: '{args.local_model}' not found in Ollama.")
            print(f"Available models: {', '.join(models)}")
            print(f"Pull it with: ollama pull {args.local_model}")
            if not args.claude_only:
                response = input("Continue with Claude only? [y/N] ")
                if response.lower() == 'y':
                    run_local_flag = False
                else:
                    sys.exit(1)

    run_comparison(
        questions=questions,
        summaries=summaries,
        db_stats=db_stats,
        local_model=args.local_model,
        claude_model=args.claude_model,
        run_claude_flag=run_claude_flag,
        run_local_flag=run_local_flag,
    )


if __name__ == "__main__":
    main()
