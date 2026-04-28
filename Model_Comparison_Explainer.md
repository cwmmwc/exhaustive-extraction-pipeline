# Can Open-Source AI Match Commercial AI on Historical Documents?

**A Non-Technical Summary of What I Tested and What I Found**

Christian McMillen, Department of History, University of Virginia -- March 2026

## The Project

I am building a system to extract structured information from thousands of historical documents that record how the federal government dispossessed Native Americans of their land. The documents -- letters, hearing transcripts, court records, fee patent files -- total roughly 139 million words across nearly 5,000 PDFs. No individual could read them all. The goal is to use artificial intelligence to read every document and pull out every person, organization, place, financial transaction, legal case, and relationship mentioned, then store all of that in a database that researchers can search and analyze.

This is not the same as asking AI a question and getting a chatbot-style answer. Instead, the AI pre-processes each document and produces a structured record -- like filling out a very detailed form for every page of every document in the archive. Once that work is done, the database becomes a tool: you can trace a single person across thirty years of records, calculate how much land a particular county lost, or discover that the same attorney appears in dozens of suspicious transactions.

## The Question

The AI models that do this work best -- such as Claude, made by Anthropic -- are commercial products that charge per use. Running the full corpus through Claude would cost several thousand dollars. That is manageable for a funded research project, but it creates a dependency: anyone who wants to reuse the tools, including the tribal nations whose histories these documents record, would face the same ongoing costs. So I asked: can freely available, open-source AI models do the same work? If so, the entire system could run on a university's own computers at no per-document cost, and the tools could be shared with anyone.

## What I Tested

I ran two sets of comparisons. The first tested open-source AI models from Meta (the Llama family) against Claude on 368 Crow Reservation documents. The second compared Claude against Kimi K2.5, an open-source model from Moonshot AI whose weights are freely available, on a single but extraordinarily rich document: a 221-page 1921 compilation of field reports in which the Board of Indian Commissioners surveyed federal employees across Indian country about what happened to Native Americans after they received fee patents to their land. This document covers dozens of reservations -- Kiowa, Pawnee, Ponca, Kaw, Tonkawa, Flathead, Pine Ridge, and many others.

Both comparisons tested two distinct tasks. The first was extraction: given a document, pull out every person, event, financial transaction, and relationship. The second was analysis: given extracted data or a full document, produce a coherent historical interpretation. I also tried fine-tuning -- a process where you take an open-source model and give it additional training on examples of correct output -- to see if that would close the gap.

Finally, I tested the full pipeline in a four-way matrix: two different extractors (Claude, Kimi) crossed with two different analysis models (Claude Opus, Kimi), all working from the same document and the same research question. This revealed what matters most -- the extraction, the analysis, or the combination.

## Finding 1: Meta's Open-Source Models Were Not Close

Meta's best open-source model, Llama 3.3 70B, extracted 46% of what Claude extracted from the same documents -- meaning it missed more than half of the people, events, and transactions that Claude found. Meta's newest and largest model, Llama 4 Maverick, performed worse at 25% and introduced hallucinations -- fabricated names and invented events that do not appear in the source documents. Another variant, Llama 4 Scout, failed entirely, producing no usable output on any test document.

The gap was not just about quantity. In a document about fee patents issued to Ponca Indians in Oklahoma, Llama tagged dozens of individuals simply as "Indian who received patent-in-fee." Claude, reading the same document, recorded that one man had sold all his land and was "broke," that another had mortgaged his land for $6,500 and was leasing it out, that a third had deeded land to his children but retained life use. Claude identified the bureaucratic structure (which agencies oversaw which reservations), the geography (fifteen towns across Oklahoma and Kansas), and the family relationships among allottees. Llama captured none of this.

When asked to answer research questions using evidence from hundreds of documents, the gap widened further. Claude cited 23 specific documents with 19 dates and 21 acreage figures. Llama 4 Maverick cited 2 documents with 1 date and 1 acreage figure. Fine-tuning -- the additional training -- made things worse, not better, dropping output to 38% of Claude's. The gap is not about format; it is about comprehension.

