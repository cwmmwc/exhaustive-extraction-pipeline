#!/usr/bin/env python3
"""
Entity Deduplication — Phase 2: Fuzzy Matching with Human Review

WHAT THIS DOES:
  Finds entity pairs that are likely the same despite spelling differences:
    - OCR errors: "Yarlotte" vs "Yarlott", "Affaire" vs "Affairs"
    - Historical abbreviations: "Chas." → Charles, "Wm." → William
    - Format variations: "Allotment No. 2237" vs "Allotment 2237"

  Unlike Phase 1 (mechanical, auto-merge), Phase 2 produces CANDIDATE PAIRS
  for human review. Nothing is merged until you approve it.

TWO-STEP WORKFLOW:
  1. PROPOSE — find candidate pairs, write a review JSON file
  2. APPLY  — read the reviewed file, merge accepted pairs

USAGE:
  # Step 1: Generate candidate pairs
  python3 dedup_entities_phase2.py propose
  python3 dedup_entities_phase2.py propose --db historical_docs
  python3 dedup_entities_phase2.py propose --types person organization

  # Step 2: Edit the review file — change "decision": null to "accept" or "reject"

  # Step 3: Apply accepted merges
  python3 dedup_entities_phase2.py apply dedup_phase2_review_XXXXXXXX.json
  python3 dedup_entities_phase2.py apply dedup_phase2_review_XXXXXXXX.json --execute

DEPENDENCIES:
  pip install thefuzz python-Levenshtein jellyfish
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

import jellyfish
import psycopg2
import psycopg2.extras
from thefuzz import fuzz

# ─────────────────────────────────────────────────
# Historical abbreviation expansions
# ─────────────────────────────────────────────────

PERSON_ABBREVIATIONS = {
    "chas.": "charles", "chas": "charles",
    "wm.": "william", "wm": "william",
    "jno.": "john", "jno": "john",
    "thos.": "thomas", "thos": "thomas",
    "jas.": "james", "jas": "james",
    "geo.": "george", "geo": "george",
    "benj.": "benjamin", "benj": "benjamin",
    "robt.": "robert", "robt": "robert",
    "saml.": "samuel", "saml": "samuel",
    "danl.": "daniel", "danl": "daniel",
    "edw.": "edward", "edw": "edward",
    "richd.": "richard", "richd": "richard",
    "nathl.": "nathaniel", "nathl": "nathaniel",
    "eliz.": "elizabeth", "eliz": "elizabeth",
    "alex.": "alexander", "alex": "alexander",
    "jos.": "joseph", "jos": "joseph",
    "fred.": "frederick", "fred": "frederick",
    "andr.": "andrew",
    "hen.": "henry",
}

LOCATION_ABBREVIATIONS = {
    "mt.": "mount", "mt": "mount",
    "ft.": "fort", "ft": "fort",
    "st.": "saint",
    "co.": "county",
}

# Titles to strip (from phase 1)
TITLE_PATTERN = re.compile(
    r"^(commissioner|congressman|chairman|senator|general|colonel|captain|"
    r"chief|miss|mrs?|dr|rev|hon|col|gen|capt|rep)\.?\s+",
    re.IGNORECASE,
)

# ─────────────────────────────────────────────────
# Per-type matching thresholds
# ─────────────────────────────────────────────────

TYPE_THRESHOLDS = {
    "person": 0.88,
    "organization": 0.90,
    "location": 0.90,
    "land_parcel": 0.85,
    "legislation": 0.85,
    "legal_case": 0.90,
    "acreage_holding": 0.90,
}

# Minimum name length for fuzzy matching (short names produce too many false positives)
MIN_NAME_LENGTH = 5


# ─────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────

def expand_abbreviations(name: str, entity_type: str) -> str:
    """Expand known abbreviations in a name for comparison purposes."""
    abbrevs = PERSON_ABBREVIATIONS if entity_type == "person" else LOCATION_ABBREVIATIONS
    if not abbrevs:
        return name

    tokens = name.lower().split()
    expanded = []
    for token in tokens:
        clean = token.rstrip(",.")
        if clean in abbrevs:
            expanded.append(abbrevs[clean])
        else:
            expanded.append(token)
    return " ".join(expanded)


def normalize_for_comparison(name: str, entity_type: str) -> str:
    """Produce a normalized comparison key for an entity name."""
    s = name.strip()
    s = s.lower()

    # Strip titles (person only)
    if entity_type == "person":
        s = TITLE_PATTERN.sub("", s)

    # Expand abbreviations
    s = expand_abbreviations(s, entity_type)

    # Type-specific normalization
    if entity_type == "land_parcel":
        # Normalize "allotment no. 2237" → "allotment 2237"
        s = re.sub(r'\bno\.?\s*', '', s)
        s = re.sub(r'#\s*', '', s)
        s = re.sub(r'\bsec\.?\s', 'section ', s)
        s = re.sub(r'\btwp\.?\s', 'township ', s)

    elif entity_type == "legislation":
        # Normalize bill references
        s = re.sub(r'\bh\.\s*r\.?\s*', 'hr ', s)
        s = re.sub(r'\bs\.\s*', 's ', s)
        s = re.sub(r'^the\s+', '', s)

    # Clean up whitespace and punctuation
    s = re.sub(r'[,.]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()

    return s


# ─────────────────────────────────────────────────
# Blocking (reduce O(n²) comparisons)
# ─────────────────────────────────────────────────

STOPWORDS = {"the", "of", "and", "for", "in", "on", "at", "to", "a", "an"}


def get_block_key(name: str, entity_type: str) -> str:
    """Generate a blocking key to reduce pairwise comparisons."""
    normalized = normalize_for_comparison(name, entity_type)
    tokens = normalized.split()
    if not tokens:
        return ""

    if entity_type == "person":
        # Block by first letter of last token (surname)
        surname = tokens[-1] if len(tokens) > 1 else tokens[0]
        return surname[0] if surname else ""

    elif entity_type in ("organization", "location"):
        # Block by first significant word
        for t in tokens:
            if t not in STOPWORDS and len(t) > 2:
                return t[:4]  # First 4 chars of first significant word
        return tokens[0][:4] if tokens else ""

    elif entity_type == "land_parcel":
        # Block by type prefix (allotment, section, etc.)
        return tokens[0] if tokens else ""

    elif entity_type == "legislation":
        # Block by bill type (hr, s, etc.)
        return tokens[0] if tokens else ""

    else:
        return tokens[0][:3] if tokens else ""


# ─────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────

def compute_phonetic_score(name_a: str, name_b: str, entity_type: str) -> float:
    """Compare names phonetically using Metaphone."""
    if entity_type != "person":
        return 0.0

    tokens_a = name_a.split()
    tokens_b = name_b.split()
    if not tokens_a or not tokens_b:
        return 0.0

    # Compare surname (last token)
    surname_a = tokens_a[-1] if len(tokens_a) > 1 else tokens_a[0]
    surname_b = tokens_b[-1] if len(tokens_b) > 1 else tokens_b[0]

    meta_a = jellyfish.metaphone(surname_a)
    meta_b = jellyfish.metaphone(surname_b)

    if meta_a == meta_b:
        # Also check first name if available
        if len(tokens_a) > 1 and len(tokens_b) > 1:
            first_a = jellyfish.metaphone(tokens_a[0])
            first_b = jellyfish.metaphone(tokens_b[0])
            return 1.0 if first_a == first_b else 0.5
        return 1.0

    return 0.0


def compute_similarity(
    entity_a: Dict, entity_b: Dict,
    entity_type: str,
    shared_docs: Set[int],
) -> Dict:
    """Compute composite similarity score between two entities."""
    norm_a = normalize_for_comparison(entity_a["name"], entity_type)
    norm_b = normalize_for_comparison(entity_b["name"], entity_type)

    # Levenshtein ratio (0-100)
    lev_ratio = fuzz.ratio(norm_a, norm_b) / 100.0

    # Token sort ratio (handles word reordering)
    token_ratio = fuzz.token_sort_ratio(norm_a, norm_b) / 100.0

    # Phonetic score (person names only)
    phonetic = compute_phonetic_score(norm_a, norm_b, entity_type)

    # Document co-occurrence
    n_shared = len(shared_docs)
    cooccurrence = min(n_shared / 2.0, 1.0) if n_shared > 0 else 0.0

    # Composite score
    score = (0.4 * lev_ratio +
             0.3 * token_ratio +
             0.2 * phonetic +
             0.1 * cooccurrence)

    # Build human-readable reasons
    reasons = []
    reasons.append(f"levenshtein: {lev_ratio:.2f}")
    reasons.append(f"token_sort: {token_ratio:.2f}")
    if phonetic > 0:
        reasons.append(f"phonetic: {'full match' if phonetic == 1.0 else 'surname match'}")
    if n_shared > 0:
        reasons.append(f"{n_shared} shared document{'s' if n_shared != 1 else ''}")

    # Type-specific constraints
    passes_constraints = True

    if entity_type == "person":
        # For persons: surname metaphone must match, OR Levenshtein >= 0.92
        surname_a = norm_a.split()[-1] if norm_a.split() else ""
        surname_b = norm_b.split()[-1] if norm_b.split() else ""
        surname_match = (jellyfish.metaphone(surname_a) == jellyfish.metaphone(surname_b)
                         if surname_a and surname_b else False)
        if not surname_match and lev_ratio < 0.92:
            passes_constraints = False

    elif entity_type == "land_parcel":
        # Numbers must match exactly
        nums_a = set(re.findall(r'\d+', norm_a))
        nums_b = set(re.findall(r'\d+', norm_b))
        if nums_a != nums_b:
            passes_constraints = False

    elif entity_type == "legislation":
        # Bill number must match
        nums_a = re.findall(r'\d+', norm_a)
        nums_b = re.findall(r'\d+', norm_b)
        if nums_a != nums_b:
            passes_constraints = False

    return {
        "score": score,
        "levenshtein": lev_ratio,
        "token_sort": token_ratio,
        "phonetic": phonetic,
        "cooccurrence": cooccurrence,
        "shared_docs": n_shared,
        "reasons": reasons,
        "passes_constraints": passes_constraints,
    }


# ─────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────

def get_connection(db_name: str):
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        dbname=db_name,
        user=os.environ.get("USER", "cwm6W"),
        host="localhost",
    )


def load_entities(conn, entity_types: Optional[List[str]] = None) -> List[Dict]:
    """Load all entities with their document counts and mention doc IDs."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    type_filter = ""
    params: list = []
    if entity_types:
        type_filter = "WHERE e.type = ANY(%s)"
        params = [entity_types]

    cur.execute(f"""
        SELECT e.id, e.name, e.type, e.context,
               COUNT(DISTINCT m.document_id) AS doc_count,
               ARRAY_AGG(DISTINCT m.document_id) FILTER (WHERE m.document_id IS NOT NULL) AS doc_ids
        FROM entities e
        LEFT JOIN mentions m ON m.entity_id = e.id
        {type_filter}
        GROUP BY e.id, e.name, e.type, e.context
        ORDER BY e.type, e.name
    """, params or None)

    entities = []
    for row in cur:
        entities.append({
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "context": row["context"] or "",
            "doc_count": row["doc_count"],
            "doc_ids": set(row["doc_ids"] or []),
        })
    cur.close()
    return entities


