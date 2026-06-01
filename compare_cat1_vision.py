#!/usr/bin/env python3
"""
Compare Sonnet vision vs Qwen vision outputs for the CAT_1 batch.

Reads:
  - Sonnet vision: validation_samples/cat1_sonnet_vision/<rid>/vision_merged.json
    Schema: full v5 (entities, fee_patents, events, etc.)
    Use the first fee_patent's allottee_name + allotment_number as the candidate.
    Fall back to the first 'person' entity if no fee_patent.
  - Qwen vision: circular_2464_extractions/vision_recovery_cat1/qwen_outputs/<rid>_page-N.json
    Schema: name, allotment_number, name_confidence, allotment_number_confidence
    Multiple page outputs per record. Use the highest-confidence per field across pages.

Produces: cat1_vision_comparison.tsv
  record_id | sonnet_name | qwen_name | sonnet_allot | qwen_allot | verdict | qwen_confidences
"""
import csv
import json
import re
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/Users/cwm6W/projects/exhaustive-extraction-pipeline")
SONNET_BASE = PROJECT_ROOT / "validation_samples" / "cat1_sonnet_vision"
QWEN_BASE = PROJECT_ROOT / "circular_2464_extractions" / "vision_recovery_cat1" / "qwen_outputs"
MANIFEST = PROJECT_ROOT / "circular_2464_extractions" / "vision_recovery_cat1" / "manifest.csv"
OUTPUT_TSV = PROJECT_ROOT / "cat1_vision_comparison.tsv"

CONF_RANK = {"high": 4, "medium": 3, "low": 2, "illegible": 1, "not_present_on_this_page": 0}


def get_sonnet_extraction(rid):
    path = SONNET_BASE / rid / "vision_merged.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return None

    name, allot, source = None, None, None
    fee_patents = data.get("fee_patents") or []
    if fee_patents:
        fp = fee_patents[0]
        name = fp.get("allottee_name") or None
        allot = fp.get("allotment_number") or None
        source = "fee_patents[0]"

    if not name:
        for ent in data.get("entities") or []:
            if ent.get("type") == "person":
                name = ent.get("name") or None
                source = source or "entities[person]"
                break

    return {"name": name, "allot": allot, "source": source}


def get_qwen_extraction(rid):
    """Find all qwen output JSONs for this record_id and pick the
    highest-confidence reading per field."""
    if not QWEN_BASE.exists():
        return None
    matches = list(QWEN_BASE.glob(f"{rid}_page-*.json"))
    if not matches:
        return None

    best_name, best_name_conf = None, -1
    best_allot, best_allot_conf = None, -1
    confidences = []

    for path in sorted(matches):
        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError:
            continue
        e = data.get("extraction") or {}
        if "_parse_error" in e:
            continue

        name = e.get("name")
        name_conf = CONF_RANK.get((e.get("name_confidence") or "").lower(), -1)
        if name and name_conf > best_name_conf:
            best_name, best_name_conf = name, name_conf

        allot = e.get("allotment_number")
        allot_conf = CONF_RANK.get(
            (e.get("allotment_number_confidence") or "").lower(), -1
        )
        if allot and allot_conf > best_allot_conf:
            best_allot, best_allot_conf = allot, allot_conf

        page = data.get("page", "?")
        confidences.append(
            f"p{page}:n={e.get('name_confidence', '?')[:1]},a={e.get('allotment_number_confidence', '?')[:1]}"
        )

    return {
        "name": best_name,
        "allot": best_allot,
        "name_confidence_rank": best_name_conf,
        "allot_confidence_rank": best_allot_conf,
        "per_page_confidences": "; ".join(confidences),
    }


def normalize_name(s):
    if not s:
        return ""
    return re.sub(r"\W+", "", s).lower()


def normalize_allot(s):
    if not s:
        return ""
    return re.sub(r"[^0-9]", "", str(s))


def main():
    # Get list of records from manifest
    if not MANIFEST.exists():
        print(f"ERROR: manifest not found at {MANIFEST}")
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

    rows = []
    for rid in rids:
        sonnet = get_sonnet_extraction(rid)
        qwen = get_qwen_extraction(rid)

        s_name = (sonnet or {}).get("name") or ""
        s_allot = (sonnet or {}).get("allot") or ""
        q_name = (qwen or {}).get("name") or ""
        q_allot = (qwen or {}).get("allot") or ""

        # Verdict
        if not sonnet and not qwen:
            verdict = "no_outputs"
        elif sonnet and not qwen:
            verdict = "sonnet_only"
        elif qwen and not sonnet:
            verdict = "qwen_only"
        else:
            n_match = normalize_name(s_name) and normalize_name(s_name) == normalize_name(q_name)
            a_match = normalize_allot(s_allot) and normalize_allot(s_allot) == normalize_allot(q_allot)
            if n_match and a_match:
                verdict = "agree"
            elif normalize_name(s_name) and normalize_name(q_name) and not n_match:
                verdict = "disagree_name"
            elif normalize_allot(s_allot) and normalize_allot(q_allot) and not a_match:
                verdict = "disagree_allot"
            elif not s_name and q_name:
                verdict = "qwen_has_name_sonnet_missing"
            elif not q_name and s_name:
                verdict = "sonnet_has_name_qwen_missing"
            elif not s_allot and q_allot:
                verdict = "qwen_has_allot_sonnet_missing"
            elif not q_allot and s_allot:
                verdict = "sonnet_has_allot_qwen_missing"
            else:
                verdict = "neither_has_data"

        rows.append({
            "record_id": rid,
            "verdict": verdict,
            "sonnet_name": s_name,
            "qwen_name": q_name,
            "sonnet_allot": s_allot,
            "qwen_allot": q_allot,
            "qwen_confidences": (qwen or {}).get("per_page_confidences", ""),
        })

    # Write TSV
    with open(OUTPUT_TSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "record_id", "verdict",
            "sonnet_name", "qwen_name",
            "sonnet_allot", "qwen_allot",
            "qwen_confidences",
        ], delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Summary
    from collections import Counter
    counts = Counter(r["verdict"] for r in rows)
    print("=" * 70)
    print("CAT_1 vision comparison: Sonnet vs Qwen")
    print("=" * 70)
    print(f"Total records:    {len(rows)}")
    print()
    print("Verdict breakdown:")
    for v, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {v:35s} {c}")
    print()
    print(f"Output: {OUTPUT_TSV}")
    print()
    print("To see disagreements:")
    print(f"  awk -F'\\t' 'NR==1 || $2 ~ /disagree/' {OUTPUT_TSV.name} | column -t -s $'\\t'")


if __name__ == "__main__":
    main()
