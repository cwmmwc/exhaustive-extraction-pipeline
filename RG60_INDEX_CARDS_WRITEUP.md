# Vision Model Extraction of NARA RG 60 DOJ Index Cards

**For:** Loren Moulds, Research Partner  
**From:** Christian McMillen  
**Date:** May 2026  
**Project:** Exhaustive Extraction Pipeline — Indian Land Allotment Research

---

## What the source material is

NARA Record Group 60, Entry A1 96C contains typed index cards produced by the Department of Justice's Lands Division. Each card documents one piece of correspondence about a legal case involving Indian land — who wrote to whom, about what case, on what date. The cards span 1920–1967 and cover tax recovery suits, quiet title actions, fraud cases, allotment disputes, and oil/mineral litigation. The collection is a finding aid for the DOJ's Indian lands litigation archive: each file number (e.g., 90-2-5-49) points to a physical box of original correspondence, motions, and decrees at NARA.

We have 87 scanned PDFs covering approximately 2,300 pages of these cards. The cards are typed on preprinted forms with a consistent structure: header (file number, jurisdiction, date), correspondent line, "Re:" subject line describing the case and action, and footer with division routing and clerk initials.

## Why vision extraction was necessary

Standard OCR text extraction (PyMuPDF) fails on these cards. The column layout, typed formatting, and card-to-card boundaries produce garbled text when linearized. A single page may contain 5–15 cards arranged in columns, and OCR flattens them into interleaved fragments. The information is readable to a human looking at the page image, but not to a pipeline that reads extracted text.

Vision mode solves this by rendering each PDF page as an image and sending it directly to a vision-language model. The model reads the actual page layout — card boundaries, column alignment, typed fields — and produces structured JSON output per card.

## Models tested

Three vision models were benchmarked on 20 pages of 1935 DOJ record slips (Box 487, file 90-2-5):

| Model | Infrastructure | Record Slips | Legal Cases | Persons | Failed Pages | Time/page | Cost |
|-------|---------------|-------------|-------------|---------|-------------|-----------|------|
| **Claude Sonnet 4.6** | Anthropic API | **28** | 20 | **15** | 0/20 | 11s | ~$0.04/page |
| **Qwen2.5-VL-72B** | UVA HPC, 4x A100-80GB, vLLM | **28** | **24** | 8 | 0/20 | 10s | Free (LawData allocation) |
| **Kimi K2.5** | UVA RC GenAI, H200 | 12 | 11 | 7 | **9/20 (45%)** | 41s | Free |

All three used the same custom `--index-cards` extraction prompt (defined as `INDEX_CARD_PROMPT` in `extract_single_pdf.py`).

### The extraction prompt

The prompt is domain-specific and template-aware. Rather than asking the model to "extract information from this image," it describes the exact physical layout of a DOJ record slip and tells the model what each field means, where it appears on the card, and what format to expect.

**Card structure description.** The prompt opens by telling the model it is reading "DOJ record slips — index cards that track correspondence about legal cases involving Indian land, taxes, and allotments." It then describes the four-part card layout:

- **Header:** file number (e.g., 90-2-5-49), jurisdiction/district abbreviation, date
- **Correspondent:** who the letter is to/from, with title (U.S. Atty., First Asst. Secy., etc.)
- **Re: line:** case name and brief description of the action
- **Footer:** division routing (e.g., Lands Div.), processing dates, clerk initials

This matters because the model needs to understand that a single page image contains multiple discrete cards, each with its own boundary, and that the same fields appear in the same positions on every card. Without this structural description, a generic vision prompt might treat the page as one continuous document.

**Three output types.** The prompt specifies a JSON schema with three arrays:

1. **`record_slips`** — one entry per card. 17 fields per slip: `file_number`, `jurisdiction`, `date`, `correspondent`, `correspondent_role` (incoming/outgoing), `case_name`, `case_number`, `allottee_name`, `allottee_number`, `tribe_or_reservation`, `subject` (the action described in the Re: line), `action_type` (filing, acknowledgment, enclosure, request, ruling, settlement, appeal), `enclosures`, `routing_division`, `routing_date`, `clerk_initials`, `processed_date`. This is the atomic unit of extraction — one JSON object per physical card.

2. **`legal_cases`** — one entry per unique case referenced on the page. Fields: `case_name`, `file_number`, `jurisdiction`, `case_type` (tax_recovery, quiet_title, allotment, termination), `allottee_name`, `tribe_or_reservation`, `county`. This is a deduplication layer — if three cards on the same page all reference "U.S. v. Roosevelt County," the model should produce three slips but only one case entry.

3. **`persons`** — one entry per named individual. Fields: `name`, `role` (allottee, attorney, official, clerk), `tribe`, `allottee_number`. The person extraction is what enables prosopographic queries downstream — tracking who appears across which cases and in what capacity.

**Domain-specific instructions.** The prompt includes six specific instructions that encode knowledge about the source material:

- **"Each page may have 1–4 cards."** Prevents the model from treating the whole page as one record.
- **"Read the file number EXACTLY."** File numbers like 90-2-5-49 are hierarchical DOJ classification codes. A misread digit (90-2-549, 90-3-5-49) breaks the case-tracking join. The instruction calls this out explicitly.
- **"Dates are in M-D-YY format. Convert to YYYY-MM-DD."** The cards use abbreviated dates (3-17-36). The model normalizes to ISO format, handling the century inference (36 → 1936).
- **"Many cards reference the same case — extract each card separately even if redundant."** This prevents the model from collapsing multiple slips about the same case into one entry. The redundancy is the research value — each card represents a dated correspondence event in the case chronology.
- **"Allottee names appear in the Re: line."** Tells the model where to look for the allottee, which is typically embedded inside the case description (e.g., "recovery of taxes upon allotment of Jessie Eng") rather than in a labeled field.
- **"If text is illegible, transcribe what you can and mark unclear portions with [?]."** Prefers partial capture over silence.

**Why one prompt for both models.** The same prompt was used for Sonnet, Qwen-VL, and Kimi without modification. This was a deliberate design choice: the prompt describes the document structure and output schema, not the model's capabilities. Any vision-language model that can read a page image and produce JSON should be able to follow these instructions. The differences in extraction quality (Sonnet's person capture vs. Qwen's case mention behavior) emerge from the models' different internal strategies for parsing the page, not from prompt variation.

The prompt is at `extract_single_pdf.py`, lines 142–205, invoked via the `--index-cards` flag.

### How the models differ

**Sonnet and Qwen-VL tie on slips.** Both extract 28 record slips from 20 pages with structurally identical JSON output: file_number, jurisdiction, date, correspondent, case_name, routing, clerk_initials.

**Qwen-VL extracts more legal cases (+20%).** 24 vs Sonnet's 20 on the 20-page test. At scale (66 dense pages), this gap widens to +90% — Qwen-VL produces 523 case entries vs Sonnet's 275. The explanation is a deduplication strategy difference: Qwen-VL creates a separate `legal_case` entry for every mention of a case across cards (a per-mention audit trail), while Sonnet consolidates repeated references into one canonical case entry. Neither is wrong — they serve different research needs.

**Sonnet extracts more persons (+88%).** 15 vs Qwen-VL's 8 on the test. At scale: Sonnet finds 462 persons vs Qwen-VL's 272 (+70%). Sonnet captures secondary mentions — assistant U.S. attorneys, county treasurers, judges, clerks named in routing lines or subject headings. Qwen-VL focuses on case principals and skips most secondary names. For prosopography (tracking who appears where across the litigation network), Sonnet's broader capture is more useful.