## Finding 2: Kimi K2.5 Changed the Picture

The comparison between Claude and Kimi K2.5 on the 221-page Board of Indian Commissioners document told a fundamentally different story than the Llama results. Where Meta's models collapsed on the hardest extraction task -- identifying that a sequence of narrative sentences about an individual allottee constitutes a fee patent case history -- Kimi matched and exceeded Claude.

On the full document, Kimi found 268 unique fee patent allottees. Claude found 169. That is 99 additional named individuals whose dispossession is documented in the historical record. Spot-checking confirmed these are real people from the correct tribes (Pawnee, Ponca, Kaw, Tonkawa, Otoe) with internally consistent details. Claude did not extract them. A person whose existence you do not know about is a more consequential gap than a person you know about with slightly less detail.

Kimi also demonstrated a genuine analytical advantage on one dimension: it correctly distinguished between different legal mechanisms of dispossession. Ponca and Tonkawa Indians applied for fee patents; Kaw Indians received certificates of competency under the Kaw Treaty. Kimi labeled these correctly. Claude labeled nearly everything generically as "administrative." For a historian analyzing how different legal mechanisms produced different outcomes across tribes, this distinction matters.

The trade-off was in per-record detail. When the source text provided rich information about an individual -- acreage, sale price, buyer, attorney -- Claude populated those structured fields more thoroughly. Kimi found more people but with thinner records for each. However, the sparse fields often reflected the source document, not a model failure. Many allottees appear in the document as a single line: "Harry Stubbs -- land sold. Funds gone. Living off his friends." Neither model can extract structured data that is not in the source text.

Overall, Kimi extracted 73% of Claude's total output across a three-document benchmark. But on fee patents -- the atomic unit of land dispossession in this research -- Kimi extracted 105-159% of Claude's output depending on the document. The category that matters most for this research is where Kimi is strongest.

This result overturned the conclusion from the Llama testing. The fee patent gap was not an inherent open-source limitation. It was a Llama-specific limitation. Kimi proved that an open-source model can comprehend narrative prose well enough to identify individual case histories.

Where Kimi still trails Claude is on documents dominated by long causal chains -- legislative correspondence where a senator writes to the BIA, the BIA writes to Interior, Interior recommends amendments, and the senator amends the bill. Tracing that sequence requires maintaining a model of causation across the entire document. On one such document, Kimi extracted 58% of Claude's output. The gap was widest in relationships and events that span multiple pages of correspondence. For record-heavy documents with many individual cases, Kimi is as good or better than Claude. For narrative-heavy documents with long bureaucratic chains, Claude remains essential.

## Finding 3: What the AI Extracts Determines What the AI Can Later Analyze

The four-way comparison -- two extractors crossed with two analysis models, all reading the same document -- produced the most important finding of the entire testing program.

When Claude Opus analyzed Claude's own extraction of the 1921 document, it produced a tightly focused analysis. Both analyses -- the one built on Claude's extraction and the one built on Kimi's -- identified the same core Kiowa evidence: Superintendent V. Stinchecum's devastating testimony that he could recall only one success out of six years of fee patents, that 60 of the most recent patents had already been alienated or mortgaged, and that blood quantum and education were useless predictors of whether an allottee would keep their land. Both recognized this as one of the most damning internal assessments of federal Indian land policy ever produced.

But the analysis built on Kimi's extraction was more comprehensive. Because Kimi had extracted more individuals across more reservations, Opus had a wider evidence base to work with. The Kimi-fed analysis assembled a comparative table covering 17 jurisdictions, versus 11 from the Claude-fed analysis. It organized the Kiowa evidence into a six-stage mechanism of land loss. It surfaced Samuel Charger's Sioux testimony as a distinct voice -- his observation about returned Indian soldiers losing their land and the connection to Kiowa veterans targeted for fee patents. Everything in the Claude-fed analysis also appeared in the Kimi-fed analysis. The reverse was not true.

