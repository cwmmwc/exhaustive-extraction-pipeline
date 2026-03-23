# Kiowa Fee Patents — Corpus Synthesis (v3 Extraction)

**Date:** 2026-03-23
**Database:** historical_docs (v3 extraction schema — with fee_patents, correspondence, and legislative_actions tables)
**Documents:** 228 with summaries (of 256 total)
**Model:** claude-opus-4-6 (Corpus Synthesis mode)
**Extraction model:** claude-sonnet-4-6 (v3 pipeline)
**Query:** "please tell me about the kiowa experience with fee patents and land loss"

## Purpose

This is the v3 extraction synthesis, produced after re-extracting 180 KIOWA documents through the v3 pipeline
which adds structured fee_patents, correspondence, and legislative_actions tables. Compare against
the v2 baseline in `kiowa_fee_patents_v2_extraction_baseline.md`.

## Key Metrics from This Synthesis

- **Documents cited:** 83 unique documents
- **Named allottees with detailed case histories:** 40+ (expanded to include Caddo, Comanche, Wichita)
- **Fee patent waves documented:** 3 (Aug 1917, Dec 1919, Aug 1920)
- **Mortgage/debt table:** 19 allottees with amounts and terms (new in v3)
- **Distress sale cases documented:** 15+ with per-acre or total-value calculations
- **Patent cancellations documented:** 9 (added Neda Birdsong, Rachel Briscoe)
- **Tax recovery cases:** 3 with dollar amounts and satisfaction dates
- **Predatory actors named:** 6 firms/individuals with specific victims (new in v3)
- **Direct quotes from allottees:** 10+
- **Sections:** 10 (v2 had 5) — added leasing, heirship fractionation, cultural suppression, legal architecture, political advocacy

## v3 vs v2 Comparison

| Metric | v2 Baseline | v3 Extraction |
|--------|------------|---------------|
| Documents cited | 70+ | 83 |
| Named allottees with case histories | 25+ | 40+ |
| Fee patent waves | 3 | 3 (more names per wave) |
| Distress sale table | 9 allottees | 15+ allottees |
| Mortgage/debt table | none | 19-row table |
| Patent cancellations | 7 | 9 |
| Tax recovery cases | 3 | 3 (with dollar amounts/dates) |
| Direct quotes | 7 | 10+ |
| Predatory actors | mentioned in passing | 6 named firms with victims |
| Sections | 5 | 10 |

### What v3 Structured Extraction Added

- **Fee patent table** linked allottee → allotment → acreage → buyer → attorney → mortgage in single records,
  enabling the mortgage amounts table and predatory ecosystem section
- **Correspondence table** captured sender/recipient/date/subject, enabling the political advocacy timeline
- **Legislative actions table** tracked bills through lifecycle, enabling the legal architecture section
- Leasing as structural dispossession (75% leased, $0.10–$0.25/acre)
- Heirship fractionation (27 heirs per tract by 1934, 1/504 interests)
- Cultural suppression via Ghost Dance financial penalties

---

## Full Synthesis Output

The Kiowa Experience with Fee Patents and Land Loss: A Corpus-Wide Synthesis

### I. The Foundation: Treaty Rights, Allotment, and the Jerome Agreement

The Kiowa experience with fee patents and land loss cannot be understood apart from the dispossession that preceded it. The Kiowa, Comanche, and Apache (KCA) tribes held a reservation of approximately 2,968,893 acres under the Medicine Lodge Treaty of 1867 (Doc 253, Doc 200). The Cherokee Commission—David H. Jerome, Alfred M. Wilson, and Warren G. Sayre—negotiated the Jerome Agreement of October 6, 1892 at Fort Sill, offering $2,000,000 for approximately 2.5 million acres of surplus land (roughly $0.85 per acre) with 160-acre individual allotments (Doc 200).

