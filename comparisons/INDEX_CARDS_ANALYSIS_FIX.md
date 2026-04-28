# Index Cards Analysis Pipeline Fix (April 2026)

This document records the substantive fixes made to `ai_analysis_interface_v4.py`
in April 2026 after the user discovered that "tell me about taxes" queries
against the DOJ index cards database were producing analyses that misrepresented
the corpus.

## How the bug was discovered

A user query against the **DOJ index cards** database (`index_cards`) for
"tell me about taxes" returned an analysis whose "named allottees" section
listed eight different women all named **Stella** (Stella D. Twiss, Stella
Blowsnake Stacy, Stella Findley, Stella Vanderzanden, Stella Perry, Stella
Barker Smith, Stella Mitchell, Estella Seay). The user — a historian — flagged
this as statistically absurd. A direct PostgreSQL query confirmed the database
actually contains **6,588 person entries across 3,637 unique names**, with
"Stella" being a normal early-twentieth-century name appearing ~0.85% of the
time. The Stella cluster was a **retrieval and synthesis bug**, not a data
problem.

## Root causes

Five distinct bugs were stacked on top of each other:

### 1. v4 records were fetched but never reached the synthesis prompt
`build_discovery_context()` had sections for entities, events,
financial_transactions, relationships, fee_patents, correspondence,
legislative_actions, and networks — but **no sections for taxes, mortgages, or
testimony**. Meanwhile the discovery flow at the call site *did* fetch them
into the `evidence` dict via `search_taxes()`, `search_mortgages()`, etc.
The data was retrieved and then silently dropped before the prompt was built.

For the Survey of Conditions database, this meant **1,553 tax records and 634
mortgage records were invisible to the synthesis layer** despite being fetched
on every query.

### 2. The Discovery tool had no search functions for the index card schema
The tool was originally built around the v3 schema (entities, events,
correspondence, fee_patents, legislative_actions). The DOJ index cards use a
later schema added by `load_vision_extractions.py`: **`record_slips`** (12,969
rows), **`legal_cases`** (4,811 rows), and `persons`. The Discovery tool had
**no `search_record_slips()` and no `search_legal_cases()`** function at all.
When queried against `index_cards`, it could only find slips' contents
indirectly — via entity context fields that happened to mention the keyword.
That's where the tiny biased sample (and the Stella cluster) came from.

### 3. The synthesis prompt promised data it didn't deliver
The Discovery prompt's "YOU HAVE MULTIPLE TYPES OF EVIDENCE" section
**statically listed** every possible category — including TESTIMONY, TAXES,
MORTGAGES, LEGISLATIVE ACTIONS — regardless of which database was being
queried. For a database (like index_cards) with empty taxes/mortgages/testimony
tables, the model was being told it had data it never received. It then wrote
a paragraph honestly admitting "no records were returned" while still framing
the topic as if it had searched a populated table. The prompt also had a
duplicate `5.` numbering bug.

### 4. The synthesis padded gaps with prior knowledge
When the database evidence was thin, Claude Opus would fall back on its
training corpus. The output would look authoritative but actually consisted
of training-data summaries of the Burke Act, Curtis Act, Dawes Act, and the
Cato Sells competency commissions — none of which came from the user's
archive. As a historian who already knows that secondary literature, the
user needed extraction from THIS archive, not a textbook section.

### 5. The retrieval treated questions as strict-AND keyword matches
Even after adding `search_record_slips()`, the FTS query used
`websearch_to_tsquery()` which requires every space-separated term to appear
in a single row's search vector. A natural question like *"trace U.S. v.
Pennington County"* parses to `trace & u.s & v & pennington & county` —
requiring all five tokens. The token "trace" doesn't appear anywhere in DOJ
slip data, so the query returned **zero rows**, and the analysis fell back
on the entity-network data (where the user got Roy B. Marker and the same
Stella cluster again).

## The fix, in five layers

### Layer 0 — taxes/mortgages reach the prompt
- `build_discovery_context()` and `build_hybrid_context()` now have `TAXES`
  and `MORTGAGES` sections that include taxpayer/borrower, tax type, amount,
  year, county, status, land description, context, and source.
- The Discovery and Hybrid UI summary counts and Browse Raw Evidence panels
  now display Testimony, Taxes, and Mortgages tabs — so you can see at a
  glance whether the search returned anything.

