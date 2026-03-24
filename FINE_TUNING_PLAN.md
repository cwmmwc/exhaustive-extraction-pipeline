# Fine-Tuning Llama 3.3 70B for Historical Document Extraction

## What is fine-tuning?

Fine-tuning means taking an existing open-source language model and training it further on a specific task, using examples of correct output as the answer key. In our case, we take Llama 3.3 70B (a general-purpose model) and train it on 109 examples of (historical document text, structured extraction JSON) pairs, where Claude's existing extractions serve as the ground truth. The goal is to teach the model what thorough structured extraction looks like — how to populate correspondence fields, identify fee patent details, and capture relationships — so it can produce similar output at a fraction of the API cost.

**What fine-tuning IS:** Teaching the model extraction *format* — the pattern of exhaustive, well-structured JSON output with all fields populated.

**What fine-tuning is NOT:** Teaching the model about Crow history or giving it analytical capability. The synthesis benchmarks showed that open-source models fail at corpus-wide analysis not because they lack domain knowledge, but because they can't do the analytical work of assembling evidence into arguments. That's a fundamental capability gap that fine-tuning won't address. This experiment is strictly about the structured extraction task.

## Status: Experiment Complete — Negative Result

The fine-tuned model **did not meet the 75% threshold**. It extracted 38% of Claude's volume — worse than the untuned base model (48%). This is a clear negative result, but a valuable one: it demonstrates that naive fine-tuning on extraction examples does not teach a smaller model to be more thorough. The result is consistent with the hypothesis that Claude's extraction advantage comes from deeper comprehension of document structure, not from knowing a specific output format.

**Success criterion:** 75%+ of Claude on test documents 798, 811, 695. **Actual result:** 38%.

## Results (March 23, 2026)

| Model | Doc 695 | Doc 798 | Doc 811 | Total | % of Claude | JSON Valid |
|-------|---------|---------|---------|-------|-------------|------------|
| Claude Sonnet | 106 | 78 | 137 | **321** | 100% | 3/3 |
| Llama 3.3 70B (untuned) | 59 | 30 | 59 | **148** | 46% | 3/3 |
| Llama 3.3 70B (few-shot) | — | — | — | **148** | 46% | 3/3 |
| **Llama 3.3 70B (fine-tuned)** | **38** | **43** | **41** | **122** | **38%** | **3/3** |
| Llama 4 Maverick (few-shot) | 27 | 31 | 43 | **101** | 31% | 3/3 |

### Key findings

1. **Fine-tuning reduced extraction volume by 18%** compared to the untuned base model (122 vs 148 items). The only document where it improved was doc 798 (43 vs 30), but docs 695 and 811 both dropped significantly (38 vs 59, 41 vs 59).

2. **Correspondence and events remained the biggest gaps.** On doc 811, the fine-tuned model found 3 correspondence records vs Claude's 22 and 7 events vs Claude's 34. Fine-tuning did not teach the model to find more items — it may have taught it to find fewer.

3. **Training data imbalance was likely a factor.** 59% of training examples had empty v3 fields (correspondence, fee_patents, legislative_actions), teaching the model that "correct output = sparse v3 fields." Additionally, 10 of the richest training examples (9.17%) were truncated at Together AI's 24,576-token sequence limit.

4. **Inference cost is prohibitive.** Fine-tuned models on Together AI require dedicated endpoints ($0.532/min = $31.92/hr). This eliminates the cost advantage over Claude, which was the primary motivation for fine-tuning.

5. **The positive:** Valid JSON 3/3, fast inference (18–22s vs 53–140s for Claude), no hallucinations observed. The model works; it just doesn't extract enough.

### What we spent

| Item | Cost |
|------|------|
| Together AI inference testing (all benchmarks) | ~$0.25 |
| Fine-tuning job (3 epochs, 109 examples, LoRA rank 64) | $12.89 |
| Together AI credits for dedicated endpoint tier | $50.00 |
| Dedicated endpoint runtime (~15 min at $0.532/min) | ~$8.00 |
| **Total** | **~$71** |

