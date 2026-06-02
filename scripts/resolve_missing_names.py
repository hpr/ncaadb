#!/usr/bin/env python3
"""
Resolve missing/incomplete names based on user-filled missing_names.json.

For each entry, "name" should be:
  - a string (update the row's name to this value)
  - null (skip, not yet resolved)
  - "skip" (can't find, skip)
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_missing_names(db_path: str, json_path: str):
    with open(json_path) as f:
        cases = json.load(f)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    updated = 0
    skipped = 0

    for case in cases:
        new_name = case.get('name')
        current_name = case['current_name']
        leg_idx = case.get('leg_idx')

        if new_name is None:
            print(f"  SKIPPED (not yet resolved): {current_name or '<empty>'} "
                  f"({case['school']}, {case['discipline']}, {case['year']} {case['environment']}"
                  f"{f', leg {leg_idx}' if leg_idx is not None else ''})")
            skipped += 1
            continue

        if new_name == 'skip':
            print(f"  SKIPPED (can't find): {current_name or '<empty>'} "
                  f"({case['school']}, {case['discipline']}, {case['year']} {case['environment']}"
                  f"{f', leg {leg_idx}' if leg_idx is not None else ''})")
            skipped += 1
            continue

        new_place = case.get('new_place')
        match_place = case.get('db_place', case['place'])

        set_parts = ['name = ?']
        set_params = [new_name]
        if new_place is not None:
            set_parts.append('place = ?')
            set_params.append(new_place)
        set_clause = ', '.join(set_parts)

        where_parts = ['year = ?', 'school = ?', 'discipline = ?',
                       'gender = ?', 'environment = ?']
        where_params = [case['year'], case['school'], case['discipline'],
                        case['gender'], case['environment']]
        if match_place is None:
            where_parts.append('place IS NULL')
        else:
            where_parts.append('place = ?')
            where_params.append(match_place)
        where_parts.append('name = ?')
        where_params.append(current_name)
        if leg_idx is not None:
            where_parts.append('leg_idx = ?')
            where_params.append(leg_idx)

        query = f"UPDATE results SET {set_clause} WHERE {' AND '.join(where_parts)}"
        c.execute(query, (*set_params, *where_params))

        leg_desc = f', leg {leg_idx}' if leg_idx is not None else ''
        place_desc = f', place={match_place}->{new_place}' if new_place is not None else f', place={match_place}'
        if c.rowcount == 0:
            print(f"  WARNING: no row matched for {current_name or '<empty>'} "
                  f"({case['school']}, {case['discipline']}, {case['year']} {case['environment']}"
                  f"{place_desc}{leg_desc})")
            skipped += 1
        else:
            print(f"  UPDATED: '{current_name or '<empty>'}' -> '{new_name}' "
                  f"({case['school']}, {case['discipline']}, {case['year']} {case['environment']}"
                  f"{place_desc}{leg_desc})")
            updated += 1

    conn.commit()
    conn.close()

    print(f"\nUpdated: {updated}, Skipped: {skipped}")


if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT / 'ncaa_history.db')
    json_path = sys.argv[2] if len(sys.argv) > 2 else str(PROJECT_ROOT / 'data' / 'missing_names.json')
    resolve_missing_names(db_path, json_path)