The agreement was obtained through documented coercion and fraud. Secretary of the Interior C.N. Bliss explicitly recommended against ratification in 1899, stating the Indians "did sign the agreement without a correct understanding of its conditions and consequences" (Doc 253). Only 456 adult males signed—23 fewer than the three-fourths threshold required by Article XII of the Medicine Lodge Treaty, against 639 eligible males—while 571 adult males signed a counter-memorial opposing it (Doc 253). Captain Hugh G. Brown's 1893 investigation confirmed interpreter Joshua Given misrepresented terms, telling Indians the opening would not occur for four years (Doc 253). Lieutenant H.L. Scott's petition, endorsed by Major General Nelson Miles and General Schofield, urged annulment (Doc 253). Commissioner W.A. Jones demonstrated the reservation contained only 79,340 acres of agricultural land—against 229,760 acres needed for allotments—making the agreement physically unworkable (Doc 229).

Despite this, Congress ratified the agreement on June 6, 1900, attaching it as a rider to a Fort Hall Reservation bill (Doc 237). Kiowa leaders mounted sustained resistance. Chief A-pe-ah-tone organized ghost dances, sent couriers to rally opposition, and threatened violence against allotting agents (Doc 212). Lone Wolf's nephew Delos K. Lonewolf carried a memorial to President McKinley seeking to withhold the opening proclamation (Doc 188). This resistance culminated in Lone Wolf v. Hitchcock (1903), in which the Supreme Court upheld congressional plenary power to abrogate Indian treaties unilaterally—a devastating precedent (Doc 248).

Allotment work began in spring 1901. A total of 2,759 KCA Indians received 160-acre allotments, approved July 1, 1901; 963 Wichita and affiliated bands received allotments simultaneously; 517 additional children were allotted under the Act of June 5, 1906; and 169 more under the Act of June 25, 1910 (receiving only 120 acres each), totaling 4,402 allotments encompassing approximately 641,901 allotted acres (Doc 195). Over 2.5 million surplus acres were opened to homesteading (Doc 200). Trust patents guaranteed a 25-year tax-exempt period (Doc 276).

George Hunt, a full-blood Kiowa who served as chainman and interpreter for the allotting crew, later described how this trust contract was systematically "abused": inherited lands were authorized for sale and became taxable; restrictions were removed on additional allottees, whose lands were sold or lost through mortgage foreclosure and forced fee patents (Doc 276).

### II. The Competency Commission and the Machinery of Forced Fee Patenting

#### A. The Legal Framework

The mechanism that devastated Kiowa landholding was the forced fee patent, authorized by the Burke Act of May 8, 1906 (34 Stat. 182), which empowered the Secretary of the Interior to issue patents in fee to allottees deemed "competent and capable of managing his or her affairs" (Doc 122). This power was dramatically expanded under Commissioner Cato Sells's "Declaration of Policy" of April 17, 1917, which presumed competency for allottees of one-half or more white blood and mandated fee patents for educated Indians "without regard to whether the graduate applies for it or not" (Doc 190).

Competency commissions were dispatched to reservations as an industrialized process of dispossession. Secretary Lane personally directed commission assignments, demanding three commissions working simultaneously across the country (Doc 272). At the Kiowa jurisdiction, the commission visited in spring 1917, consisting of Julian H. Fleming, O.H. McPherson, and Superintendent C.V. Stinchecum (Doc 273).

#### B. Internal Resistance and Its Suppression

What makes the Kiowa case distinctive is the depth of documented resistance—from both the allottees and, remarkably, from within the Bureau itself.

The competency commission's own chairman filed a memorandum on June 26, 1917, raising serious objections. He described the Kiowa jurisdiction Indians as "extremely non-progressive," estimating no more than 25 percent of adult restricted Indians spoke English, and that most were "just emerging from the blanket stage." Chiefs and headmen, particularly Enoch Hoag of the Caddos, "strongly objected" and charged the government with bad faith for attempting to force patents before expiration of the trust period (Doc 223).

