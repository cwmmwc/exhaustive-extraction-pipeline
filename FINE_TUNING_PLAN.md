# Fine-Tuning Llama 3.3 70B for Historical Document Extraction

## Goal

Train a LoRA adapter on Llama 3.3 70B using Claude's extraction output as training data, targeting 80% of Claude Sonnet's extraction quality at zero marginal API cost.

## Current State (March 2026 benchmarks)

| Model | Total Items (3 docs) | % of Claude | JSON Valid | Per-record quality |
|-------|---------------------|-------------|------------|-------------------|
| Claude Sonnet | ~310 | 100% | 3/3 | Excellent |
| Llama 3.3 70B (untuned) | 171 | 55% | 3/3 | Weak on correspondence fields |
| Llama 3.3 70B (few-shot) | 148 | 48% | 3/3 | Good field quality, low volume |
| Llama 4 Maverick (few-shot) | 101 | 32% | 3/3 | Moderate |

Few-shot prompting improved per-record quality (correspondence fields now populated, relationships captured) but did not close the volume gap. The biggest deficits are in **correspondence chains** (4 vs 20 on Doc 811) and **events** (5 vs 33). Fine-tuning should teach the model to be both thorough AND precise.

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
