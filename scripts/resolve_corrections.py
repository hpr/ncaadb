#!/usr/bin/env python3
"""
Apply corrections from data/corrections.json.
Each entry matches a row by year/school/discipline/gender/environment + name or place,
then updates the specified fields.
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def apply_corrections(db_path: str, json_path: str):
    with open(json_path) as f:
        cases = json.load(f)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    updated = 0
    skipped = 0

    for case in cases:
        corrections = case['corrections']
        name = case.get('name')
        place = case.get('place')
        school = case.get('school')

        where_clauses = [
            'year = ?', 'discipline = ?',
            'gender = ?', 'environment = ?'
        ]
        params = [case['year'], case['discipline'],
                  case['gender'], case['environment']]

        if school is not None:
            where_clauses.append('school = ?')
            params.append(school)
        if name is not None:
            where_clauses.append('name = ?')
            params.append(name)
        if place is not None:
            where_clauses.append('place = ?')
            params.append(place)

        set_parts = []
        set_params = []
        for col, val in corrections.items():
            set_parts.append(f'{col} = ?')
            set_params.append(val)

        query = f"UPDATE results SET {', '.join(set_parts)} WHERE {' AND '.join(where_clauses)}"
        c.execute(query, (*set_params, *params))

        if c.rowcount == 0:
            print(f"  WARNING: no row matched for {case}")
            skipped += 1
        else:
            desc = ', '.join(f'{k}={v}' for k, v in corrections.items())
            name_str = name or ''
            school_str = school or ''
            place_str = f' place={place}' if place else ''
            print(f"  CORRECTED: {name_str} ({school_str}, {case['discipline']}, "
                  f"{case['year']} {case['environment']}{place_str}) {desc}")
            updated += 1

    conn.commit()
    conn.close()

    print(f"\nCorrected: {updated}, Skipped: {skipped}")


if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT / 'ncaa_history.db')
    json_path = sys.argv[2] if len(sys.argv) > 2 else str(PROJECT_ROOT / 'data' / 'corrections.json')
    apply_corrections(db_path, json_path)
