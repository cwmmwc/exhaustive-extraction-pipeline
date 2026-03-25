# Model Comparison Summary

**Date:** 2026-03-23 (updated 2026-03-25 with Kimi K2.5 results)
**Purpose:** Evaluate whether open-source models can replace Claude for structured extraction and corpus-wide synthesis in a historical document analysis pipeline.

## Models Tested

| Model | Parameters | Architecture | Provider | Context Window |
|-------|-----------|-------------|----------|---------------|
| Claude Opus 4.6 | undisclosed | — | Anthropic API | 200K tokens |
| Claude Sonnet 4.6 | undisclosed | — | Anthropic API | 200K tokens |
| Llama 4 Maverick | 17B × 128 experts (MoE) | Mixture of Experts | Together AI | 1M tokens |
| Llama 4 Scout | 17B × 16 experts (MoE) | Mixture of Experts | Together AI | 512K tokens |
| Llama 3.3 70B | 70B | Dense | Together AI | 128K tokens |
| Kimi K2.5 | undisclosed | Native multimodal agentic | Together AI | 256K tokens |

Claude Opus was used for synthesis; Claude Sonnet for extraction. All open-source models were tested via Together AI's hosted API. Kimi K2.5 (Moonshot AI) was added to testing on 2026-03-25 after the initial Llama experiments.

## Test Corpus

- **368 documents** from the Crow Reservation archival collection
- Documents span 1887–1989: BIA administrative records, congressional hearings, correspondence, fee patent files, litigation records
- OCR-digitized historical documents with variable text quality

---

## 1. Extraction Comparison

Three documents were used across all extraction tests (pinned via `--doc-ids 798 811 695`):

| Doc ID | Title | Chunk Size | Type |
|--------|-------|-----------|------|
| 695 | 1952–1956: BIA Billings Area Office Administrative Records on Land, Irrigation, and Grazing | 40,000 chars | Bureaucratic/administrative |
| 798 | 1949: Murray Papers — Senate Bill S-716, Fee Patent for Crow Allottee George Peters | ~30,000 chars | Legislative/correspondence |
| 811 | 1907–1979: Illegal Patent and Dispossession of Crow Allotment No. 2336 (Frederick Geisdorff Jr.) | 40,000 chars | Litigation/multi-decade |

### Aggregate Extraction Results

| Model | JSON Valid | Total Items | % of Claude | Entities | Events | Financial | Relationships | Fee Patents | Correspondence | Legislative |
|-------|-----------|-------------|-------------|----------|--------|-----------|--------------|-------------|----------------|------------|
| **Claude Sonnet** | 3/3 | **324** | 100% | 133 | 63 | 14 | 61 | 5 | 36 | 12 |
| **Kimi K2.5** | **3/3** | **238** | **73%** | 119 | 34 | 14 | 29 | 5 | 26 | 11 |
| **Llama 3.3 70B (untuned)** | 3/3 | **148** | 46% | 88 | 16 | 8 | 15 | 5 | 9 | 7 |
| **Llama 3.3 70B (few-shot)** | 3/3 | **148** | 46% | — | — | — | — | — | — | — |
| **Llama 3.3 70B (fine-tuned)** | 3/3 | **122** | **38%** | 69 | 18 | 7 | 10 | 4 | 8 | 6 |
| **Llama 4 Maverick** | 2/3 | **80** | 25% | 38 | 11 | 6 | 9 | 2 | 8 | 6 |
| **Llama 4 Scout** | 0/3 | **0** | 0% | — | — | — | — | — | — | — |

**Note:** Claude Sonnet totals vary slightly between runs due to non-deterministic output. The fine-tuned model row represents `cwm6w_eacd/Llama-3.3-70B-Instruct-Reference-extraction-v1-a3211159`, trained on 109 examples from both Crow and Kiowa corpora. Kimi K2.5 (Moonshot AI) tested 2026-03-25.

### Per-Document Breakdown

#### Document 695: BIA Administrative Records

| Model | Valid JSON | Time | Total Items |
|-------|-----------|------|-------------|
| Claude Sonnet | Yes | 84–92s | 97–106 |
| **Kimi K2.5** | **Yes** | **59.8s** | **96** |
| Llama 3.3 70B | Yes | 10.5s | 48 |
| Llama 4 Maverick | No | 13.2s | 0 |
| Llama 4 Scout | No | 0.2s | 0 |

Kimi K2.5 effectively **tied Claude** on this document (96 vs 97). No other open-source model came close; Llama 3.3 70B extracted half as many items. This document contains discrete bureaucratic entries — personnel actions, land management records, irrigation reports — where Kimi's recognition capabilities are at full strength.

#### Document 798: George Peters Fee Patent