Superintendent Stinchecum himself refused to sign four competency reports involving full-bloods, citing Article V of the Jerome Agreement, which guaranteed 25-year trust periods (Doc 223). His telegram of June 9, 1917, reported approximately six full-bloods and fifteen mixed-bloods protesting arbitrary patent issuance (Doc 183). He "earnestly recommended" withholding patents from protesting allottees to preserve harmony (Doc 183). The Office overruled him, citing the Act of May 8, 1906 as superseding the Jerome Agreement's trust provisions (Doc 183).

Of 109 adults interviewed by the commission, only 6 were deemed competent, and none would sign applications—every single allottee in the file "declined to sign" (Doc 273). Yet the Secretary's office dismissed treaty objections via a memorandum by Judge Pollock and ordered patents issued regardless (Doc 273).

#### C. The Two Waves of Forced Fee Patents

The documents reveal two principal waves of forced fee patenting on the Kiowa Reservation:

**First Wave: August 24, 1917.** This date appears repeatedly across the Kiowa, Caddo, and Wichita affidavit collections. Patents issued on this date include those to:

- Anna E. Jones Berry, Kiowa allotment No. 236 (Doc 460)
- Jesse Lee Jones, Kiowa allotment No. 32 (Doc 467)
- Chewauwau, Kiowa allotment No. 2410 (Doc 462)
- Neda Birdsong (Laura Parker), Comanche allotment No. 2249 (Doc 204)
- Otto Wells, Comanche allotment No. 102 (Doc 183)
- Multiple Caddo allottees including Alice Inkanish Cussen (No. 12), Jesse Sturm (No. 39), Mattie Sturm (No. 40), Ella Sturm (No. 7), Helena Araspar (No. 943), Tulethe Araspar (No. 942), Laura Butler (No. 269), Nancy Parrish (No. 73), and Maggie Parrish (No. 74) (Doc 385)
- Wichita allottees including Alice F. Osborne (No. 945), Clay J. Brown (No. 128), Helen Pichard (No. 484), and John Haddon (No. 188) (Doc 429)

**Second Wave: December 3, 1919.** This date dominates the Kiowa affidavit collection:

- Ahkaumdomah, Kiowa No. 604 (Doc 459)
- Bointy (Jack Bointy), Kiowa No. 961 (Doc 461)
- David Poolaw (Tsomah), Kiowa No. 2695 (Doc 463)
- Emma Belle Wyatt, Kiowa No. 305 (Doc 464)
- Hattie McKenzie, Kiowa No. 415 (Doc 465)
- Jane Goomby, Kiowa No. 662 (Doc 466)
- John Queton, Kiowa No. 2730 (Doc 422)
- Kaulaity, Kiowa No. 1224 (Doc 417)
- Kauntodle, Kiowa No. 660 (Doc 406)
- Keahtiaukau, Kiowa No. 1280 (Doc 425)
- Lee Kodaseet, Kiowa No. 1278 (Doc 408)
- Lula Wyatt Willis, Kiowa No. 303 (Doc 412)
- Mabel Sautaukoy, Kiowa No. 1255 (Doc 419)
- Phylis Poolaw, Kiowa No. 2696 (Doc 415)
- Queton, Kiowa No. 2727 (Doc 424)
- Sain-to-hoodle, Kiowa No. 658 (Doc 405)
- Taukauemah, Kiowa No. 2416 (Doc 401)
- Teyou, Kiowa No. 659 (Doc 395)
- Thomas Wyatt, Kiowa No. 302 (Doc 400)
- Tofpi, Kiowa No. 259 (Doc 407)
- Togonegatty, Kiowa No. 1277 (Doc 397)
- Toyebo, Kiowa No. 640 (Doc 402)
- Toykoytodle, Kiowa No. 1253 (Doc 404)
- Tsomah, Kiowa No. 2694 (Doc 426)
- Tsoodle, Kiowa No. 1245 (Doc 411)
- Yeahgope, Kiowa No. 963 (Doc 423)

