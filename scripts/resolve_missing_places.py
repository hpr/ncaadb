#!/usr/bin/env python3
"""
Resolve missing places based on user-filled missing_places.json.

For each entry, "name" should be:
  - a string with athlete name (insert or update)
  - null (skip, not yet resolved)
  - "skip" (can't find, skip)
  - "tie" (confirm existing tie is correct, no insert needed)

If the athlete already exists in the DB for that event (same name/school/year/
discipline/gender/environment), their place is updated instead of inserting a new row.
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from util.constants import clean_school_name
from parse_outdoor import parse_mark


def resolve_missing_places(db_path: str, json_path: str):
    with open(json_path) as f:
        cases = json.load(f)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    inserted = 0
    updated = 0
    skipped = 0

    for case in cases:
        name = case.get('name')
        place = case.get('place')
        year = case['year']
        discipline = case['discipline']
        gender = case['gender']
        environment = case['environment']

        if name is None:
            print(f"  SKIPPED (not yet resolved): {year} {discipline} {gender} {environment} place={place}")
            skipped += 1
            continue

        if name == 'skip':
            print(f"  SKIPPED (can't find): {year} {discipline} {gender} {environment} place={place}")
            skipped += 1
            continue

        if name == 'tie':
            print(f"  CONFIRMED TIE: {year} {discipline} {gender} {environment}")
            skipped += 1
            continue

        school = case.get('school')
        if school:
            school = clean_school_name(school, year)
        mark_str = case.get('mark_str')
        class_val = case.get('class')

        mark_num = None
        mark_str_clean = None
        is_converted = False
        if mark_str:
            mark_num, mark_str_clean, _, is_converted = parse_mark(mark_str)

        insert_place = case.get('new_place', place) if place is not None else place

        c.execute(
            'SELECT id, place FROM results WHERE year = ? AND name = ? AND school = ? '
            'AND discipline = ? AND gender = ? AND environment = ?',
            (year, name, school, discipline, gender, environment)
        )
        existing = c.fetchone()

        if existing:
            existing_id, existing_place = existing
            if existing_place == 999:
                c.execute(
                    'UPDATE results SET place = ?, is_dq = 0, is_dnf = 0, is_dns = 0 WHERE id = ?',
                    (insert_place, existing_id)
                )
                print(f"  UPDATED (DQ->place {insert_place}): {name} ({school}) {year} {discipline} {gender} {environment}"
                      f"{f' mark={mark_str}' if mark_str else ''}")
                updated += 1
            elif existing_place != insert_place:
                print(f"  WARNING: {name} ({school}) already at place={existing_place} in {year} {discipline} {gender} {environment}, "
                      f"not overwriting to place={insert_place}. Add to removals.json if wrong entry.")
                skipped += 1
            else:
                print(f"  SKIPPED (already exists at place={existing_place}): {name} ({school}) {year} {discipline} {gender} {environment}")
                skipped += 1
        else:
            is_relay = 1 if case.get('is_relay') else 0
            leg_idx = case.get('leg_idx')
            split_time = case.get('split_time')
            is_international = 1 if case.get('is_international') else 0

            if name == 'Relay member unknown' and is_relay and leg_idx is None:
                for i in range(1, 5):
                    c.execute(
                        'INSERT INTO results (year, name, school, discipline, gender, environment, '
                        'place, mark_num, mark_str, class, is_relay, is_dq, is_dnf, is_dns, '
                        'is_wind_aided, is_international, split_time, leg_idx, is_converted) '
                        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?, ?, ?, ?)',
                        (year, name, school, discipline, gender, environment,
                         insert_place, mark_num, mark_str_clean, class_val,
                         is_relay, is_international, split_time, i,
                         1 if is_converted else 0)
                    )
                place_desc = f'{place}->{insert_place}' if insert_place != place else str(place)
                print(f"  INSERTED (4 relay members): {school} {year} {discipline} {gender} {environment} place={place_desc}"
                      f"{f' mark={mark_str}' if mark_str else ''}")
                inserted += 4
            else:
                c.execute(
                    'INSERT INTO results (year, name, school, discipline, gender, environment, '
                    'place, mark_num, mark_str, class, is_relay, is_dq, is_dnf, is_dns, '
                    'is_wind_aided, is_international, split_time, leg_idx, is_converted) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?, ?, ?, ?)',
                    (year, name, school, discipline, gender, environment,
                     insert_place, mark_num, mark_str_clean, class_val,
                     is_relay, is_international, split_time, leg_idx,
                     1 if is_converted else 0)
                )

                place_desc = f'{place}->{insert_place}' if insert_place != place else str(place)
                print(f"  INSERTED: {name} ({school}) {year} {discipline} {gender} {environment} place={place_desc}"
                      f"{f' mark={mark_str}' if mark_str else ''}")
                inserted += 1

    conn.commit()
    conn.close()

    print(f"\nInserted: {inserted}, Updated: {updated}, Skipped: {skipped}")


if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT / 'ncaa_history.db')
    json_path = sys.argv[2] if len(sys.argv) > 2 else str(PROJECT_ROOT / 'data' / 'missing_places.json')
    resolve_missing_places(db_path, json_path)
