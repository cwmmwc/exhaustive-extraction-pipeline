#!/usr/bin/env python3
"""
Merge Sonnet + Qwen-VL DOJ index card extractions into unified_index_cards.

Reads:
  vision_index_cards_full/        (Sonnet — 80 PDFs, vision_merged.json per dir)
  qwen_vl_index_cards_full/       (Qwen-VL — 87 PDFs, one .json per PDF)

Writes:
  PostgreSQL database `unified_index_cards` (schema_unified_index_cards.sql)

Slip-level dedup:
  Two slips from the same source_pdf with the same
  (file_number, normalized date, normalized correspondent) are treated as
  the same physical card. When both extractions found a slip:
    - Sonnet's row wins (more fields, broader person coverage)
    - extraction_source = 'sonnet+qwen'
  When only Sonnet found it: extraction_source = 'sonnet-only'
  When only Qwen found it: extraction_source = 'qwen-only'

Person dedup:
  Normalized name = lowercase, punctuation stripped, whitespace collapsed,
  words sorted (so "Smith, John" and "John Smith" merge). Variants and
  source flags are preserved on each merged row.

Case aggregation:
  One row per unique file_number. Both sonnet_slip_count, qwen_slip_count,
  sonnet_case_mention_count, qwen_case_mention_count, and the
  cases_at_file_number master-classification flag are computed during the
  merge.

Usage:
    python3 merge_index_cards.py            # do it
    python3 merge_index_cards.py --reset    # truncate all tables first
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict
from typing import Any

import fitz  # PyMuPDF — for page counts
import psycopg2
import psycopg2.extras


# ─────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────

DB_NAME = "unified_index_cards"

REPO = os.path.dirname(os.path.abspath(__file__))
SONNET_DIR = os.path.join(REPO, "vision_index_cards_full")
QWEN_DIR = os.path.join(REPO, "qwen_vl_index_cards_full")
PDF_ROOT = os.path.join(REPO, "RG 60 index cards")

# Sonnet's slip dict has 17 keys; Qwen's has 9. Sonnet-only fields:
SONNET_ONLY_FIELDS = (
    "correspondent_role", "case_number", "allottee_name", "allottee_number",
    "tribe_or_reservation", "action_type", "enclosures", "processed_date",
)
SHARED_FIELDS = (
    "file_number", "jurisdiction", "date", "correspondent",
    "case_name", "subject", "routing_division", "routing_date", "clerk_initials",
)


# ─────────────────────────────────────────────────────────────────
# Normalization helpers
# ─────────────────────────────────────────────────────────────────

def _coerce_str(s):
    """Some extraction outputs put lists where strings are expected
    (Qwen sometimes returns ['name1', 'name2'] for allottee_name when a
    slip mentions multiple people). Coerce to a single string for the
    field-level matching keys."""
    if s is None:
        return ""
    if isinstance(s, list):
        return " ".join(str(x) for x in s if x)
    return str(s)


def norm_text(s):
    """Lowercase, strip punctuation, collapse whitespace."""
    s = _coerce_str(s)
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_date(s):
    """Normalize a date string for matching. Slip dates are messy
    (1935-08-22, 8/22/35, Aug 22 1935, etc.); we just collapse non-digits."""
    s = _coerce_str(s)
    if not s:
        return ""
    return re.sub(r"\D", "", s)


def norm_file_number(s):
    """Normalize a file_number for matching."""
    s = _coerce_str(s)
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r"\s+", "", s)
    return s.lower()


def norm_person_name(s):
    """Normalize a person name for dedup: lowercase, strip punctuation,
    sort words. Handles "Smith, John" vs "John Smith"."""
    s = _coerce_str(s)
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    words = sorted(w for w in s.split() if w)
    return " ".join(words)


def slip_match_key(slip, source_pdf):
    """The key used to detect that two slips are the same physical card."""
    return (
        source_pdf,
        norm_file_number(slip.get("file_number", "")),
        norm_date(slip.get("date", "")),
        norm_text(slip.get("correspondent", "")),
    )


# ─────────────────────────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────────────────────────

def load_qwen_files():
    """Walk qwen_vl_index_cards_full/ and return {full_rel_path: parsed_json}.
    Some PDFs share the same inner basename (e.g. 3 different `09062024.pdf`
    files in different RG 60 boxes), so we use the FULL relative path from
    QWEN_DIR (without the .json extension) as the unique identifier instead
    of just the basename. The basename is preserved separately for matching
    against Sonnet (which uses basename-only directory naming)."""
    out = {}
    for path in glob.glob(os.path.join(QWEN_DIR, "**/*.json"), recursive=True):
        rel_path = os.path.relpath(path, QWEN_DIR)
        rel_no_ext = os.path.splitext(rel_path)[0]   # full relative path, no .json
        basename = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  WARN: failed to load Qwen {path}: {e}")
            continue
        rel_dir = os.path.relpath(os.path.dirname(path), QWEN_DIR)
        if rel_dir == ".":
            subcollection = ""
        else:
            subcollection = rel_dir.split(os.sep)[0]
        data["__source_pdf"] = rel_no_ext     # unique key — full relative path
        data["__basename"] = basename         # for cross-extraction matching to Sonnet
        data["__subcollection"] = subcollection
        data["__path"] = path
        out[rel_no_ext] = data
    return out


def load_sonnet_files():
    """Walk vision_index_cards_full/ and return {source_pdf: parsed_json}.
    Sonnet output uses one directory per PDF, with the merged extraction at
    vision_merged.json. The directory name IS the PDF basename."""
    out = {}
    for path in glob.glob(os.path.join(SONNET_DIR, "*", "vision_merged.json")):
        basename = os.path.basename(os.path.dirname(path))
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  WARN: failed to load Sonnet {path}: {e}")
            continue
        data["__source_pdf"] = basename
        data["__path"] = path
        out[basename] = data
    return out


def get_pdf_page_count(source_pdf):
    """Try to find the source PDF in the RG 60 index cards/ tree and return
    its page count. Returns None if the PDF is not found."""
    matches = glob.glob(
        os.path.join(PDF_ROOT, "**", f"{source_pdf}.pdf"), recursive=True
    )
    if not matches:
        return None
    try:
        doc = fitz.open(matches[0])
        n = doc.page_count
        doc.close()
        return n
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# Merge logic
# ─────────────────────────────────────────────────────────────────

def merge_slips_for_pdf(sonnet_slips, qwen_slips, source_pdf):
    """Slip-level dedup. Returns a list of (slip_dict, extraction_source)
    tuples representing the canonical merged slips for this PDF."""
    # Index Sonnet slips by match key. Within each key bucket, hold a
    # list because multiple slips can share the same key.
    sonnet_by_key = defaultdict(list)
    for s in sonnet_slips:
        sonnet_by_key[slip_match_key(s, source_pdf)].append(s)

    canonical = []                 # output: list of (slip, extraction_source)
    sonnet_consumed = set()        # ids of sonnet slips that matched a qwen slip

    # Walk Qwen slips, matching against Sonnet
    for q in qwen_slips:
        key = slip_match_key(q, source_pdf)
        bucket = sonnet_by_key.get(key, [])
        # Find the first sonnet slip in this bucket that hasn't been consumed
        match = None
        for s in bucket:
            if id(s) not in sonnet_consumed:
                match = s
                break
        if match is not None:
            sonnet_consumed.add(id(match))
            # Optionally augment Sonnet's row with any non-empty Qwen field
            # that Sonnet's row has empty (rare but useful for clerk_initials,
            # routing_date, etc.)
            for f in SHARED_FIELDS:
                if not match.get(f) and q.get(f):
                    match[f] = q[f]
            canonical.append((match, "sonnet+qwen"))
        else:
            canonical.append((q, "qwen-only"))

    # Walk remaining unmatched Sonnet slips
    for s in sonnet_slips:
        if id(s) not in sonnet_consumed:
            canonical.append((s, "sonnet-only"))

    return canonical


def _str_or_none(v):
    """Coerce a slip field to a TEXT value for the DB. Lists get
    space-joined; empty strings become NULL."""
    if v is None:
        return None
    if isinstance(v, list):
        joined = " ".join(str(x).strip() for x in v if x)
        return joined or None
    s = str(v).strip()
    return s or None


def normalize_slip_for_db(slip, extraction_source, document_id):
    """Convert a slip dict (from either extraction) into the column tuple
    expected by the unified slips table. Sonnet-only fields fall back to
    NULL when the source slip is qwen-only. List values from Qwen get
    coerced to space-joined strings."""
    return (
        document_id,
        _str_or_none(slip.get("file_number")),
        _str_or_none(slip.get("jurisdiction")),
        _str_or_none(slip.get("date")),
        _str_or_none(slip.get("correspondent")),
        _str_or_none(slip.get("case_name")),
        _str_or_none(slip.get("subject")),
        _str_or_none(slip.get("routing_division")),
        _str_or_none(slip.get("routing_date")),
        _str_or_none(slip.get("clerk_initials")),
        # Sonnet-only fields
        _str_or_none(slip.get("correspondent_role")),
        _str_or_none(slip.get("case_number")),
        _str_or_none(slip.get("allottee_name") or slip.get("named_individual")),
        _str_or_none(slip.get("allottee_number")),
        _str_or_none(slip.get("tribe_or_reservation")),
        _str_or_none(slip.get("action_type")),
        _str_or_none(slip.get("enclosures")),
        _str_or_none(slip.get("processed_date")),
        # Provenance
        str(slip.get("source_page")) if slip.get("source_page") is not None else None,
        extraction_source,
    )


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DB_NAME, help=f"Database (default: {DB_NAME})")
    parser.add_argument("--reset", action="store_true",
                        help="Truncate all tables before loading")
    args = parser.parse_args()

    print(f"Connecting to {args.db}...")
    conn = psycopg2.connect(dbname=args.db, host="localhost")
    cur = conn.cursor()

    if args.reset:
        print("Truncating all tables...")
        cur.execute("""
            TRUNCATE slip_persons, slip_cases, persons, cases, slips, documents
            RESTART IDENTITY CASCADE
        """)
        conn.commit()

    # ── Step 1: load both extraction directories ─────────────────
    print("Loading extraction files...")
    sonnet_files = load_sonnet_files()       # keyed by basename (Sonnet's structure)
    qwen_files = load_qwen_files()           # keyed by full relative path (unique)
    print(f"  Sonnet PDFs: {len(sonnet_files)}")
    print(f"  Qwen-VL PDFs: {len(qwen_files)}")

    # Build a basename → list of qwen full-path keys (for collision handling)
    qwen_by_basename = defaultdict(list)
    for q_key, q_data in qwen_files.items():
        qwen_by_basename[q_data["__basename"]].append(q_key)

    # ── Step 1b: pair Sonnet directories to specific Qwen files ──
    # When a Sonnet basename matches multiple Qwen files (the basename
    # collision case — same inner filename in different boxes), we don't
    # know which physical PDF Sonnet actually processed. Use content-based
    # matching: count how many slip keys overlap between Sonnet and each
    # Qwen candidate, pair Sonnet with the highest-overlap Qwen.
    print("Pairing Sonnet to Qwen by content overlap (handles basename collisions)...")
    sonnet_to_qwen = {}     # sonnet_basename -> qwen_full_path
    qwen_paired_to_sonnet = set()  # qwen full-paths already paired to Sonnet

    for s_basename, s_data in sonnet_files.items():
        candidates = qwen_by_basename.get(s_basename, [])
        if not candidates:
            continue   # Sonnet has no Qwen counterpart at all (shouldn't happen but safe)
        if len(candidates) == 1:
            sonnet_to_qwen[s_basename] = candidates[0]
            qwen_paired_to_sonnet.add(candidates[0])
            continue
        # Multiple Qwen candidates with the same basename — content-pair
        sonnet_keys = {
            (norm_file_number(s.get("file_number", "")),
             norm_date(s.get("date", "")),
             norm_text(s.get("correspondent", "")))
            for s in (s_data.get("record_slips", []) or [])
        }
        if not sonnet_keys:
            sonnet_to_qwen[s_basename] = candidates[0]  # fallback
            qwen_paired_to_sonnet.add(candidates[0])
            continue
        best_qwen = None
        best_overlap = -1
        for q_key in candidates:
            q_data = qwen_files[q_key]
            q_keys = {
                (norm_file_number(q.get("file_number", "")),
                 norm_date(q.get("date", "")),
                 norm_text(q.get("correspondent", "")))
                for q in (q_data.get("record_slips", []) or [])
            }
            overlap = len(sonnet_keys & q_keys)
            if overlap > best_overlap:
                best_overlap = overlap
                best_qwen = q_key
        sonnet_to_qwen[s_basename] = best_qwen
        qwen_paired_to_sonnet.add(best_qwen)
        print(f"  basename '{s_basename}' has {len(candidates)} Qwen siblings; paired with {best_qwen} (overlap: {best_overlap}/{len(sonnet_keys)})")

    # Now we know which Qwen file is "the canonical pair" for each Sonnet
    # directory. Build the inverse map and the union of all PDFs to process.
    qwen_to_sonnet = {qkey: sbase for sbase, qkey in sonnet_to_qwen.items()}
    all_pdfs = sorted(qwen_files.keys())
    sonnet_orphans = set(sonnet_files.keys()) - set(sonnet_to_qwen.keys())
    print(f"  Total documents (one per Qwen file): {len(all_pdfs)}")
    print(f"  Sonnet directories with no Qwen match: {len(sonnet_orphans)} {sorted(sonnet_orphans) if sonnet_orphans else ''}")

    # ── Step 2: per-PDF slip merge, write to slips table ─────────
    # Track aggregate counts per file_number for the cases table.
    # And aggregate person mentions across the whole corpus.
    file_number_to_sonnet_slips = defaultdict(int)
    file_number_to_qwen_slips = defaultdict(int)
    file_number_to_case_names = defaultdict(set)            # raw variants for case_name_variants[]
    file_number_to_normalized_case_names = defaultdict(set) # all variants seen, mostly noise
    # The signal that actually flags master classifications: distinct case_names
    # in SONNET's legal_cases extraction. Sonnet dedupes case names aggressively
    # so for one-case file_numbers it has 1-3 entries, for master classifications
    # like 90-2-01 it has 174 entries (different bills under one master file).
    file_number_to_sonnet_distinct_cases = defaultdict(set)
    file_number_to_jurisdictions = defaultdict(set)
    file_number_to_counties = defaultdict(set)
    file_number_to_named_individuals = defaultdict(set)
    file_number_to_tribes = defaultdict(set)
    file_number_to_case_types = defaultdict(set)
    file_number_to_distinct_persons = defaultdict(set)

    def case_name_normalized(name):
        """Aggressive normalization to detect that case_name variants are
        the same case despite paraphrase. Lowercase, strip punctuation,
        remove common boilerplate ('et al', 'etc'), take first 40 chars
        of the result. Two case_names that share their first 40 normalized
        chars are treated as the same case."""
        s = _coerce_str(name).lower()
        s = re.sub(r"\bet\s*al\b", "", s)
        s = re.sub(r"\betc\.?\b", "", s)
        s = re.sub(r"[^\w\s]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s[:40]

    # Person aggregation: norm_name -> {canonical, variants, roles, tribes, files, sonnet_count, qwen_count}
    persons_agg = {}

    def add_person(name, role, tribe, source, file_number):
        # Coerce list values to a single string. If a slip's allottee_name
        # is ['Stella D. Twiss', 'Lizzie Twiss'], explode into two persons.
        if name is None or name == "":
            return
        if isinstance(name, list):
            for n in name:
                add_person(n, role, tribe, source, file_number)
            return
        name = str(name).strip()
        if not name:
            return
        nn = norm_person_name(name)
        if not nn:
            return
        if nn not in persons_agg:
            persons_agg[nn] = {
                "canonical": name,
                "variants": set(),
                "roles": set(),
                "tribes": set(),
                "file_numbers": set(),
                "sources": set(),
                "sonnet_count": 0,
                "qwen_count": 0,
            }
        p = persons_agg[nn]
        p["variants"].add(name)
        if len(name) > len(p["canonical"]):
            p["canonical"] = name
        role_s = _coerce_str(role).strip()
        tribe_s = _coerce_str(tribe).strip()
        if role_s:
            p["roles"].add(role_s)
        if tribe_s:
            p["tribes"].add(tribe_s)
        if file_number:
            p["file_numbers"].add(file_number)
        p["sources"].add(source)
        if source == "sonnet":
            p["sonnet_count"] += 1
        elif source == "qwen":
            p["qwen_count"] += 1

    # Build slip rows for each PDF
    print("\nMerging slips per PDF...")
    total_canonical_slips = 0
    extraction_source_counts = defaultdict(int)
    pending_slip_cases = []     # deferred until cases table is populated
    sonnet_basenames_consumed = set()

    for q_key in all_pdfs:
        qwen_data = qwen_files[q_key]
        qwen_slips = qwen_data.get("record_slips", []) or []
        # Sonnet pairing: only the Sonnet directory we content-paired to this
        # Qwen file gets used here. Other Qwen files with the same basename
        # but a different content match get sonnet_data = {} (qwen-only).
        sonnet_basename_for_pair = qwen_to_sonnet.get(q_key)
        if sonnet_basename_for_pair:
            sonnet_data = sonnet_files.get(sonnet_basename_for_pair, {})
            sonnet_basenames_consumed.add(sonnet_basename_for_pair)
        else:
            sonnet_data = {}
        sonnet_slips = sonnet_data.get("record_slips", []) or []

        # Document row
        subcollection = qwen_data.get("__subcollection", "")
        page_count = get_pdf_page_count(qwen_data.get("__basename", q_key))
        sonnet_meta = sonnet_data.get("_meta") or {}
        qwen_meta = qwen_data.get("_meta") or {}
        cur.execute("""
            INSERT INTO documents (source_pdf, subcollection, num_pages,
                sonnet_extracted, qwen_extracted,
                sonnet_failed_pages, qwen_failed_pages)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_pdf, subcollection) DO UPDATE SET
                num_pages = EXCLUDED.num_pages,
                sonnet_extracted = EXCLUDED.sonnet_extracted,
                qwen_extracted = EXCLUDED.qwen_extracted,
                sonnet_failed_pages = EXCLUDED.sonnet_failed_pages,
                qwen_failed_pages = EXCLUDED.qwen_failed_pages
            RETURNING id
        """, (
            q_key, subcollection, page_count,
            bool(sonnet_data), bool(qwen_data),
            len(sonnet_meta.get("failed_pages", []) if isinstance(sonnet_meta, dict) else []),
            len(qwen_meta.get("failed_pages", []) if isinstance(qwen_meta, dict) else []),
        ))
        document_id = cur.fetchone()[0]

        # Merge slips
        canonical = merge_slips_for_pdf(sonnet_slips, qwen_slips, q_key)
        total_canonical_slips += len(canonical)

        for slip, extraction_source in canonical:
            extraction_source_counts[extraction_source] += 1
            row = normalize_slip_for_db(slip, extraction_source, document_id)
            cur.execute("""
                INSERT INTO slips (
                    document_id, file_number, jurisdiction, date, correspondent,
                    case_name, subject, routing_division, routing_date, clerk_initials,
                    correspondent_role, case_number, allottee_name, allottee_number,
                    tribe_or_reservation, action_type, enclosures, processed_date,
                    source_page, extraction_source
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, row)
            slip_id = cur.fetchone()[0]
            fn = norm_file_number(slip.get("file_number", ""))
            if fn:
                if extraction_source in ("sonnet+qwen", "sonnet-only"):
                    file_number_to_sonnet_slips[fn] += 1
                if extraction_source in ("sonnet+qwen", "qwen-only"):
                    file_number_to_qwen_slips[fn] += 1
                if slip.get("case_name"):
                    cn = _coerce_str(slip["case_name"]).strip()
                    if cn:
                        file_number_to_case_names[fn].add(cn)
                        file_number_to_normalized_case_names[fn].add(case_name_normalized(cn))
                if slip.get("jurisdiction"):
                    file_number_to_jurisdictions[fn].add(_coerce_str(slip["jurisdiction"]).strip())
                ind = slip.get("allottee_name") or slip.get("named_individual")
                if ind:
                    file_number_to_distinct_persons[fn].add(norm_person_name(ind))
                # Defer slip_cases insertion until after the cases table exists
                pending_slip_cases.append((slip_id, fn, slip.get("case_name")))
            # Track the named_individual on this slip as a person
            ind = slip.get("allottee_name") or slip.get("named_individual")
            if ind:
                src = "sonnet" if "sonnet" in extraction_source else "qwen"
                add_person(
                    ind,
                    "allottee",
                    slip.get("tribe_or_reservation"),
                    src,
                    fn,
                )

        # Aggregate from each extraction's legal_cases lists for the case
        # mention counts and metadata enrichment.
        # Sonnet's legal_cases is also the authoritative source for the
        # cases_at_file_number master-classification flag.
        for is_sonnet, source_data in ((True, sonnet_data), (False, qwen_data)):
            for c in (source_data.get("legal_cases", []) or []):
                fn = norm_file_number(c.get("file_number", ""))
                if not fn:
                    continue
                cn = _coerce_str(c.get("case_name")).strip()
                if cn:
                    file_number_to_case_names[fn].add(cn)
                    file_number_to_normalized_case_names[fn].add(case_name_normalized(cn))
                    if is_sonnet:
                        file_number_to_sonnet_distinct_cases[fn].add(case_name_normalized(cn))
                j = _coerce_str(c.get("jurisdiction")).strip()
                if j:
                    file_number_to_jurisdictions[fn].add(j)
                co = _coerce_str(c.get("county")).strip()
                if co:
                    file_number_to_counties[fn].add(co)
                ni = _coerce_str(c.get("named_individual")).strip()
                if ni:
                    file_number_to_named_individuals[fn].add(ni)
                tr = _coerce_str(c.get("tribe_or_reservation")).strip()
                if tr:
                    file_number_to_tribes[fn].add(tr)
                ct = _coerce_str(c.get("case_type")).strip()
                if ct:
                    file_number_to_case_types[fn].add(ct)

        for p in (sonnet_data.get("persons", []) or []):
            add_person(p.get("name"), p.get("role"), p.get("tribe"), "sonnet", None)
        for p in (qwen_data.get("persons", []) or []):
            add_person(p.get("name"), p.get("role"), p.get("tribe"), "qwen", None)

    conn.commit()
    print(f"  Inserted documents: {len(all_pdfs)}")
    print(f"  Inserted slips:     {total_canonical_slips}")
    print(f"  By extraction_source:")
    for k, v in sorted(extraction_source_counts.items()):
        print(f"    {k}: {v}")
    print(f"  Pending slip_cases inserts: {len(pending_slip_cases)} (will run after cases table is populated)")

    # ── Step 3: case mention counts (per-extraction) ─────────────
    # Re-walk the legal_cases lists per extraction to count mentions per file_number.
    print("\nComputing case mention counts...")
    sonnet_case_mentions = defaultdict(int)
    qwen_case_mentions = defaultdict(int)
    for source_pdf in all_pdfs:
        for c in (sonnet_files.get(source_pdf, {}).get("legal_cases", []) or []):
            fn = norm_file_number(c.get("file_number", ""))
            if fn:
                sonnet_case_mentions[fn] += 1
        for c in (qwen_files.get(source_pdf, {}).get("legal_cases", []) or []):
            fn = norm_file_number(c.get("file_number", ""))
            if fn:
                qwen_case_mentions[fn] += 1

    # ── Step 4: insert cases table ───────────────────────────────
    print(f"Inserting {len(file_number_to_sonnet_slips | file_number_to_qwen_slips)} unique file_numbers as cases...")
    all_file_numbers = set(file_number_to_sonnet_slips.keys()) | set(file_number_to_qwen_slips.keys()) \
                       | set(sonnet_case_mentions.keys()) | set(qwen_case_mentions.keys())

    for fn in sorted(all_file_numbers):
        case_names = file_number_to_case_names.get(fn, set())
        canonical_name = max(case_names, key=len) if case_names else None
        variants = sorted(case_names) if case_names else None

        jurisdictions = file_number_to_jurisdictions.get(fn, set())
        jurisdiction = max(jurisdictions, key=len) if jurisdictions else None

        counties = file_number_to_counties.get(fn, set())
        county = max(counties, key=len) if counties else None

        named_individuals = file_number_to_named_individuals.get(fn, set())
        named_individual = max(named_individuals, key=len) if named_individuals else None

        tribes = file_number_to_tribes.get(fn, set())
        tribe = max(tribes, key=len) if tribes else None

        case_types = file_number_to_case_types.get(fn, set())
        case_type = max(case_types, key=len) if case_types else None

        # cases_at_file_number: distinct case_names in Sonnet's legal_cases
        # extraction for this file_number. Sonnet's legal_cases is dedupe-d
        # at extraction time, so a count of 1 means "one canonical case",
        # and a count of 174 (e.g. 90-2-01) means "this file_number is a
        # master classification with 174 distinct bills/cases under it".
        # Falls back to 1 when Sonnet didn't extract this PDF.
        sonnet_distinct = {n for n in file_number_to_sonnet_distinct_cases.get(fn, set()) if n}
        cases_at = max(len(sonnet_distinct), 1)
        distinct_persons = len(file_number_to_distinct_persons.get(fn, set()))

        cur.execute("""
            INSERT INTO cases (
                file_number, canonical_case_name, case_name_variants,
                jurisdiction, county, case_type, named_individual, tribe_or_reservation,
                sonnet_slip_count, qwen_slip_count,
                sonnet_case_mention_count, qwen_case_mention_count,
                cases_at_file_number, distinct_persons_count
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (file_number) DO UPDATE SET
                canonical_case_name = EXCLUDED.canonical_case_name,
                case_name_variants = EXCLUDED.case_name_variants,
                jurisdiction = EXCLUDED.jurisdiction,
                county = EXCLUDED.county,
                case_type = EXCLUDED.case_type,
                named_individual = EXCLUDED.named_individual,
                tribe_or_reservation = EXCLUDED.tribe_or_reservation,
                sonnet_slip_count = EXCLUDED.sonnet_slip_count,
                qwen_slip_count = EXCLUDED.qwen_slip_count,
                sonnet_case_mention_count = EXCLUDED.sonnet_case_mention_count,
                qwen_case_mention_count = EXCLUDED.qwen_case_mention_count,
                cases_at_file_number = EXCLUDED.cases_at_file_number,
                distinct_persons_count = EXCLUDED.distinct_persons_count
        """, (
            fn, canonical_name, variants,
            jurisdiction, county, case_type, named_individual, tribe,
            file_number_to_sonnet_slips.get(fn, 0),
            file_number_to_qwen_slips.get(fn, 0),
            sonnet_case_mentions.get(fn, 0),
            qwen_case_mentions.get(fn, 0),
            cases_at,
            distinct_persons,
        ))
    conn.commit()
    print(f"  Inserted/updated {len(all_file_numbers)} cases")

    # ── Step 4b: drain the deferred slip_cases queue ─────────────
    # Now that every file_number has a row in cases, the FK is satisfied.
    print(f"\nInserting {len(pending_slip_cases)} deferred slip_cases rows...")
    inserted = 0
    skipped = 0
    for slip_id, fn, case_name in pending_slip_cases:
        try:
            cur.execute("""
                INSERT INTO slip_cases (slip_id, file_number, case_name_as_mentioned)
                VALUES (%s, %s, %s)
                ON CONFLICT (slip_id, file_number) DO NOTHING
            """, (slip_id, fn, case_name))
            inserted += 1
        except psycopg2.errors.ForeignKeyViolation:
            conn.rollback()
            skipped += 1
    conn.commit()
    print(f"  slip_cases inserted: {inserted}, skipped (FK violation): {skipped}")

    # ── Step 5: insert persons table ─────────────────────────────
    print(f"\nInserting {len(persons_agg)} unique persons...")
    person_id_by_norm = {}  # for join table inserts
    for nn, p in persons_agg.items():
        cur.execute("""
            INSERT INTO persons (
                canonical_name, normalized_name, name_variants, roles, tribes,
                file_numbers, sources, sonnet_mention_count, qwen_mention_count
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (normalized_name) DO UPDATE SET
                canonical_name = EXCLUDED.canonical_name,
                name_variants = EXCLUDED.name_variants,
                roles = EXCLUDED.roles,
                tribes = EXCLUDED.tribes,
                file_numbers = EXCLUDED.file_numbers,
                sources = EXCLUDED.sources,
                sonnet_mention_count = EXCLUDED.sonnet_mention_count,
                qwen_mention_count = EXCLUDED.qwen_mention_count
            RETURNING id
        """, (
            p["canonical"],
            nn,
            sorted(p["variants"]),
            sorted(p["roles"]) if p["roles"] else None,
            sorted(p["tribes"]) if p["tribes"] else None,
            sorted(p["file_numbers"]) if p["file_numbers"] else None,
            sorted(p["sources"]),
            p["sonnet_count"],
            p["qwen_count"],
        ))
        person_id_by_norm[nn] = cur.fetchone()[0]
    conn.commit()
    print(f"  Inserted/updated {len(persons_agg)} persons")

    # ── Step 6: build slip_persons join table ────────────────────
    # Walk slips again and link each named_individual to its person row.
    print("\nBuilding slip_persons join table...")
    cur.execute("""
        SELECT id, allottee_name FROM slips
        WHERE allottee_name IS NOT NULL AND allottee_name <> ''
    """)
    rows = cur.fetchall()
    join_count = 0
    for slip_id, name in rows:
        nn = norm_person_name(name)
        person_id = person_id_by_norm.get(nn)
        if person_id is None:
            continue
        cur.execute("""
            INSERT INTO slip_persons (slip_id, person_id, role_on_this_slip)
            VALUES (%s, %s, %s)
            ON CONFLICT (slip_id, person_id) DO NOTHING
        """, (slip_id, person_id, "allottee"))
        join_count += 1
    conn.commit()
    print(f"  Inserted {join_count} slip_persons rows")

    # ── Step 7: report ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Merge complete. Final counts:")
    for tbl in ("documents", "slips", "cases", "persons", "slip_cases", "slip_persons"):
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        n = cur.fetchone()[0]
        print(f"  {tbl:<15} {n:>10,}")

    print("\nMaster classifications (cases_at_file_number > 1):")
    cur.execute("""
        SELECT file_number, cases_at_file_number,
               sonnet_slip_count + qwen_slip_count AS total_slips
        FROM cases
        WHERE cases_at_file_number > 1
        ORDER BY cases_at_file_number DESC LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:<20} {row[1]:>4} cases  {row[2]:>5} slips")

    print("\nTop 15 single cases by total slip count (cases_at_file_number=1):")
    cur.execute("""
        SELECT file_number, canonical_case_name,
               sonnet_slip_count, qwen_slip_count
        FROM cases
        WHERE cases_at_file_number = 1
        ORDER BY (sonnet_slip_count + qwen_slip_count) DESC LIMIT 15
    """)
    for row in cur.fetchall():
        name = (row[1] or "")[:60]
        print(f"  {row[0]:<15} S={row[2]:>3} Q={row[3]:>3}  {name}")

    print("\nTop 15 file_numbers by total slip count (any cases_at_file_number):")
    cur.execute("""
        SELECT file_number, canonical_case_name,
               sonnet_slip_count, qwen_slip_count, cases_at_file_number
        FROM cases
        ORDER BY (sonnet_slip_count + qwen_slip_count) DESC LIMIT 15
    """)
    for row in cur.fetchall():
        name = (row[1] or "")[:50]
        print(f"  {row[0]:<15} S={row[2]:>3} Q={row[3]:>3} cases={row[4]:>3}  {name}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