### Layer 0.5 — search functions for the index card schema
- New **`search_record_slips()`** function that queries the `record_slips`
  table by file_number, jurisdiction, correspondent, case_name,
  named_individual, tribe_or_reservation, subject, action_type, and routing.
- New **`search_legal_cases()`** function that queries the `legal_cases`
  table similarly, with a `LEFT JOIN` on `record_slips` to compute a
  `slip_count` per case (the number of slips citing that file_number — a
  frequency signal for how heavily the case was litigated).
- Both wired into the Discovery and Hybrid evidence dicts.
- New `RECORD SLIPS` and `LEGAL CASES` sections in
  `build_discovery_context()` and `build_hybrid_context()`.
- New tabs in the Discovery and Hybrid Browse Raw Evidence panels.
- `get_db_stats()` extended to count `record_slips` and `legal_cases` per
  database.

### Layer 1 — bigger result pools
- `search_record_slips(limit=500)` and `search_legal_cases(limit=500)` —
  raised from 100. With 12,969 slips in the index_cards database, 100 was
  far too narrow.

### Layer 2 — two-phase case-trace expansion
After Phase 1's keyword search, the Discovery flow now extracts the most
frequent `file_number`s from the matching slips and cases (the top 20),
then runs a Phase 2 query that pulls **every slip with those file_numbers**
(capped at 30 slips per file_number). This is implemented via a new helper
`fetch_slips_by_file_numbers()` that uses a `ROW_NUMBER() OVER (PARTITION BY
file_number ORDER BY date)` to cap rows per file_number.

The effect: even if a keyword like "Pennington County" only matches one
slip in a long case, Phase 2 then drags in the complete chronology of all
slips for that file_number. Cases like 90-2-5-71 (12 slips), 90-2-5-81
(Stella D. Twiss case, 12 slips), and 90-2-5-49 (Fort Peck, 161 slips)
become traceable end-to-end.

The synthesis prompt was updated to tell the model the slips it sees are
"near-complete chronologies" for the file_numbers that surfaced, so it
treats them as a complete audit trail and reconstructs case timelines
instead of just listing the keyword hits.

### Layer 3 — PostgreSQL full-text search
- Migration script `migrate_fts_record_slips.sql` adds `STORED` `tsvector`
  generated columns to `record_slips` and `legal_cases`, with GIN indexes:

  ```sql
  ALTER TABLE record_slips
      ADD COLUMN IF NOT EXISTS search_vector tsvector
      GENERATED ALWAYS AS (
          to_tsvector('english',
              coalesce(file_number, '')        || ' ' ||
              coalesce(jurisdiction, '')       || ' ' ||
              coalesce(correspondent, '')      || ' ' ||
              ... eleven fields total ...
          )
      ) STORED;

  CREATE INDEX IF NOT EXISTS idx_record_slips_search_vector
      ON record_slips USING GIN (search_vector);
  ```

- A new `_build_or_tsquery()` helper converts free-form natural-language
  questions into permissive OR-based tsquery strings, after stripping a
  hard-coded list of stopwords (the, a, of, etc.) AND command words
  (trace, tell, show, find, list, give, describe, explain, discuss, etc.).
  Example: `"trace U.S. v. Pennington County"` →
  `"pennington | county"`.

- The search functions now use `to_tsquery()` with the OR-built string and
  `ts_rank()` for relevance ordering. They fall back to the original ILIKE
  search if either FTS returns nothing or the `search_vector` column doesn't
  exist (so non-migrated databases still work).

### Layer 4 — synthesis prompts that report ONLY what's in the data
- The Discovery and Hybrid prompts now build the "YOU HAVE MULTIPLE TYPES OF
  EVIDENCE" list **dynamically from `db_stats`**, so a database with zero
  testimony rows never sees TESTIMONY listed. The DOJ index cards database
  no longer gets prompted with congressional-hearing categories that don't
  apply to it.
- New caveats added to both prompts:
  - *"REPORT ONLY WHAT IS IN THE EVIDENCE BELOW. Do not introduce historical
    context, statutory background, or policy analysis from outside the
    database (e.g. the Burke Act, Curtis Act, Dawes Act, Cato Sells
    competency commissions) unless that material appears in the evidence.
    If the database is silent on a topic, say so explicitly. The user is a
    historian who already knows the secondary literature; your job is to
    surface what is in THIS archive, not to summarize what is already
    known."*
  - *"EVERY claim must cite a specific source filename. If you cannot cite
    a source, do not make the claim."*
  - *"Do not pad short evidence with speculation. If only 5 records were
    returned, write a short focused analysis of those 5. Do not extrapolate
    to 'patterns' from a handful of records."*
