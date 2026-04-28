# Retired: part11_ledger_page_01 through _page_14 (Sonnet text extraction)

Retired on: 2026-04-21

Reason: Three-way source verification established that the current text-extraction
ledger has pervasive row-integrity issues from OCR column misalignment. Qwen2.5-VL-72B
vision extraction produces the correct name-to-allotment bindings on every disputed
field verified against source images.

Superseded by: extractions/sonnet/part11_ledger_page_01.json .. _page_14.json
(new files based on Qwen vision output, with seven character-OCR patches and nine
dual-allotment NOTES annotations applied)

Record count change: 311 (text) → 277 (vision), with 34-record gap accounted for
entirely by OCR artifacts and duplicates (per page-by-page verification).

Audit trail: vision_test/qwen_full_ledger/validation/
