#!/usr/bin/env python3
"""Generate display titles for all documents using AI + summaries."""

import anthropic
import psycopg2
import psycopg2.extras
import os
import json
import time
import sys

DB_NAME = "crow_historical_docs"
BATCH_SIZE = 25  # docs per API call
MODEL = "claude-sonnet-4-6"

PROMPT_TEMPLATE = """Generate a short, clear display title for each document below. These are historical archival documents about the Crow Nation.

Rules:
- Include the year or date range at the START of the title: "1920: House Hearings on..." or "1920–1924: BIA Efforts to Repeal..."
- The date should reflect when the document was CREATED or when the events it documents occurred — NOT the full historical span referenced. A 1920 hearing that mentions events from 1891 should be dated 1920, not 1891–1920. A BIA file containing correspondence from 1920–1924 should be dated 1920–1924. A 1963 Senate Report should be dated 1963, not 1920–1963. Use your judgment based on the summary.
- For compiled collections or correspondence files spanning years, use the range of the documents in the file.
- Be concise but descriptive, like a library catalog entry
- Do NOT include ".pdf" or file classification numbers (CCF, RG 75, etc.) unless they add meaning

Return JSON array with objects {{"id": N, "title": "..."}} — nothing else, no markdown fencing.

Documents:
{docs_json}"""


def get_documents():
    conn = psycopg2.connect(dbname=DB_NAME, host="localhost")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, file_name, LEFT(summary, 500) as summary
        FROM documents
        WHERE summary IS NOT NULL
        ORDER BY id
    """)
    docs = cur.fetchall()
    cur.close()
    conn.close()
    return docs


def generate_titles(client, batch):
    """Send a batch of docs to the AI and get titles back."""
    docs_for_prompt = [
        {"id": d["id"], "file_name": d["file_name"], "summary": d["summary"]}
        for d in batch
    ]

    prompt = PROMPT_TEMPLATE.format(docs_json=json.dumps(docs_for_prompt, indent=2))

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    # Strip markdown fencing if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]

    return json.loads(text)


def update_titles(titles):
    """Write titles to the database."""
    conn = psycopg2.connect(dbname=DB_NAME, host="localhost")
    cur = conn.cursor()
    for t in titles:
        cur.execute(
            "UPDATE documents SET display_title = %s WHERE id = %s",
            (t["title"], t["id"])
        )
    conn.commit()
    cur.close()
    conn.close()


def main():
    dry_run = "--dry-run" in sys.argv

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    docs = get_documents()
    print(f"Found {len(docs)} documents with summaries")

    total_titles = 0
    batches = [docs[i:i + BATCH_SIZE] for i in range(0, len(docs), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        ids = [d["id"] for d in batch]
        print(f"\nBatch {i+1}/{len(batches)} — docs {ids[0]}–{ids[-1]} ({len(batch)} docs)")

        try:
            titles = generate_titles(client, batch)
            print(f"  Generated {len(titles)} titles")

            if dry_run:
                for t in titles[:3]:
                    print(f"    [{t['id']}] {t['title']}")
                if len(titles) > 3:
                    print(f"    ... and {len(titles) - 3} more")
            else:
                update_titles(titles)
                print(f"  Saved to database")

            total_titles += len(titles)

        except json.JSONDecodeError as e:
            print(f"  ERROR: Failed to parse JSON: {e}")
            continue
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        # Brief pause between batches
        if i < len(batches) - 1:
            time.sleep(1)

    print(f"\nDone. Generated {total_titles} titles for {len(docs)} documents.")
    if dry_run:
        print("(Dry run — no changes saved. Run without --dry-run to save.)")


if __name__ == "__main__":
    main()