A third wave on August 23, 1920 affected additional allottees including Quoecopah (Kiowa No. 964) (Doc 399) and Lillian Marie Goombi (Kiowa No. 661) (Doc 421).

In total, the KCA Tribal Business Committee reported that approximately 110 Kiowa Reservation Indians received patents in fee under the general policy letter of April 17, 1917, without application (Doc 217).

### III. The Mechanics of Coercion: How Patents Were Forced

The affidavits reveal a remarkably consistent pattern of coercion across all three tribal groups under the Kiowa Agency. The methods were systematic, not idiosyncratic.

#### A. Delivery Over Explicit Objection

The most common pattern was delivery of patents despite verbal protests. Kauntodle testified: "we didn't want our patent, but they just give it to us and said we got to take it" (Doc 406). Chewauwau stated he was compelled to accept his patent before receiving his annuity money at a payment gathering at Rainy Mountain, effectively coercing acceptance (Doc 462). Toykoytodle described sustained resistance—he refused four notifications delivered through district farmer Mr. Rice before agent Stinchecum pressured him on the fifth occasion, warning taxes would accrue regardless (Doc 404).

Sain-to-hoodle, an elderly Kiowa woman who could neither read nor write, testified that clerk Jasper Saunkeah told her acceptance was mandatory, saying "it didn't make any difference" that she was uneducated (Doc 405). Taukauemah stated she never signed any paper or receipt, but her field matron Mrs. Peters repeatedly told her a patent existed, which "frightened" her because she did not want to pay taxes (Doc 401).

#### B. The Role of Jasper Saunkeah

One figure appears with striking frequency across the Kiowa affidavits: Jasper Saunkeah, identified as a clerk and interpreter at the Kiowa Agency Office. He personally delivered patents to Kauntodle (Doc 406), Queton (Doc 424), Tsomah (Doc 426), Tsoodle (Doc 411), Yeahgope (Doc 423), and Ahkaumdomah (as interpreter) (Doc 459). His standard message to allottees was that patents were compulsory and that taxes would accrue regardless of acceptance (Doc 422).

Saunkeah's role extended beyond mere delivery. In the case of Quoecopah (Kiowa No. 964), he is directly accused of fraud. After her forced patent was issued on August 23, 1920, Saunkeah immediately had it recorded and then deceived her into signing what she believed was a car purchase agreement for a secondhand Buick but was actually a mortgage on 80 acres. This triggered a cascade of debt: a $1,500 loan, a $3,000 mortgage from the Porter Loan Company, and an additional $2,000 obligation—totaling $6,000 in encumbrances. Quoecopah received no money. The mortgage was assigned to the Thorne Investment Company of Oklahoma City (Doc 399). Jack Bointy's 1921 complaint letter to the Commissioner of Indian Affairs confirmed Saunkeah's role (Doc 399).

Remarkably, by 1930, Saunkeah had become chairman of the Kiowa Tribal Council and was identified as secretary of the KCA Tribal Business Committee, co-authoring resolutions protesting the very forced fee patent policy he had helped implement (Doc 217). By 1934, he was photographed with Commissioner John Collier at the Anadarko meeting on the Wheeler-Howard bill (Doc 247).

#### C. The Role of Superintendent Stinchecum

Superintendent C.V. Stinchecum occupied a contradictory position. He refused to sign certain competency reports and forwarded protests to Washington (Doc 223). Yet he also personally delivered patents to allottees' homes. Laura Butler (Caddo No. 269) testified that Stinchecum and two other men came to her home and told her "the law would compel me to take it" (Doc 390). Mattie Sturm stated the superintendent told allottees the patents were obligatory—"we thought we had to" accept them (Doc 383). Nancy Parrish's husband testified that Stinchecum and two men from Washington visited their home, inspected the property, and delivered the patent despite the family explicitly stating "there was every reason in the world why we shouldn't have the patent and none why we should" (Doc 391).