def get_sample_filenames(conn, doc_ids: Set[int], limit: int = 3) -> List[str]:
    """Get filenames for a set of document IDs."""
    if not doc_ids:
        return []
    cur = conn.cursor()
    cur.execute(
        "SELECT file_name FROM documents WHERE id = ANY(%s) ORDER BY id LIMIT %s",
        [list(doc_ids), limit]
    )
    names = [row[0] for row in cur.fetchall()]
    cur.close()
    return names


def pick_best_variant(entity_a: Dict, entity_b: Dict) -> Tuple[Dict, Dict]:
    """Choose which entity to keep (canonical) and which to merge away.
    Returns (keep, remove)."""
    def sort_key(e):
        name = e["name"]
        is_mixed = not name.isupper() and not name.islower()
        return (e["doc_count"], is_mixed, len(name))

    if sort_key(entity_a) >= sort_key(entity_b):
        return entity_a, entity_b
    return entity_b, entity_a


# ─────────────────────────────────────────────────
# Propose: find candidate pairs
# ─────────────────────────────────────────────────

def find_candidates(
    conn,
    entities: List[Dict],
    entity_type: str,
    threshold: Optional[float] = None,
) -> List[Dict]:
    """Find fuzzy-match candidate pairs for a given entity type."""
    type_entities = [e for e in entities if e["type"] == entity_type]

    # Filter out short names
    type_entities = [e for e in type_entities if len(e["name"].strip()) >= MIN_NAME_LENGTH]

    if len(type_entities) < 2:
        return []

    min_score = threshold or TYPE_THRESHOLDS.get(entity_type, 0.90)

    # Build blocks
    blocks: Dict[str, List[Dict]] = defaultdict(list)
    for e in type_entities:
        key = get_block_key(e["name"], entity_type)
        if key:
            blocks[key].append(e)

    candidates = []
    pairs_checked = 0
    seen_pairs: Set[Tuple[int, int]] = set()

    for block_key, block_entities in blocks.items():
        n = len(block_entities)
        for i in range(n):
            for j in range(i + 1, n):
                a = block_entities[i]
                b = block_entities[j]

                # Skip if already compared
                pair_key = (min(a["id"], b["id"]), max(a["id"], b["id"]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                # Skip if normalized forms are identical (should be caught by phase 1)
                norm_a = normalize_for_comparison(a["name"], entity_type)
                norm_b = normalize_for_comparison(b["name"], entity_type)
                if norm_a == norm_b:
                    continue

                pairs_checked += 1

                # Compute similarity
                shared = a["doc_ids"] & b["doc_ids"]
                sim = compute_similarity(a, b, entity_type, shared)

                if sim["score"] >= min_score and sim["passes_constraints"]:
                    keep, remove = pick_best_variant(a, b)
                    candidates.append({
                        "entity_a": a,
                        "entity_b": b,
                        "score": sim["score"],
                        "details": sim,
                        "shared_doc_ids": shared,
                        "recommended_keep": keep,
                        "recommended_remove": remove,
                    })

    # Sort by score descending, then by total doc coverage
    candidates.sort(key=lambda c: (c["score"],
                                    c["entity_a"]["doc_count"] + c["entity_b"]["doc_count"]),
                    reverse=True)

    return candidates


def generate_review_file(conn, args) -> str:
    """Generate a review JSON file with all candidate pairs."""
    print("Loading entities...")
    entities = load_entities(conn, args.types)
    print(f"  {len(entities)} entities loaded")

    # Get types to process
    if args.types:
        types_to_process = args.types
    else:
        types_to_process = list(TYPE_THRESHOLDS.keys())

    all_candidates = []
    for entity_type in types_to_process:
        type_count = sum(1 for e in entities if e["type"] == entity_type)
        if type_count < 2:
            continue

        print(f"\nProcessing {entity_type} ({type_count} entities)...")
        threshold = args.threshold if args.threshold else None
        candidates = find_candidates(conn, entities, entity_type, threshold)
        print(f"  Found {len(candidates)} candidate pairs")
        all_candidates.extend(candidates)

    if not all_candidates:
        print("\nNo candidate pairs found above threshold.")
        return ""

    # Build review file
    print(f"\nBuilding review file ({len(all_candidates)} candidates)...")
    review_entries = []
    for idx, cand in enumerate(all_candidates, 1):
        a = cand["entity_a"]
        b = cand["entity_b"]
        keep = cand["recommended_keep"]
        shared_filenames = get_sample_filenames(conn, cand["shared_doc_ids"])
        a_filenames = get_sample_filenames(conn, a["doc_ids"])
        b_filenames = get_sample_filenames(conn, b["doc_ids"])

        review_entries.append({
            "id": idx,
            "decision": None,
            "score": round(cand["score"], 3),
            "match_reasons": cand["details"]["reasons"],
            "entity_a": {
                "id": a["id"],
                "name": a["name"],
                "type": a["type"],
                "doc_count": a["doc_count"],
                "context": a["context"][:200] if a["context"] else "",
                "sample_documents": a_filenames,
            },
            "entity_b": {
                "id": b["id"],
                "name": b["name"],
                "type": b["type"],
                "doc_count": b["doc_count"],
                "context": b["context"][:200] if b["context"] else "",
                "sample_documents": b_filenames,
            },
            "shared_documents": shared_filenames,
            "recommended_canonical": keep["name"],
        })

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"dedup_phase2_review_{timestamp}.json"
    filepath = os.path.join(os.path.dirname(__file__) or ".", filename)

    review_data = {
        "phase": 2,
        "generated": datetime.now(timezone.utc).isoformat(),
        "database": args.db,
        "instructions": (
            "Review each candidate pair below. Change \"decision\": null to "
            "\"accept\" to merge, or \"reject\" to skip. Pairs left as null "
            "will be skipped. The 'recommended_canonical' name will be kept; "
            "the other will be merged into it."
        ),
        "summary": {
            "total_candidates": len(review_entries),
            "by_type": {},
        },
        "candidates": review_entries,
    }

    # Count by type
    by_type: Dict[str, int] = defaultdict(int)
    for entry in review_entries:
        by_type[entry["entity_a"]["type"]] += 1
    review_data["summary"]["by_type"] = dict(by_type)

    with open(filepath, "w") as f:
        json.dump(review_data, f, indent=2, default=str)

    print(f"\nReview file written to: {filename}")
    print(f"  {len(review_entries)} candidate pairs")
    for etype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {etype}: {count}")
    print(f"\nNext steps:")
    print(f"  1. Open {filename} in a text editor")
    print(f"  2. For each pair, change \"decision\": null to \"accept\" or \"reject\"")
    print(f"  3. Run: python3 dedup_entities_phase2.py apply {filename}")

    return filepath


# ─────────────────────────────────────────────────
# Apply: execute accepted merges
# ─────────────────────────────────────────────────

def execute_merge_pair(conn, keep_id: int, remove_id: int, dry_run: bool) -> Dict:
    """Merge one entity into another (same logic as phase 1)."""
    cur = conn.cursor()

    log = {"keep_id": keep_id, "remove_id": remove_id,
           "mentions_reassigned": 0, "mentions_consolidated": 0}

    if dry_run:
        cur.close()
        return log

    # Check both entities still exist
    cur.execute("SELECT id, name, context FROM entities WHERE id = %s", (keep_id,))
    keep_row = cur.fetchone()
    cur.execute("SELECT id, name, context FROM entities WHERE id = %s", (remove_id,))
    remove_row = cur.fetchone()

    if not keep_row or not remove_row:
        log["skipped"] = "entity no longer exists"
        cur.close()
        return log

    # Reassign or consolidate mentions
    cur.execute(
        "SELECT id, document_id, context FROM mentions WHERE entity_id = %s",
        (remove_id,)
    )
    remove_mentions = cur.fetchall()

    for mention_id, doc_id, mention_context in remove_mentions:
        cur.execute(
            "SELECT id, context FROM mentions WHERE entity_id = %s AND document_id = %s",
            (keep_id, doc_id)
        )
        existing = cur.fetchone()

        if existing:
            # Consolidate
            existing_id, existing_context = existing
            if mention_context and mention_context.strip():
                new_ctx = (existing_context or "") + "; " + mention_context if existing_context else mention_context
                cur.execute("UPDATE mentions SET context = %s WHERE id = %s", (new_ctx, existing_id))
            cur.execute("DELETE FROM mentions WHERE id = %s", (mention_id,))
            log["mentions_consolidated"] += 1
        else:
            # Reassign
            cur.execute("UPDATE mentions SET entity_id = %s WHERE id = %s", (keep_id, mention_id))
            log["mentions_reassigned"] += 1

    # Merge context
    remove_context = remove_row[2]
    if remove_context and remove_context.strip():
        keep_context = keep_row[2] or ""
        if remove_context not in keep_context:
            updated = keep_context + ("; " if keep_context else "") + remove_context
            cur.execute("UPDATE entities SET context = %s WHERE id = %s", (updated, keep_id))

    # Delete the merged entity
    cur.execute("DELETE FROM entities WHERE id = %s", (remove_id,))

    cur.close()
    return log


def apply_review(conn, review_path: str, dry_run: bool):
    """Apply accepted merges from a review file."""
    with open(review_path) as f:
        review_data = json.load(f)

    candidates = review_data.get("candidates", [])
    accepted = [c for c in candidates if c.get("decision") == "accept"]
    rejected = [c for c in candidates if c.get("decision") == "reject"]
    skipped = [c for c in candidates if c.get("decision") is None]

    mode_label = "DRY RUN" if dry_run else "EXECUTING"
    print(f"{'=' * 60}")
    print(f"Entity Deduplication — Phase 2 Apply ({mode_label})")
    print(f"Review file: {review_path}")
    print(f"{'=' * 60}\n")
    print(f"  Total candidates: {len(candidates)}")
    print(f"  Accepted: {len(accepted)}")
    print(f"  Rejected: {len(rejected)}")
    print(f"  Skipped (no decision): {len(skipped)}")

    if not accepted:
        print("\nNo accepted pairs to merge.")
        return

    # Track merged IDs to handle transitive merges
    merged_to: Dict[int, int] = {}  # old_id → new_canonical_id

    def resolve_id(entity_id: int) -> int:
        """Follow the merge chain to find current canonical ID."""
        while entity_id in merged_to:
            entity_id = merged_to[entity_id]
        return entity_id

    print(f"\n{'Merging' if not dry_run else 'Would merge'} {len(accepted)} pairs...\n")

    log_entries = []
    for i, cand in enumerate(accepted, 1):
        a_id = cand["entity_a"]["id"]
        b_id = cand["entity_b"]["id"]
        canonical_name = cand["recommended_canonical"]

        # Determine which to keep based on recommended_canonical
        if cand["entity_a"]["name"] == canonical_name:
            keep_id, remove_id = a_id, b_id
        else:
            keep_id, remove_id = b_id, a_id

        # Resolve transitive merges
        keep_id = resolve_id(keep_id)
        remove_id = resolve_id(remove_id)

        if keep_id == remove_id:
            print(f"  [{i}] Skip (already merged): {cand['entity_a']['name']} ↔ {cand['entity_b']['name']}")
            continue

        if not dry_run:
            log = execute_merge_pair(conn, keep_id, remove_id, dry_run=False)
            if log.get("skipped"):
                print(f"  [{i}] Skip ({log['skipped']}): {cand['entity_a']['name']} ↔ {cand['entity_b']['name']}")
            else:
                print(f"  [{i}] Merged: {cand['entity_b']['name']} → {canonical_name}")
                merged_to[remove_id] = keep_id
        else:
            print(f"  [{i}] Would merge: {cand['entity_b']['name']} → {canonical_name} "
                  f"(score: {cand['score']:.3f})")
            log = {"keep_id": keep_id, "remove_id": remove_id, "dry_run": True}

        log["candidate_id"] = cand["id"]
        log["canonical_name"] = canonical_name
        log_entries.append(log)

    if not dry_run:
        conn.commit()
        total_reassigned = sum(e.get("mentions_reassigned", 0) for e in log_entries)
        total_consolidated = sum(e.get("mentions_consolidated", 0) for e in log_entries)
        print(f"\nDone.")
        print(f"  Pairs merged: {len([e for e in log_entries if not e.get('skipped')])}")
        print(f"  Mentions reassigned: {total_reassigned}")
        print(f"  Mentions consolidated: {total_consolidated}")

    # Write audit log
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_filename = f"dedup_phase2_applied_{timestamp}.json"
    log_path = os.path.join(os.path.dirname(__file__) or ".", log_filename)
    log_data = {
        "phase": 2,
        "mode": "dry_run" if dry_run else "executed",
        "source_review": review_path,
        "database": review_data.get("database", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "accepted": len(accepted),
            "rejected": len(rejected),
            "skipped": len(skipped),
        },
        "merges": log_entries,
    }
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2, default=str)

    print(f"\nAudit log: {log_filename}")
    if dry_run:
        print(f"\nThis was a DRY RUN. To execute:")
        print(f"  python3 dedup_entities_phase2.py apply {review_path} --execute")


# ─────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Phase 2 entity deduplication: fuzzy matching with human review"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Propose subcommand
    propose_parser = subparsers.add_parser("propose", help="Generate candidate pairs for review")
    propose_parser.add_argument("--db", default="crow_historical_docs",
                                help="Database name (default: crow_historical_docs)")
    propose_parser.add_argument("--types", nargs="+",
                                help="Entity types to process (default: all)")
    propose_parser.add_argument("--threshold", type=float, default=None,
                                help="Override similarity threshold (0.0–1.0)")

    # Apply subcommand
    apply_parser = subparsers.add_parser("apply", help="Apply accepted merges from review file")
    apply_parser.add_argument("review_file", help="Path to the review JSON file")
    apply_parser.add_argument("--execute", action="store_true",
                              help="Actually merge (default is dry run)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "propose":
        conn = get_connection(args.db)
        generate_review_file(conn, args)
        conn.close()

    elif args.command == "apply":
        if not os.path.exists(args.review_file):
            print(f"ERROR: Review file not found: {args.review_file}")
            sys.exit(1)

        # Read database name from review file
        with open(args.review_file) as f:
            review = json.load(f)
        db_name = review.get("database", "crow_historical_docs")

        conn = get_connection(db_name)
        apply_review(conn, args.review_file, dry_run=not args.execute)
        conn.close()


if __name__ == "__main__":
    main()
