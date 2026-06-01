#!/usr/bin/env python3
"""
CAT_1 Sonnet-only arbitration triage helper.

For each of the 26 CAT_1 records, prints:
  - Sonnet vision's name + allotment guesses (with source_page reference)
  - Existing corpus record's Document type and PO Address (for context)
  - Path to the source PNGs
  - An `open` command you can copy/paste to view all pages for that record
  - A blank line for source review notes

Also writes cat1_sonnet_arbitration.tsv with one row per record so you
can fill in your source-review findings as you go through them.

Workflow per record:
  1. Run this script (once)
  2. For record N:
     - Open the source PNGs (the script prints the open command)
     - Read the Sonnet vision guess (the script prints it)
     - Compare to source; decide name/allotment/tribe/PO
     - Tell Claude the answer; Claude writes the patch
"""
import csv
import json
from pathlib import Path

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
EXTRACTIONS = PROJECT_ROOT / "circular_2464_extractions" / "extractions" / "sonnet"
SONNET_VISION_BASE = PROJECT_ROOT / "validation_samples" / "cat1_sonnet_vision"
IMAGES_BASE = PROJECT_ROOT / "circular_2464_extractions" / "vision_recovery_cat1" / "images"
MANIFEST = PROJECT_ROOT / "circular_2464_extractions" / "vision_recovery_cat1" / "manifest.csv"
OUTPUT_TSV = PROJECT_ROOT / "cat1_sonnet_arbitration.tsv"


def get_sonnet_guess(rid):
    """Return name/allotment guess from Sonnet vision."""
    path = SONNET_VISION_BASE / rid / "vision_merged.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return None

    name = None
    allot = None
    source_page = None
    note = None

    fee_patents = data.get("fee_patents") or []
    if fee_patents:
        fp = fee_patents[0]
        name = fp.get("allottee_name") or None
        allot = fp.get("allotment_number") or None
        source_page = fp.get("source_page") or None
        if len(fee_patents) > 1:
            note = f"vision found {len(fee_patents)} fee_patents (possible bundle?)"

    if not name:
        for ent in data.get("entities") or []:
            if ent.get("type") == "person":
                name = ent.get("name") or None
                source_page = source_page or ent.get("source_page")
                note = note or "fallback to entities[person]"
                break

    return {
        "name": name,
        "allot": allot,
        "source_page": source_page,
        "note": note,
    }


def get_corpus_context(rid):
    """Get existing corpus record's doc type and PO."""
    path = EXTRACTIONS / f"{rid}.json"
    with open(path) as f:
        d = json.load(f)
    e = d.get("extraction", {}) or {}
    if isinstance(e, list):
        e = e[0] if e else {}
    return {
        "doc_type": e.get("Document type", ""),
        "po": e.get("Post Office Address", ""),
    }


def get_image_paths(rid):
    """List PNG paths for this record."""
    return sorted(IMAGES_BASE.glob(f"{rid}-*.png"))


def main():
    if not MANIFEST.exists():
        print(f"ERROR: manifest not found")
        return

    seen = set()
    rids = []
    with open(MANIFEST) as f:
        for row in csv.DictReader(f):
            rid = row["record_id"]
            if rid in seen:
                continue
            seen.add(rid)
            rids.append(rid)

    print("=" * 80)
    print(f"CAT_1 SONNET-ONLY ARBITRATION — {len(rids)} records")
    print("=" * 80)
    print()
    print("Workflow per record:")
    print("  1. Copy the `open` command and view source PNGs")
    print("  2. Compare to Sonnet vision's guess (printed below)")
    print("  3. Tell Claude what the source actually says")
    print("  4. Claude writes the patch")
    print()
    print("Patch template Claude will use:")
    print("  Name = <source name>")
    print("  Allotment number = <source allotment, or 'not stated' if absent>")
    print("  Tribe/Reservation = <inferred or known tribe>")
    print("  Post Office Address = <source PO if visible>")
    print("  NOTES = <existing notes> + arbitration audit trail")
    print()

    rows = []
    for i, rid in enumerate(rids, 1):
        sonnet = get_sonnet_guess(rid) or {}
        corpus = get_corpus_context(rid)
        pngs = get_image_paths(rid)

        sonnet_name = sonnet.get("name") or "(none)"
        sonnet_allot = sonnet.get("allot") or "(none)"
        sonnet_pages = sonnet.get("source_page") or "?"
        sonnet_note = sonnet.get("note") or ""

        # Open command
        png_args = " ".join(f'"{p}"' for p in pngs)
        open_cmd = f"open {png_args}" if pngs else "(no PNGs found)"

        print(f"--- [{i:2d}/{len(rids)}]  {rid}  ---")
        print(f"  doc_type:        {corpus['doc_type']}")
        print(f"  PO from corpus:  {corpus['po']}")
        print(f"  Sonnet vision:   name='{sonnet_name}'  allot='{sonnet_allot}'  pages={sonnet_pages}")
        if sonnet_note:
            print(f"                   note: {sonnet_note}")
        print(f"  Source PNGs ({len(pngs)}):")
        for p in pngs:
            print(f"    {p}")
        print(f"  Open all in Preview:")
        print(f"    {open_cmd}")
        print()

        rows.append({
            "record_id": rid,
            "doc_type": corpus["doc_type"],
            "po_corpus": corpus["po"],
            "sonnet_name": sonnet_name,
            "sonnet_allot": sonnet_allot,
            "sonnet_pages": sonnet_pages,
            "sonnet_note": sonnet_note,
            "n_pages": len(pngs),
            # Blank columns for user to fill in
            "source_name": "",
            "source_allot": "",
            "source_tribe": "",
            "source_po": "",
            "verdict": "",  # e.g. 'sonnet_correct', 'sonnet_partially_correct', 'sonnet_wrong', 'admin_correspondence'
            "notes": "",
        })

    # Write TSV
    with open(OUTPUT_TSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "record_id", "doc_type", "po_corpus",
            "sonnet_name", "sonnet_allot", "sonnet_pages", "sonnet_note", "n_pages",
            "source_name", "source_allot", "source_tribe", "source_po", "verdict", "notes",
        ], delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print("=" * 80)
    print(f"Triage TSV written: {OUTPUT_TSV}")
    print("Fill in source_name, source_allot, source_tribe, source_po, verdict")
    print("as you work through each record.")
    print("=" * 80)


if __name__ == "__main__":
    main()