**Kimi K2.5 vision fails.** Kimi on RC GenAI returns SSE streaming responses with separate `reasoning` and `content` fields. For vision requests, Kimi puts its analysis into the `reasoning` field as narrative description rather than producing structured JSON in the `content` field. This happens on approximately 45% of pages, consistently timing out at ~51 seconds. Kimi's strength is text comprehension of long narrative documents, not vision extraction from structured card layouts.

### Scale validation (66 dense pages)

The 20-page test used sparse pages (~1.4 slips/page). Dense pages from different boxes (~11 slips/page) showed the same patterns at larger scale:

| Combined across 66 pages, 744 slips | Sonnet | Qwen-VL | Gap |
|------|--------|---------|-----|
| Record slips | 763 | 744 | Tied (Sonnet +2.5%) |
| Legal cases | 275 | **523** | **Qwen +90%** |
| Persons | **462** | 272 | **Sonnet +70%** |
| Failed pages | 0 | 0 | Both 100% reliable |

Speed was identical at scale: ~10 seconds per page for both models.

## Production extraction

Both models were run on the full 87-PDF collection:

- **Sonnet:** completed via Anthropic API. Output at `vision_index_cards_full/`. 80 PDFs produced merged JSON. Cost ~$130.
- **Qwen-VL:** completed on HPC using Loren's vLLM container (`vllm_0.14.1-cu130.sif`, `--tensor-parallel-size 4` on 4x A100-80GB). Server started via `start_qwen_vl_server.slurm`, extraction batch via `run_qwen_vl_full_index_cards.slurm`. Output at `qwen_vl_index_cards_full/`. Cost: zero (LawData GPU allocation).

### Per-extraction totals

| | Sonnet | Qwen-VL |
|---|--------|---------|
| Record slips | 12,969 | 13,887 |
| Legal cases | 4,811 | 9,591 |
| Persons | 6,588 | 3,998 |

## Merging the two extractions

Because each model captures things the other misses, we merged both extractions into a single unified database rather than picking one. The merge follows the same principle as content-based dedup in information retrieval: match at the record level, prefer the richer source when both agree, preserve unique contributions from each.

### Merge logic

**Slip-level matching** on a composite key: `(source_pdf, file_number, date, correspondent)`. When both models found the same slip, Sonnet's row is stored (it has the broader 17-field schema). When only one model found a slip, that model's row is kept with provenance tagged.

**Content-based PDF pairing.** A complication: 6 of the 87 source PDFs share inner filenames across DOJ boxes, which Sonnet's directory naming scheme cannot disambiguate. The pairing logic counts how many slip keys each Qwen sibling shares with Sonnet and picks the highest-overlap match. Overlap ratios were 3–7x higher for the correct pair than for wrong ones in every case.

**Case-level merge.** One canonical row per unique `file_number`, with both `sonnet_case_mention_count` and `qwen_case_mention_count` preserved as separate columns. Qwen's per-mention behavior becomes a useful research variable (correspondence volume per case) without requiring duplicate slip storage.

**Person-level dedup.** Normalized on name; tracks variants, roles, file_numbers, and extraction source.

### Unified database

| Table | Rows | Meaning |
|-------|-----:|---------|
| documents | 87 | One per source PDF |
| **slips** | **17,211** | 33% more than either extraction alone |
| cases | 2,108 | One per unique file_number |
| persons | 4,359 | Deduped on normalized name |
| slip_cases | 17,087 | Many-to-many join |
| slip_persons | 7,032 | Many-to-many join |

**Slip-level provenance:**

| Source | Count | Meaning |
|--------|------:|---------|
| `sonnet+qwen` | 9,645 | Both models agreed; Sonnet's row stored |
| `sonnet-only` | 3,324 | Sonnet found it; Qwen missed it |
| `qwen-only` | 4,242 | Qwen found it; Sonnet missed it |

The 9,645 agreements show the bulk of slips are found identically by both models. The ~7,500 single-model slips are the genuine complement — records you'd lose by picking either extraction alone.

