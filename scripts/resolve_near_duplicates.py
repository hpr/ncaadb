#!/usr/bin/env python3
"""
Resolve near-duplicates based on user-filled near_duplicates.json.

For each entry, "keep_place" should be:
  - an integer place value (keep that row, delete the other(s))
  - "both" (keep all rows)
  - "neither" (delete all rows)
  - null (skip, will print a warning)
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_near_duplicates(db_path: str, json_path: str):
    with open(json_path) as f:
        cases = json.load(f)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    resolved = 0
    deleted = 0
    skipped = 0

    for case in cases:
        name = case['name']
        keep_place = case.get('keep_place')
        key = (name, case['school'], case['discipline'],
               case['gender'], case['year'], case['environment'])

        if keep_place is None:
            print(f"  SKIPPED (keep_place=null): {name} ({case['discipline']}, {case['year']} {case['environment']})")
            skipped += 1
            continue

        c.execute(
            'SELECT id, place FROM results WHERE name=? AND school=? AND discipline=? AND gender=? AND year=? AND environment=?',
            key
        )
        rows = c.fetchall()

        if not rows:
            print(f"  WARNING: no rows found for {name}")
            skipped += 1
            continue

        if keep_place == 'both':
            print(f"  KEPT BOTH: {name}")
            resolved += 1
            continue

        if keep_place == 'neither':
            ids = [r[0] for r in rows]
            placeholders = ','.join('?' * len(ids))
            c.execute(f'DELETE FROM results WHERE id IN ({placeholders})', ids)
            print(f"  DELETED ALL: {name} ({c.rowcount} rows)")
            deleted += c.rowcount
            resolved += 1
            continue

        keep_place_int = int(keep_place)
        to_delete = [r[0] for r in rows if r[1] != keep_place_int]
        if not to_delete:
            print(f"  WARNING: no row with place={keep_place_int} for {name}")
            skipped += 1
            continue

        placeholders = ','.join('?' * len(to_delete))
        c.execute(f'DELETE FROM results WHERE id IN ({placeholders})', to_delete)
        print(f"  KEPT place={keep_place_int}, DELETED {to_delete}: {name}")
        deleted += c.rowcount
        resolved += 1

    conn.commit()
    conn.close()

    print(f"\nResolved: {resolved}, Deleted: {deleted} rows, Skipped: {skipped}")


if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT / 'ncaa_history.db')
    json_path = sys.argv[2] if len(sys.argv) > 2 else str(PROJECT_ROOT / 'data' / 'near_duplicates.json')
    resolve_near_duplicates(db_path, json_path)