- A new explicit instruction tells the model that record slips for a given
  file_number are a near-complete chronology when they appear, enabling real
  case-tracing.

### Other small changes
- Discovery prompt's `total_structured` counter now includes
  taxes/mortgages/testimony/record_slips/legal_cases.
- `max_tokens` for the LLM call bumped from 8,000 to 16,000 across all three
  analysis modes (Discovery, Deep Read, Hybrid) so longer evidence can produce
  longer outputs.
- The Kimi K2.5 model option in the model dropdown switched from Together AI
  (`moonshotai/Kimi-K2.5`) to **UVA RC GenAI** (model name `Kimi K2.5`),
  using the open-webui gateway with `Authorization: Bearer $UVARC_GenAI_API`.
  The new `_call_uvarc()` function handles the SSE streaming format and falls
  back to the `reasoning` field if Kimi routes content there.
- Fixed two pre-existing `", ".join(...)` crashes when an entity's
  `source_display_names` list contained `None` values.

## Verification

Two queries exercised the full pipeline against the index_cards database
after the fix landed:

1. **"tell me about taxes"** — produced an analysis grounded in real DOJ
   slips spanning 1922–1943, naming dozens of Pine Ridge / Fort Peck /
   Osage / Five Civilized Tribes / Omaha allottees (including the eight
   Stellas, but as 8 people among 200+ rather than as the entire population),
   with concrete file numbers, dates, and the multi-county litigation totals
   ($10,746.97 across 43 judgments in four South Dakota counties). The
   synthesis cited file 90-2-5-49 (Fort Peck, **161 slips**) and the
   relief bill H.R. 5918 (file 90-2-01, **182 slips**) as the heavily
   litigated cases — both surfaced via the `slip_count` aggregation.

2. **"trace U.S. v. Pennington County"** — produced a day-by-day chronology
   of the litigation campaign across 15+ individual allottee cases under
   90-2-5 sub-numbers, traced from August 1935 bills of complaint through
   November 1935 filings, December 1935 quit-claim deeds (Treasurer C.I.
   Leedy, purchaser I.H. Chase), March 1936 amended complaints, the
   September 1936 decree pro confesso in the Twiss case, and the October
   1937 aggregate judgment report. None of this was visible to the broken
   pipeline, which kept reporting "no direct case match" because its strict
   AND-tsquery couldn't find any single slip containing all the words in the
   user's question.

## Files changed

- `ai_analysis_interface_v4.py` — all of the above changes
- `migrate_fts_record_slips.sql` — new migration for Layer 3
- `INDEX_CARDS_ANALYSIS_FIX.md` — this document

## How to apply the fix to a new database

1. Run the migration:
   ```
   psql NEW_DB_NAME -f migrate_fts_record_slips.sql
   ```
2. The discovery tool will automatically use FTS for the new database. If
   the tables aren't present, the tool falls back to the older ILIKE search.
3. The dynamic prompt logic uses whichever evidence types are non-zero in
   `db_stats`, so no per-database prompt configuration is needed.

---

## Follow-up: Text Passage Discipline and Mandatory Gap-Flagging (April 2026)

After the index card pipeline fix produced visibly better analyses on the
DOJ slips collection, the same prompt-honesty discipline was extended to
the text-based corpora (Survey of Conditions, Crow Nation, Kiowa/KCA, full
corpus). The user's framing was: *"can the same approach work for text? or
because it's text will it not work that way?"*

### Why text corpora needed additional caveats

Index cards have a structural advantage for "report only what's in the
archive" discipline:

- Each slip is one short atomic record
- The slip subject is a single sentence the model can quote exactly
- The file_number is a citable identifier
- There is no ambiguity about what counts as "in" the data — it's the
  explicit fields

Narrative text corpora are subtly harder:

- The Survey database has full text passages (long paragraphs of OCR'd
  hearing testimony) plus extracted entity/event/tax/mortgage records
- A query like *"tell me about taxes"* returns dozens of text passages and
  hundreds of structured atoms
- The model has more raw material to **paraphrase**, and the temptation to
  smooth narrative-summary the testimony "as if it were your own framing"
  is much stronger than the temptation to invent atomic slip data
