You are extracting structured data from a document in the Circular 2464 corpus — records about Indian allottees who received fee patents on their land. The document you are extracting from is one of three types:

- **Affidavit**: sworn first-person testimony by the allottee or their heir, taken before a notary public
- **Questionnaire**: printed question form with the allottee's answers filled in, notarized at the end
- **Agency narrative**: third-person account written by agency staff describing the patent and related transactions for one allottee

Extract the following 18 fields. Use "not stated" as the value when the document does not contain the information. Do not invent, infer, or guess values.

- **Name**: The allottee's full name as it appears in the document
- **Tribe/Reservation**: The tribe or reservation (e.g., "Pine Ridge Agency," "Rosebud Sioux," "Kiowa Agency")
- **Post Office Address**: The allottee's stated post office address
- **Allotment number**: The allotment number, including any letter suffix (e.g., "3913," "922a," "1334-284")
- **Cancelled**: Whether the patent was cancelled, in exact source language (e.g., "Yes," "No," "Not stated," or verbatim agency text describing cancellation)
- **Refused/Protested**: The allottee's stated consent status or the agency's record of it, in EXACT SOURCE LANGUAGE. Preserve verbatim phrasing (e.g., "did not want this patent but was told he would be forced to take it," "with protest," "without protest," "No application," "Application on file"). Do not paraphrase or translate.
- **Recorded patent**: Whether the patent was recorded, where, and by whom if stated (e.g., "Recorded patent at Kadoka, SD" or "Wells did not record patent and does not know who did")
- **Sold/Mortgaged**: What happened to the land (e.g., "Sold," "Mortgaged," "Mortgaged and sold," "Land has not been sold," exact source language)
- **Buyer**: Who bought or foreclosed on the land, with price and details if stated (e.g., "Mortgaged to Ed Ross of Gordon, Nebraska for $1,600," "Sold to A. V. Watson for $1.00")
- **Tax burden forced sale/Mortgage**: Whether taxes or tax burden forced sale or mortgage (e.g., "Unable to pay the mortgage and land was foreclosed," "got behind in taxes and mortgaged")
- **Trust Patent Date**: The original trust patent date if stated
- **Fee Patent Date**: The fee patent date (e.g., "March 12, 1920," "1919")
- **Gender**: Male or Female if stated
- **Age**: The allottee's age at time of document (e.g., "46 years old," "48")
- **Occupation/Income**: Source of income and occupation (e.g., "Income from cattle and odd jobs like common labor," "By my labor," "Day laborer")
- **NOTES**: Additional context including family, health, dependents, or document-specific details (e.g., "mentally competent and in good health; has wife and three minor children to support; wife has poor health," patent numbers, file references, cross-references)
- **Literate/Illiterate**: Whether the document indicates literacy. "Not stated" if no indication. If the deponent signed with an "X" mark, note that.
- **Document type**: "affidavit," "questionnaire," or "agency_narrative" — set based on what you are told this document is

**Critical instructions:**

- For **Refused/Protested**, preserve the exact wording of the document. If Ben Irving's affidavit says "did not want his patent to his allotment of 320 acres, but was told that he would be forced to take it, so he accepted it," that is the value. Do not shorten it to "protested" or expand it to "refused under coercion."
- If a field is not addressed in the document, return **"not stated."** Do not infer. An affidavit that doesn't mention literacy has "Literate/Illiterate: not stated." It does not mean the person was literate.
- For agency narratives (third-person accounts), most first-person fields (Refused/Protested, Age, Occupation/Income, health details in NOTES, Literate/Illiterate) will typically be "not stated" because the document doesn't record that information. Do not hallucinate content to populate these fields.
- Return the result as a single JSON object with all 18 fields.

**Example (affidavit — Ben Irving, Pine Ridge No. 18):**

```json
{
  "Name": "Ben Irving",
  "Tribe/Reservation": "Pine Ridge",
  "Post Office Address": "Pine Ridge, South Dakota",
  "Allotment number": "not stated",
  "Cancelled": "not stated",
  "Refused/Protested": "did not want his patent to his allotment of 320 acres, but was told that he would be forced to take it, so he accepted it",
  "Recorded patent": "not stated",
  "Sold/Mortgaged": "sold his allotment, in 1919, for $3200.00, $1600.00 cash, and the other $1600.00 went in on a car deal",
  "Buyer": "not stated",
  "Tax burden forced sale/Mortgage": "when he sold his place he paid the delinquent taxes",
  "Trust Patent Date": "not stated",
  "Fee Patent Date": "not stated",
  "Gender": "Male",
  "Age": "46 years old",
  "Occupation/Income": "only source of income is what he can make as a day laborer",
  "NOTES": "mentally competent, has good health; has a wife and three minor children to support; wife has poor health, being troubled with her heart, and one child is troubled with a bone disease; has never received any help from the County or Government",
  "Literate/Illiterate": "not stated",
  "Document type": "affidavit"
}
```

**Example (agency narrative — Grace Burnette Giroux, Allotment 2406):**

```json
{
  "Name": "Grace Burnette Giroux",
  "Tribe/Reservation": "Rosebud",
  "Post Office Address": "not stated",
  "Allotment number": "2406",
  "Cancelled": "not stated",
  "Refused/Protested": "not stated",
  "Recorded patent": "The receipt for the patent was signed April 5, 1920, by P. J. Navin",
  "Sold/Mortgaged": "Sold",
  "Buyer": "Grace Burnette Giroux and Vern Giroux conveyed to A. V. Watson for $1.00 and other valuable consideration",
  "Tax burden forced sale/Mortgage": "not stated",
  "Trust Patent Date": "not stated",
  "Fee Patent Date": "March 12, 1920",
  "Gender": "not stated",
  "Age": "not stated",
  "Occupation/Income": "not stated",
  "NOTES": "Fee patent No. 739657 issued; Northwest quarter section 21, township 43, north of range 30; conveyance dated July 24, 1920",
  "Literate/Illiterate": "not stated",
  "Document type": "agency_narrative"
}
```

Return the JSON object only, with no additional text.
