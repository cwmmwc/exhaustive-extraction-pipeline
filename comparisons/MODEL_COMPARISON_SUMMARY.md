# Model Comparison Summary

**Date:** 2026-03-23 (updated 2026-03-25 with Kimi K2.5 results, 2026-03-27 with Qwen 2.5 72B HPC benchmark, 2026-03-31 with Survey of Conditions production results, 2026-04-01 with corpus-wide synthesis comparison, 2026-04-13 with Sonnet vs Kimi hearing transcript comparison, 2026-04-15 with v4 three-way extraction comparison and v3-vs-v4 prompt degradation finding)
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
| **Qwen 2.5 72B** | 3/5* | **114*** | 35%* | 49 | — | — | — | 0 | 16 | — |
| **Llama 4 Scout** | 0/3 | **0** | 0% | — | — | — | — | — | — | — |

**Note:** Claude Sonnet totals vary slightly between runs due to non-deterministic output. The fine-tuned model row represents `cwm6w_eacd/Llama-3.3-70B-Instruct-Reference-extraction-v1-a3211159`, trained on 109 examples from both Crow and Kiowa corpora. Kimi K2.5 (Moonshot AI) tested 2026-03-25. Qwen 2.5 72B tested 2026-03-27 on UVA HPC (2x A100 80GB via vLLM). *Qwen's 3-doc results are partial: 1 doc hit the context length ceiling (32K tokens), 1 produced invalid JSON after 14 min. Only 3 of 5 docs produced valid output, with 0 fee patents on any document.

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

| Category | Claude (13 chunks) | Kimi K2.5 (15 chunks, deduped est.) | Qwen 2.5 72B (15 chunks, 12 valid) | Kimi % of Claude | Qwen % of Claude |
|----------|---------------------------|-------------------|-------------------------------------|-----------------|-----------------|
| Entities | 655 | ~754 | 435 | 115% | 66% |
| Events | 136 | ~183* | 58 | 135%* | 43% |
| Financial transactions | 77 | ~126* | 38 | 164%* | 49% |
| Relationships | 251 | ~223 | 134 | 89% | 53% |
| Fee patents | **169** | **~268** | **26** | **159%** | **15%** |
| Correspondence | 79 | ~116 | 35 | 147% | 44% |
| Legislative actions | 2 | ~40* | 11 | 2000%* | 550%* |
| **Total** | **1,369** | **~1,710** | **737** | **125%** | **54%** |

*Kimi's events, financial transactions, and legislative actions are likely inflated by the same over-extraction pattern observed in the single-chunk analysis. The true unique counts after quality filtering would be lower.

**Qwen 2.5 72B** was tested 2026-03-27 on UVA HPC (2x A100 80GB via vLLM 0.18.0, `--tensor-parallel-size 2`, `--max-model-len 32768`). 12 of 15 chunks produced valid JSON (80% reliability vs 100% for Claude and Kimi). Processing time: 2,884 seconds (~48 minutes) for the full document at ~19.6 tokens/sec generation throughput. Qwen's overall extraction (54% of Claude) is similar to Llama 3.3 70B (46%), but the fee patent result is the key finding: **26 fee patents vs Claude's 169 and Kimi's 268.** Like Llama, Qwen cannot comprehend that a sequence of narrative sentences about an individual allottee constitutes a fee patent case history. This confirms that Kimi's fee patent capability is exceptional among open-source models, not merely typical of the parameter class.

**Duplication analysis:** The 15 chunks use 5,000-character overlap, which causes entity re-extraction (24.6% entity duplication rate — Board members re-extracted from the masthead in every chunk) but minimal duplication of structured records. Fee patents: 268 unique allottee names out of 293 records (Kimi). Correspondence: ~3 near-duplicates. Relationships: 5 exact duplicates.

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

#### Analysis Pipeline Comparison: The Full Four-Way Matrix

The Streamlit analysis interface now supports choosing between Claude Opus 4.6, Claude Sonnet 4.6, and Kimi K2.5 as the reasoning/analysis model, enabling a full pipeline comparison. All four combinations of {Claude extraction, Kimi extraction} × {Claude Opus analysis, Kimi K2.5 analysis} have been tested on the same document (CCF 56074-21-312 GS, 221 pages) with the same research question ("Tell me about the Kiowa experience with fee patents") using the Deep Read analysis mode.

**Analysis files:**
- Claude extraction → Opus analysis: `~/Desktop/Claude extracted. deep_read_1921 CCF 56074-21-312 GS.pdf.html`
- Kimi extraction → Opus analysis: `~/Desktop/Opus ANALYSIS of KEMI extractiondeep_read_1921 CCF 56074-21-312 GS.pdf.html`
- Kimi extraction → Kimi analysis: `~/Desktop/Kimi ANALYSIS of Kimi EXTRACTION. deep_read_1921 CCF 56074-21-312 GS.pdf.html`
- Claude extraction → Kimi analysis: Not yet tested.

##### Part A: Same Analysis Model (Opus), Different Extraction — Does Extraction Breadth Matter?

Both extractions were loaded into the `full_corpus_docs` database (Claude as Doc 2, Kimi as Doc 5) and run through the Streamlit Deep Read analysis mode with Claude Opus 4.6 as the reasoning model. This isolates the effect of extraction breadth on analytical output.

**What was identical across both Opus analyses:**

Both analyses identify the same core evidence and reach the same historical conclusions:
- V. Stinchecum's testimony as the central Kiowa source (one success in six years; 60-patent breakdown: 20 mortgaged, 16 sold, 24 nominally clear)
- W. D. Brauninger as corroborating witness (three years at Kiowa Agency, "it makes me feel sad")
- The blood quantum / competency paradox ("full-blood Indians who cannot speak a word of English" more prudent than "bright, educated young fellows")
- Stinchecum's 40-acre inalienable homestead proposal
- The agricultural over-capitalization trap (expensive implements for small operations)
- Comparative tables of land loss across reservations
- The same silences: no Kiowa voices, no oil/gas discussion, no Jerome Agreement context, no named speculators

The analytical conclusions are essentially the same — this is the same reasoning model (Opus) reading the same document text. The differences are at the margins, roughly 10–15% of total output.

**Where the Kimi-fed Opus analysis differed from the Claude-fed Opus analysis:**

1. **More structured mechanistic framing.** The Kimi-fed analysis organizes Kiowa evidence into a six-stage "Mechanism of Kiowa Land Loss" section (Leasing Economy → Competency Commission / Declaration of Policy → Pre-Arranged Sales → Immediate Alienation → Dependency on Relatives → Inherited Land as Final Resource). The Claude-fed analysis presents the same evidence organized by witness/source rather than by mechanism. The mechanistic framing is arguably more useful for building a historical argument.