| Model | Valid JSON | Time | Total Items |
|-------|-----------|------|-------------|
| Claude Sonnet | Yes | 53–63s | 74–90 |
| **Kimi K2.5** | **Yes** | **169.9s** | **52** |
| Llama 3.3 70B | Yes | 13.1s | 64 |
| Llama 4 Maverick | Yes | 42.8s | 34 |
| Llama 4 Scout | No | 0.2s | 0 |

Kimi's weakest result — and notably, Llama 3.3 70B actually outperforms Kimi here (64 vs 52). This document is a chain of legislative correspondence (Murray → BIA → Interior → Senate committee) where extracting relationships (Kimi: 7 vs Claude: 23) and tracing the causal sequence of events (Kimi: 5 vs Claude: 12) requires comprehending a multi-party narrative, not recognizing discrete records.

#### Document 811: Illegal Patent Dispossession

| Model | Valid JSON | Time | Total Items |
|-------|-----------|------|-------------|
| Claude Sonnet | Yes | 131–152s | 128–137 |
| **Kimi K2.5** | **Yes** | **122.7s** | **90** |
| Llama 3.3 70B | Yes | 16.5s | 59 |
| Llama 4 Maverick | Yes | 49.0s | 46 |
| Llama 4 Scout | No | 0.2s | 0 |

Kimi significantly outperforms Llama (90 vs 59) but still trails Claude on this multi-decade litigation narrative. The gap is widest in correspondence (14 vs 23) — the 14-month bureaucratic chain between Superintendent Asbury, the Commissioner, and the General Land Office — and events (14 vs 34), where each court filing and administrative decision across 72 years is a separate event woven through pages of legal prose.

### Extraction Quality Analysis (Doc 798: George Peters)

Side-by-side comparison on the same document reveals qualitative differences beyond item counts:

**Claude found that other models missed:**
- Secondary actors: George Redfield (intended buyer in 1921), W.P. Marshall (Western Union president), Mills Astin (Chief Clerk), Morris (House report submitter)
- All 10 Senate committee member names with state affiliations
- Exact legal land descriptions (section, township, range, meridian)
- Archival provenance (University of Montana, Mansfield Library, Collection No. 91)
- The 1921 prior sale indication event

**Maverick errors:**
- "Jones E. Murray" instead of "James E. Murray" — a hallucinated name variant
- Fabricated "bill_signed_into_law" event not present in source document
- Correspondence entry with sender listed as "Unknown" when the document clearly identifies Murray
- Multiple "not specified" fields where data is present in the source text

**Llama 3.3 70B** was the strongest open-source performer on Doc 798, extracting 64 items vs Claude's 74 — the closest any model came. Entity counts were nearly equal (35 vs 38). The gap was widest in relationships (6 vs 12) and events (11 vs 12).

### Deep-Dive: 1921 Board of Indian Commissioners Report (CCF 56074-21-312 GS)

A 221-page document containing Board of Indian Commissioners correspondence and field agent reports on the condition of patent-in-fee Indians across Pawnee, Ponca, Otoe, Kaw, and Tonkawa reservations. This is a document the PI knows well and which Claude's full extraction (all 13 chunks) produced 1,369 items that powered significant analytical findings, including the discovery of what we term the "Nez Perce paradox."

#### Single-Chunk Comparison (First 40K Characters)

| Category | Claude Sonnet | Kimi K2.5 | Llama 3.3 70B | Kimi % | Llama % |
|----------|-------------|-----------|---------------|--------|---------|
| Entities | 173 | 164 | 142 | 95% | 82% |
| Events | 18 | 81 | 17 | 450%* | 94% |
| Financial transactions | 10 | 79 | 10 | 790%* | 100% |
| Relationships | 34 | 37 | 20 | 109% | 59% |
| Fee patents | **83** | **87** | **8** | **105%** | **10%** |
| Correspondence | 7 | 9 | 10 | 129% | 143% |
| Legislative actions | 1 | 3 | 6 | 300% | 600% |
| **Total** | **326** | **460** | **213** | **141%** | **65%** |

*Kimi's event and financial transaction counts are inflated — see quality analysis below.

**Kimi K2.5's fee patent result is the headline.** On the same 40K-character chunk where Llama found 8 fee patents (10% of Claude), Kimi found 87 — slightly more than Claude's 83. This is the first open-source model to match Claude on the category that matters most for this research: individual allottee case histories.

**Quality analysis of Kimi's fee patents:** No hallucinated names. All 87 allottees are from the correct tribes (Pawnee, Ponca, Kaw, Tonkawa, Otoe) with internally consistent details. Kimi has one clear analytical advantage: it correctly distinguishes between "application" (for Ponca/Tonkawa fee patents) and "certificate_of_competency" (for Kaw Indians under the Kaw Treaty). Claude labels everything generically as "administrative." Claude's advantage is richer per-record detail — it captures specific acreage notes ("934 acres plus town home retained" for Oliver Thompson) where Kimi defaults to template fills ("homestead and inheritance"). Each model found 5–8 allottees the other missed.