### Why it didn't work

The fine-tuning experiment tested whether teaching a model the *format* of thorough extraction would make it *perform* thorough extraction. The answer is no. The gap between Claude and Llama 3.3 is not about output format — it's about the model's ability to comprehend long, OCR-degraded historical documents and identify every entity, event, relationship, and correspondence record within them. That's a capability difference rooted in model scale and training, not something a LoRA adapter can bridge with 109 examples.

This is consistent with what Claude Chat predicted: "The model gets better at populating fields it finds, but still doesn't find the same number of things Claude finds."

### Possible next steps (not recommended unless pursuing as research)

If someone wanted to continue this line of investigation:

1. **Crow-only training set (24 examples, 91% v3-rich)** — removes the imbalance problem. Cost: ~$5 to fine-tune.
2. **Increase sequence length** — the 24K token limit truncated 10% of examples. A platform with longer context training might help.
3. **Larger training set** — 109 examples is small. Literature suggests 500+ for task-specific fine-tuning, but we're limited by the number of documents with non-oversized completions.
4. **Different base model** — Llama 3.3 70B may simply be too small. A 405B model fine-tune would be more expensive but might have more headroom.

None of these are recommended given the dedicated endpoint cost problem, which makes the fine-tuned model more expensive to run than Claude for any practical workload.

## Original Goal

Train a LoRA adapter on Llama 3.3 70B using Claude's extraction output as training data, targeting 75–80% of Claude Sonnet's extraction quality at low marginal cost.

## Training Data

We have a ready-made dataset: Claude's extraction output for 566 documents (386 Crow + 180 Kiowa).

### Data Preparation Steps

1. **Export training pairs from the database:**