- A pre-fix April 1 corpus synthesis on the Survey database had real doc
  citations and concrete numbers (it was already grounded in the data) but
  it paraphrased every witness, blurred extracted entity records into the
  same narrative voice as direct testimony, and ended without a methodology
  gap-flagging section

### The three new caveats

Added to the **Discovery**, **Hybrid**, and **Corpus Synthesis** prompts:

**1. TEXT PASSAGE DISCIPLINE.** When the model uses a quotation from a
document text passage, it must format it as a markdown block quote
(`> ...`) with the source filename in the attribution immediately after.
No paraphrasing-as-framing — either quote it or explicitly summarize "the
[filename] hearing records that…". For Corpus Synthesis specifically — where
the model only sees AI-compressed summaries, not raw text — the rule
becomes: never present summary text as if it were a verbatim quotation
from the underlying document.

**2. DISTINGUISH EVIDENCE TYPES IN PROSE.** Use clear signal phrases so the
reader can tell what kind of evidence each claim rests on:

- *"the document text states…"* → primary text quote
- *"the AI extraction recorded a [type] entry showing…"* → extracted
  entity/event/transaction (an AI summary of some passage)
- *"across N records the data shows…"* → aggregate count

Never blur a database aggregate with a direct quotation, and never present
an extracted entity as if it were a verbatim quote.

