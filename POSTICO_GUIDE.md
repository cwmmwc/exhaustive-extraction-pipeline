# Postico 2 Guide for the Extraction Pipeline Databases

A practical reference for using Postico 2 to explore the PostgreSQL
databases that power this project — `unified_index_cards`,
`survey_of_conditions`, `crow_historical_docs`, `historical_docs`,
`full_corpus_docs`, and `index_cards`. Written for a historian, not a
DBA: every example is a real research question, every concept is
introduced when you need it, not before.

---

## 1. What Postico is and why you'd use it

Postico is a Mac-native graphical front end for PostgreSQL. It does
three things well:

- **Browses tables** like a spreadsheet — click a table, see the rows
- **Runs SQL queries** in an editor and shows results in a grid below
- **Exports** any result set to CSV with one click

Think of it as the "look directly at the data" tool. The Streamlit
analysis interface is the AI-narrated tool — it writes prose synthesis
about what's in the database. Postico is what you reach for when you
want exact counts, raw rows, or you want to verify something the AI
wrote. The two complement each other; neither replaces the other.

---

## 2. Connecting

Postico opens to a Servers window. The first time you run it:

1. Click **New Server** (or use the existing "Untitled Server").
2. Fill in the connection panel:

   | Field | Value |
   |---|---|
   | Nickname | `Local Postgres` |
   | Host | `localhost` |
   | Port | `5432` |
   | User | `cwm6W` |
   | Password | *(leave blank — local trust auth)* |
   | Database | `postgres` |

3. Click **Connect**.

You only need to do this once. Postico remembers the favorite. Next
time you launch it, double-click "Local Postgres" to reconnect.

**Why `postgres` in the Database field?** Postgres requires you to
connect to *some* database to log in, even if it's not the one you
want. `postgres` is the system default that always exists. Once
connected, click the **eject icon** in the toolbar (top-left) to go
back to the server view, then **double-click any other database** in
the list to switch to it. You'll do this constantly.

---

## 3. The Postico window, top to bottom

When you have a database open you'll see roughly this layout:

```
┌───────────────────────────────────────────────────────────────┐
│ Toolbar: [sidebar] [eject]  ←→  Database name      [+]  [💬]  │
├──────────────────┬────────────────────────────────────────────┤
│ Queries          │  SQL editor                                │
│   • SQL Query    │                                            │
│   • (saved...)   │  SELECT … FROM … WHERE …;                  │
│                  │                                            │
│ ─────────────    │                                            │
│ Tables           │                                            │
│   • cases        │                                            │
│   • documents    │                                            │
│   • persons      │                                            │
│   • slips        │                                            │
│   • slip_cases   ├────────────────────────────────────────────┤
│   • slip_persons │  Results grid (or error message)           │
│                  │  appears down here after you Execute       │
└──────────────────┴────────────────────────────────────────────┘
```

- **Left sidebar — Queries panel.** Saved SQL queries. Click `+` to
  save your current query. Build a library here over time.
- **Left sidebar — Tables panel.** Every table in the current
  database. Single-click a table to open the row browser. Double-click
  is the same as single-click for tables.
- **Main editor.** Where you type SQL. The numbers down the left are
  line numbers, not part of the query.
- **Bottom — results.** Empty until you execute. After ⌘-Return, the
  results grid (or an error) appears here.
- **Toolbar — eject icon (↑).** Goes up one level: from the SQL editor
  to the database, from the database to the server list. Used for
  switching databases.

---

## 4. SQL in 10 minutes

A SQL query is one sentence that asks the database a question. Every
query has the same skeleton. The optional parts are bracketed.

```sql
SELECT   <which columns>
FROM     <which table>
[WHERE   <filter rows>]
[GROUP BY <bucket rows>]
[ORDER BY <sort order>]
[LIMIT   <how many rows>];
```

The semicolon at the end is the period — it ends the sentence.
Whitespace and line breaks don't matter; you can write a query on one
line or across ten. Postgres is case-insensitive for keywords (`SELECT`
and `select` work the same), but column and table names are
lowercase.