```python
# prepare_finetune_data.py
import psycopg2, json

def export_training_pairs(db_name, output_file, limit=None):
    """Export (document_chunk, claude_extraction_json) pairs."""
    conn = psycopg2.connect(dbname=db_name)
    cur = conn.cursor()

    # Get documents with their extracted data
    cur.execute("""
        SELECT d.id, d.display_title,
               SUBSTRING(d.full_text FROM 1 FOR 40000) as chunk
        FROM documents d
        WHERE d.full_text IS NOT NULL
          AND LENGTH(d.full_text) > 5000
        ORDER BY d.id
    """ + (f" LIMIT {limit}" if limit else ""))

    pairs = []
    for doc_id, title, chunk in cur.fetchall():
        # Gather all extracted data for this document
        extraction = gather_extraction(cur, doc_id)
        if extraction and any(len(v) > 0 for v in extraction.values()):
            pairs.append({
                "doc_id": doc_id,
                "title": title,
                "prompt": build_extraction_prompt(chunk),
                "completion": json.dumps(extraction, indent=2),
            })

    with open(output_file, 'w') as f:
        json.dump(pairs, f, indent=2)

    print(f"Exported {len(pairs)} training pairs to {output_file}")
    return pairs


def gather_extraction(cur, doc_id):
    """Reconstruct the extraction JSON from database tables."""
    extraction = {
        "entities": [],
        "events": [],
        "financial_transactions": [],
        "relationships": [],
        "fee_patents": [],
        "correspondence": [],
        "legislative_actions": [],
    }

    # Entities (via mentions table)
    cur.execute("""
        SELECT e.name, e.type, e.context
        FROM entities e
        JOIN mentions m ON e.id = m.entity_id
        WHERE m.document_id = %s
    """, [doc_id])
    for name, etype, context in cur.fetchall():
        extraction["entities"].append({
            "name": name, "type": etype, "context": context or ""
        })

    # Events
    cur.execute("""
        SELECT type, date, location, description
        FROM events WHERE document_id = %s
    """, [doc_id])
    for etype, date, location, desc in cur.fetchall():
        extraction["events"].append({
            "type": etype or "", "date": str(date) if date else "",
            "location": location or "", "description": desc or ""
        })

    # Financial transactions
    cur.execute("""
        SELECT type, amount, payer, payee, date, description
        FROM financial_transactions WHERE document_id = %s
    """, [doc_id])
    for ftype, amount, payer, payee, date, desc in cur.fetchall():
        extraction["financial_transactions"].append({
            "type": ftype or "", "amount": amount or "",
            "payer": payer or "", "payee": payee or "",
            "date": str(date) if date else "", "description": desc or ""
        })

    # Relationships
    cur.execute("""
        SELECT subject, type, object, context
        FROM relationships WHERE document_id = %s
    """, [doc_id])
    for subj, rtype, obj, context in cur.fetchall():
        extraction["relationships"].append({
            "subject": subj or "", "type": rtype or "",
            "object": obj or "", "context": context or ""
        })

    # Fee patents
    cur.execute("""
        SELECT allottee_name, allotment_number, acreage, patent_date,
               patent_number, mechanism, buyer, sale_price, attorney, mortgage
        FROM fee_patents WHERE document_id = %s
    """, [doc_id])
    for row in cur.fetchall():
        extraction["fee_patents"].append({
            "allottee_name": row[0] or "", "allotment_number": row[1] or "",
            "acreage": row[2] or "", "patent_date": str(row[3]) if row[3] else "",
            "patent_number": row[4] or "", "mechanism": row[5] or "",
            "buyer": row[6] or "", "sale_price": row[7] or "",
            "attorney": row[8] or "", "mortgage": row[9] or ""
        })

    # Correspondence
    cur.execute("""
        SELECT sender, sender_title, recipient, recipient_title,
               date, subject, action_requested, outcome
        FROM correspondence WHERE document_id = %s
    """, [doc_id])
    for row in cur.fetchall():
        extraction["correspondence"].append({
            "sender": row[0] or "", "sender_title": row[1] or "",
            "recipient": row[2] or "", "recipient_title": row[3] or "",
            "date": str(row[4]) if row[4] else "", "subject": row[5] or "",
            "action_requested": row[6] or "", "outcome": row[7] or ""
        })

    # Legislative actions
    cur.execute("""
        SELECT bill_number, sponsor, action_type, date,
               vote_count, committee, outcome
        FROM legislative_actions WHERE document_id = %s
    """, [doc_id])
    for row in cur.fetchall():
        extraction["legislative_actions"].append({
            "bill_number": row[0] or "", "sponsor": row[1] or "",
            "action_type": row[2] or "", "date": str(row[3]) if row[3] else "",
            "vote_count": row[4] or "", "committee": row[5] or "",
            "outcome": row[6] or ""
        })

    return extraction
```

2. **Convert to chat format for fine-tuning:**

```python
def convert_to_chat_format(pairs, output_file):
    """Convert to Together AI / OpenAI fine-tuning JSONL format."""
    with open(output_file, 'w') as f:
        for pair in pairs:
            entry = {
                "messages": [
                    {"role": "user", "content": pair["prompt"]},
                    {"role": "assistant", "content": pair["completion"]}
                ]
            }
            f.write(json.dumps(entry) + '\n')
    print(f"Wrote {len(pairs)} examples to {output_file}")
```

3. **Split into train/validation:**

```python
import random

def split_data(pairs, val_ratio=0.1):
    """Split into train and validation sets."""
    random.shuffle(pairs)
    split_point = int(len(pairs) * (1 - val_ratio))
    return pairs[:split_point], pairs[split_point:]
```

### Data Quality Considerations

- **Filter out short documents** (<5,000 chars) — too little context for meaningful extraction
- **Filter out documents with very few extractions** (<5 items total) — may indicate OCR-heavy/unreadable docs
- **Cap document text at 40,000 chars** — matches our extraction chunk size
- **Verify JSON validity** of all training completions before upload
- **Review 10–20 random examples manually** to ensure Claude's extractions are accurate (they become ground truth)

### Known Issue: Training Data Imbalance