**Quality analysis of Kimi's inflated categories:** Kimi's 81 events (vs Claude's 18) and 79 financial transactions (vs Claude's 10) are overwhelmingly over-extractions. Kimi mechanically creates a separate event and financial_transaction for every allottee whose land was sold — entries like `type=land_sale, date=partial, description="Henry Wy-e-nah-she land sold"` with no real date, no amount, no buyer. These duplicate information already captured in the fee patent records. Only ~18 events and ~10 financial transactions contain actual data (dates, dollar amounts). The inflated counts are a category-confusion artifact, not genuine additional extraction.

**Entity quality:** Both models capture the same core people (Board members, agency staff, allottees) with similar geographic specifics in context fields. Kimi includes "Philadelphia, Pa." and "Mohonk Lake, N.Y." from letterheads — matching Claude's context richness. Both include ages and blood quantum for individual allottees. Claude has a slight edge with a few more contextual details per entry.

**Llama 3.3 70B on this document:** Competent at entity and event recognition (82%, 94% of Claude) but catastrophic on fee patents (8 vs 83). The gap between Llama and Kimi on fee patents — 8 vs 87 — demonstrates that this is not an inherent open-source limitation but a model-specific capability. Kimi can comprehend that a sequence of sentences about an individual allottee constitutes a fee patent case history; Llama cannot.

#### Full-Document Comparison (All Chunks)

Claude's full extraction of this document (13 chunks via the v3 pipeline) is stored in the `full_corpus_docs` database. Kimi K2.5 was run on the full document (15 chunks, 500,812 characters) via `extract_single_pdf.py --chunked`. This enables a direct comparison of total extraction across the entire 221-page document.

| Category | Claude (13 chunks, from DB) | Kimi K2.5 (15 chunks, raw) | Kimi (deduped est.) | Kimi % of Claude |
|----------|---------------------------|---------------------------|-------------------|-----------------|
| Entities | 655 | 1,000 | ~754 | 115% |
| Events | 136 | 193 | ~183 | 135%* |
| Financial transactions | 77 | 135 | ~126 | 164%* |
| Relationships | 251 | 228 | ~223 | 89% |
| Fee patents | **169** | **293** | **~268** | **159%** |
| Correspondence | 79 | 119 | ~116 | 147% |
| Legislative actions | 2 | 40 | ~40 | 2000%* |
| **Total** | **1,369** | **2,008** | **~1,710** | **125%** |

*Events, financial transactions, and legislative actions are likely inflated by the same over-extraction pattern observed in the single-chunk analysis. The true unique counts after quality filtering would be lower.

**Duplication analysis:** The 15 chunks use 5,000-character overlap, which causes entity re-extraction (24.6% entity duplication rate — Board members re-extracted from the masthead in every chunk) but minimal duplication of structured records. Fee patents: 268 unique allottee names out of 293 records. Correspondence: ~3 near-duplicates. Relationships: 5 exact duplicates.

#### The Allottee Count: 268 vs 169

This is the most significant finding of the Kimi K2.5 testing. Claude found 169 fee patent allottees across the full document. Kimi found 268 — **99 additional named individuals** who received fee patents, lost their land, and had their stories recorded in this document.

These are not hallucinations. Spot-checking confirms they are real people from the correct tribes (Pawnee, Ponca, Kaw, Tonkawa, Otoe) with internally consistent details. Claude simply did not extract them. A person Claude skipped entirely — a named individual whose dispossession is documented in the historical record — is a more consequential gap than a person Claude found with richer field detail. You cannot go back to look up someone whose existence you don't know about.

#### The Field Quality Trade-Off

Kimi finds more people but with thinner per-record data:

| Fee Patent Field | Kimi K2.5 unknown/empty rate |
|-----------------|----------------------------|
| allottee_name | 2% (only "Various" placeholders) |
| mechanism | 3% |
| patent_date | 25% |
| acreage | 48% |
| sale_price | 61% |
| buyer | 74% |
| allotment_number | 80% |

However, the sparse fields often reflect the source document, not a model failure. This document is a collection of field agent reports where detail varies widely by allottee. Some individuals get a full paragraph with acreage, sale price, and buyer. Others get a single line: "Harry Stubbs — land sold, money spent, living off friends." Neither model can extract structured data that isn't in the source text. When the source provides detail, Claude populates the structured fields more thoroughly. When the source provides only a name and a disposition, both models produce sparse records — and Kimi finds more of those sparse records than Claude does.

The mechanism field is a genuine Kimi advantage. Kimi correctly uses "application" for Ponca/Tonkawa Indians (who applied for fee patents) and "certificate_of_competency" for Kaw Indians (who received certificates under the Kaw Treaty). Claude labels nearly everything "administrative." This distinction matters for analyzing the different legal mechanisms of dispossession across tribes.

