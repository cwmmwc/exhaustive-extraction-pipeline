"""
Re-stamp recovery_notes entries dated 2026-05-04 to 2026-06-01.

These records were originally patched on 2026-05-04 (Task 5 CAT_3 backfill, etc.).
git filter-repo on 2026-06-01 wiped the uncommitted modifications, and the work
was mechanically re-applied in commit 83c8fb6 the same day. The internal date
strings still read "2026-05-04" because the replay copied the original payloads
verbatim. Per TRIBE_NORMALIZATION_NOTES.md, the date should reflect when the
JSON on disk was written: 2026-06-01.

Idempotent. Only mutates recovery_notes[i].date == "2026-05-04". Leaves every
other field, including any nested "2026-05-04" string inside previous_values or
corrected_values, untouched.
"""
import json
from pathlib import Path

OLD_DATE = "2026-05-04"
NEW_DATE = "2026-06-01"
SONNET_DIR = Path(__file__).parent / "circular_2464_extractions" / "extractions" / "sonnet"


def fix_file(path: Path) -> int:
    raw = path.read_text()
    data = json.loads(raw)
    notes = data.get("recovery_notes")
    if not isinstance(notes, list):
        return 0
    changed = 0
    for n in notes:
        if isinstance(n, dict) and n.get("date") == OLD_DATE:
            n["date"] = NEW_DATE
            changed += 1
    if changed:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return changed


def main() -> None:
    files = sorted(SONNET_DIR.glob("*.json"))
    total_entries = 0
    files_touched = 0
    for f in files:
        n = fix_file(f)
        if n:
            files_touched += 1
            total_entries += n
    print(f"Scanned {len(files)} files in {SONNET_DIR}")
    print(f"Re-stamped {total_entries} recovery_notes entries across {files_touched} files")
    print(f"  {OLD_DATE} -> {NEW_DATE}")


if __name__ == "__main__":
    main()
