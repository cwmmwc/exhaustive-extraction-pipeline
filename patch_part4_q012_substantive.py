#!/usr/bin/env python3
"""
Apply substantive content from Sonnet vision extraction to
part4_questionnaire_012 (Alphonse Charbonneau).

The earlier identification patch (identify_part4_q012_charbonneau.py) only
filled in name, allotment, tribe — losing the substantive questionnaire
content. This patch adds the full content from running Sonnet vision on
the source PDF (validation_samples/part4_q012_vision/vision_merged.json),
extracted on 2026-05-02.

Key substantive findings:
  - Allotment 1466 (confirmed across Sonnet vision + Kimi v3/v4/v5)
  - Patent mechanism: APPLICATION — he applied for the patent himself
  - Patent received: mailed to him at Valentine, NE in 1918
  - Patent acceptance: signed a receipt for it; accepted WITHOUT PROTEST
  - Document notarized: June 11, 1929, Cherry County, Nebraska
  - Land sale: NW 1/4 sold for $7,000 cash (buyer unknown, date unknown)
  - Q7 response: states he still owns the land (apparent inconsistency
    with the NW 1/4 sale — possibly a different parcel, possibly post-
    sale framing)
  - Personal: in good health, no dependents, self-supported by farming

Analytical significance: the application-and-no-protest combination
goes against the predominant narrative of Circular 2464 (forced fee
patents). Charbonneau's record represents a case where the allottee
voluntarily applied, received, and accepted the patent.

The earlier Kimi v5 extraction of part 4 reported $2000 sale to Jesse
E. Keeler in 1924. The Sonnet vision shows a $7000 sale of NW 1/4 with
buyer unknown. These may be:
  - The same transaction with different details
  - Two separate sales (one of NW 1/4 for $7000, another to Keeler for $2000)
  - The Kimi $2000 figure being a partial payment or different parcel
This warrants future cross-reference against BLM patent records and the
agency narrative record (part4_agency_narrative_016).
"""
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
RECORD_PATH = (
    PROJECT_ROOT
    / "circular_2464_extractions"
    / "extractions"
    / "sonnet"
    / "part4_questionnaire_012.json"
)


def main():
    with open(RECORD_PATH) as f:
        record = json.load(f)
    e = record["extraction"]
    if isinstance(e, list):
        print("ERROR: list-shaped extraction")
        return

    previous_notes = e.get("NOTES", "")

    # Update structured fields with the most accurate data from Sonnet vision
    e["Name"] = "Alphonse M. Charbonneau"  # full signed name from notary block
    e["Allotment number"] = "1466"
    e["Tribe/Reservation"] = "Rosebud Sioux"
    e["Post Office Address"] = "Valentine, Nebraska"
    e["Date"] = "1929-06-11"
    e["Document type"] = "questionnaire"

    # Add substantive content as enriched NOTES
    substantive_content = (
        " | TASK 5 PART 4 SUBSTANTIVE EXTRACTION 2026-05-02 (SONNET VISION): "
        "Sonnet vision extraction of source PDF replaces thin Sonnet text "
        "extraction which had Name='not stated' and Allotment='not stated'. "
        "Vision extraction file: validation_samples/part4_q012_vision/"
        "vision_merged.json. "
        "ALLOTMENT 1466 confirmed (also confirmed by Kimi v3/v4/v5). "
        "PATENT MECHANISM: Charbonneau APPLIED for the fee patent himself "
        "(not government-initiated forced fee). "
        "PATENT RECEIPT: Patent was mailed to him at Valentine, Nebraska in "
        "1918. He signed a receipt for it. Accepted WITHOUT PROTEST. "
        "NOTARIZATION: Document notarized June 11, 1929 in Cherry County, "
        "Nebraska, where Charbonneau personally appeared before the notary. "
        "SALE: NW 1/4 sold for $7,000 cash (buyer name not captured by "
        "vision extraction; date not specified). "
        "Q7 RESPONSE: States he still owns the land — apparent inconsistency "
        "with the NW 1/4 sale; possibly a different parcel from the same "
        "allotment, or framing-dependent. "
        "PERSONAL: In good health, no dependents, self-supported by farming. "
        "ANALYTICAL NOTE: This case (voluntary application, no protest, "
        "signed receipt) is meaningfully different from the predominantly "
        "involuntary fee patent narrative of Circular 2464. Worth "
        "preserving the distinction in any aggregate analysis. "
        "CROSS-REFERENCE: Companion record at part4_agency_narrative_016 "
        "(agency's own version of his case). Cross-referenced from "
        "part3_agency_narrative_014 (Mary Julia Neiss) which originally "
        "noted Alphonse as adjacent allottee 1466. "
        "DISCREPANCY WITH KIMI v5: Kimi v5 reports a $2000 sale to Jesse "
        "E. Keeler on April 2, 1924, with patent recorded by Tri County "
        "Abstract Company on April 18, 1924. Sonnet vision reports a $7000 "
        "NW 1/4 sale (buyer unknown). These may be the same transaction "
        "with different details, or separate transactions. Worth "
        "future cross-reference against BLM patent records."
    )
    e["NOTES"] = (previous_notes or "") + substantive_content

    record.setdefault("recovery_notes", []).append({
        "date": "2026-05-02",
        "type": "task5_part4_sonnet_vision_substantive_extraction",
        "method": "claude_sonnet_4_6_vision_on_handwritten_pdf",
        "fields_corrected": [
            "Name", "Allotment number", "Tribe/Reservation",
            "Post Office Address", "Date", "Document type", "NOTES",
        ],
        "vision_extraction_path": (
            "validation_samples/part4_q012_vision/vision_merged.json"
        ),
        "substantive_findings": {
            "patent_mechanism": "application (voluntary)",
            "patent_received": "mailed to Valentine NE 1918",
            "patent_acceptance": "signed receipt, no protest",
            "notarization": "1929-06-11 Cherry County NE",
            "land_sale_per_questionnaire": "NW 1/4 for $7000 cash",
            "land_sale_per_kimi_v5": "$2000 to Jesse E. Keeler 1924-04-02",
            "personal": "good health, no dependents, supported by farming",
            "q7_apparent_inconsistency": (
                "states still owns land but also reports NW 1/4 sale"
            ),
        },
        "rationale": (
            "Sonnet text-extraction failed completely on this handwritten "
            "questionnaire. Sonnet vision (rendered PDF as PNG, sent to "
            "Claude vision API) succeeded in extracting full substantive "
            "content. This is the corpus's first per-record use of Sonnet "
            "vision recovery (vs. Qwen vision which has been used for "
            "ledger/tabular content). The success suggests Sonnet vision "
            "is a viable recovery path for handwritten questionnaire "
            "responses where text extraction fails."
        ),
        "user_confirmed": True,
    })

    with open(RECORD_PATH, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print("Patched part4_questionnaire_012 with full substantive content:")
    print(f"  Name:      {e['Name']}")
    print(f"  Allotment: {e['Allotment number']}")
    print(f"  Tribe:     {e['Tribe/Reservation']}")
    print(f"  PO:        {e['Post Office Address']}")
    print(f"  Date:      {e['Date']}")
    print(f"  Document:  {e['Document type']}")
    print()
    print("Substantive content captured in NOTES:")
    print("  - Patent mechanism: APPLICATION (voluntary)")
    print("  - Patent receipt: signed, no protest")
    print("  - Land sale: NW 1/4 for $7000")
    print("  - Q7 apparent inconsistency flagged")
    print("  - Cross-references to agency_narrative_016 and Mary Julia Neiss")


if __name__ == "__main__":
    main()
