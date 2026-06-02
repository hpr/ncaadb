#!/usr/bin/env python3
"""
Generate a JSON file listing missing indoor entries (places 6-8) that need manual entry.
"""

import sqlite3
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RELAY_EVENTS = ['4x400m Relay', '4x800m Relay', 'DMR']


def generate_missing_entries(db_path: str, output_path: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Get all (year, gender, discipline) combinations with fewer than 8 competitors
    # For relays, use COUNT(DISTINCT place) to count teams, not total rows
    c.execute("""
    SELECT year, gender, discipline, 
           CASE 
               WHEN discipline IN ('4x400m Relay', '4x800m Relay', 'DMR') 
               THEN COUNT(DISTINCT place) 
               ELSE COUNT(*) 
           END as competitor_count
    FROM results 
    WHERE environment='indoor' AND place > 0
    GROUP BY year, gender, discipline
    HAVING competitor_count < 8
    ORDER BY year, gender, discipline
    """)

    missing_by_year = {}

    for row in c.fetchall():
        year, gender, discipline, count = row
        year = str(year)

        if year not in missing_by_year:
            missing_by_year[year] = {"men": {}, "women": {}}

        entries = []
        missing_places = list(range(count + 1, 9))

        if discipline in RELAY_EVENTS:
            for place in missing_places:
                for leg_idx in range(1, 5):
                    entries.append({
                        "place": place,
                        "discipline": discipline,
                        "leg_idx": leg_idx,
                        "name": None,
                        "school": None,
                        "mark_str": None,
                        "split_time": None,
                        "source_url": None,
                        "skip": False
                    })
        else:
            for place in missing_places:
                entries.append({
                    "place": place,
                    "discipline": discipline,
                    "name": None,
                    "school": None,
                    "mark_str": None,
                    "source_url": None,
                    "skip": False
                })

        if entries:
            missing_by_year[year][gender][discipline] = entries

    conn.close()

    # Remove empty gender dicts
    for year in list(missing_by_year.keys()):
        for gender in list(missing_by_year[year].keys()):
            if not missing_by_year[year][gender]:
                del missing_by_year[year][gender]
        if not missing_by_year[year]:
            del missing_by_year[year]

    with open(output_path, 'w') as f:
        json.dump(missing_by_year, f, indent=2)

    return missing_by_year


if __name__ == '__main__':
    db_path = str(PROJECT_ROOT / 'ncaa_history.db')
    output_path = str(PROJECT_ROOT / 'data' / 'missing_indoor.json')

    missing = generate_missing_entries(db_path, output_path)

    print(f"Years with missing data: {sorted(missing.keys())}")
    print(f"Total years: {len(missing)}")

    total = sum(
        len(entries)
        for year_data in missing.values()
        for gender_data in year_data.values()
        for entries in gender_data.values()
    )
    print(f"Total missing entries: {total}")
    print(f"\nSaved to {output_path}")