#### Bottom Line: CCF 56074

Kimi K2.5 is the first open-source model to match and exceed Claude on fee patent extraction — the category that constitutes the historical evidence in this corpus. It finds 59% more allottees than Claude, with no hallucinated names, and correctly distinguishes between dispossession mechanisms. Its per-record fields are sparser, and it over-extracts in events and financial transactions (creating empty records that duplicate fee patent data). But for building a comprehensive roster of every individual affected by fee-patent-driven land dispossession in this document, Kimi produces a more complete record than Claude.

#### Analysis Pipeline Comparison: Kimi Extraction → Opus Analysis vs. Claude Extraction → Opus Analysis

Both extractions were loaded into the `full_corpus_docs` database (Claude as Doc 2, Kimi as Doc 5) and run through the Streamlit Deep Read analysis mode, which sends the full document text plus all extracted data to Claude Opus 4.6 for interpretive analysis. The research question was identical: "Tell me about the Kiowa experience with fee patents." This tests whether extraction breadth (Kimi) or extraction depth (Claude) produces better analytical output when the same reasoning model interprets the results.

**Analysis files:**
- Claude extraction → Opus analysis: `~/Desktop/Claude extracted. deep_read_1921 CCF 56074-21-312 GS.pdf.html`
- Kimi extraction → Opus analysis: `~/Desktop/Kimi. deep_read_1921 CCF 56074-21-312 GS.pdf.html`

**What was identical across both analyses:**

Both analyses identify the same core evidence and reach the same historical conclusions:
- V. Stinchecum's testimony as the central Kiowa source (one success in six years; 60-patent breakdown: 20 mortgaged, 16 sold, 24 nominally clear)
- W. D. Brauninger as corroborating witness (three years at Kiowa Agency, "it makes me feel sad")
- The blood quantum / competency paradox ("full-blood Indians who cannot speak a word of English" more prudent than "bright, educated young fellows")
- Stinchecum's 40-acre inalienable homestead proposal
- The agricultural over-capitalization trap (expensive implements for small operations)
- Comparative tables of land loss across reservations
- The same silences: no Kiowa voices, no oil/gas discussion, no Jerome Agreement context, no named speculators

The analytical conclusions are essentially the same — this is the same reasoning model (Opus) reading the same document text. The differences are at the margins, roughly 10–15% of total output.

**Where the Kimi-fed analysis differed:**

1. **More structured mechanistic framing.** The Kimi-fed analysis organizes Kiowa evidence into a six-stage "Mechanism of Kiowa Land Loss" section (Leasing Economy → Competency Commission / Declaration of Policy → Pre-Arranged Sales → Immediate Alienation → Dependency on Relatives → Inherited Land as Final Resource). The Claude-fed analysis presents the same evidence organized by witness/source rather than by mechanism. The mechanistic framing is arguably more useful for building a historical argument.

