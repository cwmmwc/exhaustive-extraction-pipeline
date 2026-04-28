# names_match_v2 Diff Table

## New Matches (v2 finds, v1 doesn't)

| AI Name | AI Allot | GT Name | GT Allot | Last Sim | First Sim | Fix Required |
|---------|----------|---------|----------|----------|-----------|-------------|
| Benjamin Janis, junior | 711 | Benjamin Janis | 709 | 1.00 | 1.00 | Fix 1 (suffix strip) |
| Samuel Lessert Junior | 967 | Samuel Lessert, Jr. | 967 | 1.00 | 1.00 | Fix 1 |
| John Galligo, senior | 1178 | John Galligo Sr. | 1178 | 1.00 | 1.00 | Fix 1 |
| John Cottier, Junior | 988 | John Cottier, Sr. | 986 | 1.00 | 1.00 | Fix 1 |
| Jennie Red Wing, ne Velandry | 1082 | Jennie Red Wing (nee Valandry) | 1082 | 0.88 | 1.00 | Fix 2 (fuzzy last) |
| Louis Mosseau | 1859 | Louis Mousseau | 1856 | 0.93 | 1.00 | Fix 2 |

## False Positives (v2 merges distinct GT entries that v1 keeps separate)

| Name A | Allot A | Name B | Allot B | Status |
|--------|---------|--------|---------|--------|
| Benjamin Janis | 709 | Bejmain Janis Jr. | 711 | **FALSE POSITIVE** — different people (father/son or typo) |
| John Cottier, Sr. | 986 | John Cottier, Jr. | 988 | **FALSE POSITIVE** — father and son, different allotments |

## Analysis

- **Fix 1 alone (suffix stripping):** +4 true matches, +2 false positives. The false positives are father/son pairs where Jr. and Sr. get collapsed.
- **Fix 2 alone (fuzzy last name, exact first required):** +2 true matches, +0 false positives. Clean but narrow.
- **Both together:** +6 true matches, +2 false positives.

## Recommended Fix

Fix 1 needs refinement: strip suffixes but if BOTH names had suffixes, require the suffixes to agree (Jr.↔Jr., Sr.↔Sr.). "John Cottier Junior" matches "John Cottier Jr." but NOT "John Cottier Senior."

Fix 2 is safe as-is: the exact-first-name constraint prevents false positives.