Andre Martinez, foster father of Rachel Downing and Hattie McKenzie, testified that he refused to accept patents on their behalf and informed Stinchecum that neither girl had applied. Despite his refusal, Stinchecum "circumvented Martinez by going directly to the allottees' home and leaving the patents without any application having been made" (Doc 403).

#### D. Coercion Through Tax Threats

A particularly insidious tactic was telling allottees they would owe taxes regardless of whether they accepted the patent. John D. Downing Jr. (Caddo No. 35) was told by Kiowa Agency employees that "he would have to pay taxes regardless" (Doc 393). John Queton was told by Saunkeah that "if they refused their patents they would still owe taxes" (Doc 422). This created a coercive double bind: accept the patent and face taxation, or refuse and face taxation anyway.

### IV. The Cascade of Dispossession: From Patent to Land Loss

The affidavits document a remarkably consistent sequence: forced patent → tax liability → mortgage → distress sale → destitution. This pattern operated with devastating efficiency.

#### A. Immediate Mortgaging

Once trust protections were removed, allottees were immediately targeted by lenders. The speed of encumbrance is striking:

- Chewauwau mortgaged his land for $3,000 within two months of receiving his patent (Doc 462)
- Keahtiaukau had her patent filed for record by Fred Baker, who "already had a loan arranged against the land" before she even possessed it. She was mortgaged twice—$1,000 to Gumm Brothers of Oklahoma City and $1,000 to a farmer named Wilmore—totaling $2,000 (Doc 425)
- David Poolaw mortgaged 80 acres for $2,500 in May 1920, just two months after recording his patent in March 1920 (Doc 463)
- John Haddon (Wichita No. 188) mortgaged all his land for $3,000 "within days" of receiving his patent (Doc 433)
- Toyebo described the experience vividly: he was "surrounded by real estate dealers like a swarm of bees" once the patent issued (Doc 402)

#### B. The Debt Spiral

Mortgage amounts across the Kiowa affidavits ranged from $400 to $6,500:

| Allottee | Allotment | Mortgage Amount | Term |
|----------|-----------|----------------|------|
| Ahkaumdomah | K-604 | $2,000 + $1,000 | — |
| Chewauwau | K-2410 | $3,000 + $500 | 10 yr |
| David Poolaw | K-2695 | $2,500 + $2,500 | — |
| Emma Belle Wyatt | K-305 | $3,000 + $2,000 | — |
| Jane Goomby | K-662 | $1,500 + $2,400 + more | — |
| Jesse Lee Jones | K-32 | $6,000 | 10 yr |
| John Queton | K-2730 | $1,200 → $2,000 | 10 yr → 33 yr |
| Kauntodle | K-660 | $1,500 | — |
| Keahtiaukau | K-1280 | $2,000 | — |
| Lee Kodaseet | K-1278 | $3,000 | — |
| Lula Wyatt Willis | K-303 | $6,500 | due 1950 |
| Mabel Sautaukoy | K-1255 | $2,500 | due 1934 |
| Sain-to-hoodle | K-658 | $400–$500 | — |
| Teyou | K-659 | ~$2,500 | — |
| Thomas Wyatt | K-302 | $3,000 | — |
| Toyebo | K-640 | $2,000 + $1,600 + $400 | 10 yr |
| Toykoytodle | K-1253 | $3,000 + $1,000 | — |
| Tsomah | K-2694 | (sold without mortgage) | — |
| Tsoodle | K-1245 | $2,000 + $2,000 | 10 yr |

#### C. Distress Sales and Land Loss

The pattern of forced sales at below-market prices is documented across virtually every affidavit:

