#!/usr/bin/env python3
"""
Validate event_groups.json against the database.
Checks that every (discipline, environment, gender, year) in the DB
is covered by event_groups.json, and vice versa.
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / 'ncaa_history.db'
EG_PATH = PROJECT_ROOT / 'data' / 'event_groups.json'


def load_event_groups():
    with open(EG_PATH) as f:
        return json.load(f)


def years_for_gender(variants, gender):
    years = set()
    for v in variants:
        ranges = v.get(gender)
        if not ranges:
            continue
        for start, end in ranges:
            end = end or 9999
            for y in range(start, min(end, 9999) + 1):
                years.add(y)
    return years


def main():
    eg = load_event_groups()
    conn = sqlite3.connect(str(DB_PATH))

    failures = 0
    warnings = 0

    db_combos = conn.execute(
        'SELECT DISTINCT discipline, environment, gender, year '
        'FROM results ORDER BY environment, discipline, gender, year'
    ).fetchall()

    print("=== Checking DB rows against event_groups.json ===\n")

    for disc, env, gender, year in db_combos:
        groups = eg.get(env, [])
        group = next((g for g in groups if g['discipline'] == disc), None)
        if group is None:
            print(f"FAIL: discipline '{disc}' not found in event_groups.{env}")
            failures += 1
            continue

        valid_years = years_for_gender(group['variants'], gender)
        if year not in valid_years:
            print(f"FAIL: {disc}/{env}/{gender} year {year} not in event_groups ranges")
            failures += 1

    print(f"\n=== Checking event_groups.json ranges against DB ===\n")

    for env in ['outdoor', 'indoor']:
        for group in eg[env]:
            disc = group['discipline']
            for gender in ['men', 'women']:
                valid_years = years_for_gender(group['variants'], gender)
                if not valid_years:
                    continue

                db_years = set(
                    r[0] for r in conn.execute(
                        'SELECT DISTINCT year FROM results '
                        'WHERE discipline = ? AND environment = ? AND gender = ?',
                        (disc, env, gender)
                    ).fetchall()
                )

                expected = valid_years - db_years
                expected = {y for y in expected if y not in (1924, 2020) and y < 2026}
                if expected:
                    sorted_missing = sorted(expected)
                    chunks = []
                    start = sorted_missing[0]
                    end = sorted_missing[0]
                    for y in sorted_missing[1:]:
                        if y == end + 1:
                            end = y
                        else:
                            chunks.append(f"{start}" if start == end else f"{start}-{end}")
                            start = y
                            end = y
                    chunks.append(f"{start}" if start == end else f"{start}-{end}")
                    print(f"WARN: {disc}/{env}/{gender} has no DB data for: {', '.join(chunks)}")
                    warnings += 1

    conn.close()

    print(f"\nFailures: {failures}, Warnings: {warnings}")
    if failures > 0:
        print("RESULT: FAIL")
        sys.exit(1)
    else:
        print("RESULT: PASS")
        sys.exit(0)


if __name__ == '__main__':
    main()
