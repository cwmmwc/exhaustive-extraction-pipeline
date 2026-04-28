"""Align the NARA 90-2-5 case file spreadsheet with the unified DOJ
index cards database.

For every Case File number in
  Class 90-2-5 - RG 60 A1-COR 90-2-5 (Indian Matters Tax on Indian Land) Litigation Case Files.xlsx
this script queries `unified_index_cards.slips WHERE file_number = ?`
and writes a brief description into new columns appended to the end
of Sheet1. The original columns are preserved untouched.

Output is saved to a NEW workbook so the source file is never modified.

New columns appended:
  - Slip Count           — total slips in unified DB for this file_number
  - Date Range           — earliest – latest dated slip
  - Cases at File Number — value from cases.cases_at_file_number (master-file flag)
  - Top Case Names       — up to 3 most-frequent case_name strings
  - Top Correspondents   — up to 5 most-frequent correspondents
  - Named Persons        — up to 8 distinct allottee_names
  - Subject Sample       — first 2 non-empty subject lines
  - Sonnet/Qwen Split    — e.g., "12 sonnet+qwen / 4 sonnet-only / 7 qwen-only" (last column)

Also fills in original columns E (Tribe/Reservation), F (State), and
G (County) from the unified DB's cases table where the original
spreadsheet left them blank.

Run:
    python align_nara_90_2_5.py
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter
from typing import Dict, List, Optional, Tuple

import openpyxl
import psycopg2
import psycopg2.extras


SOURCE_XLSX = (
    "/Users/cwm6W/Databases/Land Sales.dtBase2/Files.noindex/xlsx/8/"
    "Class 90-2-5 - RG 60 A1-COR 90-2-5 (Indian Matters Tax on Indian Land) "
    "Litigation Case Files.xlsx"
)

OUTPUT_XLSX = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "Class 90-2-5 — aligned with unified_index_cards.xlsx",
)

DB_NAME = "unified_index_cards"

NEW_COLUMNS = [
    "Slip Count",
    "Date Range",
    "Cases at File Number",
    "Top Case Names",
    "Top Correspondents",
    "Named Persons",
    "Subject Sample",
    "Sonnet/Qwen Split",  # last column — least important for quick reading
]


def db_connect():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=os.environ.get("USER", "cwm6W"),
        host="localhost",
    )


def normalize_file_number(raw) -> Optional[str]:
    """The spreadsheet uses formats like '90-2-5-1' or '90-2-5-49-1'.
    The unified DB uses the same format. Strip whitespace; return None
    for empties or values that don't look like a 90-2-5 file number.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Accept things matching ^90-2-5(-\d+)+$
    if re.fullmatch(r"90-2-5(?:-\d+)+", s):
        return s
    return None


def first_nonempty(items: List[Optional[str]]) -> List[str]:
    return [str(x).strip() for x in items if x is not None and str(x).strip()]


def fetch_slips(cur, file_number: str) -> List[Dict]:
    cur.execute(
        """
        SELECT s.file_number, s.date, s.correspondent, s.case_name,
               s.subject, s.allottee_name, s.extraction_source
        FROM slips s
        WHERE s.file_number = %s
        """,
        [file_number],
    )
    return [dict(r) for r in cur.fetchall()]


def fetch_case_meta(cur, file_number: str) -> Optional[Dict]:
    cur.execute(
        """
        SELECT canonical_case_name, cases_at_file_number, distinct_persons_count,
               sonnet_slip_count, qwen_slip_count
        FROM cases
        WHERE file_number = %s
        """,
        [file_number],
    )
    row = cur.fetchone()
    return dict(row) if row else None


_DATE_RX = re.compile(r"(1[89]\d{2}|20[0-2]\d)")


def date_range(slips: List[Dict]) -> str:
    """Best-effort date range. Slip `date` fields are free-text strings,
    so we extract the four-digit year as a stable sort key and bracket
    the earliest/latest non-empty date verbatim.
    """
    dated = [(s.get("date") or "").strip() for s in slips]
    dated = [d for d in dated if d]
    if not dated:
        return ""
    keyed = []
    for d in dated:
        m = _DATE_RX.search(d)
        if m:
            keyed.append((int(m.group(1)), d))
    if not keyed:
        return f"{dated[0]} … {dated[-1]}"
    keyed.sort()
    earliest = keyed[0][1]
    latest = keyed[-1][1]
    if earliest == latest:
        return earliest
    return f"{earliest} – {latest}"