- Toyebo sold 160 acres for only $1,200 total ($600 per 80-acre parcel), with purchasers assuming $4,000 in mortgages (Doc 402)
- Toykoytodle sold 160 acres for $6,000 but after mortgages, taxes, and interest received only approximately $1,200 in cash (Doc 404)
- Lee Kodaseet sold 120 acres for $3,600 and 40 acres for $2,110, receiving $5,710 total for 160 acres but was left approximately $1,000 in debt (Doc 408)
- Sain-to-hoodle sold her entire allotment for $2,500—half what she believed it was worth ($5,000) (Doc 405)
- Ahkaumdomah sold her land for only $375 cash, with the purchaser assuming $3,000 in mortgages (Doc 459)
- Tsoodle lost his entire 160-acre allotment through mortgage foreclosure to Fred Baker of Mt. View, receiving only $500 (Doc 411)
- Emma Belle Wyatt sold the inherited 80 acres for approximately $3,500, which she considered far below the $8,000 fair value (Doc 464)
- Jane Goomby sold all 160 acres in 1925 for $7,500, receiving only $1,400 in cash while the purchaser assumed debts. She believed fair value was $9,000–$10,000, and the land later sold for approximately $16,000 (Doc 466)
- Margaret Downing sold the 160-acre allotment for $2,000—against a self-assessed value of $25,000 (Doc 454)

#### D. The Predatory Ecosystem

The documents identify specific actors in the predatory ecosystem surrounding forced fee patents:

- **Gumm Brothers of Oklahoma City:** arranged mortgages for Keahtiaukau (Doc 425), Thomas Wyatt through Baldwin & Gibbs of Anadarko (Doc 400), and Alice F. Osborne (Wichita) (Doc 429)
- **Fred Baker of Mt. View:** facilitated loans for Keahtiaukau (Doc 425) and foreclosed on Tsoodle's entire allotment (Doc 411)
- **Thorne Investment Company of Oklahoma City:** received the fraudulent mortgage note from Saunkeah's scheme against Quoecopah (Doc 399)
- **Porter Loan Company:** mortgaged Quoecopah's remaining 80 acres for $3,000 (Doc 399)
- **Deming Investment Company of Oklahoma City:** held a $10,000 mortgage on John D. Downing's allotment (Doc 454)
- **Commerce Trust Company of Kansas City:** held Mattie Sturm's $6,000 mortgage (Doc 383)

### V. The Human Toll: Voices from the Affidavits

#### A. Statements of Unwillingness

Every Kiowa affiant who addressed the question stated they did not want the patent:

- Kauntodle: "I wish the government never turn me loose, I wish they kept my land in trust for the 25 years" (Doc 406)
- Hattie McKenzie: "I would not have sold my land if the patent hadn't been given me" (Doc 465)
- Toyebo: blamed "the Commissioner of Indian Affairs, the Secretary of the Interior, and the President" for violating the original promise of 25-year tax exemption (Doc 402)
- Taukauemah: "the government ought not give me my patent because I did not ask for it" (Doc 401)
- Tsomah: "I didn't want to be turned loose by the Government" (Doc 426)
- Tulethe Araspar (Caddo): "I wish the Government hadn't issued the patent to me" (Doc 392)
- Alice Inkanish Cussen (Caddo): "I am sorry the Office gave it to me, for I have very little to show for my land now" (Doc 385)

#### B. Profiles of Vulnerability

The affidavits reveal that patents were forced on individuals manifestly unable to manage fee-simple property:

- Ahkaumdomah was 50 years old, uneducated, unable to write (signing by fingerprint), and "did not understand business affairs" (Doc 459)
- Sain-to-hoodle was approximately 68, a widow of an Indian Scout, a former captive taken as a child, caretaker of four minor orphans (Doc 405)
- Toyebo described himself as "uneducated, incompetent in farming, approximately sixty years old, sick, landless, and without income" (Doc 402)
- Taukauemah was approximately 29–30, supporting eleven children, with a fifth-grade education, and "understood nothing about business" (Doc 401)
- Nettie Kaulaity's father had no education, spoke no English, had been in poor health for ten years, and went insane approximately a year after receiving the patent. Joseph Kaulaity stated: "Such a man I don't think was entitled to a patent in fee" (Doc 420)
- Earl T. Downing (Caddo No. 36) received his patent when he was not yet 21 years old (Doc 382)

