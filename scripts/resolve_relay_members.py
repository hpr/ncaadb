#!/usr/bin/env python3
"""
Resolve relay members from user-filled JSON template files.

For each team entry, if ALL members have name != null, the script:
  - DELETES ALL relay rows for the team (year/discipline/gender/environment/place/school)
  - INSERTS 4 member rows with is_relay=1 and individual leg_idx/split_time

Members with name = "skip" are inserted as "Unknown" placeholders.
Teams with any name = null member are skipped entirely.
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
sys.path.insert(0, str(PROJECT_ROOT))

from parse_outdoor import parse_mark

TEMPLATE_FILES = [
    'relay_members_men_indoor.json',
    'relay_members_men_outdoor.json',
    'relay_members_women_indoor.json',
    'relay_members_women_outdoor.json',
]


def resolve_relay_members(db_path: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    total_deleted = 0
    total_inserted = 0
    total_skipped = 0

    for filename in TEMPLATE_FILES:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"  SKIP (file not found): {filepath}")
            continue

        with open(filepath) as f:
            teams = json.load(f)

        print(f"\n{filename}: {len(teams)} teams")

        for team in teams:
            year = team['year']
            discipline = team['discipline']
            gender = team['gender']
            environment = team['environment']
            place = team['place']
            school = team['school']
            mark_str = team.get('mark_str')
            members = team['members']

            has_unresolved = any(m.get('name') is None for m in members)
            if has_unresolved:
                print(f"  SKIPPED (unresolved members): {year} {discipline} "
                      f"{gender} {environment} place={place} {school}")
                total_skipped += 1
                continue

            c.execute(
                "DELETE FROM results WHERE year = ? AND discipline = ? "
                "AND gender = ? AND environment = ? AND school = ? "
                "AND place IS ? AND is_relay = 1",
                (year, discipline, gender, environment, school, place)
            )
            deleted = c.rowcount
            total_deleted += deleted
            if deleted > 0:
                print(f"  Deleted {deleted} existing relay rows for "
                      f"{year} {discipline} {gender} {environment} place={place} {school}")

            mark_num = None
            is_converted = False
            if mark_str:
                mark_num, _, _, is_converted = parse_mark(mark_str)

            # Insert member rows
            for member in members:
                name = member['name']
                if name == 'skip':
                    name = 'Unknown'
                leg_idx = member.get('leg_idx')
                split_time = member.get('split_time')

                c.execute(
                    "INSERT INTO results "
                    "(year, name, school, discipline, gender, environment, "
                    "place, mark_str, mark_num, is_relay, leg_idx, split_time, "
                    "is_dq, is_dnf, is_dns, is_wind_aided, is_international, is_converted) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 0, 0, 0, 0, 0, ?)",
                    (year, name, school, discipline, gender, environment,
                     place, mark_str, mark_num, leg_idx, split_time,
                     1 if is_converted else 0)
                )
                total_inserted += 1

            member_names = [m['name'] for m in members]
            print(f"  RESOLVED: {year} {discipline} {gender} {environment} "
                  f"place={place} {school} -> {member_names}")

    conn.commit()
    conn.close()

    print(f"\nDeleted: {total_deleted}, Inserted: {total_inserted}, Skipped: {total_skipped}")


if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT / 'ncaa_history.db')
    resolve_relay_members(db_path)