def top_n(values: List[Optional[str]], n: int) -> str:
    cleaned = first_nonempty(values)
    if not cleaned:
        return ""
    counts = Counter(cleaned)
    return "; ".join(f"{name} ({c})" for name, c in counts.most_common(n))


def split_summary(slips: List[Dict]) -> str:
    c = Counter(s.get("extraction_source", "") for s in slips)
    parts = []
    for k in ("sonnet+qwen", "sonnet-only", "qwen-only"):
        if c.get(k):
            parts.append(f"{c[k]} {k}")
    return " / ".join(parts)


def subject_sample(slips: List[Dict], n: int = 2) -> str:
    subjects = first_nonempty([s.get("subject") for s in slips])
    if not subjects:
        return ""
    seen = []
    for s in subjects:
        if s not in seen:
            seen.append(s)
        if len(seen) >= n:
            break
    return " | ".join(seen)


def fetch_case_location(cur, file_number: str) -> Dict[str, str]:
    """Pull state/county/tribe from the cases table for filling in
    the original spreadsheet's empty E/F/G columns."""
    cur.execute(
        """
        SELECT jurisdiction, county, tribe_or_reservation
        FROM cases
        WHERE file_number = %s
        """,
        [file_number],
    )
    row = cur.fetchone()
    if not row:
        return {"state": "", "county": "", "tribe": ""}
    return {
        "state": (row.get("jurisdiction") or "").strip(),
        "county": (row.get("county") or "").strip(),
        "tribe": (row.get("tribe_or_reservation") or "").strip(),
    }


def build_row_summary(cur, file_number: str) -> Dict[str, str]:
    slips = fetch_slips(cur, file_number)
    if not slips:
        return {col: "" for col in NEW_COLUMNS} | {"Slip Count": "0"}

    case_meta = fetch_case_meta(cur, file_number) or {}

    return {
        "Slip Count": str(len(slips)),
        "Sonnet/Qwen Split": split_summary(slips),
        "Date Range": date_range(slips),
        "Cases at File Number": str(case_meta.get("cases_at_file_number", "") or ""),
        "Top Case Names": top_n([s.get("case_name") for s in slips], 3),
        "Top Correspondents": top_n([s.get("correspondent") for s in slips], 5),
        "Named Persons": top_n([s.get("allottee_name") for s in slips], 8),
        "Subject Sample": subject_sample(slips, 2),
    }


def main() -> int:
    if not os.path.exists(SOURCE_XLSX):
        print(f"ERROR: source not found: {SOURCE_XLSX}", file=sys.stderr)
        return 1

    print(f"Loading {SOURCE_XLSX}")
    wb = openpyxl.load_workbook(SOURCE_XLSX)
    ws = wb["Sheet1"]

    # Header row: append our new columns at the end
    existing_max_col = ws.max_column
    for offset, col_name in enumerate(NEW_COLUMNS, start=1):
        ws.cell(row=1, column=existing_max_col + offset, value=col_name)

    conn = db_connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    matched = 0
    missing = 0
    skipped = 0

    for r in range(2, ws.max_row + 1):
        case_file_raw = ws.cell(row=r, column=2).value  # column B = "Case File"
        fn = normalize_file_number(case_file_raw)
        if not fn:
            skipped += 1
            continue

        summary = build_row_summary(cur, fn)
        if summary.get("Slip Count") == "0":
            missing += 1
        else:
            matched += 1

        # Fill in original columns E (Tribe/Reservation), F (State),
        # G (County) from unified DB when the spreadsheet left them blank.
        loc = fetch_case_location(cur, fn)
        if not ws.cell(row=r, column=5).value and loc["tribe"]:
            ws.cell(row=r, column=5, value=loc["tribe"])
        if not ws.cell(row=r, column=6).value and loc["state"]:
            ws.cell(row=r, column=6, value=loc["state"])
        if not ws.cell(row=r, column=7).value and loc["county"]:
            ws.cell(row=r, column=7, value=loc["county"])

        for offset, col_name in enumerate(NEW_COLUMNS, start=1):
            ws.cell(
                row=r,
                column=existing_max_col + offset,
                value=summary.get(col_name, ""),
            )

    cur.close()
    conn.close()

    print(f"Saving {OUTPUT_XLSX}")
    wb.save(OUTPUT_XLSX)

    print()
    print(f"Matched (slips found):    {matched}")
    print(f"Missing (no slips in DB): {missing}")
    print(f"Skipped (blank/non-case): {skipped}")
    print(f"Output: {OUTPUT_XLSX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