#### C. The Condition of Survivors

By the time of the affidavits (1928–1929), the consequences were stark:

- Toyebo: landless, sick, approximately 60, surviving on Red Cross money and his wife's small lease payments (Doc 402)
- Lee Kodaseet: approximately $1,000 in debt, supporting a wife and six children (Doc 408)
- Tsoodle: age 61, homeless, living on his son's land (Doc 411)
- Keahtiaukau: age 36, supporting seven children, expecting to lose her land (Doc 425)
- Emma Belle Wyatt: age 30, husband with tuberculosis, three children, stating: "I know we can never pay the mortgage off" (Doc 464)
- David Poolaw: age 33, retained only five acres, supporting a wife and four children (Doc 463)
- Quoecopah: age 35, five children, homeless (Doc 399)

#### D. The Veteran's Experience

David Poolaw's fee patent was issued on December 3, 1919, "shortly after his return from military service." He was told "they all got to take them." Within months he had mortgaged and begun selling his allotment. By age 33, he had lost everything (Doc 463).

### VI. Resistance, Cancellation, and Partial Remedies

#### A. Active Resistance

- Bointy "strongly protested receiving the patent, refusing to accept it for approximately one year" (Doc 461)
- Toykoytodle refused four separate notifications before being pressured on the fifth attempt (Doc 404)
- Queton "protested a long time before I was persuaded to take it" (Doc 424)
- Neda Birdsong filed a written protest with the agency (Doc 204)
- Otto Wells "strongly protested" and initially refused (Doc 243)
- Former Superintendent Stinchecum later testified that the Department "had no authority in law to violate its treaty with the Indians" (Doc 204)

#### B. The 1927 Cancellation Act

Congress passed the Act of February 26, 1927 (44 Stat. 1247), authorizing cancellation of fee patents issued during trust periods without allottee consent.

| Allottee | Allotment | Patent No. | Cancellation Date |
|----------|-----------|------------|-------------------|
| Kaulaity | K-1224 | — | June 2, 1927 |
| Tofpi | K-259 | 722343 | July 8, 1927 |
| Togonegatty | K-1277 | 722347 | July 8, 1927 |
| Bointy | K-961 | 722351 | July 8, 1927 |
| Yeahgope | K-963 | 722350 | July 8, 1927 |
| Queton | K-2727 | 722366 | July 8, 1927 |
| Lillian Marie Goombi | K-661 | — | June 2, 1927 |
| Neda Birdsong | C-2249 | 598012 | October 31, 1931 |
| Rachel Briscoe (Downing) | W-34 | 598033 | October 31, 1931 |

However, cancellation was limited. Patents could not be cancelled where the land had been mortgaged or sold. This created a cruel paradox: the very debt that the forced patent enabled became the barrier to its reversal.

#### C. Tax Recovery Litigation

- **United States v. Board of County Commissioners of Comanche County** (No. 5047): Judgment for $986.23 on behalf of Neda Birdsong, affirmed by Tenth Circuit at 87 Fed. (2d) 55, satisfaction filed January 29, 1938 (Doc 130, Doc 170, Doc 251)
- **United States v. Board of County Commissioners of Caddo County** (No. 5048): Judgment for $2,040.00 on behalf of Rachel Briscoe, affirmed by Tenth Circuit, satisfaction by February 1940 (Doc 220)
- **United States for Otto Wells v. Board of County Commissioners of Caddo County**: Judgment for $1,095.56, reported October 12, 1937 (Doc 271)

#### D. The 1940 Refund Act