### 4.1 The minimum

```sql
SELECT * FROM slips LIMIT 5;
```

Read this aloud: *"Give me every column (`*` means all), from the
slips table, but only 5 rows."* Run this against any table when you
want a quick peek at what's in it without knowing the column names.

### 4.2 SELECT — picking columns

Replace `*` with a comma-separated list of column names to get only
the columns you care about:

```sql
SELECT file_number, date, correspondent, subject FROM slips LIMIT 5;
```

You can rename a column in the output with `AS`:

```sql
SELECT file_number AS case_file,
       sonnet_slip_count + qwen_slip_count AS total_slips
FROM cases
LIMIT 5;
```

The `+` lets you do arithmetic in the SELECT line. Useful for
combining columns into a single number.

### 4.3 WHERE — filtering rows

`WHERE` is the most important clause. It cuts the table down to just
the rows you care about.

```sql
-- Exact match
SELECT * FROM slips WHERE file_number = '90-2-5-158';

-- Substring (case-sensitive)
SELECT * FROM slips WHERE subject LIKE '%consent%';

-- Substring (case-insensitive — usually what you want)
SELECT * FROM slips WHERE subject ILIKE '%consent%';

-- Multiple conditions
SELECT * FROM slips
WHERE date LIKE '1939%'
  AND subject ILIKE '%fee patent%';

-- Either/or
SELECT * FROM slips
WHERE subject ILIKE '%cancel%'
   OR subject ILIKE '%revoke%';

-- Not null (the column has a value)
SELECT * FROM slips WHERE allottee_name IS NOT NULL;

-- Not null and not empty
SELECT * FROM slips WHERE allottee_name IS NOT NULL AND allottee_name != '';

-- Pattern with anchored start
SELECT * FROM slips WHERE file_number LIKE '90-2-5-%';
```

Key syntax:

| Operator | Meaning |
|---|---|
| `=` | Exact match (use single quotes around text values) |
| `!=` or `<>` | Not equal |
| `LIKE` | Substring match, case-sensitive. `%` is "anything," `_` is "one character." |
| `ILIKE` | Same as LIKE but case-insensitive — almost always what you want |
| `IS NULL` / `IS NOT NULL` | Test for missing values |
| `IN (a, b, c)` | Match any of a list |
| `BETWEEN x AND y` | Range match |
| `AND` / `OR` | Combine conditions |

**Quoting rule:** text values go in **single** quotes (`'90-2-5-158'`).
Double quotes mean something different in SQL (they quote column
names) — don't use them for values.

### 4.4 ORDER BY — sorting

```sql
SELECT * FROM slips
WHERE file_number = '90-2-5-158'
ORDER BY date;          -- ascending (oldest first)

ORDER BY date DESC;     -- descending (newest first)

ORDER BY date NULLS LAST;   -- put missing dates at the end
```

You can sort by multiple columns:

```sql
ORDER BY file_number, date;
```

That sorts by file_number first; within each file_number, by date.

### 4.5 LIMIT — capping the result

```sql
SELECT * FROM slips ORDER BY date DESC LIMIT 50;
```

Always use `LIMIT` until you know how many rows a query returns.
Otherwise you might ask for 17,000 rows and wait for the grid to
render them.

### 4.6 COUNT, GROUP BY — counting and bucketing

`COUNT(*)` returns one number — how many rows match.

```sql
-- Total slips in the unified database
SELECT COUNT(*) FROM slips;

-- How many slips mention "tax"?
SELECT COUNT(*) FROM slips WHERE subject ILIKE '%tax%';
```

`GROUP BY` rolls rows up into buckets, and `COUNT(*)` (or `SUM`,
`AVG`, `MAX`, `MIN`) tells you how many fell into each bucket. Read
the next query as: *"For each correspondent, count how many slips
they sent."*

```sql
SELECT correspondent, COUNT(*) AS n_slips
FROM slips
GROUP BY correspondent
ORDER BY n_slips DESC
LIMIT 20;
```

A more useful version that filters out blank correspondents:

```sql
SELECT correspondent, COUNT(*) AS n_slips
FROM slips
WHERE correspondent IS NOT NULL AND correspondent != ''
GROUP BY correspondent
ORDER BY n_slips DESC
LIMIT 20;
```

Rule: anything in your `SELECT` list that isn't an aggregate function
(`COUNT`, `SUM`, etc.) must appear in `GROUP BY`. Postgres will
complain otherwise.

### 4.7 JOIN — combining tables

The unified database has six tables that link together via shared
columns. To pull information from two tables in one query, you JOIN
them on the shared column. The most common pattern in this database:

```sql
-- Slips for a case file, with the source PDF filename
SELECT s.file_number, s.date, s.correspondent, s.subject,
       d.source_pdf
FROM slips s
JOIN documents d ON s.document_id = d.id
WHERE s.file_number = '90-2-5-158'
ORDER BY s.date;
```

Three things going on:

1. The `FROM slips s` aliases the slips table as `s`. The `JOIN
   documents d ON …` aliases documents as `d`. Aliases save typing —
   you can write `s.date` instead of `slips.date`.
2. The `ON` clause specifies the join column: rows are matched where
   `slips.document_id = documents.id`. Postico knows nothing about
   meaning; you tell it which columns to match on.
3. The SELECT list can pull from both tables using the `s.` and `d.`
   prefixes.

You'll use this same pattern any time you want to combine
slip-level data with the document it came from.

### 4.8 Comments

Anything after `--` on a line is a comment. Use them liberally:

```sql
-- 1939 slips mentioning "consent" in the Nez Perce campaign
SELECT date, correspondent, subject
FROM slips
WHERE file_number LIKE '90-2-5-5%'   -- the 50-59 range
  AND date LIKE '1939%'
  AND subject ILIKE '%consent%';
```

---

## 5. The unified_index_cards database — what's in it

Six tables, all linked by shared columns. Quick reference:

### `documents` (87 rows)

One row per source PDF. Key columns: `id`, `source_pdf` (the relative
path inside the source directory tree — used to disambiguate basename
collisions), `subcollection` (top-level folder like `90-2-5` or
`90-2-11`), `num_pages`, and the booleans `sonnet_extracted` /
`qwen_extracted` recording which extraction processed this PDF.

### `slips` (17,211 rows)

The atomic unit. One row per physical record slip after slip-level
dedup. Key columns:

| column | what it is |
|---|---|
| `id` | unique slip ID |
| `document_id` | foreign key → `documents.id` |
| `file_number` | DOJ case file (e.g. `90-2-5-49`) — the join key for everything |
| `date` | free-text date as written on the slip |
| `correspondent` | who wrote the slip |
| `correspondent_role` | their role (Attorney General, U.S. Atty., etc.) |
| `case_name` | the legal case name as it appeared on this slip |
| `case_number` | court docket number when known |
| `allottee_name` | the named individual / allottee |
| `allottee_number` | their allotment number |
| `tribe_or_reservation` | tribal affiliation |
| `subject` | the slip's subject line |
| `action_type` | nature of the action being taken |
| `extraction_source` | `sonnet+qwen`, `sonnet-only`, or `qwen-only` |
| `search_vector` | the FTS index (don't query directly, see §6) |

### `cases` (2,108 rows)

One row per unique `file_number`. Aggregate columns:

| column | what it is |
|---|---|
| `file_number` | primary key |
| `canonical_case_name` | longest variant of the case name |
| `case_name_variants` | array of all observed case_name variants |
| `sonnet_slip_count` / `qwen_slip_count` | how many slips each extraction found |
| `cases_at_file_number` | distinct cases under this file_number (>1 = master file) |
| `distinct_persons_count` | unique persons across all slips |

### `persons` (4,359 rows)

One row per unique normalized name. Key columns: `canonical_name`,
`name_variants` (array), `roles` (array), `tribes` (array),
`file_numbers` (array of file_numbers this person appears in),
`sources` (which extractions found them), `sonnet_mention_count`,
`qwen_mention_count`.

### `slip_cases` and `slip_persons`

Many-to-many join tables. You'll rarely query them directly — use the
`persons.file_numbers` array instead for person→case lookups.

---

## 6. Real research queries

Every query in this section is something you'd actually want to ask a
historical archive. Paste any of them into Postico and run.

### 6.1 What's in here?

```sql
-- How many of everything?
SELECT
  (SELECT COUNT(*) FROM documents) AS documents,
  (SELECT COUNT(*) FROM slips)     AS slips,
  (SELECT COUNT(*) FROM cases)     AS cases,
  (SELECT COUNT(*) FROM persons)   AS persons;
```

```sql
-- Slip distribution by extraction source
SELECT extraction_source, COUNT(*)
FROM slips
GROUP BY extraction_source;
```

```sql
-- Slip distribution by subcollection (90-2-5 vs 90-2-11 etc.)
SELECT d.subcollection, COUNT(s.id) AS slips
FROM documents d
LEFT JOIN slips s ON s.document_id = d.id
GROUP BY d.subcollection
ORDER BY slips DESC;
```

### 6.2 Heaviest case files

```sql
-- The 25 case files with the most slips
SELECT file_number, canonical_case_name,
       sonnet_slip_count + qwen_slip_count AS total_slips,
       cases_at_file_number,
       distinct_persons_count
FROM cases
ORDER BY total_slips DESC
LIMIT 25;
```

### 6.3 Master classifications (file numbers covering many cases)

```sql
-- File numbers that cover more than one distinct case — likely
-- campaigns or master files (e.g. 90-2-01 = Indians--Legislation)
SELECT file_number, canonical_case_name,
       cases_at_file_number,
       sonnet_slip_count + qwen_slip_count AS total_slips
FROM cases
WHERE cases_at_file_number > 5
ORDER BY cases_at_file_number DESC
LIMIT 30;
```

### 6.4 Trace a specific case file

```sql
-- Every slip for the Pearly DeRoin file (Iowa, Kansas), in order
SELECT date, correspondent, correspondent_role, subject, allottee_name
FROM slips
WHERE file_number = '90-2-5-158'
ORDER BY date;
```

### 6.5 Trace a person across the corpus

```sql
-- All file numbers a person appears in
SELECT canonical_name, file_numbers, sources,
       sonnet_mention_count, qwen_mention_count
FROM persons
WHERE canonical_name ILIKE '%deroin%'
   OR canonical_name ILIKE '%roubidoux%';
```

```sql
-- All slips mentioning a person by allottee_name
SELECT file_number, date, correspondent, subject
FROM slips
WHERE allottee_name ILIKE '%mko-quah-wah%'
ORDER BY date;
```

### 6.6 Free-text search across slips

The slips table has a generated `search_vector` column that indexes
the file_number, jurisdiction, correspondent, correspondent_role,
case_name, case_number, allottee_name, tribe_or_reservation, subject,
action_type, and routing_division all together. Use it like this:

```sql
-- Slips matching "forced fee patent" anywhere in the indexed fields
SELECT file_number, date, correspondent, subject
FROM slips
WHERE search_vector @@ to_tsquery('english', 'forced & fee & patent')
ORDER BY date;
```

The `@@` operator is "matches." `to_tsquery` is the parser for the
search expression — `&` is AND, `|` is OR, `!` is NOT. Use English
stems: `tax` will also match `taxes`, `taxation`, etc.

```sql
-- "consent" OR "application" near "patent"
SELECT file_number, date, subject
FROM slips
WHERE search_vector @@ to_tsquery('english', '(consent | application) & patent')
ORDER BY date;
```

When you don't know the exact phrasing, ILIKE is more forgiving:

```sql
SELECT file_number, date, subject
FROM slips
WHERE subject ILIKE '%competen%'   -- matches competent, competency, competence
ORDER BY date;
```

### 6.7 Date range for a case file

```sql
SELECT file_number,
       MIN(date) AS earliest,
       MAX(date) AS latest,
       COUNT(*)  AS n_slips
FROM slips
WHERE file_number LIKE '90-2-5-%'
GROUP BY file_number
ORDER BY n_slips DESC
LIMIT 20;
```

(Date sorting is alphabetic here because the `date` column is text,
not a real date type — slip dates are too varied to parse cleanly.
Good enough for sorting if the format is consistent within a
file_number.)

### 6.8 Cross-table — slips with their source PDF

```sql
SELECT s.file_number, s.date, s.case_name, s.subject,
       d.source_pdf, d.subcollection
FROM slips s
JOIN documents d ON s.document_id = d.id
WHERE s.subject ILIKE '%cancel%' AND s.subject ILIKE '%patent%'
ORDER BY s.date;
```

### 6.9 Persons with the broadest reach

```sql
-- People who appear across the most distinct case files
SELECT canonical_name,
       array_length(file_numbers, 1) AS n_files,
       sonnet_mention_count + qwen_mention_count AS total_mentions
FROM persons
WHERE array_length(file_numbers, 1) IS NOT NULL
ORDER BY n_files DESC
LIMIT 25;
```

`array_length(col, 1)` returns the size of an array column.

### 6.10 Persons in a specific master file

```sql
-- Everyone named in any case under master file 90-2-01
-- (Indians--Legislation)
SELECT canonical_name, sonnet_mention_count + qwen_mention_count AS mentions
FROM persons
WHERE '90-2-01' = ANY(file_numbers)
ORDER BY mentions DESC;
```

`ANY(array_column)` checks if a value appears anywhere in an array.

---

## 7. Working with the other databases

The same techniques apply, but the table names differ. Quick map:

### `survey_of_conditions`

`documents`, `entities`, `mentions`, `events`, `financial_transactions`,
`relationships`, `fee_patents`, `correspondence`,
`legislative_actions`, `testimony`, `taxes`, `mortgages`. The atomic
unit is the entity, not the slip. Use the `documents.full_text` column
for full-text search:

```sql
SELECT file_name, display_title
FROM documents
WHERE to_tsvector('english', full_text) @@ websearch_to_tsquery('english', 'forced fee patent')
LIMIT 20;
```

### `crow_historical_docs`, `historical_docs`, `full_corpus_docs`

Same v3 schema as `survey_of_conditions`. The `fee_patents` table is
the heart of these — it's the structured allottee/acreage/buyer/date
breakdown.

```sql
-- Heaviest fee_patent extractors in the Crow database
SELECT allottee_name, COUNT(*) AS n_patents,
       SUM(acres) AS total_acres
FROM fee_patents
WHERE allottee_name IS NOT NULL
GROUP BY allottee_name
ORDER BY total_acres DESC NULLS LAST
LIMIT 25;
```

### `index_cards` (the legacy DOJ index card DB, pre-merge)

Two tables: `record_slips` and `legal_cases`. The unified database
supersedes this for most uses, but it's still here.

---

## 8. Postico tips and ergonomics

### 8.1 Keyboard shortcuts you'll actually use

| shortcut | what it does |
|---|---|
| `⌘-Return` | Execute the current query |
| `⌘-T` | Open a new query tab in the same connection |
| `⌘-A` | Select all (in the SQL editor — useful before deleting) |
| `⌘-/` | Toggle comment on the selected lines |
| `⌘-S` | Save the current query as a `.sql` file |
| `⌘-F` | Find within the current query |
| `⌘-+` / `⌘--` | Zoom the editor font in / out |

### 8.2 Saving queries

Click the **+** button at the bottom of the Queries panel (left
sidebar) to save the current SQL as a named query. Saved queries
persist across Postico restarts and live in the favorite, not on
disk. Build a small library — "heaviest case files," "all DeRoin
slips," "every slip mentioning consent" — and they're one click away
forever.

If you want a query stored on disk (e.g. to commit to git or share),
**⌘-S** writes it to a `.sql` file you choose the location for.

### 8.3 Exporting results

After running a query, the bottom of the result grid has an
**Export** button. Click it to dump the current result set to CSV.
The dialog lets you pick the filename and location. CSV opens
directly in Excel and Numbers.

You can also select cells in the result grid and **⌘-C** to copy
them as tab-separated text — paste straight into Excel or a Markdown
table.

### 8.4 The table browser (no SQL needed)

Single-click any table in the Tables panel and Postico shows it as a
spreadsheet. At the top of the grid:

- **Magnifying glass** — opens a filter row. Type in any column to
  filter rows where that column contains your text.
- **Sort** — click any column header to sort by it.
- **Column show/hide** — right-click a header to hide columns you
  don't care about.

For quick browsing this is faster than writing SQL. For anything that
involves combining tables, counting, or pulling specific subsets, use
the SQL editor.

### 8.5 Don't accidentally edit data

The table browser lets you click into a cell, change its value, and
press tab/return — and Postico will write the change back to the
database. There is no "undo" button.

Two ways to protect yourself:

- **Stay in the SQL editor** for any work that isn't explicit
  browsing. SQL queries don't accidentally write data.
- **Use a read-only role.** In the favorite settings you can set a
  startup query like `SET default_transaction_read_only = on;` which
  will block accidental writes for the entire connection. Useful if
  you're nervous.

### 8.6 Switching databases

The eject icon in the toolbar (top-left, next to the sidebar icon)
goes up one level: from a query window to the database list. From
there, double-click any other database to switch. Postico opens it in
the same window — your saved queries from the previous database stay
where they were.

If you want both databases open at once, use **File → New Window**
and connect to the second one.

### 8.7 Query History

The **Query History** button at the bottom of the SQL editor opens a
log of every query you've run, with timestamps. Click any past query
to bring it back into the editor. Useful for "what was that thing I
ran an hour ago…"

### 8.8 Following foreign keys

In the table browser, ⌥-click on a foreign-key cell (e.g.
`slips.document_id`) and Postico jumps to the referenced row in the
parent table. Handy for slip → document navigation without writing a
JOIN.

### 8.9 If a query hangs

The **Cancel** button next to Execute Statement aborts a long-running
query. Postgres will roll back any partial work — nothing gets
half-committed.

If Postico itself hangs (rare), force-quit and reopen. Your saved
queries persist; only the current session is lost.

---

## 9. Common errors and what they mean

| error | cause | fix |
|---|---|---|
| `column "X" does not exist` | typo, or you forgot the FROM clause, or the column lives in a different table | check spelling; make sure FROM is present; check `\d table_name` (or click the table in the sidebar) for the actual columns |
| `relation "X" does not exist` | wrong table name, or you're connected to the wrong database | check the database name in the toolbar; check the Tables panel for the real name |
| `syntax error at or near "..."` | missing comma, missing quote, missing semicolon, mistyped keyword | look at the line/character the error points to and the token just before it |
| `column must appear in the GROUP BY clause` | you used GROUP BY but selected a column that isn't grouped or aggregated | either add the column to GROUP BY or wrap it in an aggregate like `MAX(col)` |
| `more than one row returned by a subquery used as an expression` | a subquery in your SELECT or WHERE returned multiple rows when only one was expected | add `LIMIT 1`, or use `IN (...)` instead of `=` |
| `invalid input syntax for type ...` | passing text where a number is expected, or vice versa | check your value types; remember text needs single quotes, numbers don't |
| `connection failed` | Postgres isn't running, or wrong host/port/user, or trying to connect to a non-existent database | run `pg_isready -h localhost -p 5432` in Terminal; if not running, `brew services start postgresql` (or however you installed it) |

---

## 10. Where to go next

- **The Postgres docs** at https://www.postgresql.org/docs/current/ —
  the SQL reference is exhaustive but very readable. The "Tutorial"
  chapter covers everything in this guide more formally.
- **Postico's own help**: Help → Postico Help in the menu bar.
- **Practice queries**: every research question you've asked the
  Streamlit interface can be reformulated as a SQL query against the
  same database. Try translating one — it forces you to think about
  what the AI was actually doing under the hood.

The single most useful habit you can build: **whenever you're not sure
what's in a table, write `SELECT * FROM tablename LIMIT 5;` first.**
That gives you the shape of the data in two seconds and saves you
five minutes of guessing column names.
