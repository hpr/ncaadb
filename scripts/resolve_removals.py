#!/usr/bin/env python3
"""
Remove incorrect entries based on user-filled removals.json.

Each entry identifies a row to delete by matching on year, discipline, gender,
environment, and optionally name, school, and/or place.
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from util.constants import clean_school_name


def resolve_removals(db_path: str, json_path: str):
    with open(json_path) as f:
        cases = json.load(f)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    deleted = 0
    skipped = 0

    for case in cases:
        year = case['year']
        discipline = case['discipline']
        gender = case['gender']
        environment = case['environment']

        conditions = ['year = ?', 'discipline = ?', 'gender = ?', 'environment = ?']
        params = [year, discipline, gender, environment]

        name = case.get('name')
        if name:
            conditions.append('name = ?')
            params.append(name)

        school = case.get('school')
        if school:
            conditions.append('school = ?')
            params.append(clean_school_name(school, year))

        place = case.get('place')
        if place is not None:
            conditions.append('place = ?')
            params.append(place)

        where = ' AND '.join(conditions)

        c.execute(f'SELECT id, name, school, place FROM results WHERE {where}', params)
        rows = c.fetchall()

        if not rows:
            print(f"  WARNING: no match for {year} {discipline} {gender} {environment}"
                  f"{f' name={name}' if name else ''}{f' school={school}' if school else ''}"
                  f"{f' place={place}' if place is not None else ''}")
            skipped += 1
            continue

        for row in rows:
            c.execute('DELETE FROM results WHERE id = ?', (row[0],))
            print(f"  DELETED: id={row[0]} {row[1]} ({row[2]}) place={row[3]}"
                  f" {year} {discipline} {gender} {environment}")
            deleted += 1

    conn.commit()
    conn.close()

    print(f"\nDeleted: {deleted}, Skipped: {skipped}")


if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT / 'ncaa_history.db')
    json_path = sys.argv[2] if len(sys.argv) > 2 else str(PROJECT_ROOT / 'data' / 'removals.json')
    resolve_removals(db_path, json_path)