Extraction breadth feeds analysis breadth. A wider extraction does not produce a different analysis -- it produces a richer one.

## Finding 4: Kimi as Analyst Was Surprisingly Competitive

The four-way matrix also tested Kimi K2.5 as the analysis model, not just as the extractor. Working from the same Kimi extraction, Kimi-as-analyst delivered roughly 80-85% of Opus's analytical value. A historian could work productively from either analysis.

Where Opus was stronger was in interpretive framing -- telling you why a passage matters, not just what it says. When Opus quoted a government farmer comparing Indian allotments to the Russian Revolution, it framed this within broader intellectual history. Kimi quoted the same passage but presented it as evidence without doing the historiographical framing work. Opus also named structural concepts -- "the leasing trap," "geographic dislocation of allotments," "inheritance fragmentation" -- that a historian can cite and argue with. Naming a mechanism makes it usable in prose. Kimi covered similar ground but did not crystallize it into citable concepts.

Opus found several historically significant details that Kimi missed entirely: a proposed government-backed loan system that would have provided capital without requiring land alienation (a road not taken in Indian policy), a Baptist missionary's philosophical observation about Indians' right to learn from experience, and a devastating natural experiment at Rocky Boy where sixty years of "freedom" from government supervision had produced exactly the degradation that fee patent advocates claimed supervision was causing.

Where Kimi was the stronger analyst was in organization: cleaner tables, more systematic enumeration of silences and omissions, better collection of cross-respondent consensus on the homestead proposal. Kimi also caught details Opus missed -- a Nez Perce woman holding $14,000 in mortgages on white men's farms (a counter-narrative of Indian financial sophistication), and specific research leads about "Indian Rights" organizations whose relationship to land speculation deserves investigation. Kimi surfaced the case of Dadie Pappan, whose biographical sentence -- "Land sold. When money was spent, husband left. Married again, husband Theodore Sumner, got certificate, bought house, and deeded to Dadie. Rest spent" -- captures the cycle of gendered land loss with devastating clarity.

The missing 15-20% is precisely the interpretive framing that turns evidence into historical argument. For publication-quality analysis, that gap matters. For a first pass, triage, or generating research leads, Kimi is sufficient.

## What This Means for the Project

The practical conclusion is not that commercial AI wins and open-source fails. It is that different models are best at different things, and the optimal system uses both.

The evidence now supports a complementary pipeline. Kimi K2.5 -- an open-source model whose weights are freely available -- is the strongest extractor for record-heavy documents, the kind that contain lists of individual allottees and their outcomes. It finds more people than Claude does. For building a comprehensive roster of every individual affected by fee-patent-driven land dispossession, Kimi produces a more complete record. Claude remains essential for narrative-heavy documents -- legislative correspondence, multi-decade litigation, congressional hearings -- where tracing causal chains across pages of prose is the core task. Claude is also the only viable option for corpus-wide synthesis, where the AI must hold hundreds of documents in context and cross-reference specific details across dozens of sources.

The optimal pipeline, confirmed by testing, is Kimi extraction fed into Claude Opus analysis. This combination produces the widest evidence base interpreted with the deepest analytical framing. Neither model alone achieves what the combination produces.

For cost and accessibility, this changes the picture. Kimi can run on a university's high-performance computing cluster at no per-document cost. The expensive commercial step -- Claude Opus for analysis -- can be targeted rather than applied to every document. And because Kimi-as-analyst delivers 80-85% of Opus's value, communities or institutions without API budgets can still produce strong analytical output from the extracted data.

The open-source commitment holds more firmly than the initial Llama results suggested. The question was never simply "commercial versus open-source." It was "which model for which task." The answer is now clear: Kimi for breadth, Claude for depth, and the combination for the best result.

The negative fine-tuning result remains a contribution. Anyone working in digital humanities who faces the same decision now has concrete evidence that fine-tuning a smaller model on a larger model's output does not close the comprehension gap. But they also have evidence that the right open-source model -- one with sufficient scale and architecture -- can match or exceed commercial AI on the extraction tasks that matter most.