**3. MANDATORY "What This Archive Does Not Tell You" CLOSING SECTION.**
Required on every analysis, every database, every mode. Must name *specific*
gaps — e.g. *"the data does not include the final decree in U.S. v. X
County"* not *"outcomes are not documented."* This is methodology, not
weakness — it tells the historian which gaps to fill from other archival
sources. The Corpus Synthesis version of this rule additionally instructs
the model to flag when a topic is poorly served by the SUMMARY MODE
specifically (i.e. when the summaries probably compressed out detail that
is in the underlying documents but isn't visible to the synthesis layer).

### Verification — Discovery mode

Query: *"tell me about the effects of fee patents on taxes and land"*
against `survey_of_conditions` in **Discovery** mode after the fix.

The output produced:

- **Direct block quotes from hearing testimony with attribution.** The
  Kickapoo dispossession-by-tax-purchase passage from the Anadarko
  hearings (*"The Indians have been told that these pieces of land have
  been taxed since 1900..."*). The Wisconsin case where an allottee's
  taxes accumulated unbeknownst to her (*"That up to this time she was
  unware that the land was being taxed by the county officials..."*).
  The Yakima/Klamath irrigation-lien-vs-fee-patent conflict (*"To
  receive fee patent free of all charges and encumbrances..."*). The
  Preston-Engle Report on operation and maintenance assessments. The
  Pueblo Cayuga land-sale historical reference (*"The State paid the
  Cayugas at the rate of 4 shillings per acre and thereafter sold the
  land for 16 shillings per acre."*).

- **Visible signal phrases distinguishing primary text from
  AI-summarized atoms from aggregates.** Example sequence on the
  Kickapoo case: *(1)* block quote of the testimony, attributed to the
  source filename, *(2)* *"The AI extraction of the corresponding tax
  record confirms…"* showing the extracted `tax` entry separately, *(3)*
  the model's own analytical framing labeled as such (*"This was not a
  one-off transaction but a described method..."*). All three layers are
  visibly distinct.

- **A 10-item "What This Archive Does Not Tell You" section** listing
  specific actionable gaps:

  1. Specific tax sale records (dates, parcel descriptions, sale prices,
     purchaser names, redemption outcomes)
  2. Acreage lost specifically to tax delinquency (vs the 40,905 acres
     the corpus does record for mortgage foreclosure 1910–1927)
  3. County-level tax assessment rolls
  4. The text of the *Choate v. Trapp* decision
  5. Outcomes of the Kickapoo taxation question raised in committee
  6. Tax records from North Dakota, South Dakota, and Wisconsin
     specifically
  7. Correspondence from county officials to Congress requesting
     restriction removal
  8. Individual-level tracing from fee patent → tax delinquency → tax
     sale → new owner
  9. Post-1932 outcomes under the IRA
  10. Aggregate dollar amounts of taxes actually paid by Indians

  Each gap is a concrete research lead.

### Verification — Corpus Synthesis mode

Query: *"tell me about the effects of fee patents on american indian
land"* against `survey_of_conditions` in **Corpus Synthesis** mode after
extending the same caveats to `analyze_corpus()`.

The output produced:

- **Provenance-tagged claims throughout.** Every factual assertion is
  framed as *"the Doc N summary records that…"* — making the AI
  compression visible at every step. Pre-fix outputs paraphrased
  witnesses ("Edgar B. Meritt acknowledged…"); post-fix outputs make the
  AI compression explicit (*"The Doc 29 summary records that Assistant
  Commissioner Edgar B. Meritt acknowledged…"*). The reader can never
  confuse a verbatim witness quote with a summary phrasing.

- **A three-section conclusion** (What the Documents Prove / What the
  Documents Suggest / What This Corpus Does Not Tell You) where every
  "Suggest" claim is explicitly hedged. Example on the central
  interpretive claim:

  > "The fee patent system functioned as a coordinated mechanism of
  > wealth transfer from Indian to non-Indian ownership, not merely as a
  > failed experiment in Indian 'emancipation.' The consistency of
  > outcomes across geography and time, the involvement of identifiable
  > predatory actors (merchants, loan companies, speculators), and the
  > continued pursuit of the policy despite known consequences suggest
  > systemic design rather than unintended consequences. **However, the
  > corpus does not contain explicit evidence of a single coordinated
  > conspiracy**; rather, it documents a policy environment in which
  > multiple actors independently exploited the same structural
  > vulnerability."

  Each of the four "Suggest" claims is qualified the same way: *"may
  have been designed to facilitate land transfer… **but the corpus does
  not contain the internal deliberations of the commissions
  themselves**"*; *"may have been deliberately engineered… **but the
  corpus does not contain direct evidence**"*; *"appears significant…
  **but the text of that directive is not reproduced in the
  summaries**"*.

- **Explicit summary-mode limitation flagging.** The "What This Corpus
  Does Not Tell You" section includes items that explicitly call out
  when the corpus IS in the database but the summaries don't surface it:

  > "The 2,317 fee patents in the database likely contain far more
  > granular information than the summaries convey."

  > "The 4,283 correspondence records and 634 mortgages in the database
  > almost certainly contain far more granular evidence of individual
  > dispossession than is visible in the summaries. The summaries
  > necessarily compress thousands of individual transactions into
  > pattern descriptions."

  The model is now telling the historian, explicitly, *"I'm working from
  compressed summaries; for granular evidence drop into Discovery
  mode."* That's the SUMMARY MODE LIMITATION caveat doing its work.
  Corpus Synthesis stays the right tool for the meta-pattern, and the
  model now actively points the user toward Discovery mode for the
  detail.

- **Other actionable gap items:** the text of key policy directives
  (April 17, 1917 letter), individual-level tract data, post-1932
  outcomes for individuals named in 1928–1931 testimony, tribal-specific
  acreage losses attributable specifically to fee patents (vs other
  mechanisms), legal outcomes of challenges to forced fee patents, the
  role of state courts in facilitating or resisting dispossession,
  comparative data by blood quantum, any systematic federal remediation
  effort beyond the underfunded IRA Section 5 program.

### What did NOT change

The pre-fix April 1 output was already grounded in the data — it had real
`[Doc N]` citations, concrete dollar amounts ($5,004,196.83 irrigation
debt at Flathead, $940,040.19 at Fort Peck, the Wilson-Clinton guardian
case at $200K spent in 18 months), named witnesses (Robert Hamilton,
Edgar B. Meritt, James Humphreys, Philip Deines), and specific cases. It
wasn't producing the bullshit Stella problem. The new caveats sharpen the
provenance discipline and add the mandatory gap-flagging — they don't
fundamentally change what kind of analysis the tool produces, they make
the existing kind more rigorous and more useful for historical research.

### What the user said about the result

> "this is in fact what i like about the analysis now: it does not feed me
> bs i do not want."

> "what i really need is a tool that helps me navigate my archive which is
> too big to read on my own."

The new output is exactly that: a structured map of where the evidence
lives in 26 hearing volumes (or 87 index card PDFs), with direct quotes
for the load-bearing passages, explicit labeling of provenance, and an
honest map of what's missing so the historian knows which gaps to fill
from other sources.

### Lesson

Honest gap-flagging is a research virtue, not a software shortcoming. A
good monograph footnote is "the X archive does not preserve Y; for Y see
Z." Building that habit into the prompt produces analyses that historians
can actually cite from instead of having to manually verify every claim.
