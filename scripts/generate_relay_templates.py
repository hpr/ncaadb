#!/usr/bin/env python3
"""
Generate JSON templates for missing relay members.

Queries the DB for teams where all 4 rows have name = 'Relay member unknown',
groups by gender/environment, and writes 4 JSON files to data/.
Each file contains an array of team entries, each with a 'members'
array of 4 slots for the user to fill in with names and split times.
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'

FILES = {
    ('men', 'indoor'): 'relay_members_men_indoor.json',
    ('men', 'outdoor'): 'relay_members_men_outdoor.json',
    ('women', 'indoor'): 'relay_members_women_indoor.json',
    ('women', 'outdoor'): 'relay_members_women_outdoor.json',
}


def generate_templates(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        "SELECT year, discipline, gender, environment, place, mark_str, school "
        "FROM results WHERE name = 'Relay member unknown' AND is_relay = 1 AND place != 999 "
        "GROUP BY year, discipline, gender, environment, place, school, mark_str "
        "HAVING COUNT(*) = 4 "
        "ORDER BY gender, environment, year, discipline, place"
    )
    rows = c.fetchall()

    buckets = {k: [] for k in FILES}

    for row in rows:
        key = (row['gender'], row['environment'])
        entry = {
            'year': row['year'],
            'discipline': row['discipline'],
            'gender': row['gender'],
            'environment': row['environment'],
            'place': row['place'],
            'school': row['school'],
            'mark_str': row['mark_str'],
            'members': [
                {'leg_idx': i + 1, 'split_time': None, 'name': None}
                for i in range(4)
            ],
        }
        buckets[key].append(entry)

    for key, filename in FILES.items():
        filepath = DATA_DIR / filename
        entries = buckets[key]
        with open(filepath, 'w') as f:
            json.dump(entries, f, indent=2)
        print(f"  Wrote {filepath} ({len(entries)} teams)")

    total = sum(len(v) for v in buckets.values())
    print(f"\nTotal: {total} teams across {len(FILES)} files")

    conn.close()


if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT / 'ncaa_history.db')
    generate_templates(db_path)