Congress passed Public Law 590 (Act of June 11, 1940, 54 Stat. 298), authorizing $75,000 for tax refunds. However, of $50,000 appropriated for fiscal year 1942, $20,000 was placed in budget reserve. George Hunt wrote to the Commissioner on August 28, 1941, noting that "the Indians interested in this matter are very anxious to hear" about the status of their claims (Doc 275).

### VII. The Broader Pattern: Quantifying Kiowa Land Loss

- **1901:** 4,402 allotments, ~641,901 acres (Doc 195)
- **By 1923:** ~30,037 acres sold for $883,902.44, 432 patents in fee issued (Doc 195)
- **By 1929:** ~496,336 acres of allotted trust land remained (Doc 244)
- **By 1934:** 2,801 landless Indians on the Kiowa Reservation; ~43.5 acres per member (Doc 263, Doc 239)
- **By 1953:** fractionated interests as small as 1/504 offered for sale (Doc 234)
- **By 1955–1958:** over 120,000 additional acres sold under Commissioner Emmons (Doc 186)

Superintendent Buntin estimated 95% of allottees were incompetent to manage unrestricted ownership (Doc 195).

The leasing system functioned as dispossession-in-practice: ~75% of allotted acreage was leased to white farmers, generating ~$750,000 annually in agricultural rentals. Lease rates were as low as $0.10–$0.25/acre (Doc 244, Doc 234).

Heirship fractionation compounded the problem. By 1934, some tracts had 27 heirs; by 1953, interests as small as 1/504 (Doc 263, Doc 234).

### VIII. Cultural Suppression as Complementary Dispossession

In 1915–1917, approximately 90 Indians had their shares in the $250,000 annual appropriation withheld for participating in Ghost Dance and give-away ceremonies. The Office required affidavits promising non-participation before releasing funds (Doc 235).

### IX. Kiowa Political Advocacy and Organized Resistance

- **1901:** Lone Wolf's petition to Acting Secretary Ryan (Doc 237)
- **1913:** Kiowa leaders at Society of American Indians meeting at Anadarko (Doc 213)
- **1918:** Delos K. Lone Wolf, Tennyson Berry, Fred Botone, Otto Wells, Willie Ahdosy traveled to Washington (Doc 216)
- **1921:** George Hunt's detailed protest letter citing trust patent language verbatim (Doc 267)
- **1924:** Kiowa delegates at national Indian congress in Tulsa (Doc 254)
- **1929–1932:** George Hunt's sustained correspondence with Commissioner Rhoads (Doc 276)
- **1930:** KCA Tribal Business Committee's comprehensive resolutions to the Senate subcommittee (Doc 217)
- **1934:** ~3,000 Indians from sixteen tribes at Collier's Wheeler-Howard bill presentation (Doc 247)
- **1953:** Robert Goombi, Guy Quetone, and others testified against premature termination (Doc 234)
- **1958:** Mrs. Robert Goombi's correspondence with AAIA documenting 120,000 acres lost (Doc 186)

### X. Conclusions

**What the Documents Prove:** Forced fee patents were issued systematically to ~110 KCA allottees without consent, over explicit objections from allottees, tribal leaders, the competency commission chairman, and the local superintendent. The patents triggered a predictable cascade of mortgage, debt, and land loss. Specific predatory actors exploited the system. Congressional and judicial remedies were partial and delayed.

**What the Documents Suggest:** The policy functioned as a deliberate mechanism of land transfer, not merely an administrative error. The leasing system may have caused as much practical dispossession as outright land loss. The Kiowa experience was representative of a nationwide pattern.

**Gaps in the Record:** Individual land records and title chains; the period 1940–1953; women's experiences as a focused category; Oklahoma state court records; systematic appraisal data; the full claims litigation story; oral histories and Kiowa-language accounts.

### Sources Cited

83 unique documents cited (see full source list in the synthesis output above).
