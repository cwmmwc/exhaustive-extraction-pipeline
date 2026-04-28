You are extracting structured data from a fee patent ledger — a tabular register compiled by an Indian agency listing allottees, their allotments, fee patent dates, and application status. Each row in the ledger is a separate fee patent record. Multiple rows may refer to the same person if they had multiple allotments; each row is still a distinct record.

The ledger is organized into sections by Township and Range. Within each section, rows list: allotment number (possibly with letter suffix like "922a" or hyphenated like "1334-284"), name, year of patent, application status, and occasionally notes about patent delivery, file references, or special circumstances.

Extract every row as a separate record. Use the following 18 fields. Use "not stated" when the ledger does not contain the information (most fields will be "not stated" for ledger entries — this is expected and correct).

- **Name**: The allottee's name as listed in the row
- **Tribe/Reservation**: The agency name if identifiable from the ledger header or letterhead (e.g., "Fort Berthold Indian Agency")
- **Post Office Address**: Usually "not stated" for ledger entries
- **Allotment number**: The allotment number including letter suffixes or hyphenation (e.g., "777," "922a," "1334-284")
- **Cancelled**: Usually "not stated" unless the row explicitly notes cancellation
- **Refused/Protested**: The application status in EXACT SOURCE LANGUAGE. Preserve verbatim (e.g., "No application," "Application on file," "Signed application on file," "Application not on file," "No application on file"). Do not paraphrase. Do not translate "No application" into "Refused" or "Forced."
- **Recorded patent**: Any notes about patent delivery from the row (e.g., "Fee Patent No. 611264 delivered to patentee by F. E. Brandon, 11-22-17"). Otherwise "not stated."
- **Sold/Mortgaged**: Usually "not stated" unless the row notes "Sold" or similar (e.g., "Sold. Appli. on file")
- **Buyer**: Usually "not stated" for ledger entries
- **Tax burden forced sale/Mortgage**: Usually "not stated"
- **Trust Patent Date**: Usually "not stated" — ledgers track fee patents, not trust patents
- **Fee Patent Date**: The year as listed (e.g., "1919," "1916"). If a full date is given (e.g., "11-21-19," "3-13-20"), preserve the full date.
- **Gender**: Usually "not stated" for ledger entries
- **Age**: Usually "not stated" for ledger entries
- **Occupation/Income**: Usually "not stated" for ledger entries
- **NOTES**: Township and Range from the section header (e.g., "Township 146 Range 88"). Also any additional notes in the row (e.g., "Partitioned," "Heirship," file reference numbers like "Reference 127874-14. 115924-14," cross-references to other allotment numbers like "Application for Allot. No. 726 on file. Receipts for other patents, 1645, 922a, attached")
- **Literate/Illiterate**: Usually "not stated" for ledger entries. If the row notes a thumb mark or signature method, note it.
- **Document type**: Always "ledger_entry" for these records

**Critical instructions:**

- Every row is a distinct record. If Reuben Duckett appears twice with two different allotments (1645 and 922a), produce two records. Do not combine them. Each patent is one record.
- Preserve the Township and Range headers in the NOTES field for every row in that section. The ledger's geographic organization is research-relevant.
- Preserve exact source language for Refused/Protested. Do not interpret. "No application" stays "No application." "Application on file" stays "Application on file."
- OCR of column-aligned ledger text sometimes separates allotment numbers from their corresponding names. If the allotment number for a given row is unclear or absent in the source, use "unknown" for that field rather than guessing. Do not assign the previous or next row's allotment number to a row whose number is unclear.
- Return a JSON array of records, one object per row, each with all 18 fields.

**Example output (two rows from Fort Berthold ledger, Township 146 Range 89):**

```json
[
  {
    "Name": "Reuben Duckett",
    "Tribe/Reservation": "Fort Berthold Indian Agency",
    "Post Office Address": "not stated",
    "Allotment number": "1645",
    "Cancelled": "not stated",
    "Refused/Protested": "No application",
    "Recorded patent": "not stated",
    "Sold/Mortgaged": "not stated",
    "Buyer": "not stated",
    "Tax burden forced sale/Mortgage": "not stated",
    "Trust Patent Date": "not stated",
    "Fee Patent Date": "11-21-19",
    "Gender": "not stated",
    "Age": "not stated",
    "Occupation/Income": "not stated",
    "NOTES": "Township 146 Range 89",
    "Literate/Illiterate": "not stated",
    "Document type": "ledger_entry"
  },
  {
    "Name": "Reuben Duckett",
    "Tribe/Reservation": "Fort Berthold Indian Agency",
    "Post Office Address": "not stated",
    "Allotment number": "922a",
    "Cancelled": "not stated",
    "Refused/Protested": "Application for Allot. No. 726 on file",
    "Recorded patent": "not stated",
    "Sold/Mortgaged": "not stated",
    "Buyer": "not stated",
    "Tax burden forced sale/Mortgage": "not stated",
    "Trust Patent Date": "not stated",
    "Fee Patent Date": "11-21-19",
    "Gender": "not stated",
    "Age": "not stated",
    "Occupation/Income": "not stated",
    "NOTES": "Township 146 Range 89. Receipts for other patents, 1645, 922a, attached",
    "Literate/Illiterate": "not stated",
    "Document type": "ledger_entry"
  }
]
```

Return the JSON array only, with no additional text.