The combined training set (109 examples) has a significant imbalance in v3 types (correspondence, fee_patents, legislative_actions):

| Subset | Examples | v3-rich | v3-empty | Correspondence | Fee Patents | Legislative Actions |
|--------|----------|---------|----------|----------------|-------------|-------------------|
| Crow train | 24 | 22 (91%) | 2 (8%) | 123 | 29 | 41 |
| Kiowa train | 85 | 22 (25%) | 63 (74%) | 200 | 37 | 22 |
| **Combined** | **109** | **44 (40%)** | **65 (59%)** | **323** | **66** | **63** |

59% of training examples have empty v3 fields. The model sees "correct output = empty correspondence/fee_patents/legislative_actions" more often than populated ones. This works against the primary goal — teaching the model to find and populate v3 types. The Kiowa documents are mostly affidavits and short records that genuinely don't contain correspondence chains or legislative actions, while the test documents (798, 811, 695) are all Crow bureaucratic records rich in v3 types.

**Run 1 (submitted):** Combined 109 examples as-is — establishes baseline.

**If results underwhelm, try in order:**
1. **Crow-only (24 examples)** — 91% v3-rich, structurally matches test documents
2. **v3-filtered combined (44 examples)** — only examples with at least one v3 type populated
3. **Crow 3x-duplicated + v3-filtered Kiowa** — rebalances toward rich examples while keeping Kiowa diversity

## Fine-Tuning Options

### Option A: Together AI Fine-Tuning API (Recommended to start)

**Pros:** No local hardware needed, managed infrastructure, simple API
**Cons:** Model stays on Together's servers, ongoing inference cost (though cheap)

```bash
# Install Together CLI
pip install together

# Upload training data
together files upload finetune_train.jsonl

# Start fine-tuning job
together fine-tuning create \
  --training-file file-xxxxxxxx \
  --model meta-llama/Llama-3.3-70B-Instruct-Turbo \
  --n-epochs 3 \
  --learning-rate 1e-5 \
  --lora-rank 16 \
  --suffix "crow-extraction-v1"
```

**Estimated cost:** ~$10–20 for training (depends on dataset size and epochs)
**Estimated time:** 1–4 hours

After training, the fine-tuned model appears in your Together AI account and can be called via the same API:

```bash
python3 compare_claude_vs_local_models.py \
  --provider together \
  --local-models your-username/Llama-3.3-70B-Instruct-Turbo-crow-extraction-v1 \
  --mode extraction --doc-ids 798 811 695
```

### Option B: Local Fine-Tuning with Unsloth (For MacBook deployment)

**Pros:** Model runs locally forever, no ongoing cost, full control
**Cons:** Requires more setup, slower training, needs to quantize for MacBook

```bash
# Install Unsloth
pip install unsloth

# Fine-tune with LoRA
python3 finetune_local.py \
  --base-model meta-llama/Llama-3.3-70B-Instruct \
  --data finetune_train.jsonl \
  --output ./models/crow-extraction-v1 \
  --lora-rank 16 \
  --epochs 3 \
  --batch-size 1 \
  --learning-rate 2e-5
```

