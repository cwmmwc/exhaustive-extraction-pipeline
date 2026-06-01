#!/usr/bin/env python3
"""
Append a top-level principle section to OPERATIONS.md establishing
that this is an academic-historian project, not a business or startup,
and that resource-driven shortcuts are explicitly out of scope.

User instruction (2026-05-04): "I am an academic historian who needs to
remain committed to the data and data integrity, complexity, and detail.
Never consider resources of time, money, or compute unless explicitly
asked. All decisions should be made regardless of their cost."
"""
from pathlib import Path

OPERATIONS_PATH = Path(
    "/Users/cwm6W/projects/exhaustive-extraction-pipeline/OPERATIONS.md"
)

ADDITIONS = """

---

## NO QUICK FIXES — academic-historian principles (2026-05-04)

This is not a business project, a startup, or a resource-constrained
sprint. It is an academic historian's research apparatus, where the
deliverable is scholarly argument grounded in defensible source-level
evidence. The standards that apply:

**Correctness over speed.** When a data question has multiple plausible
answers, the answer is "render the source and verify" — not "pick the
likeliest one and move on." Speed is not a goal. Coverage is not a
goal. Defensibility is the goal.

**Complexity is preserved, not collapsed.** Real historical records
contain ambiguity, partial information, contradictions across sources,
and edge cases that don't fit clean schemas. The job is to capture
that complexity, not paper over it. When two records appear to be
about the same person but disagree, that disagreement is data — not
something to resolve by picking one and discarding the other.

**Detail is preserved.** Substantive content (a quoted phrase, a
buyer's name, a sale price, a marginal note) goes into the record
even if it doesn't fit a column. NOTES exists for this. Vision
extractions preserve the full v5 schema even when the flat schema
doesn't have a column for a given field.

**Resources are not constraints unless explicitly asked.** Do not
propose decisions framed by:
  - Time ("we should do X tonight rather than wait for Y")
  - Money / API spend ("X costs $0.05 per record so we should batch")
  - Compute ("the queue is deep so let's defer this")
  - Convenience ("X is faster, even though Y is more rigorous")

If a tradeoff between rigor and resources is genuinely material,
state it explicitly and ask. Do not preemptively choose the cheap
or fast option.

**No quick fixes for complex problems.** The disagreement scan
(Sonnet vs Kimi v5) is a triage tool, not a patch tool. Both models
can be wrong (Edward Little Eagle case). Bulk patches that replace
visibly-garbled values with confident-looking-but-unverified values
remove the signal of failure and replace it with silent error. This
is not acceptable. Per-record source verification is the workflow,
even when slow.

**The corpus is a research tool, not a forensic database.** Pattern-
level claims (Role 2) and atmospheric/illustrative evidence (Role 1)
are the load-bearing analytical moves. Precise quantitative claims
(Role 3) are not. But within the records that are kept, the standard
is correctness — including capturing what is unknown as unknown,
not as "not stated" when it should be "not visible on this page" or
"contradicted by another source."

**Default behaviors that follow from these principles:**

- Always render the source page when there is genuine doubt
- Always preserve original extraction artifacts (`pre_split_sonnet_extraction`,
  `recovery_notes`) before patching — never silently overwrite
- Always record the methodology used (which models, which sources,
  which user verifications) so the audit trail is intact
- When in doubt about which of two interpretations is correct, say so
  in NOTES rather than committing to one
- When two records appear redundant, distinguish duplicates (delete)
  from continuation pages (keep both, cross-reference)
- Never propose `agency_correspondence` or any other umbrella reclass-
  ification when a more specific type captures the analytical reality
  (e.g., `agency_buyer_report`)
"""

MARKER = "## NO QUICK FIXES — academic-historian principles"


def main():
    if not OPERATIONS_PATH.exists():
        print(f"ERROR: {OPERATIONS_PATH} does not exist.")
        return

    with open(OPERATIONS_PATH) as f:
        existing = f.read()

    if MARKER in existing:
        print(f"Marker '{MARKER}' already present. Refusing to duplicate.")
        return

    with open(OPERATIONS_PATH, "a") as f:
        f.write(ADDITIONS)

    print(f"Appended {len(ADDITIONS.splitlines())} lines to OPERATIONS.md")
    print()
    print("New section: NO QUICK FIXES — academic-historian principles")


if __name__ == "__main__":
    main()