Schema: `schema_unified_index_cards.sql`. Merge loader: `merge_index_cards.py`. Full design doc: `comparisons/UNIFIED_INDEX_CARDS_MERGE.md`.

## What the extracted data reveals

From the unified database:

- **408+ named allottees** whose land was the subject of DOJ litigation
- **291 unique case file numbers** spanning tax recovery, quiet title, fraud, allotment disputes
- **Geographic concentration in Oklahoma** — Osage (322 mentions), Choctaw (157), Cherokee (48), Five Civilized Tribes (105)
- **175 oil/mineral cases** — allottees' land exploited by Continental Oil, Carter Oil, Furman Oil
- **Cases trackable across time** — e.g., U.S. v. Ralph Hughes followed through 18 cards from decree to $42,935.44 disbursement
- **166 dollar amounts** documenting judgments, settlements, and damages

## Key technical lessons

**1. The same model produces different things depending on document type.** Claude Sonnet is the best extractor for narrative text (congressional testimony, correspondence, litigation records — see the v4 three-way comparison in MODEL_COMPARISON_SUMMARY.md §9). Qwen-VL is competitive or superior on structured visual layouts (index cards, tabular ledgers). Model selection should be document-type-aware, not one-size-fits-all.

**2. Two models that disagree in complementary directions are more valuable merged than either one alone.** Sonnet's person capture and Qwen's case audit trail are both correct — they reflect different extraction strategies, not different error rates. The unified database preserves both signals. This is the core design insight: when parallel extractions are different *kinds* of correct, the merge should expose both contributions on a deduped canonical row rather than picking a winner.

**3. Kimi K2.5 is not a viable vision model despite being excellent at text.** Kimi's architecture routes vision analysis into a reasoning trace rather than structured output. This is a model behavior, not a configuration problem — the same prompt that produces clean JSON from Sonnet and Qwen produces narrative description from Kimi. For text extraction (Survey of Conditions hearings, Circular 2464 affidavits), Kimi outperforms on fee patent detection. For vision, it doesn't work.

**4. HPC infrastructure for Qwen-VL.** The production setup uses Loren's `vllm_0.14.1-cu130.sif` container with `--tensor-parallel-size 4` on 4x A100-80GB GPUs. The server runs as a long-lived SLURM job (`start_qwen_vl_server.slurm`) that writes its address to a file; extraction batch jobs read that file and send requests to the server's OpenAI-compatible endpoint. At ~10 seconds per page, the full 2,300-page extraction completes in under 7 hours of GPU time. The two-job pattern (server + worker) is documented in `OPERATIONS.md` under "Qwen-VL server is a separate slurm."

**5. Vision extraction at 200 DPI is sufficient for typed index cards.** No benefit observed from higher resolution. The 5MB per-image API limit for Anthropic's Sonnet occasionally requires DPI reduction for oversized pages; Qwen-VL on HPC has no such limit.

## Relevance to other corpora

The same dual-model vision approach has been applied to two other document types in this project:

- **Fort Berthold fee patent ledger** (Circular 2464, Part 11) — a 14-page tabular ledger where OCR linearization destroyed column alignment. Qwen-VL vision produced the correct reading on every disputed field; the text extraction had pervasive row-integrity errors. The ledger was replaced wholesale with the Qwen vision extraction.

- **Circular 2464 handwriting recovery** — 38 affidavits/questionnaires where Sonnet text extraction missed handwritten names and allotment numbers (signatures, margin annotations). Dual-model Sonnet+Qwen vision recovery is in progress; Sonnet vision captures full v5 structured content while Qwen provides cross-validation on name/allotment fields.

The index card merge pattern (`merge_index_cards.py`) is the direct precedent for the planned Circular 2464 database loader, which will merge three extraction layers (Sonnet text per-allottee, Kimi text per-part, Sonnet vision per-allottee) using the same provenance-preserving architecture.