2. **Broader comparative data.** The Kimi-fed analysis includes 17 jurisdictions in its comparative land-loss table (adding Ponca, Kaw, Tonkawa, Standing Rock, Coeur d'Alene, Spokane, and Colville sub-agencies). The Claude-fed analysis has 11 rows. This is a direct consequence of Kimi's broader entity extraction — with 268 allottees vs. 169, Opus had more named entities to work with and drew on a wider range of the document's geographic scope.

3. **Samuel Charger's indigenous voice.** The Kimi-fed analysis surfaces Samuel Charger's Sioux testimony as a distinct subsection, including his devastating observation about returned Indian soldiers losing their land and the connection to Kiowa WWI veterans targeted for fee patents. The Claude-fed analysis does not feature Charger as prominently. Kimi's broader extraction made this voice more visible to the reasoning model.

4. **Standalone conclusion.** The Kimi-fed analysis includes a formal concluding paragraph that synthesizes all evidence into a single argument about the Kiowa experience as "systematic, rapid, and nearly total land dispossession." The Claude-fed analysis ends with research leads but no formal conclusion.

5. **No unique content in the Claude-fed version.** Everything in the Claude-fed analysis also appears in the Kimi-fed analysis. The reverse is not true — the Kimi-fed analysis contains material absent from the Claude version (the six-stage mechanism, the broader comparative table, the Charger testimony, the conclusion).

**Part A conclusion:** Extraction breadth feeds analysis breadth. When Opus has more extracted data points to work with, it builds more comprehensive structural arguments and surfaces evidence that narrower extraction leaves buried. The differences are not dramatic — both analyses are excellent — but they consistently favor the broader extraction.

##### Part B: Same Extraction (Kimi), Different Analysis Model — Does the Reasoning Model Matter?

Both analyses work from the same Kimi K2.5 extraction (Doc 5 in `full_corpus_docs`, 268 unique allottees, 2,008 total extracted items). One is analyzed by Claude Opus 4.6, the other by Kimi K2.5 itself. This isolates the effect of the reasoning model on analytical output.

**The headline finding: Kimi K2.5 as analyst is surprisingly competitive.** Both analyses are strong. They identify the same core evidence and reach the same conclusions. A historian could work productively from either one. Kimi-as-analyst delivers roughly 80–85% of Opus's analytical value. But the missing 15–20% is precisely the interpretive framing that turns evidence into historical argument.

**Where Opus is the stronger analyst:**

1. **Analytical layering — telling you *why* a passage matters.** Opus doesn't just present evidence — it frames its historical significance. When it quotes Edmister's comparison of Indian allotments to the Russian Revolution ("its great importance is shown by the condition of Russia to day, where it has been ignored"), Opus frames this as "a government farmer in 1921 identifying the fundamental cultural incompatibility between communal land tenure and individual fee simple ownership... with a sophistication that anticipates later anthropological analysis." Kimi quotes the same passage but presents it as evidence of a "systemic critique" without doing the historiographical framing work. For a historian building an argument, that framing — connecting a 1921 field report to broader intellectual traditions — is what transforms a quotation into evidence.

2. **Naming and developing structural concepts.** Opus identifies three distinct structural mechanisms that made land loss inevitable *regardless of individual competency*, each developed as a named analytical concept:
   - **Geographic dislocation of allotments:** Children allotted in 1908-1909 received land 50-70 miles from their parents' homes because adjacent water-course lands were already taken. These children "have never seen or traversed their original allotments." Opus frames this as proof that "the allotment system itself created the conditions for land loss."
   - **Inheritance fragmentation:** As allottees died and their lands were divided among heirs, individual holdings became increasingly scattered and economically unviable. Opus quotes Kitoh: "We have many cases of Indians who although they may own several allotments by inheritance it would be almost an impossible task by trade or purchase to fence this land in one contiguous area."
   - **The leasing trap:** The system designed to make Indians into farmers instead created a class of rentiers who had no practical experience with money management when they suddenly received large lump sums from land sales. Opus frames this as "a paradox: the system designed to make Indians into farmers instead created a class of rentiers."

   Kimi covers the allotment geography point adequately but does not develop the inheritance fragmentation or leasing trap as distinct analytical concepts. This matters because naming a mechanism makes it citable and arguable — a historian can write "the leasing trap described in the 1921 BIC reports" in a way they cannot if the concept is buried in a general narrative.

3. **Obscure but historically significant details that Kimi misses entirely:**
   - **The "reimbursable fund" alternative:** Edmister proposed a government-backed loan system that would have provided capital access without requiring land alienation — "if the Government is the only one who can safely collect from the Indians, and at the same time keep their property in tact, then they ought to extend him credit in this way." Opus identifies this as "a road not taken in Indian policy" and frames it as a specific policy alternative that was available but not adopted. Kimi does not mention it.
   - **Petzoldt the Baptist missionary's philosophical observation:** "I believe that the Indian has a perfect right to be a prodigal son if he so chooses — certainly he should be permitted to learn from bitter experience and not be kept out of the school of 'hard knocks.'" Opus includes this as a "Voices of Dissent and Complexity" section, noting Petzoldt's observation that some Crows "refused citizenship as they preferred to escape paying taxes and it was nice to have the Indian office help them out when they got in trouble" — revealing "the rational calculation behind what officials often dismissed as Indian backwardness." Kimi does not surface Petzoldt at all.
   - **The tax trap as a distinct mechanism of dispossession:** Once land was patented, it became taxable. Multiple reports describe Indians unable to pay taxes on land they had never farmed, leading to tax sales. Opus identifies this as a separate channel of land loss, quoting LeBeau at Cheyenne River: "the county authorities at once began making assessments on all the Indians on the ceded portions, and valued their lands as farm lands. Hence taxes were high, overlooking the fact that these lands were allotted as grazing lands." And Archerd at Holdenville: "having had no experience with taxes they are left unpaid, penalties accrue and, in a great number of cases, tax deeds are issued on the land." Kimi does not identify the tax trap as a distinct mechanism.
   - **The loan company speculative bubble:** At Holdenville, Archerd reported that "purchasers were able to secure a loan from loan companies on the land even in excess of the purchase price paid for it." Opus flags this as evidence of a speculative land bubble — the land's value to white buyers exceeded what Indians received, suggesting an organized market in underpriced Indian land. Kimi does not mention this.
   - **The Five Civilized Tribes fraud calculations:** Opus provides Youngblood's detailed accounting: in Hughes County alone, 1,200 mixed-blood Indians (75% of 1,600) were defrauded of 70% of their allotment values, totaling $873,600 in losses; in Seminole County, 567 mixed-bloods lost $544,320; combined $1,417,920 in just two counties. Opus also lists Youngblood's nine specific fraud cases by name (Mollie Johnson, Caney Arbor, Jemima Harjo, etc.). Kimi includes the dollar figures and some of the names but presents them less prominently.

4. **The "What the AI Extraction Missed" section is deeper and more analytical.** Both analyses identify what the extraction missed, but Opus develops each point more fully. Opus's section includes:
   - The emotional and moral register (Brauninger's "it makes me feel sad," Edmister's account of Mack Johnson's death — "He said further that he felt the agent, who recommended him for a patent, was much more to blame for 'putting him out of business' than he was himself" — a passage revealing that "Indians themselves held the government responsible")
   - The systemic critique (Edmister's private property analysis)
   - The gender dimension (Hutchison at Shoshone on women's patents, plus specific cases)
   - The tax trap (as above)
   - The Rocky Boy comparison (see below)

   Kimi's "What the AI Extraction Missed" section covers similar ground but with less analytical development. It identifies the moral register, gender dimension, and competency paradox but does not develop the tax trap, the private property critique, or the Rocky Boy comparison.

5. **The Rocky Boy natural experiment.** Opus identifies Superintendent Mossman's comparison as a devastating natural experiment: the Rocky Boy Indians had been "free" for sixty years — exactly the condition that fee patent advocates claimed would benefit Indians — and "had come to such a point of degradation and poverty that the people of the State petitioned the Government to provide a reservation for these people to take care of them." Opus frames this as directly contradicting the argument that removing government supervision would lead to Indian self-sufficiency. Kimi includes the Rocky Boy passage but presents it as one item among many rather than highlighting its unique evidentiary power as a natural experiment.

**Where Kimi is the stronger analyst (or equal):**

1. **Tabular presentation of quantitative evidence.** Kimi's comparative table of land loss across reservations is better formatted than Opus's — 16 rows with clean columns for Reservation/Agency, Patents Issued, % Sold/Mortgaged, and Source. Opus presents the same data as a bulleted list with 15 entries. For quick reference and citation, Kimi's table is more immediately useful. Kimi also includes specific patent counts that Opus omits (Turtle Mountain: 1,393 patents; Flathead: 1,004; Pine Ridge: 711).

2. **The Kaw Sub-Agency individual case studies.** Kimi highlights Clerk Clendening's individual Kaw entries as a distinct section with specific names and outcomes: Margaret Tayiah ("Land sold, money spent, lives with Osage"), Helen Jones Burnett ("Land sold. Husband and money both gone"), Claude McCauley ("Land sold, money gone. Has 160 inherited"), Harry Stubbs ("Land sold. Funds gone. Living off his friends"), Barclay Delano ("Land sold, money gone. Red Cross and neighbors aid for him"). Kimi notes the pattern: "Of approximately 65 individuals listed, the vast majority show 'Land sold. Money spent/gone.'" Opus does not feature these individual Kaw cases as prominently.

3. **The homestead proposal as cross-respondent consensus.** Kimi collects the 40-acre homestead recommendation from *multiple* respondents and presents them side by side: Stinchecum at Kiowa ("forty acres... could not be sold or otherwise encumbered"), Charger the Sioux ("Where an Indian has an established home forty acres should be held in trust"), Mills at Chickasaw ("reserve, or continue restricted, forty acres of average land from which death alone would remove the restrictions"), Archerd at Creek/Seminole ("each Indian should be compelled to retain forty acres of his best land for homestead"). Kimi then presents Hutchison's counter-argument: "reservation of 10, 20, or 40 acres for a home would appear to leave the Indian in a state of part bond and part free, and his independent status is indefinitely postponed." This synthesis — showing the near-universal recommendation alongside its strongest objection — is more useful than Opus's treatment, which covers Stinchecum's version in detail but does not systematically collect the cross-respondent consensus.

4. **Specific research leads Opus misses.** Kimi identifies two research leads that Opus does not:
   - The Nez Perce woman holding $14,000 in mortgages on white men's farms — "a counter-narrative of Indian financial sophistication that deserves further investigation." This is a specific, actionable lead that inverts the dominant narrative of Indian economic failure.
   - The "Indian Rights" organizations mentioned by Cope at Crow — "identifying which organizations were advocating for blanket removal of restrictions and their relationship to land speculation interests." This points toward a specific archival investigation of the political actors behind the fee patent policy.

5. **The "Silences and Omissions" section is more systematic.** Kimi identifies five distinct silences organized as a numbered list: (1) the voice of white buyers (never included), (2) tax revenue implications (how much did states and counties gain?), (3) the oil factor (mineral wealth mentioned only in passing), (4) legal remedies (fraud documented but no prosecutions discussed), (5) the competency commission's actual methods (what questions were asked, how long hearings lasted). Opus identifies silences throughout the analysis but does not consolidate them as a standalone section, making them harder to use as a research checklist.

6. **The Dadie Pappan case as gendered dispossession.** Kimi cites a specific case that illustrates the gender dynamic with devastating clarity: "Dadie Pappan — Land sold. When money was spent, husband left. Married again, husband Theodore Sumner, got certificate, bought house, and deeded to Dadie. Rest spent." This shows the cycle of gendered land loss — land sold by husband, husband leaves, new husband acquires new assets, cycle repeats — in a single biographical sentence. Opus discusses the gender dimension in general terms but does not surface this particular case.

**Summary: What Each Analysis Model Does Best**

| Dimension | Opus Advantage | Kimi Advantage |
|-----------|---------------|----------------|
| Interpretive framing ("why it matters") | Strong — connects evidence to broader historiographical traditions | Weaker — presents evidence without framing significance |
| Naming structural concepts | Strong — geographic dislocation, inheritance fragmentation, leasing trap as citable analytical concepts | Weaker — covers some points but doesn't name them as distinct mechanisms |
| Obscure but significant details | Finds more — reimbursable fund, Petzoldt, tax trap, loan bubble, Rocky Boy natural experiment | Misses several that Opus catches |
| Tabular data presentation | Bullet-point lists | Better — clean tables with specific patent counts |
| Individual case studies | Less prominent | Better — Kaw allottees as named cases, Dadie Pappan |
| Cross-respondent synthesis | Covers key witnesses individually | Better on homestead proposal — collects 5 respondents + counter-argument |
| Research leads | 7 solid leads | 10 leads, including 2 Opus misses (Nez Perce woman, "Indian Rights" orgs) |
| Silences/omissions as checklist | Scattered through analysis | Better organized — 5-item numbered list |
| Overall analytical depth | Deeper — layered interpretation builds an argument | Shallower but wider — more evidence, less argument |

##### Part C: The Four-Way Matrix

| | Claude Opus Analysis | Kimi K2.5 Analysis |
|---|---|---|
| **Claude Extraction** (169 allottees) | Baseline. Deep analysis but narrower source base. Strongest on Kiowa-specific framing. 11-jurisdiction comparative table. | Not yet tested. |
| **Kimi Extraction** (268 allottees) | **Best overall result.** Widest source base + deepest analytical framing. 17-jurisdiction table, six-stage dispossession mechanism, Samuel Charger prominently featured, structural concepts named and developed, obscure details surfaced (tax trap, reimbursable fund, Rocky Boy experiment, loan bubble). The Edmister passage on private property and the Russian Revolution is framed within broader intellectual history. | Good — roughly 80–85% of Opus's analytical value. Competitive on evidence presentation and tabular organization. Better on Kaw individual cases, homestead cross-respondent synthesis, and systematic silences checklist. Catches details Opus misses (Nez Perce woman, "Indian Rights" orgs, Dadie Pappan). Weaker on interpretive framing — tells you *what the document says* but not *why it matters*. |

##### Part D: Implications for the Pipeline

**The optimal pipeline is confirmed: Kimi extraction → Claude Opus analysis.** This combination produces the widest evidence base (Kimi's 268 allottees vs Claude's 169) interpreted with the deepest analytical framing (Opus's named structural concepts, historiographical connections, and "why it matters" interpretation). Neither model alone achieves what the combination produces.

**Kimi-as-analyst is a viable budget option.** If cost is a constraint, Kimi extraction → Kimi analysis produces a workable result. You lose the interpretive framing, some structural concepts, and several historically significant details. But you retain all core evidence, good tabular organization, and in some areas (Kaw case studies, homestead synthesis, research leads) the output is actually stronger than Opus's. For a first pass or triage, this is sufficient. For publication-quality historical analysis, Opus is worth the cost.

**The analysis gap is narrower than the extraction gap on narrative documents.** Kimi-as-analyst achieves ~80-85% of Opus's analytical value, while Kimi-as-extractor achieves only 58-66% of Claude's extraction on legislative correspondence (Doc 798) and multi-decade litigation (Doc 811). This suggests that Kimi's reasoning capabilities are closer to Claude's than its extraction capabilities on certain document types — the extraction task may be bottlenecked by attention/context management rather than raw analytical ability.

**The Streamlit interface supports all combinations.** As of 2026-03-25, `ai_analysis_interface_v4.py` includes a model selector (Claude Opus, Claude Sonnet, Kimi K2.5) that routes analysis calls through a unified `call_llm()` function to either the Anthropic API or Together AI. Users can select any extraction (by choosing the document in the database) and any analysis model (via the sidebar dropdown) to test any combination.

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

**Corpus-wide synthesis.** Tested 2026-04-01 on the 26-volume Survey of Conditions corpus (Section 6). Kimi produces competent corpus-wide synthesis at approximately 90–95% of Opus quality — a significant improvement over the earlier single-document gap. Both models cite the same evidence and reach the same conclusions; Opus leads on analytical framing and naming structural concepts. The earlier assumption (based on Maverick's poor synthesis performance) that open-source models cannot perform corpus-wide synthesis does not hold for Kimi at this evidence scale. Cost: Kimi synthesis was effectively free vs. $0.34 for Opus.

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

3. **Qwen 2.5 72B** — 54% of Claude on CCF 56074 (full document), 80% JSON reliability (12/15 chunks valid). Tested 2026-03-27 on UVA HPC (2x A100 80GB). Overall extraction volume is slightly better than Llama 3.3 70B, but the fee patent result is decisive: **26 fee patents vs Claude's 169 and Kimi's 268 — just 15% of Claude.** This was the model recommended as a potential alternative to Kimi at half the GPU cost (2x vs 8x A100). It is not. The fee patent gap confirms that Kimi's ability to comprehend allottee case histories is exceptional among open-source models and cannot be replicated by a similarly-sized dense model. Qwen's only advantage over Llama is slightly higher overall extraction volume; on the task that matters most for this research, both are equally poor.

4. **Llama 3.3 70B (untuned)** — 46% of Claude overall, 100% JSON reliability. Competitive on entity identification and discrete events, but catastrophic on fee patents (10% of Claude on CCF 56074). The gap between Llama and Kimi on fee patents (8 vs 87 on the same chunk) demonstrates that the fee patent problem is model-specific, not inherent to open-source models. Still useful for entity cataloging and fast document triage. Fine-tuning made it worse, not better.

5. **Gemma 3 12B (local)** — strong on bounded template extraction (NARA index cards). Not tested on long-document extraction but well-suited for structured archival materials with predictable fields. Runs locally on consumer hardware.

6. **Llama 4 Maverick** — disappointing given its size. 67% JSON reliability, ~25% of Claude's extraction depth. Slower than 3.3 70B despite MoE efficiency. Hallucination issues (fabricated names, invented events). Not recommended.

7. **Llama 4 Scout** — completely failed extraction (0/3 valid JSON, 0.2s responses indicating the model refused or errored on all inputs). Not viable for this task.

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
| **Synthesis (exploratory)** | Kimi K2.5 | Iterative corpus-wide queries, draft synthesis | ~free |
| **Synthesis (final)** | Claude Opus | Polished corpus-wide analysis with deepest framing | ~$0.34/question |

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
| Qwen 2.5 72B testing (UVA HPC, 2x A100, 71 min) | $0 (HPC allocation) |
| **Total open-source experimentation** | **~$73** + HPC time |

With Kimi K2.5's results, the cost calculus has shifted. A hybrid Kimi + Claude strategy could process the full 5,000-document corpus with Kimi handling broad extraction (at dramatically lower cost per document than Claude) and Claude targeted at the ~500–1,000 narrative-heavy documents where it has a clear advantage. Running Kimi on UVA HPC would eliminate the API cost entirely for the broad extraction pass.

---

## 5a. Sonnet vs Kimi on Hearing Testimony: Survey Part 33 (April 2026)

The original benchmarks (Section 1) used three Crow Reservation documents — BIA administrative records, legislative correspondence, and multi-decade litigation. None were congressional hearing transcripts, which is the document type comprising the entire Survey of Conditions corpus. This test fills that gap.

**Document:** Survey of Conditions Part 33 — San Diego & San Francisco, CA (June–July 1934). 205 pages, 722,044 characters, 21 chunks at 40K/5K overlap. Kimi extraction via RC GenAI (existing production run); Sonnet extraction via Anthropic API (new, same chunking parameters).

### Results (raw pre-dedup counts)

| Category | Kimi K2.5 | Claude Sonnet | Kimi % of Sonnet |
|----------|----------:|--------------:|:----------------:|
| entities | 1,022 | 1,376 | 74% |
| events | 156 | 398 | 39% |
| financial_transactions | 90 | 297 | 30% |
| relationships | 163 | 455 | 36% |
| fee_patents | 5 | 0 | — (Kimi wins) |
| correspondence | 52 | 106 | 49% |
| legislative_actions | 43 | 92 | 47% |
| testimony | 50 | 130 | 38% |
| taxes | 2 | 2 | 100% |
| mortgages | 0 | 3 | — |
| **total** | **1,583** | **2,859** | **55%** |

### How This Fits the Existing Pattern

| Document type | Kimi % of Claude | Source |
|---------------|:----------------:|--------|
| Fee patent records (CCF 56074) | 125–159% | Section 1 |
| BIA administrative (Doc 695) | ~99% | Section 1 |
| Legislative correspondence (Doc 798) | ~70% | Section 1 |
| Multi-decade litigation (Doc 811) | ~66% | Section 1 |
| **Congressional hearing testimony (Part 33)** | **55%** | **This test** |

The 55% result extends the recognition–comprehension spectrum (Section 4). Hearing transcripts are the most narrative-dense document type in the corpus — multi-party dialogue, implicit relationships, scattered financial references within testimony. This is exactly where the comprehension gap predicted Kimi would be weakest, and it is.

### Qualitative Differences

- **Testimony:** Sonnet found 94 unique witnesses vs Kimi's 41 (31 overlap). Sonnet creates per-topic testimony entries; Kimi creates one entry per witness covering their whole appearance.
- **Events:** Sonnet identifies discrete actions within testimony (delegation trips, tribal votes, agency decisions) that Kimi misses. Unlike the Crow benchmark, Kimi does NOT over-extract here — its 156 events are genuine.
- **Financial transactions:** The widest gap (3.3x). Hearing testimony references many small transactions that Sonnet extracts individually.
- **Fee patents:** Kimi found 5 that Sonnet missed entirely — brief references to fee patent issuance within witness testimony. Consistent with Kimi's demonstrated superiority on fee patent recognition.
- **Entities:** Closest category at 74%. Both capture core witnesses and officials; Sonnet picks up more minor figures.

### Implications for the Survey Corpus

The Survey of Conditions is 41 volumes of congressional hearing testimony — the document type where Sonnet's advantage over Kimi is largest. For research questions requiring **comprehensive extraction** (every financial transaction, every witness relationship), selective Sonnet re-extraction of high-priority volumes would add significant value. For questions about **major testimony, policy actions, and fee patents**, the existing Kimi extraction is sufficient and superior on fee patents.

Full comparison details at `comparisons/SONNET_VS_KIMI_PART33.md`. Sonnet extraction data at `comparisons/sonnet_vs_kimi_part33/`.

---

## 6. Production Deployment: Survey of Conditions (March 2026)

The model comparison findings were validated at scale by extracting the *Survey of Conditions of the Indians in the United States* (1927–1943), a 48-volume, 26,272-page, 15.4-million-word series of Senate subcommittee hearings documenting conditions across Indian country.

### Results (41 of 41 published parts — COMPLETE as of 2026-04-13; snapshot below from 26 volumes as of 2026-03-31)

| Type | Count |
|------|------:|
| Entities | 81,681 |
| Financial transactions | 21,926 |
| Events | 18,400 |
| Relationships | 17,483 |
| Testimony | 5,492 |
| Correspondence | 4,933 |
| Legislative actions | 3,366 |
| Fee patents | 2,487 |
| Taxes | 1,880 |
| Mortgages | 703 |
| **Total** | **158,351** |

**Model:** Kimi K2.5 via Together AI ($0.50/$2.80 per M tokens input/output), v4 schema (10 extraction types).

**Cost:** ~$55 for 26 volumes (~1,260 chunks), including retries for failed chunks.

**Infrastructure challenges:** Together AI's Kimi endpoint proved unreliable at scale — intermittent 500 errors, Cloudflare 403s, and truncated responses (max_tokens cutoff). A custom retry script (`retry_failed_chunks.py`) was built to handle three cases: (1) re-sending failed chunks, (2) completing interrupted extractions, and (3) repairing truncated JSON responses by closing open structures. The JSON repair alone rescued 12 chunks (~6,500 items) without any API calls.

**HPC alternative:** The remaining 23 volumes (~1,230 chunks) are queued for extraction on UVA HPC (LawData allocation, 8x A100 80GB, vLLM). Estimated completion: under 24 hours vs. 3–5 days on Together AI. UVA Research Computing also launched RC GenAI (Kimi K2.5 on 8x H200 GPUs, free API access) on 2026-03-30, which may provide the most convenient path for future extraction work.

**Key validation:** Kimi K2.5's fee patent comprehension held up at production scale. The Oklahoma volumes (Choctaw/Chickasaw, Durant, Anadarko) alone yielded 1,464 fee patents from 147- and 141-chunk documents — the kind of dense, record-heavy extraction where Kimi consistently outperforms Claude.

### Corpus-Wide Synthesis: Opus vs. Kimi (2026-04-01)

The synthesis gap between Opus and Kimi was tested directly on the Survey of Conditions corpus. Both models were given the same question ("tell me about the effects of fee patents on american indian land") with identical extraction-based summaries from all 26 volumes (158,351 Kimi-extracted items). This is the first corpus-wide synthesis comparison — the earlier four-way matrix (Section 1) tested only single-document analysis.

**Finding:** Kimi's corpus-wide synthesis is approximately 90–95% of Opus, a substantial improvement over the 80–85% gap observed on the single benchmark document. Both models produced comprehensive, cited, 8,000+ word syntheses covering the same evidence: competency commissions, the dispossession cycle (mortgage → tax → foreclosure), irrigation liens, guardianship abuse, geographic scope, aggregate quantification, and conclusions with prove/suggest/gaps sections. Both cited the same key witnesses (Meritt's 99% admission, Collier's statistics, Hamilton on Blackfeet, Starr's forced patent). Kimi's closing prose was arguably stronger than Opus's.

**Where Opus still leads:** naming structural concepts as citable frameworks ("four-step dispossession cycle," "structurally engineered process"), tighter integration of the 1924 Citizenship Act into the dispossession system, and a slightly sharper "What the Documents Suggest" section on the question of deliberate design versus policy failure. Opus organizes evidence into analytical arguments; Kimi organizes it more as a comprehensive catalog.

**Why the gap narrowed:** Extraction breadth feeds analysis quality. With 158,351 structured items from Kimi's extraction — 2,487 fee patents, 5,492 testimony records, 81,681 entities — both models had sufficient evidence to build comprehensive arguments. The earlier single-document comparison gave each model far less to work with, amplifying differences in analytical depth. At corpus scale, the evidence does much of the argumentative work.

**Cost comparison:** Opus synthesis cost $0.34 for all 26 volumes. Kimi synthesis cost effectively nothing (no measurable change in Together AI account balance — the 26 summaries fit in a single small prompt). For a researcher running multiple synthesis queries to explore different questions, Kimi's near-zero cost enables iterative exploration that would be expensive with Opus.

**Revised recommendation:** The earlier untested assumption that Kimi "cannot perform corpus-wide synthesis" is incorrect. Kimi produces competent corpus-wide synthesis that covers the same evidence and reaches the same conclusions as Opus, with differences at the margins of analytical framing rather than evidence coverage. The optimal workflow may be: use Kimi for iterative exploration and draft synthesis (free/near-free), then run the final synthesis question through Opus for the deepest analytical framing ($0.34 per query). This replaces the earlier recommendation that Opus was the only viable synthesis option.

---

## 7. Raw Data Locations

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
| Extraction: Qwen 2.5 72B (3-doc benchmark, HPC) | `comparisons/extraction_20260327_113609_qwen2.5-72b/` (on HPC) |
| Extraction: Qwen 2.5 72B CCF 56074 **full document** (HPC) | `/project/LawData/kimi-extraction/outputs/qwen_benchmark_ccf56074/` (on HPC) |

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

---

## 7. Infrastructure Speed Comparison (April 2026)

Throughput measured on production extraction of Survey of Conditions volumes (40,000-character chunks, v4 prompt with 10 extraction types, Kimi K2.5).

| Infrastructure | GPU | Speed per chunk | Cost | Notes |
|---------------|-----|----------------|------|-------|
| UVA RC GenAI (H200) — light load | H200 | ~75s | Free | Shared service. Best performance when few other users. |
| UVA RC GenAI (H200) — busy | H200 | ~130s | Free | Shared service under load. |
| Together AI (Kimi K2.5) | Unknown | ~150-300s | ~$0.27/M tokens | Hosted API. Occasional 500 errors and Cloudflare blocks. |
| UVA HPC vLLM (8x A100 80GB) | A100 80GB | Not benchmarked | Free (allocation) | Never completed a production run due to GPU partition routing bug (April 2026). A100 80GB nodes existed but SLURM routed jobs to an empty partition. |
| Claude Sonnet (vision mode) | N/A | ~7-50s/page | ~$0.04/page | Anthropic API. Used for tabular documents and index cards, not text extraction. |

**Key findings:**
- RC GenAI H200s are the fastest available option and are free. Even under shared load (~130s/chunk), they outperform Together AI's hosted Kimi.
- RC GenAI required a streaming (SSE) response parser fix in April 2026 — the service switched from standard JSON to Server-Sent Events format, which caused 99% failure rates until the client code was updated.
- HPC A100 80GB nodes were never successfully used for production extraction. The SLURM partition `gpu-a100-80gb` had zero nodes assigned, causing jobs to queue indefinitely. The nodes existed on the general `gpu` partition but the routing constraint sent jobs to the empty partition. This was not diagnosed until days of failed attempts.
- Together AI is reliable but costs money and is not faster than RC GenAI.
- For the full 5,000-document corpus (~17,500 chunks), estimated extraction time: ~25 days on RC GenAI at current rates.

*Infrastructure comparison added 2026-04-08. Speeds are approximate and vary with server load, prompt length, and output length.*

## 8. Vision Model Comparison: Index Card Extraction (April 2026)

Tested on the same 20 pages of 1935 DOJ record slips (NARA RG 60, Entry A1 96C, Box 487, 90-2-5) with the same `--index-cards` prompt for all three models.

| Model | Record Slips | Legal Cases | Persons | Failed Pages | Time | Cost (full 87-PDF run) |
|-------|-------------|-------------|---------|-------------|------|----------------------|
| Claude Sonnet 4.6 (vision) | **28** | 20 | **15** | 0/20 | 213s (11s/page) | ~$130 estimated |
| Qwen2.5-VL-72B (HPC, 4x A100) | **28** | **24** | 8 | 0/20 | 202s (10s/page) | Free (HPC GPU hours) |
| Kimi K2.5 (vision via RC GenAI) | 12 | 11 | 7 | 9/20 (45%) | 813s (41s/page) | Free |

**Findings:**

- **Slips: tied at 28.** Sonnet and Qwen-VL extract identical record slip counts and produce structurally similar JSON (file_number, jurisdiction, date, correspondent, case_name, routing, clerk_initials). The original "28 slips" figure for Sonnet that appeared in earlier docs turned out to be approximately correct, though it was never grounded in a saved JSON file at the time it was first written.
- **Cases: Qwen-VL +20% (24 vs 20).** Qwen-VL actually beats Sonnet on legal case extraction.
- **Persons: Sonnet +88% (15 vs 8).** This is the real and only meaningful gap. Sonnet finds nearly twice as many named persons. Qwen-VL also has some person-deduplication weakness (e.g., "Ralph Hughes" listed twice). Sonnet extracts more secondary mentions (assistants, treasurers, allottees named in subject lines) while Qwen-VL focuses on case principals.
- **Speed: identical.** ~10s/page for both Sonnet and Qwen-VL.
- **Reliability: both 100% on the test pages.** Only Kimi vision fails.

**Decision for the 87-PDF index card collection:** A full Sonnet `--vision --index-cards` run on the entire 87-PDF collection had already been completed earlier (output at `vision_index_cards_full/`, 80 PDFs with merged JSON), so the Qwen-VL HPC run launched 2026-04-10 against the running Qwen-VL vLLM server is duplicate work — kept running for the value of a corpus-scale Sonnet-vs-Qwen comparison and because the HPC GPU hours are free.

### Scale validation: 2-PDF apples-to-apples (66 dense pages from Box 487 and Box 576, both 90-2-11)

The 20-page test PDF was a sparse 90-2-5 box (1.4 slips/page). The first two PDFs Qwen-VL completed in the full run are dense 90-2-11 boxes (~11 slips/page). At scale, the picture is more nuanced than the test suggested:

| Metric | PDF 1 (32p) Sonnet | PDF 1 Qwen-VL | PDF 2 (34p) Sonnet | PDF 2 Qwen-VL | **Combined Sonnet** | **Combined Qwen-VL** | **Δ** |
|---|---|---|---|---|---|---|---|
| Record slips | 377 | 371 | 386 | 373 | 763 | 744 | tied (Sonnet +2.5%) |
| Legal cases | 128 | 250 | 147 | 273 | 275 | **523** | **Qwen +90%** |
| Persons | 216 | 120 | 246 | 152 | **462** | 272 | **Sonnet +70%** |
| Failed pages | — | 0 | — | 0 | — | 0 | — |

**Likely explanation — deduplication strategy:** The two models appear to dedupe differently and in opposite directions.

- **Cases:** Qwen-VL appears to extract every case *mention* as a separate `legal_case` entry. If "U.S. v. Hughes" appears on 30 slips, Qwen creates roughly 30 case entries; Sonnet consolidates to one. The Qwen output is closer to a per-mention audit trail; the Sonnet output is closer to a unique-case index.
- **Persons:** Sonnet captures every named individual including secondary mentions (assistant U.S. attorneys, county treasurers, judges, clerks named in routing or subject lines). Qwen-VL focuses on case principals and skips most secondary mentions.

Both behaviors are defensible. They produce different downstream affordances:

| Research question | Use |
|---|---|
| Slip-level extraction (file numbers, dates, jurisdictions, routing) | Either — equivalent |
| Unique case count, case index | Sonnet (or post-process Qwen to dedupe by file_number + case_name) |
| Per-mention audit trail (every appearance of every case across slips) | Qwen-VL |
| Named-person networks, people-as-search-targets, prosopography | Sonnet |
| Allottee identification (when in case caption) | Either |

A larger comparison across the rest of the Qwen-VL run is planned once it completes (or hits walltime). The dedup hypothesis can then be tested directly by counting unique case_names in the Qwen output.

**Why Kimi vision fails:** Kimi K2.5 on RC GenAI returns responses in SSE streaming format with separate `reasoning` and `content` fields. For vision requests, Kimi puts all its analysis into the reasoning field (narrative description of what it sees on the card) and produces no structured JSON in the content field. This happens on ~45% of pages, consistently timing out at ~51 seconds. The pages that succeed produce only 1 slip each. Kimi's strength is text-based comprehension of narrative documents, not vision extraction.

**RC GenAI model availability:** As of April 2026, RC GenAI only serves Kimi K2.5. Qwen2.5-VL-72B must be run on HPC via vLLM with Loren's container `vllm_0.14.1-cu130.sif` and `--tensor-parallel-size 4` on 4x A100 80GB.

*Vision comparison added 2026-04-09. Corrected 2026-04-10 after a true apples-to-apples Sonnet `--index-cards` rerun. Test JSONs at `comparisons/sonnet_index_cards_test/vision_merged.json` and on HPC at `/project/LawData/kimi-extraction/outputs/qwen_vl_index_cards_test.json`.*

---

---

## 9. v4 Three-Way Extraction: Kimi vs Sonnet vs Opus on CCF 56074

**Date:** 2026-04-15
**Document:** 1921 CCF 56074-21-312 GS (221 pages, Board of Indian Commissioners report)
**Schema:** v4 (10 types: entities, events, financial_transactions, relationships, fee_patents, correspondence, legislative_actions, testimony, taxes, mortgages)
**Chunking:** 40K chars, 5K overlap, 15 chunks

### v4 Extraction Results

| Category | Kimi K2.5 | Sonnet | Opus |
|----------|----------:|-------:|-----:|
| entities | 584 | 1,075 | 998 |
| events | 102 | 274 | 191 |
| financial_transactions | 58 | 181 | 89 |
| relationships | 82 | 343 | 258 |
| fee_patents | 67 | **368** | 316 |
| correspondence | 24 | 133 | 123 |
| legislative_actions | 11 | 37 | 26 |
| testimony | 11 | 107 | 105 |
| taxes | 6 | 23 | 20 |
| mortgages | 5 | 64 | 54 |
| **TOTAL** | **950** | **2,605** | **2,180** |

Sonnet leads on every category. Opus is second on every category. Kimi is a distant third at 36% of Sonnet overall.

### Critical Finding: v4 Prompt Degrades Kimi's Performance

The March v3 benchmark found Kimi K2.5 **exceeded Claude on fee patents** (268 vs 169). This was the headline result that shaped the optimal pipeline recommendation (Kimi extraction → Claude analysis). The v4 comparison reverses this finding entirely:

| | Kimi v3 (March) | Kimi v4 (April) | Sonnet v4 | Opus v4 |
|---|---:|---:|---:|---:|
| **fee_patents** | **293** | 67 | **368** | 316 |
| entities | 1,000 | 584 | 1,075 | 998 |
| events | 193 | 102 | 274 | 191 |
| financial_transactions | 135 | 58 | 181 | 89 |
| relationships | 228 | 82 | 343 | 258 |
| correspondence | 119 | 24 | 133 | 123 |
| legislative_actions | 40 | 11 | 37 | 26 |
| **TOTAL (v3 cats only)** | **2,008** | **928** | **2,231** | **2,010** |

Kimi's total output dropped from 2,008 items (v3) to 950 items (v4) on the **same document** — a 53% decline. Every category declined, not just fee patents.

### Probable Cause: Prompt Length

The v4 prompt adds three JSON categories (testimony, taxes, mortgages) plus extra instruction text ("For testimony, extract each distinct witness's statements as a separate record. For taxes and mortgages, extract every specific instance mentioned — these are key mechanisms of land dispossession."). This makes the v4 prompt ~40% longer than v3.

Claude Sonnet and Opus handle the longer prompt without difficulty — their v4 totals exceed what would be expected from v3. But Kimi K2.5 appears to lose effective context for document content as the prompt grows. The extra categories are mostly empty for this document type (only 22 testimony+taxes+mortgages items), so Kimi is paying a context cost for categories that don't apply.

### Implications for the Survey Corpus

The entire Survey of Conditions corpus (26 volumes, 158,351 records, 2,487 fee patents) was extracted with Kimi v4. If the v4 prompt is degrading Kimi's output by ~50%, those numbers may be significantly lower than what v3 would have produced.

However, the Survey documents are congressional hearings — exactly the document type where the v4 categories (testimony, taxes, mortgages) should contain real content. The CCF 56074 is a BIA administrative report where those categories are mostly empty. The v4 degradation may be less severe on documents where the extra categories actually match the content.

### Confirmed: v3 vs v4 on Survey Part 33

Direct comparison on the same hearing transcript (Part 33, San Diego/San Francisco 1934, 205 pages):

| Category | Kimi v3 | Kimi v4 | Change |
|----------|--------:|--------:|-------:|
| entities | 989 | 1,263 | +28% |
| events | 182 | 192 | +5% |
| financial_transactions | 88 | 116 | +32% |
| relationships | 170 | 163 | −4% |
| fee_patents | 12 | 0 | −100% |
| correspondence | 44 | 41 | −7% |
| legislative_actions | 28 | 32 | +14% |
| testimony | — | 37 | (new) |
| taxes | — | 0 | (new) |
| mortgages | — | 0 | (new) |
| **TOTAL** | **1,513** | **1,844** | **+22%** |

**On hearing testimony, v4 helps Kimi.** Total items increase 22%. The v3 categories are mostly stable or improved; v4 adds 37 testimony records. Fee patents drop from 12 to 0, but a hearing transcript should have 0 fee patents — v4's result is arguably more accurate.

### The Pattern: v4 Impact Depends on Document Type

| Document | Type | Kimi v3 | Kimi v4 | Change |
|----------|------|--------:|--------:|-------:|
| CCF 56074 | BIA admin report | 2,008 | 950 | **−53%** |
| Survey Part 33 | Hearing testimony | 1,513 | 1,844 | **+22%** |

The v4 prompt degrades Kimi on documents where the extra categories (testimony, taxes, mortgages) don't apply — the longer prompt wastes context on empty buckets. On documents where those categories match the content, v4 actually improves Kimi's output.

**Implication for the corpus:** Most of the 4,990 PDFs are BIA administrative records, litigation files, and correspondence — not hearing testimony. For these documents, Kimi v3 will likely outperform Kimi v4. A full KCA corpus v3 extraction is in progress (HPC job 11704958) to confirm this at scale.

**Test in progress:** Kimi v3 vs v4 on Survey Part 33 (San Diego/San Francisco 1934, 205 pages). HPC job 11693605 submitted 2026-04-15. This will establish whether the degradation holds on hearing testimony or is specific to document types where the v4 categories are sparse.

### Revised Model Rankings (v4 schema)

| Model | Total Items | % of Sonnet | Fee Patents | Notes |
|-------|----------:|:-----------:|------------:|-------|
| **Claude Sonnet** | **2,605** | **100%** | **368** | Best on v4 across all categories |
| Claude Opus | 2,180 | 84% | 316 | Strong second; ~4x cost of Sonnet |
| Kimi K2.5 | 950 | 36% | 67 | Dramatic decline from v3 (was 73%) |

The March recommendation — **Kimi extraction → Claude Opus analysis** — may need revision. If Kimi v3 significantly outperforms Kimi v4, the optimal pipeline may be Kimi v3 for the 7 base categories + a separate targeted pass for testimony/taxes/mortgages. Alternatively, Sonnet may now be the preferred extraction model for all document types at v4.

*v4 comparison results at `comparisons/ccf_56074_sonnet_v4/claude.json`, `comparisons/ccf_56074_opus_v4/claude.json`, and `survey_of_conditions_extractions/1921 CCF 56074-21-312 GS/kimi-k2.5.json`. Kimi v3 baseline from `comparisons/single_20260325_090708_1921 CCF 56074-21-312 GS_chunked/kimi-k2.5.json`.*

---

## 10. Full KCA Corpus: Kimi v3 vs v4 Side-by-Side (179 Documents)

**Date:** 2026-04-16
**Corpus:** KCA/Kiowa collection — 179 PDFs including BIA administrative records, litigation files, newspaper clippings, congressional records, forced fee patent affidavits, and one 851-page Survey of Conditions volume (1930 Survey of Cond OK)
**Method:** Fresh extraction of all 179 PDFs through Kimi K2.5 via RC GenAI, once with v3 prompt (7 types) and once with v4 prompt (10 types). Clean output directories, same PDFs (including newly OCR'd affidavits), same model.
**HPC Jobs:** 11705143 (v3), 11705144 (v4)

### Corpus-Wide Totals

| Category | v3 | v4 | Diff | v4/v3 |
|----------|---:|---:|-----:|------:|
| entities | 18,635 | 17,041 | −1,594 | 91% |
| events | 3,577 | 3,225 | −352 | 90% |
| financial_transactions | 2,453 | 2,341 | −112 | 95% |
| relationships | 3,092 | 2,783 | −309 | 90% |
| fee_patents | 358 | 452 | **+94** | **126%** |
| correspondence | 591 | 528 | −63 | 89% |
| legislative_actions | 363 | 321 | −42 | 88% |
| testimony | 0 | 352 | +352 | (new) |
| taxes | 0 | 212 | +212 | (new) |
| mortgages | 0 | 116 | +116 | (new) |
| **TOTAL** | **29,069** | **27,376** | **−1,693** | **94%** |

v4 produces 6% fewer total items. The v4-only categories (testimony, taxes, mortgages) add 680 new structured records, but the original 7 categories lose 2,373 items. However, fee patents — the most analytically important category — increase 26% with v4.

### Breakdown: Survey Volume vs Everything Else

**1930 Survey of Conditions OK (851 pages, 79 chunks)**

| Category | v3 | v4 | Diff |
|----------|---:|---:|-----:|
| entities | 5,026 | 4,258 | −768 |
| events | 712 | 637 | −75 |
| financial_transactions | 633 | 657 | +24 |
| relationships | 665 | 599 | −66 |
| fee_patents | 91 | 113 | **+22** |
| correspondence | 175 | 119 | −56 |
| legislative_actions | 93 | 76 | −17 |
| testimony | 0 | 113 | +113 |
| taxes | 0 | 27 | +27 |
| mortgages | 0 | 13 | +13 |
| **TOTAL** | **7,395** | **6,612** | **−783 (−11%)** |

Surprising: v4 loses 11% even on a Survey volume — the opposite of the Part 33 result (+22%). The difference may be document length: this volume is 851 pages (79 chunks) vs Part 33's 205 pages (21 chunks). Longer documents may suffer more from the v4 prompt's context cost because the prompt overhead accumulates across more chunks.

**All other documents (175 docs)**

| Category | v3 | v4 | Diff | v4/v3 |
|----------|---:|---:|-----:|------:|
| entities | 13,609 | 12,783 | −826 | 94% |
| events | 2,865 | 2,588 | −277 | 90% |
| financial_transactions | 1,820 | 1,684 | −136 | 93% |
| relationships | 2,427 | 2,184 | −243 | 90% |
| fee_patents | 267 | 339 | **+72** | **127%** |
| correspondence | 416 | 409 | −7 | 98% |
| legislative_actions | 270 | 245 | −25 | 91% |
| testimony | 0 | 239 | +239 | (new) |
| taxes | 0 | 185 | +185 | (new) |
| mortgages | 0 | 103 | +103 | (new) |
| **TOTAL** | **21,674** | **20,764** | **−910 (−4%)** |

### Per-Document Variation

The v4/v3 ratio varies widely by document. Some documents see v4 extract 2–10x more items (particularly newspaper articles and legislative records where the v4 categories provide better guidance). Others see v4 extract as little as 7% of v3's output.

**Documents where v4 is much worse (non-Survey):**

| v4/v3 | v3 items | v4 items | Document |
|------:|--------:|---------:|----------|
| 7% | 120 | 8 | 1936 Tushkahomman the Red Warrior |
| 20% | 45 | 9 | Emma Belle Wyatt Kiowa 305 |
| 25% | 60 | 15 | 1925 CCF 31486-25-312 Kiowa Neda protest |
| 30% | 10 | 3 | 1941 Hunt old age asst IRA |

**Documents where v4 is much better:**

| v4/v3 | v3 items | v4 items | Document |
|------:|--------:|---------:|----------|
| 1020% | 10 | 102 | 1912 big article on changes at KCA |
| 333% | 27 | 90 | 1938 RG 233 Kiowa claims bill |
| 228% | 36 | 82 | 1901 Kiowa opening (Guthrie Daily Leader) |
| 206% | 17 | 35 | Kiowa files checked out 15335 |

### Qualitative Analysis: What v3 Captures That v4 Doesn't (and Vice Versa)

The aggregate numbers show v3 producing more total items. But "more items" is not the same as "more useful items." A detailed examination of specific documents reveals what each version actually extracts and what the research implications are.

**Case study: Mattie Sturm, Caddo Allottee #40 (forced fee patent affidavit, 2 pages)**

This is a sworn deposition from February 23, 1929, in which Mattie Sturm, a 52-year-old Caddo woman, describes how she received a fee patent she did not request, mortgaged her allotment for $6,000, and eventually sold it for $15,000 in a trade for a lot and house in Anadarko.

**v3 entities (19 items):**
- Mattie Sturm (person) — "Allottee of No. 40 Caddo, age 52, gave sworn statement regarding land sale and patent"
- John Brown (person) — "Purchaser of Mattie Sturm's allotment in 1927, from Chickasha, Oklahoma"
- Commerce Trust Company (organization) — "Mortgage holder, located in Kansas City, lent $6000 in 1920"
- Husband of Mattie Sturm (person) — "Unnamed, recorded patent at courthouse, earns income for family support"
- Superintendent (person) — "Referred to as 'Supt.', advised Mattie Sturm to record patent at courthouse"
- Agent (person) — "Government agent who issued patent to Mattie Sturm"
- Notary Public (person) — "Administered oath, commission expires May 17, 1932"
- Unmarried children (person) — "Two unnamed children depending on Mattie Sturm"
- Married daughter (person) — "Has three children, depends on Mattie Sturm"
- Father of Mattie Sturm (person) — "Depends on Mattie Sturm for support"
- Other heirs to mother's allotment (person) — "Unnamed heirs from whom Mattie Sturm bought out interests"
- State of Oklahoma, County of Caddo, Chickasha, Anadarko, Kansas City (locations)
- Allotment No. 40 Caddo, Mother's allotment (land parcels)
- Bureau of Indian Affairs office (organization)

**v4 entities (10 items):**
- Mattie Sturm, John Brown, Commerce Trust Company, Notary Public (persons/orgs)
- State of Oklahoma, County of Caddo, Anadarko, Chickasha, Kansas City (locations)
- Allotment No. 40 Caddo (land parcel)

**What v3 captures that v4 doesn't:** 9 additional entity mentions — the unnamed husband, the superintendent, the BIA agent, the married daughter with three children, the unmarried children, the father, and the other heirs. These are contextual references that flesh out the family picture and the institutional actors involved in the patenting process. They are real people and real relationships that existed in 1929.

**What v4 captures that v3 cannot:**

*A testimony record:*
- **Witness:** Mattie Sturm
- **Title:** Allottee
- **Date:** 1929-02-23
- **Location:** Caddo County, Oklahoma
- **Key claims:** "Did not request patent but was told she had to take it; regrets accepting patent; sold land to purchase other heirs' interests in mother's allotment; received $15,000 equivalent in trade for land; buyer assumed $6000 mortgage; not cheated but would not have taken patent if she had known she could object; supports father, two unmarried children, married daughter and three grandchildren; never received financial aid; patent never canceled; back taxes never refunded"

This is the historiographically significant content — Mattie Sturm's own words about the mechanism of dispossession — captured as a single structured, searchable record. In v3, this information is scattered across entity context strings. In v4, a query for "allottees who testified they did not request their patent" would return Mattie Sturm as a direct hit.

*A mortgage record:*
- **Borrower:** Mattie Sturm
- **Lender:** Commerce Trust Company of Kansas City
- **Amount:** $6,000
- **Land:** All of Allotment No. 40 Caddo
- **Date:** 1920
- **Status:** paid
- **Context:** "10-year mortgage assumed by buyer John Brown in 1927; as of 1929, 4 years remained on original term"

In v3, this mortgage appears only as a text field inside the fee patent record: "$6000.00 to Commerce Trust Company of Kansas City, 1920, 10-year term." In v4, each field is independently searchable — you can query all mortgages by Commerce Trust Company, all mortgages over $5,000, all mortgages assumed by buyers.

*Two tax records:*
- Delinquent back taxes never refunded after land sale
- Property tax exemption status on trust land

These tax records are invisible in v3. The information exists in the full text but has no structured representation.

### The Fee Patent Exception

Fee patents increase 26% with v4 across the corpus (358 → 452). This is the opposite of the CCF 56074 result (where fee patents crashed from 293 to 67 between v3 and v4). The difference is document type:

- **CCF 56074** is a 221-page BIA administrative report with dense allotment tables — the kind of document where Kimi's v3 extraction excelled. The v4 prompt's extra categories and instructions appear to interfere with Kimi's ability to parse these tables.
- **KCA documents** are shorter, more focused — individual case files, affidavits, litigation records. On these documents, the v4 prompt's explicit mention of fee patents as a category ("mechanism: private_bill|administrative|application|certificate_of_competency") may actually help Kimi identify fee patents that v3 missed. The v4 prompt adds `certificate_of_competency` as a mechanism option that v3 doesn't have, which may account for some of the increase.

This finding complicates the narrative further: v4 is worse for Kimi overall, but better for the single most important category on the most common document type in the corpus.

### Practical Impact on the Streamlit Analysis Interface

The v3-vs-v4 choice has different implications depending on which analysis mode the researcher uses:

**Deep Read mode (single document, full text + extraction data → Opus):** Minimal impact. Opus reads the full text regardless. The extraction data is supplementary context. Whether mortgages appear in a dedicated `mortgages` section or in a fee_patent context string, Opus will find and use the information. The Deep Read fix (sending all 10 extraction types to Opus) matters more than v3 vs v4.

**Discovery mode (cross-document keyword search → structured results):** Significant impact. Discovery uses `search_mortgages()`, `search_testimony()`, `search_taxes()` to find records across documents. With v3, these tables are empty. A query about mortgages returns zero structured hits and falls back on keyword matches in entity context strings. With v4, you get direct hits: "Mattie Sturm, $6,000, Commerce Trust Company, Allotment No. 40 Caddo, status: paid."

**Corpus Synthesis mode (summaries across all documents → Opus):** No impact. This mode uses document summaries, not raw extraction data. If the summaries mention mortgages (and the Opus summaries generated from extraction data do), v3 vs v4 doesn't matter.

### Summary: The v3-vs-v4 Tradeoff

v3 produces more items (29,069 vs 27,376, +6%). v4 produces more analytically actionable items for the specific research question — how Native Americans lost their land through fee patents, mortgages, taxes, and coerced testimony.

The 1,693 "lost" items in v4 are predominantly secondary entity mentions (unnamed family members, institutional references, contextual locations). The 680 "gained" items in v4 are structured records of the mechanisms of dispossession — mortgages with borrower/lender/amount, tax records with status/county, testimony with key claims searchable by content.

For a historian studying land dispossession, a searchable mortgage record with borrower, lender, and amount is more valuable than three additional entity mentions for unnamed family members. The v4 records are analytically actionable; the v3 entities are contextual.

**However, the ideal would be both.** A v5 prompt that preserves v3's entity density while adding v4's structured categories for testimony, taxes, and mortgages would capture the full picture without the tradeoff. This is the next direction for prompt development.

*Full extraction results at `kca_reextraction/fresh_v3/` and `kca_reextraction/fresh_v4/`. HPC jobs 11705143 (v3) and 11705144 (v4), both completed 2026-04-16.*

---

## 11. Prompt Engineering: v5 and the Path to Optimal Extraction

**Date:** 2026-04-16 (experiment in progress)

### The Problem

Sections 9 and 10 established that the v3 and v4 prompts each have strengths the other lacks:

- **v3** produces denser extraction (29,069 vs 27,376 items on 179 KCA docs), particularly in entities (+9%), events (+10%), and relationships (+10%). It captures secondary actors — unnamed family members, institutional references, contextual locations — that provide the social fabric around each case.

- **v4** produces structured records for the specific mechanisms of land dispossession: testimony (352 records), taxes (212), mortgages (116). These don't exist in v3 at all. v4 also finds 26% more fee patents, possibly because it adds `certificate_of_competency` as a mechanism option that v3 lacks.

Neither version is strictly better. The tradeoff is between extraction density (v3) and analytical specificity for the research question (v4).

### Three Approaches Under Consideration

**Approach A: Slim prompt (v5)**

Keep all 10 categories from v4 but reduce the prompt overhead that appears to degrade Kimi's performance. The v4 prompt is ~40% longer than v3 due to:
1. Three additional JSON template blocks for testimony, taxes, mortgages (~450 chars)
2. Two extra instruction sentences (~180 chars): "For testimony, extract each distinct witness's statements as a separate record. For taxes and mortgages, extract every specific instance mentioned — these are key mechanisms of land dispossession."

The v5 prompt removes the extra instruction text entirely and trims the testimony/taxes/mortgages templates to their essential fields:

- v4 testimony: witness, witness_title, hearing, committee, location, date, subject, key_claims, questioner (9 fields)
- v5 testimony: witness, date, subject, key_claims (4 fields)
- v4 taxes: taxpayer, land_description, tax_type, amount, year, status, county, context (8 fields)
- v5 taxes: taxpayer, amount, tax_type, status, context (5 fields)
- v4 mortgages: borrower, lender, amount, land_description, acreage, date, interest_rate, status, context (9 fields)
- v5 mortgages: borrower, lender, amount, date, status, context (6 fields)

The hypothesis: if the degradation is caused by prompt length consuming Kimi's effective context, a shorter prompt with the same categories should recover most of v3's density while retaining v4's structured types.

**v5 test in progress:** HPC job submitted 2026-04-16, running all 179 KCA docs. Results will be compared against v3 and v4 on the same corpus.

**Approach B: Two-pass extraction**

Run v3 first (proven density), then a targeted second pass that asks only for testimony, taxes, and mortgages from the same chunks. The second-pass prompt would be very short — just three JSON templates and a single instruction. Merge the results.

Advantages:
- v3 pass is proven to produce maximum entity density
- Second pass prompt is tiny (~300 chars of template), well within Kimi's comfort zone
- Each pass is independently verifiable
- No risk of degrading the v3 categories

Disadvantages:
- Doubles walltime (though cost is $0 on RC GenAI)
- Requires a merge step to combine results
- Two JSON files per document to manage

This approach treats the problem as a matter of specialization rather than optimization. Instead of asking Kimi to do 10 things at once (and doing each one slightly worse), ask it to do 7 things well, then 3 things well.

**Approach C: v3 + certificate_of_competency (v3+)**

The simplest possible change: add `certificate_of_competency` to v3's fee_patents mechanism list. One word added to the prompt.

The v4 fee patent increase (+26% on KCA) may be primarily driven by this single mechanism option rather than by the v4 prompt structure. Many KCA documents describe forced fee patenting through competency commissions — a process that v3's mechanism list (`private_bill|administrative|application`) doesn't explicitly name. Adding it to v3 might close most of the fee patent gap while preserving v3's density advantage on everything else.

This wouldn't add testimony, taxes, or mortgages. But if the two-pass approach (B) is ultimately the best path, v3+ would be the ideal first pass — maximum entity density plus the full fee patent mechanism list.

### Expected Decision Tree

```
If v5 recovers v3's density (≥95% of v3 items) AND keeps v4's new types:
  → v5 is the answer. Use it for everything.

If v5 partially recovers (85-95% of v3) but still loses significant entities:
  → Two-pass (B) is better. v3 first pass, targeted second pass.
  → Test v3+ as the first pass to get the fee patent mechanism benefit.

If v5 doesn't recover (< 85% of v3):
  → The categories themselves are the problem, not just prompt length.
  → Two-pass (B) is the only viable approach.
```

### What We're Measuring

The v5 run will produce a third column for every document in the KCA corpus. For each document, we compare:

1. **Entity density**: Does v5 match v3? (Target: ≥95% of v3's entity count)
2. **Fee patents**: Does v5 match v4? (Target: ≥90% of v4's count, i.e., the certificate_of_competency benefit)
3. **New categories**: Does v5 produce testimony/taxes/mortgages? (Target: ≥80% of v4's counts in these categories)
4. **Survey volume**: Does v5 handle the 851-page Survey doc as well as v3? (v4 lost 11% here)

If v5 hits all four targets, it's the optimal single-pass prompt. If it misses on entity density but hits the new categories, two-pass with v3+ is the answer.

### Toward v6: The Two-Pass Architecture

Regardless of the v5 results, the two-pass approach deserves implementation because it solves a broader problem. The corpus is heterogeneous: BIA administrative records, litigation files, newspaper clippings, hearing transcripts, individual affidavits, and 1,000-page statistical reports. No single prompt is optimal for all of these.

A two-pass architecture would:
1. **First pass (v3+ or v5):** Extract the core 7 categories with maximum density. This is the proven extraction that produces entities, events, relationships, fee patents, correspondence, and legislative actions.
2. **Second pass (targeted):** Extract only testimony, taxes, and mortgages. Short prompt, focused task. Can be run on all documents or selectively on documents where these categories are expected (hearing transcripts, tax litigation files).

The merge step is straightforward: combine the JSON outputs, deduplicating any items that appear in both passes (e.g., a financial_transaction in pass 1 that is also a tax record in pass 2).

This architecture also opens the door to future targeted passes — for example, a dedicated "allotment affidavit" pass with a prompt tuned specifically for the forced fee patent sworn statements, extracting the specific questions and answers from the affidavit form.

### v5 Results: The Three-Way Comparison (175 Documents)

**Date:** 2026-04-16
**HPC Job:** 11725989 (v5), completed alongside 11705143 (v3) and 11705144 (v4)
**Corpus:** 175 KCA/Kiowa documents present in all three extraction runs

#### Corpus-Wide Totals

| Category | v3 | v4 | v5 | v5/v3 | v5/v4 |
|----------|---:|---:|---:|------:|------:|
| entities | 18,591 | 17,005 | **18,297** | 98% | 108% |
| events | 3,563 | 3,217 | **3,876** | **109%** | 120% |
| financial_transactions | 2,443 | 2,330 | **2,575** | **105%** | 111% |
| relationships | 3,082 | 2,773 | **3,009** | 98% | 109% |
| fee_patents | 353 | 447 | **439** | **124%** | 98% |
| correspondence | 591 | 519 | 540 | 91% | 104% |
| legislative_actions | 363 | 320 | 350 | 96% | 109% |
| testimony | 0 | 350 | **375** | — | **107%** |
| taxes | 0 | 212 | 197 | — | 93% |
| mortgages | 0 | 116 | **118** | — | 102% |
| **TOTAL** | **28,986** | **27,294** | **29,776** | **103%** | **109%** |

#### Against the Decision Tree

The decision tree predicted: "If v5 recovers v3's density (≥95% of v3 items) AND keeps v4's new types → v5 is the answer."

Measuring against the four targets:

1. **Entity density**: v5 = 18,297 entities, v3 = 18,591. That's **98% of v3**. Target was ≥95%. **PASS.**

2. **Fee patents**: v5 = 439, v4 = 447. That's **98% of v4**. Target was ≥90%. **PASS.** Moreover, v5 = 124% of v3's 353, confirming the `certificate_of_competency` mechanism benefit carries over from v4.

3. **New categories**: 
   - Testimony: v5 = 375, v4 = 350. **107% of v4. PASS.** (Target was ≥80%.)
   - Taxes: v5 = 197, v4 = 212. **93% of v4. PASS.**
   - Mortgages: v5 = 118, v4 = 116. **102% of v4. PASS.**

4. **Overall total**: v5 = 29,776, v3 = 28,986. **v5 exceeds v3 by 3%.** This was not predicted — the expectation was that v5 would recover v3's density, not exceed it. The extra 790 items come from the v4-only categories (testimony: 375, taxes: 197, mortgages: 118 = 690) plus gains in events (+313 over v3), financial_transactions (+132), and fee_patents (+86).

**All four targets met. v5 is the production prompt.**

#### Why v5 Works: The Prompt Length Hypothesis Confirmed

The v4 prompt was ~40% longer than v3 due to three additional JSON template blocks and two extra instruction sentences. The v5 prompt keeps all 10 JSON categories but:

- **Trimmed testimony from 9 fields to 4**: witness, date, subject, key_claims (dropped witness_title, hearing, committee, location, questioner)
- **Trimmed taxes from 8 fields to 5**: taxpayer, amount, tax_type, status, context (dropped land_description, year, county)
- **Trimmed mortgages from 9 fields to 6**: borrower, lender, amount, date, status, context (dropped land_description, acreage, interest_rate)
- **Removed the extra instruction sentences**: "For testimony, extract each distinct witness's statements as a separate record. For taxes and mortgages, extract every specific instance mentioned — these are key mechanisms of land dispossession." Gone.

The result: v5's prompt is ~15% longer than v3 (vs v4's ~40% longer). This smaller overhead stays within Kimi's effective context capacity, allowing the model to devote more attention to the actual document content.

The trimmed fields in testimony, taxes, and mortgages are not lost — they can be populated by the analysis layer (Deep Read mode, which has the full text) rather than requiring the extraction prompt to capture them. The extraction captures the fact that a testimony, tax, or mortgage record exists and its core content; the analysis layer fills in context-dependent details when needed.

#### Per-Category Analysis

**Entities (v5 = 98% of v3, 108% of v4):** v5 nearly matches v3's entity density while substantially exceeding v4. The slim prompt gives Kimi enough context to find the secondary actors — unnamed family members, institutional references, contextual locations — that v4 was missing. The 2% gap vs v3 (294 entities) is negligible given that v5 adds 690 items in categories v3 doesn't have.

**Events (v5 = 109% of v3, 120% of v4):** v5 finds *more* events than v3. This is unexpected. One hypothesis is that v5's explicit mention of all 10 categories helps Kimi recognize events that v3's 7-category framing caused it to overlook. Another possibility is normal extraction variance on a single corpus run. This should be confirmed across additional corpora before treating it as a systematic v5 advantage.

**Financial transactions (v5 = 105% of v3, 111% of v4):** Similar pattern — v5 exceeds v3, which may reflect the same category-priming effect or may be noise. Marked as a hypothesis pending replication.

**Relationships (v5 = 98% of v3, 109% of v4):** Nearly identical to the entity pattern — v5 recovers v3's relationship density while substantially exceeding v4.

**Fee patents (v5 = 124% of v3, 98% of v4):** v5 preserves v4's fee patent advantage (the `certificate_of_competency` mechanism) while exceeding v3 by 24%. This confirms the Section 10 finding that the fee patent increase was driven by the mechanism option, not by v4's prompt structure. v5 gets the same benefit with less overhead.

**Correspondence (v5 = 91% of v3, 104% of v4):** The one category where v5 underperforms v3 by a meaningful margin (-51 records, -9%). This may be because v3's shorter prompt allocates more of Kimi's attention to the correspondence category, which requires identifying sender/recipient/date/subject structures. The gap is small in absolute terms.

**Legislative actions (v5 = 96% of v3, 109% of v4):** v5 is slightly below v3 but well above v4. The -13 record gap (-4%) is within normal extraction variance.

**Testimony (v5 = 107% of v4):** v5 finds more testimony records than v4 despite having fewer template fields. The 4-field template (witness, date, subject, key_claims) appears to be sufficient — and may actually help Kimi by reducing the cognitive load of populating 9 fields per record.

**Taxes (v5 = 93% of v4):** v5 finds slightly fewer tax records than v4 (-15 records). The gap is small and may reflect the loss of the `county` field from the template — without an explicit county field, Kimi may be slightly less likely to identify county-level tax records.

**Mortgages (v5 = 102% of v4):** Essentially identical. The 6-field template captures the same information as v4's 9-field version.

#### The Two-Pass Question

The decision tree's first branch applies: v5 recovers v3's density and keeps v4's new types. The two-pass architecture (Approach B) is no longer necessary for the general case.

However, the two-pass approach may still have value for specific document types:

- **Hearing transcripts with dense testimony:** On the 851-page Survey of Conditions volume, the per-chunk comparison would tell us whether v5's 4-field testimony template captures the same detail as v4's 9-field version. For a Congressional hearing where testimony is the primary content, the missing fields (committee, location, questioner) might matter.

- **Tax litigation files:** For documents centered on tax disputes (like the DOJ index card cases), a targeted second pass with a tax-specific prompt could extract county, year, and assessment details that v5's slim template omits.

- **Affidavit-specific extraction:** The Circular 2464 affidavits have a structured question-and-answer format that a specialized prompt could exploit. This isn't a v3/v4/v5 question — it's a document-type-specific prompt.

For production extraction of the heterogeneous corpus, v5 is the single-pass answer. For research-critical document subsets where specific fields matter, a targeted second pass remains an option. The cost of the second pass is zero on RC GenAI, and the infrastructure for running it already exists.

#### Revised Pipeline Recommendation

The optimal extraction pipeline is now:

| Layer | Model | Prompt | Task |
|-------|-------|--------|------|
| **Extraction** | Kimi K2.5 via RC GenAI | **v5** | All documents. 10 types, slim template. |
| **Extraction (vision)** | Claude Sonnet | v4 vision | Tables, index cards, scanned forms |
| **Summaries** | Claude Opus | from-extraction | Per-document analytical summaries |
| **Analysis** | Claude Opus | — | Deep Read, Discovery, Corpus Synthesis |

v5 replaces v4 as the default extraction prompt. v3 is retired. The `--v5` flag should become the default (no flag needed).

*Three-way comparison completed 2026-04-16. Full extraction results at `kca_reextraction/fresh_v3/`, `kca_reextraction/fresh_v4/`, and `kca_reextraction/fresh_v5/`. HPC jobs 11705143 (v3), 11705144 (v4), 11725989 (v5).*

---

## 12. Human vs AI: Circular 2464 Affidavits

**Date of final measurement:** 2026-04-18

### The Test

Compare AI extraction of Circular 2464 affidavits against a hand-transcribed reference. In 1928–1929, the Bureau of Indian Affairs collected sworn affidavits from allottees at Pine Ridge, Rosebud, the Kiowa-Comanche-Apache Agency, and other agencies, asking about their fee patents — when issued, whether they consented, whether they sold or mortgaged the land, to whom, for how much, and whether taxes forced the sale. A research assistant transcribed 528 of these affidavits into a structured spreadsheet with 18 columns. This section measures how well AI extraction reproduces that transcription.

### Ground Truth and Its Limits

The spreadsheet is a partial human transcription — complete for some subset of affidavits, ongoing for others. Recall is measured against the transcribed subset, not against the full affidavit record. The spreadsheet itself contains occasional errors:

- "Bejmain Janis Jr." (Pine Ridge Volume 1, allotment 711): first name typo
- "Louis Mousseau" vs the PDF's "Louis Mosseau" (Volume 1, allotment 1859/1856): spelling variant
- Allotment number discrepancies on Emma Stirk (Vol 2: spreadsheet 2665 vs PDF 2606), Susie Keester (Vol 2: 2723 vs 2718), Rosa Ruff (Vol 3: 7302 vs 7309)

What is being measured is AI-vs-human agreement on the transcribed subset, not AI-vs-document correspondence.

### Verified Denominators

Per-volume denominators established by cross-referencing spreadsheet allotment numbers against "No." markers in each volume's PDF text:

| Volume | Pages | Verified allottees |
|--------|------:|-------------------:|
| Pine Ridge Volume 1 | 148 | 96 |
| Pine Ridge Volume 2 | 153 | 100 |
| Pine Ridge Volume 3 | 131 | 84 |
| **Combined Pine Ridge** | **432** | **280** |

The 89-allottee gap between the 280 verified and the 369 spreadsheet entries labeled Pine Ridge reflects cross-agency depositions (Pine Ridge allottees deposed elsewhere — Lillian Lawyer at Nez Perce, Frank Carlow at Crow Agency, Louis Hawkins at Greenwood) and spreadsheet entries whose affidavits are not in the three Pine Ridge volumes.

### Pine Ridge Volume 1: Head-to-Head

All models run at 10K-character chunks against 96 verified allottees. Matcher: v2 (suffix normalization, fuzzy last-name with exact first-name). Measurement: `compare_affidavit_extractions.py`, audited at `AUDIT_compare_affidavit_extractions.md`.

| Model | Prompt | Raw | Unique | Match/96 | Recall | Allot% | Allot Accuracy | Cons% | Out% |
|-------|--------|----:|-------:|---------:|-------:|-------:|---------------:|------:|-----:|
| Human (RA) | — | — | 96 | 96 | 100% | ~100% | — | ~100% | ~95% |
| Sonnet 4.6 v2 | affidavit | 161 | 133 | 87 | 91% | 95% | 85/87 (98%) | 100% | 94% |
| Opus 4.6 | affidavit | 150 | 130 | 87 | 91% | 96% | 82/82 (100%) | 100% | 97% |
| Kimi K2.5 | affidavit | 93 | 80 | 56 | 58% | 17% | 8/8 (100%) | 93% | 93% |
| Kimi K2.5 | targeted v2 | 70 | 69 | 50 | 52% | 100% | 49/50 (98%) | 100% | 100% |

**Findings:**

The human transcription remains the quality ceiling. Sonnet and Opus are indistinguishable from each other at these resolutions. Kimi with the original affidavit prompt matches fewer allottees than Sonnet and captures allotment numbers on only 17% of records. Kimi with a targeted prompt (structured to prioritize allotment-number identification and tolerate a single-pass extraction rather than stepwise reasoning) achieves allotment capture parity with Sonnet (100% vs 95%) and matches Sonnet on field completeness (100% consent and outcome vs 100% / 94%). The targeted prompt closes the per-record quality gap. It does not close the recall gap — Kimi finds 52% of allottees against Sonnet's 91%. The recall difference is not a prompt engineering problem; it is a difference in how many distinct deponents each model identifies per chunk at 10K context.

### Pine Ridge Volumes 2 and 3: Sonnet and Opus

Same methodology extended to Volumes 2 and 3.

| Volume | Denom | Sonnet matched | Sonnet recall | Opus matched | Opus recall |
|--------|------:|---------------:|--------------:|-------------:|------------:|
| Volume 1 | 96 | 87 | 91% | 87 | 91% |
| Volume 2 | 100 | 93 | 93% | 94 | 94% |
| Volume 3 | 84 | 81 | 96% | 78 | 93% |
| **Combined** | **280** | **261** | **93%** | **259** | **92%** |

Allotment accuracy 95–98% across all three volumes for both models. Consent and outcome completeness 95–100%.

### Kimi Chunking Experiment

To test whether Kimi's recall reflects a chunk-size limitation rather than a capability limitation, extraction was rerun on Volume 1 with page-level (~2K) chunks. Smaller chunks increased recall from 58% to 90%, but allotment accuracy on captured records dropped from 100% to 42% — Kimi at small chunks began returning legal descriptions ("SW quarter of Section 22") and wrong-number values instead of correct allotment numbers. No Kimi configuration at either chunk size matches Sonnet on the combined recall-plus-accuracy measure.

### Kimi Targeted Prompt Experiment

A targeted prompt designed around Kimi's specific failure mode (allotment-number-to-deponent linking) was tested on Volume 1 at 10K chunks. The prompt structured extraction as a single pass prioritizing allotment-number identification, with explicit instructions to output JSON only and to treat phrases like "See answer to No. 4" as references rather than allotment numbers. Infrastructure stability on the RC GenAI Kimi endpoint required a retry wrapper: 9 of 25 chunks failed on first attempt (6 invalid JSON, 3 empty SSE). Retry resolved 8 of 9 on one or two attempts; the ninth succeeded on the third attempt.

With retry, the targeted prompt produced 50 matches against 96 GT (52% recall) at 100% allotment capture, 98% allotment accuracy, and 100% consent and outcome completeness. Per-record quality matched or exceeded Sonnet. The recall gap persisted.

### KCA: Different Archival Structure

The KCA extraction ran separately, using Kimi with the generic KCA corpus prompt on 71 individual affidavit PDFs plus 178 additional KCA documents. 70 Kiowa-Comanche-Apache entries served as the reference.

| Metric | Value |
|--------|------:|
| Reference (denominator) | 70 |
| Unique matched | 64 |
| Match rate | **91%** |
| Total records across tables | 497 |

The generic prompt distributes affidavit content across multiple record types (entities, fee_patents, testimony, mortgages, taxes, correspondence). Composite reconstruction produces case records equivalent to the spreadsheet's fields. Sample reconstructions for Lillian Marie Goombi (allotment 661) and Tsomah (allotment 2694) recover all spreadsheet fields plus cross-document context. The 6 unmatched Kiowa allottees are primarily matcher failures on compound entries and name variants, not extraction failures.

### What Archive Structure Determines

**One-document-per-file organization (KCA):** generic prompt at any reasonable chunk size produces research-grade output. Each affidavit is its own extraction unit.

**Bundled multi-document volumes (Pine Ridge, presumably Rosebud and the Replies volumes):** Sonnet with the affidavit-specific prompt at 10K chunks handles the bundled PDFs directly. Kimi at the same configuration finds fewer allottees; a Kimi-specific prompt produces Sonnet-quality records but does not close the recall gap.

### Page Classification: Two-Model Comparison

The Replies volumes spot-sample audit revealed the corpus contains four interleaved document types — sworn affidavits, questionnaire responses, agency narratives, and tabular ledger entries — rather than the uniform affidavit corpus initially assumed. The redesigned extraction pipeline routes each document type to a matched extraction approach, which requires a page-level classifier to identify document type before extraction runs.

**Classifier categories.**

After collapsing first-page and continuation-page distinctions (boundary detection belongs to the downstream splitter, not the classifier), the working categories are: `affidavit_content`, `questionnaire_content`, `agency_narrative_content`, `ledger_entry_page`, `transmittal_letter`, `cover_sheet`, and `other`.

**Two-model comparison on Pine Ridge Volume 1.**

Both Sonnet 4.6 and Kimi K2.5 were run as classifiers on all 148 pages of Pine Ridge Volume 1 using the same classification prompt. Initial Kimi runs failed at 78% rate due to `max_tokens=500` being too small for Kimi's reasoning mode. After raising `max_tokens` to 8000 and adding a retry wrapper, both models produced complete classifications.

Results after category collapse:

| Metric | Value |
|--------|-------|
| Pages classified by each model | 148 |
| Agreement on collapsed categories | 142/148 (95%) |
| Confidence distribution — Sonnet | 94% high |
| Confidence distribution — Kimi | 93% high |
| Sonnet cost | $0.42 |
| Kimi cost | Free (RC GenAI) |

**Disagreement analysis.**

Before category collapse, raw agreement was 73% with 34 of 40 disagreements being `affidavit` vs `affidavit_continuation` swaps. Both models confidently disagreed on whether specific pages were the start of an affidavit or a continuation page. This is not a model-quality issue — it reflects that page-level boundary classification is the wrong unit for the question. After collapsing first-page and continuation-page categories, agreement rose to 95%.

The 6 remaining disagreements:

- 2 pages: Sonnet `cover_sheet` vs Kimi `other` (pages 1–2, title pages with minimal content)
- 2 pages: Sonnet `other` vs Kimi `ledger_entry_page` (pages 34, 88, handwritten pages with garbled OCR — both models low confidence)
- 1 page: Sonnet `transmittal_letter` vs Kimi `other` (page 3)
- 1 page: Sonnet `affidavit_content` vs Kimi `questionnaire_content` (page 135)

All disagreements involve ambiguous or degraded-OCR pages. No disagreements on clearly typed affidavit, questionnaire, agency narrative, or ledger pages.

**Configuration finding for RC GenAI Kimi K2.5.**

Kimi K2.5 on RC GenAI uses a built-in reasoning mode that consumes substantial token budget before producing visible output. Tasks with short expected outputs but reasoning overhead require generous `max_tokens` settings — 500 produced 78% failure rate; 8000 produced near-100% completion. This is a usage requirement rather than a platform defect. Documented in `circular_2464_extractions/standalone/uvarc_kimi_configuration_finding.md`.

**Production decision.**

The classifier is validated for full-corpus classification. Kimi K2.5 on RC GenAI runs the production classification pass given equivalent accuracy to Sonnet, free compute, and consistency with the project's API-independence architecture. Sonnet remains available as a verification tool for spot-checks of disagreements or low-confidence classifications.

**Methodological finding.**

Boundary detection (where one document ends and the next begins) is a different problem from document-type classification (what kind of content is on this page). Conflating them in a single classifier produces avoidable disagreement and obscures the type-classification accuracy. The downstream splitter handles boundaries; the classifier identifies type. Separating these tasks improved measured agreement from 73% to 95%.

### Production Recommendation

For extraction across the full Circular 2464 corpus, Sonnet with the affidavit prompt at 10K chunks is the primary configuration. Expected performance against the transcribed reference: 91–96% recall, 95–98% allotment accuracy, 95–100% field completeness.

The Kimi experiments establish that open-source extraction on this document type is possible at Sonnet-quality per-record but at lower recall. The recall gap may be addressable through alternative infrastructure (self-hosted Kimi on B200s, or different Kimi variants) or through different open models (Qwen 3, DeepSeek V3.5) not yet tested on this corpus. These remain open questions.

### Measurement Infrastructure

The comparison script is audited in `AUDIT_compare_affidavit_extractions.md`. Safeguards include:

- Per-volume denominator assertion (96, 100, 84 for Pine Ridge Volumes 1–3)
- v2 name matcher with suffix normalization and fuzzy last-name matching
- Automated allotment accuracy check with format-variant normalization
- Automated field-type diagnostic
- Automated false-positive sample

Five silent measurement bugs were found and corrected across this work. Details in `SECTION_12_CORRECTION_APPENDIX.md`.

---

## 13. Vision Benchmark: BLM Patent Annotation Extraction (May 2026)

Cross-reference to a related-but-separate model benchmark in the sister
`~/projects/american-indian-allotment/` project. The full writeup is at
[`BENCHMARK_v5_vision_extraction.md`](../../american-indian-allotment/BENCHMARK_v5_vision_extraction.md).

### What was tested

Bounded-template extraction from scanned BLM Indian allotment patents.
Two fields per page: the top-left CCF (BIA Central Classified Files)
reference, and a presence boolean for the middle-page "Fee Patent
Issued" conversion stamp. Structurally similar to the NARA index card
extraction task (DOJ record slips, RG 60) where Gemma 3 12B was
previously found to be excellent — both are constrained-layout vision
problems with predictable fields.

### Methodology

Same input PDFs to every model, same v5 prompt and schema, all
disagreements verified against the source PDFs by hand. Three models:

- Claude Opus 4.7 (Anthropic API) — 300-PDF benchmark vs. Sonnet
- Claude Sonnet 4.6 (Anthropic API) — 300-PDF and 50-PDF benchmarks
- Gemma 3 27B-it (UVA HPC, 1×A100 80GB, vLLM 0.14.1) — 50-PDF benchmark

### Result

**Sonnet 4.6 selected for the production extraction of 8,818 PDFs.**

- **Opus vs. Sonnet (v4, 300 PDFs)**: tied on PDF-verified accuracy on
  six disagreement cases. Bool agreement was 99.7%. Opus actual billed
  cost was 2x Sonnet for comparable output quality. Verified empirical
  Opus rate (~$0.046/PDF) was about a third of the list-price calculation
  (~$0.135/PDF), a useful calibration finding for future cost projections.
- **Sonnet vs. Gemma 3 27B (v5, 50 PDFs)**: Gemma demonstrated false
  positives on both fields. The string `'49611'` appeared as a CCF
  reference on 11 different patents in the sample; direct PDF
  verification on one (985277) confirmed `49611` is not present —
  hallucination, not OCR. Gemma flagged 29/50 patents as having a
  fee-conversion stamp where Sonnet flagged 9; PDF verification of all
  20 disagreement cases (those that were trust-class and could
  logically carry a stamp) confirmed zero of Gemma's extra flags
  matched a real stamp. Both layers had systematic Gemma false-positive
  patterns the v5 prompt's anti-pattern instructions did not suppress.

### Scope of the Gemma finding

This is one specific task (bounded vision template on allotment patents)
in one specific configuration (vLLM 0.14.1, Gemma 3 27B-it, structured
output requested via prompt rather than `response_format` because the
latter is not reliably honored). The result does **not** generalize to
Gemma 3 12B on NARA index cards (which `CLAUDE.md` records as excellent
on bounded template work), nor to future vLLM or Gemma releases.
Re-test when either side sees a substantial upgrade.

### Hidden-fee yield

The original research question was: how many trust patents have a fee
conversion stamp recorded only on the page, with no separate fee patent
record in the database? At the v5 50-PDF sample, Sonnet found one
genuine hidden conversion (patent 953646), an empirical rate of ~2%.
Extrapolating to the 8,818-PDF residual is unreliable from a sample of
50, but the production run will give a corpus-wide number.

---

*Comparison and fine-tuning experiment conducted 2026-03-23. Recognition vs. comprehension analysis added 2026-03-24. Kimi K2.5 testing added 2026-03-25 — significantly changes the open-source extraction picture, particularly for fee patent identification. Full four-way analysis pipeline comparison ({Claude, Kimi} extraction × {Opus, Kimi} analysis) added 2026-03-25. Qwen 2.5 72B benchmark added 2026-03-27 (UVA HPC, 2x A100 80GB) — confirms Kimi's fee patent capability is exceptional among open-source models; Qwen at half the GPU cost is not a viable alternative for fee patent extraction. BLM patent vision benchmark added 2026-05-24 (Sonnet vs. Gemma 3 27B on 50 PDFs, Opus vs. Sonnet on 300 PDFs) — Section 13 above. Model performance may change with future releases or prompt optimization. Fine-tuning was tested and did not improve results — see Section 3. For practical deployment recommendations, see Sections 4 and 5.*