**Hardware requirements for training:**
- 128GB MacBook: Possible with QLoRA (4-bit quantized base + LoRA adapters), very slow (~12–24 hours for 200 examples)
- Better: Use a cloud GPU (A100 80GB on Lambda Labs ~$1.10/hr, or Together AI's fine-tuning API)

**After training, export to Ollama for local inference:**

```bash
# Merge LoRA weights and quantize
python3 -c "
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained('models/crow-extraction-v1')
model.save_pretrained_gguf('models/crow-extraction-v1-Q4', quantization_method='q4_k_m')
"

# Create Ollama model
cat > Modelfile <<EOF
FROM ./models/crow-extraction-v1-Q4/unsloth.Q4_K_M.gguf
PARAMETER temperature 0.3
PARAMETER num_ctx 40000
SYSTEM You are a historical document extraction system. Extract all structured information as JSON.
EOF

ollama create crow-extraction:v1 -f Modelfile
```

Then test locally:
```bash
python3 compare_claude_vs_local_models.py \
  --local-models crow-extraction:v1 \
  --mode extraction --doc-ids 798 811 695
```

## Recommended Approach

### Phase 1: Prepare data and validate (1–2 hours)

1. Run `prepare_finetune_data.py` against `crow_historical_docs` (386 docs)
2. Filter to ~200 highest-quality examples (documents with >20 extracted items)
3. Manually spot-check 10 random examples
4. Convert to JSONL chat format
5. Split 90/10 train/val

### Phase 2: Fine-tune on Together AI (1 afternoon)

1. Upload training data to Together AI
2. Run fine-tuning job (3 epochs, LoRA rank 16, learning rate 1e-5)
3. Run benchmark against test docs 798, 811, 695
4. Compare: untuned → few-shot → fine-tuned → Claude

### Phase 3: Evaluate and iterate (1 day)

1. If results are promising (>70% of Claude), run on 20 random documents and spot-check
2. Try increasing training data (add Kiowa corpus)
3. Try different hyperparameters (epochs, LoRA rank, learning rate)
4. If results plateau below 70%, the gap may be fundamental to the model size

### Phase 4: Local deployment (optional, 1 day)

1. Export fine-tuned model from Together AI
2. Quantize to Q4_K_M for MacBook deployment
3. Create Ollama model and benchmark locally
4. Compare local quantized vs Together AI hosted (quality may drop with quantization)

## Evaluation Criteria

The fine-tuned model should be evaluated on:

1. **Volume:** Total items extracted vs Claude (target: >80%)
2. **Correspondence completeness:** action_requested and outcome populated with specific content (not "none" or "unknown")
3. **Fee patent field population:** patent_number, patent_date, mechanism, buyer, sale_price all filled when present in source
4. **Relationship richness:** Family ties, transactional connections, political representation — not just employment
5. **Event coverage:** Every dated occurrence in the document captured with YYYY-MM-DD format
6. **JSON reliability:** 100% valid JSON (must match Claude's 3/3)
7. **No hallucination:** No fabricated names, dates, or events not in the source text
8. **OCR handling:** Resolves common OCR errors (Jas.→James, Chas.→Charles) rather than reproducing them

## Cost Estimate

| Step | Cost | Time |
|------|------|------|
| Data preparation | $0 | 1–2 hours |
| Together AI fine-tuning | ~$15 | 1–4 hours (automated) |
| Benchmark runs | ~$0.10 | 30 minutes |
| Iteration (2–3 rounds) | ~$30 | 1 day |
| **Total** | **~$50** | **2–3 days** |

Compare to: Running Claude Sonnet on 5,000 documents at ~$0.75/doc = $3,750.
A fine-tuned model that hits 80% quality saves ~$3,000 on a full corpus run.

## Files to Create

| File | Purpose |
|------|---------|
| `prepare_finetune_data.py` | Export training pairs from database |
| `finetune_train.jsonl` | Training data in chat format |
| `finetune_val.jsonl` | Validation data |
| `finetune_local.py` | Local fine-tuning script (Unsloth) |
| `Modelfile` | Ollama model definition for fine-tuned model |

## Open Questions

1. **How many training examples are enough?** Start with 200, increase if results are promising. Literature suggests 50–500 examples for task-specific fine-tuning with LoRA.
2. **Should we use the few-shot prompt during fine-tuning?** Probably not — the fine-tuned model should learn the extraction pattern from training data, not from prompt examples. Use the base prompt for training.
3. **Will quantization (Q4) degrade extraction quality?** Unknown until tested. The unquantized model on Together AI is the ceiling; local Q4 is the floor. If the gap is >10%, consider Q8 (needs ~70GB of 128GB RAM).
4. **Should we fine-tune Maverick instead?** Probably not — Llama 3.3 70B outperformed Maverick on every metric and is more likely to benefit from fine-tuning (dense architecture vs MoE).