2. **Broader comparative data.** The Kimi-fed analysis includes 17 jurisdictions in its comparative land-loss table (adding Ponca, Kaw, Tonkawa, Standing Rock, Coeur d'Alene, Spokane, and Colville sub-agencies). The Claude-fed analysis has 11 rows. This is a direct consequence of Kimi's broader entity extraction — with 268 allottees vs. 169, Opus had more named entities to work with and drew on a wider range of the document's geographic scope.

3. **Samuel Charger's indigenous voice.** The Kimi-fed analysis surfaces Samuel Charger's Sioux testimony as a distinct subsection, including his devastating observation about returned Indian soldiers losing their land and the connection to Kiowa WWI veterans targeted for fee patents. The Claude-fed analysis does not feature Charger as prominently. Kimi's broader extraction made this voice more visible to the reasoning model.

4. **Standalone conclusion.** The Kimi-fed analysis includes a formal concluding paragraph that synthesizes all evidence into a single argument about the Kiowa experience as "systematic, rapid, and nearly total land dispossession." The Claude-fed analysis ends with research leads but no formal conclusion.

5. **No unique content in the Claude-fed version.** Everything in the Claude-fed analysis also appears in the Kimi-fed analysis. The reverse is not true — the Kimi-fed analysis contains material absent from the Claude version (the six-stage mechanism, the broader comparative table, the Charger testimony, the conclusion).

**What this means for the pipeline:**

Extraction breadth feeds analysis breadth. When Opus has more extracted data points to work with (more entities, more fee patents, more geographic coverage), it builds slightly more comprehensive structural arguments and surfaces evidence that narrower extraction leaves buried. The differences are not dramatic — both analyses are excellent — but they consistently favor the broader extraction.

This has practical implications for the recommended architecture (Section 5). Running Kimi for broad extraction doesn't just find more allottees for the database; it also produces better analytical output when that data is fed to the reasoning model. The optimal pipeline is: **Kimi extraction (breadth) → Claude Opus analysis (depth)**, combining the strengths of both models at different stages.

As of 2026-03-25, the Streamlit analysis interface (`ai_analysis_interface_v4.py`) includes a model selector that allows choosing Kimi K2.5 as the reasoning/analysis model as well, enabling a full four-way comparison: {Claude extraction, Kimi extraction} × {Claude analysis, Kimi analysis}. Kimi-as-analyst has not yet been formally tested.

---

## 2. Synthesis Comparison

Synthesis used the full corpus (368 documents, ~147,264 tokens per prompt) with three research questions. Claude Opus was the baseline; only Maverick was tested for synthesis (Scout and 3.3 70B were not tested in synthesis mode).

### Questions

1. Tell me about Harlow Pease and his relationship with the Crow generally and with Section 2 of the Crow Act specifically.
2. What were the primary mechanisms of forced fee patent issuance on the Crow Reservation? Who were the key actors and what were the outcomes?
3. How much Crow land was lost and to whom? Quantify the scale of land dispossession using specific acreages, dollar amounts, and transaction counts from the documents.

### Results

| Metric | Claude Opus | Maverick |
|--------|------------|----------|
| **Q1: Word count** | 2,826 | 708 |
| **Q1: Document citations** | 23 | 2 |
| **Q1: Specific dates** | 19 | 1 |
| **Q1: Acreage mentions** | 21 | 1 |
| **Q2: Word count** | 4,024 | 846 |
| **Q2: Document citations** | 72 | 17 |
| **Q2: Dollar amounts** | 18 | 0 |
| **Q2: Specific dates** | 24 | 0 |
| **Q3: Word count** | 4,508 | 857 |
| **Q3: Document citations** | 80 | 13 |
| **Q3: Dollar amounts** | 97 | 2 |
| **Q3: Acreage mentions** | 71 | 4 |
| **Q3: Specific dates** | 13 | 0 |

### Synthesis Quality Assessment

Claude Opus produced deeply evidence-grounded historical analysis — reconstructing Harlow Pease's 35-year biography from documentary fragments across dozens of sources, tracing specific allotment numbers and patent dates through chains of transactions, and assembling named dollar amounts and acreages into a quantified account of dispossession.

Maverick produced competent thematic summaries that correctly identified the major topics (fee patents, acreage limitations, Section 2 violations) but could not populate specifics. Its output followed the requested three-part structure (Prove/Suggest/Gaps) — demonstrating prompt compliance — but the content was generic. Where Claude identified missing records by specific file number, Maverick cited "OCR quality issues" and "gaps exist."

The synthesis gap is wider than extraction. Maverick can recognize what a document is about; Claude can tell you what the document says.

---

## 3. Fine-Tuning Experiment

We fine-tuned Llama 3.3 70B on 109 training examples (Claude's extraction output as ground truth) using Together AI's LoRA fine-tuning API.

### Training Details

| Parameter | Value |
|-----------|-------|
| Base model | meta-llama/Llama-3.3-70B-Instruct-Reference |
| Training method | LoRA (rank 64, alpha 128) |
| Training examples | 109 (24 Crow + 85 Kiowa) |
| Epochs | 3 |
| Training time | 55 minutes |
| Training cost | $12.89 |
| Truncated examples | 10 (9.17%) at 24,576 token limit |

### Result: Negative

The fine-tuned model extracted **fewer** items than the untuned base model on all three test documents except doc 798:

| Document | Claude | Untuned | Fine-tuned | Fine-tuned % of Claude |
|----------|--------|---------|------------|----------------------|
| 695 | 106 | 59 | 38 | 36% |
| 798 | 78 | 30 | 43 | 55% |
| 811 | 137 | 59 | 41 | 30% |
| **Total** | **321** | **148** | **122** | **38%** |

### Why It Didn't Work

1. **Training data imbalance:** 59% of training examples had empty v3 fields (correspondence, fee_patents, legislative_actions), teaching the model that sparse output is correct.
2. **Truncation:** 10% of the richest examples were cut at Together AI's 24K token sequence limit.
3. **Fundamental capability gap:** Claude's extraction advantage comes from deep comprehension of long, OCR-degraded documents — not from knowing a specific output format. A LoRA adapter cannot bridge that gap with 109 examples.

### Infrastructure Finding

Fine-tuned models on Together AI require **dedicated endpoints** at $0.532/min ($31.92/hr). There is no serverless inference for custom fine-tunes. This eliminates the cost advantage over Claude, which was the primary motivation for fine-tuning.

---

## 4. Recognition vs. Comprehension: What Open-Source Models Are Actually Good At

The aggregate numbers obscure a more nuanced picture. Category-level analysis across all tests reveals that open-source models perform very differently depending on the *type* of extraction task — and the distinction maps to a fundamental difference between **recognition** and **comprehension**. However, Kimi K2.5's results (added 2026-03-25) complicate this framework in an important way.

### The Recognition–Comprehension Spectrum

The CCF 56074 deep-dive (Section 1) provides the clearest evidence. Reframing those results by task type:

| Task Type | Llama % of Claude | Kimi % of Claude | Cognitive Demand |
|-----------|-------------------|-----------------|-----------------|
| Entities | 82% | 95% | Recognition — identifying named people, organizations, places |
| Events | 94% | 450%* | Recognition — discrete happenings with dates |
| Financial transactions | 100% | 790%* | Recognition — amounts, payers, payees explicitly stated |
| Correspondence | 143% | 129% | Recognition — letters are bounded units with labeled fields |
| Relationships | 59% | 109% | Comprehension — connecting information across paragraphs |
| Fee patents | **10%** | **105%** | Comprehension — allottee case histories woven through narrative prose |

*Kimi's event and financial transaction counts are inflated by over-extraction (see Section 1 quality analysis).

The original recognition–comprehension framework was built on Llama's results, where the pattern was stark: near-parity on recognition tasks, collapse on comprehension tasks. **Kimi K2.5 breaks that pattern.** It matches Claude on fee patents (87 vs 83 in single-chunk, 268 vs 169 in full-document) — the category we originally classified as requiring deep comprehension. It also matches Claude on relationships (37 vs 34), where Llama captured only 59%.

This means the fee patent gap was not an inherent open-source limitation. It was a Llama-specific limitation. The task of recognizing that a sequence of sentences about an individual allottee constitutes a fee patent case history is something Kimi K2.5 can do and Llama 3.3 70B cannot.

### Where the Framework Still Holds

Despite Kimi's fee patent success, the recognition–comprehension distinction still predicts performance on two document types:

**Legislative correspondence (Doc 798: George Peters).** Kimi extracted 52 items vs Claude's 90. The gap is in relationships (7 vs 23) and events (5 vs 12). Tracing a chain of legislative action — Murray writes to BIA, BIA writes to Interior, Interior recommends amendments, Murray amends the bill — requires maintaining a model of causation across the entire document. Both Kimi and Llama struggle with this; it is genuinely a comprehension task that open-source models have not yet matched.

**Multi-decade litigation (Doc 811: Geisdorff).** Kimi extracted 90 items vs Claude's 137. The correspondence chain (14 vs 23) and event timeline (14 vs 34) spanning 72 years are the gap. Each court filing, administrative decision, and land transfer is a separate event embedded in legal prose. Claude traces the full bureaucratic sequence; Kimi captures roughly two-thirds of it.

**Corpus-wide synthesis.** Not tested for Kimi, but Maverick's synthesis (Section 2) demonstrated the pattern: open-source models can identify what a document is *about* but cannot tell you what it *says*. Cross-document analysis requires holding 147K+ tokens of context and connecting specific details across dozens of sources.

### Revised Understanding: What Each Model Does Best

**Kimi K2.5** excels on documents with **many discrete case records** — field agent reports listing individual allottees and their outcomes, BIA administrative files with personnel and land management entries. It can comprehend that a paragraph about an individual constitutes a structured record (fee patent), and it correctly distinguishes between legal mechanisms (application vs certificate of competency). It finds people that Claude misses. It struggles with long causal chains across pages of legislative correspondence or litigation narrative.

**Llama 3.3 70B** is good at **recognition** in the original sense: identifying named entities, discrete events, financial amounts, and individual letters. It cannot identify that narrative prose describes a fee patent case history. It is the fastest model tested and produces clean JSON reliably.

**Claude** is strongest on **comprehension-intensive documents**: legislative correspondence, multi-decade litigation, and any document where the information must be assembled from scattered references across many pages. It also populates structured fields more thoroughly when the source text provides detail. And it remains the only option for corpus-wide synthesis.

**Gemma 3 12B** excels on **bounded template extraction**: index cards, forms, and short structured documents with predictable fields. It runs locally on consumer hardware.

### Practical Division of Labor

This analysis suggests a hybrid architecture where each model tier handles the tasks it does well:

| Layer | Model | Task | Value |
|-------|-------|------|-------|
| **Triage** | Llama 3.3 70B or Kimi K2.5 | Document classification, prioritization | Route documents to appropriate extraction depth |
| **Index** | Gemma 3 12B (local) | Index card extraction, form parsing | Structured metadata from bounded archival materials |
| **Broad extraction** | Kimi K2.5 | Full v3 extraction on record-heavy documents | Find every allottee, every case history, every correspondence record — maximize name coverage |
| **Deep extraction** | Claude Sonnet | Full v3 extraction on narrative-heavy documents | Relationships, causal chains, rich per-record field population, legislative/litigation documents |
| **Synthesis** | Claude Opus | Cross-document analysis, research questions | Historical interpretation grounded in documentary evidence |

The revised insight: the distinction is not simply recognition vs. comprehension, but **which kind of comprehension**. Kimi can comprehend that a paragraph about an individual constitutes a fee patent case history — and it finds more individuals than Claude. Claude can comprehend that a chain of letters across 14 months constitutes a single bureaucratic process — and it traces those chains more completely. The optimal strategy uses both: Kimi for breadth (finding every person), Claude for depth (tracing every chain).

---

## 5. Conclusions

### Model Ranking for This Pipeline

1. **Claude (Opus for synthesis, Sonnet for extraction)** — irreplaceable for synthesis and for narrative-heavy documents (legislative correspondence, multi-decade litigation). 100% JSON reliability, richer per-record field population, and the ability to trace causal chains across pages of prose. The only viable option for corpus-wide synthesis. However, Claude is no longer the clear winner on all extraction tasks — Kimi K2.5 finds more allottees on record-heavy documents.

2. **Kimi K2.5 (Moonshot AI)** — a breakthrough result among open-source models. 73% of Claude on the 3-document benchmark, but **105–159% of Claude on fee patent extraction** depending on the document. On the 221-page CCF 56074 report, Kimi found 268 unique allottees vs Claude's 169 — 99 additional named individuals whose dispossession is documented in the historical record. 100% JSON reliability. Correctly distinguishes between dispossession mechanisms (application vs certificate of competency). Weakest on legislative correspondence (58% of Claude on Doc 798) and long causal chains. Over-extracts in events and financial transactions (creates empty duplicate records). Per-record fields are sparser than Claude's when the source text provides detail. Best suited for record-heavy documents where maximizing the allottee roster matters most.

3. **Llama 3.3 70B (untuned)** — 46% of Claude overall, 100% JSON reliability. Competitive on entity identification and discrete events, but catastrophic on fee patents (10% of Claude on CCF 56074). The gap between Llama and Kimi on fee patents (8 vs 87 on the same chunk) demonstrates that the fee patent problem is model-specific, not inherent to open-source models. Still useful for entity cataloging and fast document triage. Fine-tuning made it worse, not better.

4. **Gemma 3 12B (local)** — strong on bounded template extraction (NARA index cards). Not tested on long-document extraction but well-suited for structured archival materials with predictable fields. Runs locally on consumer hardware.

5. **Llama 4 Maverick** — disappointing given its size. 67% JSON reliability, ~25% of Claude's extraction depth. Slower than 3.3 70B despite MoE efficiency. Hallucination issues (fabricated names, invented events). Not recommended.

6. **Llama 4 Scout** — completely failed extraction (0/3 valid JSON, 0.2s responses indicating the model refused or errored on all inputs). Not viable for this task.

### Recommended Architecture

The evidence now supports a **complementary approach** where Claude and Kimi K2.5 are used together rather than a simple tiered hierarchy:

**Kimi K2.5 for breadth:** Run Kimi on the full corpus to build the most complete roster of individuals, fee patents, correspondence records, and entities. Kimi finds people that Claude misses — 99 additional allottees on a single document. For building a comprehensive knowledge graph of every person affected by fee-patent-driven land dispossession, Kimi's broader extraction is essential. It also correctly labels dispossession mechanisms, enabling cross-tribal analysis.

**Claude for depth:** Run Claude on narrative-heavy documents (legislative files, litigation records, congressional hearings) where tracing causal chains and populating rich structured fields matters most. Claude is also essential for enriching Kimi's sparse records — filling in allotment numbers, acreages, and sale prices where the source text provides them.

**Claude Opus for synthesis:** No open-source model has been tested or is expected to match Claude's ability to hold 147K+ tokens of context and produce grounded, evidence-rich historical analysis across dozens of documents.

**Gemma for index cards:** Bounded template extraction from structured archival materials continues to be handled locally.

| Layer | Model | Task | Cost |
|-------|-------|------|------|
| **Broad extraction** | Kimi K2.5 | Full corpus — maximize person/record coverage | API or HPC |
| **Deep extraction** | Claude Sonnet | Narrative-heavy documents — relationships, causal chains, field enrichment | ~$0.50–1.00/doc |
| **Index cards** | Gemma 3 12B | NARA index card parsing | Free (local) |
| **Synthesis** | Claude Opus | Corpus-wide research questions | ~$3–5/question |

### Should You Run Models Locally?

**For broad extraction (entity rosters, fee patent identification, correspondence cataloging):** Yes — Kimi K2.5 on HPC or via Together AI. This is the biggest change from our initial findings. An open-source model can now handle the extraction task that previously required Claude, and it finds more individuals than Claude does on record-heavy documents.

**For deep extraction (relationship tracing, legislative chains, field enrichment):** Claude remains essential. Kimi captures 58–66% of Claude's output on narrative-heavy documents, and the missing portion is precisely the causal and relational data that makes those documents analytically valuable.

**For synthesis:** No. No open-source model tested came close to Claude Opus. The synthesis task requires holding 147K tokens of context and cross-referencing specific details across dozens of documents. This is where Claude's advantage is most pronounced and where local models are not a viable substitute.

### Cost Summary

| Experiment | Cost |
|-----------|------|
| Open-source inference testing (Llama 3.3, Maverick, Scout) | ~$0.25 |
| Fine-tuning job (LoRA, 3 epochs, 109 examples) | $12.89 |
| Together AI credits for dedicated endpoint tier | $50.00 |
| Dedicated endpoint runtime (~15 min) | ~$8.00 |
| Kimi K2.5 testing (3-doc benchmark + CCF 56074 full extraction) | ~$2.00 |
| **Total open-source experimentation** | **~$73** |

With Kimi K2.5's results, the cost calculus has shifted. A hybrid Kimi + Claude strategy could process the full 5,000-document corpus with Kimi handling broad extraction (at dramatically lower cost per document than Claude) and Claude targeted at the ~500–1,000 narrative-heavy documents where it has a clear advantage. Running Kimi on UVA HPC would eliminate the API cost entirely for the broad extraction pass.

---

## 6. Raw Data Locations

| Run | Directory |
|-----|-----------|
| Synthesis: Claude Opus vs Maverick | `comparisons/synthesis_20260323_132103_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Synthesis: Maverick only | `comparisons/synthesis_20260323_133836_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Extraction: Maverick (fixed docs) | `comparisons/extraction_20260323_142938_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8/` |
| Extraction: Scout (fixed docs) | `comparisons/extraction_20260323_143734_meta-llama-Llama-4-Scout-17B-16E-Instruct/` |
| Extraction: Llama 3.3 70B (fixed docs) | `comparisons/extraction_20260323_144208_meta-llama-Llama-3.3-70B-Instruct-Turbo/` |
| Extraction: Llama 3.3 70B few-shot | `comparisons/extraction_20260323_155714_meta-llama-Llama-3.3-70B-Instruct-Turbo_tuned/` |
| Extraction: Maverick few-shot | `comparisons/extraction_20260323_161751_meta-llama-Llama-4-Maverick-17B-128E-Instruct-FP8_tuned/` |
| Extraction: Llama 3.3 70B **fine-tuned** | `comparisons/extraction_20260323_182629_cwm6w_eacd-Llama-3.3-70B-Instruct-Reference-extraction-v1-a3211159-eb529166/` |
| Extraction: CCF 56074 deep-dive (Claude vs Llama 3.3) | `comparisons/single_20260324_091852_1921 CCF 56074-21-312 GS/` (Claude) + `comparisons/single_20260324_093343_1921 CCF 56074-21-312 GS/` (Llama) |
| Extraction: Kimi K2.5 (3-doc benchmark) | `comparisons/extraction_20260325_085246_moonshotai-Kimi-K2.5/` |
| Extraction: Kimi K2.5 CCF 56074 single chunk | `comparisons/single_20260325_083929_1921 CCF 56074-21-312 GS/` |
| Extraction: Kimi K2.5 CCF 56074 **full document** (15 chunks) | `comparisons/single_20260325_090708_1921 CCF 56074-21-312 GS_chunked/` |

### Reproducibility

To re-run the extraction comparison with the same documents:

```bash
export TOGETHER_API_KEY=your_key
python3 compare_claude_vs_local_models.py --provider together --local-models llama4-maverick --mode extraction --doc-ids 798 811 695
python3 compare_claude_vs_local_models.py --provider together --local-models llama4-scout --mode extraction --doc-ids 798 811 695
python3 compare_claude_vs_local_models.py --provider together --local-models llama3.3-70b --mode extraction --doc-ids 798 811 695
python3 compare_claude_vs_local_models.py --provider together --local-models kimi-k2.5 --mode extraction --doc-ids 798 811 695
```

To run Kimi K2.5 on a full document in chunked mode:

```bash
python3 extract_single_pdf.py "document.pdf" --together-model kimi-k2.5 --together-only --chunked
```

---

*Comparison and fine-tuning experiment conducted 2026-03-23. Recognition vs. comprehension analysis added 2026-03-24. Kimi K2.5 testing added 2026-03-25 — significantly changes the open-source extraction picture, particularly for fee patent identification. Analysis pipeline comparison (Kimi extraction → Opus analysis vs. Claude extraction → Opus analysis) added 2026-03-25. Model performance may change with future releases or prompt optimization. Fine-tuning was tested and did not improve results — see Section 3. For practical deployment recommendations, see Sections 4 and 5.*
