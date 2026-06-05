#!/usr/bin/env python3
"""
Apply athlete profiles from data/profiles.json.
Adds athlete_id column to results table, matching rows to profiles.
Unmatched rows get auto-assigned IDs based on (name, gender, school) + 5-year gap clustering.
"""

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "ncaa_history.db"
PROFILES_PATH = PROJECT_ROOT / "data" / "profiles.json"
ID_MAP_PATH = PROJECT_ROOT / "data" / "athlete_id_map.json"

YEAR_GAP_THRESHOLD = 5


def normalize_name(name: str) -> str:
    return name.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')


def split_by_year_gap(years):
    if not years:
        return []
    sorted_years = sorted(years)
    clusters = [[sorted_years[0]]]
    for y in sorted_years[1:]:
        if y - clusters[-1][-1] > YEAR_GAP_THRESHOLD:
            clusters.append([y])
        else:
            clusters[-1].append(y)
    return clusters


def apply_profiles(db_path: str, json_path: str):
    with open(json_path) as f:
        profiles = json.load(f)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("SELECT rowid, name FROM results WHERE name IS NOT NULL")
    updates = []
    for rowid, name in c.fetchall():
        fixed = normalize_name(name)
        if fixed != name:
            updates.append((fixed, rowid))
    if updates:
        c.executemany("UPDATE results SET name = ? WHERE rowid = ?", updates)
        print(f"  Normalized {len(updates)} curly-quote names")
        conn.commit()

    c.execute("PRAGMA table_info(results)")
    columns = [row[1] for row in c.fetchall()]
    if "athlete_id" not in columns:
        c.execute("ALTER TABLE results ADD COLUMN athlete_id INTEGER")
        print("  Added athlete_id column")
    else:
        c.execute("UPDATE results SET athlete_id = NULL")
        print("  Reset athlete_id column")
    conn.commit()

    # Apply explicit profiles (single UPDATE per member, no SELECT needed)
    matched = 0
    num_profiles = len(profiles)
    for i, profile in enumerate(profiles):
        aid = profile["athlete_id"]
        for member in profile["members"]:
            c.execute(
                "UPDATE results SET athlete_id = ? "
                "WHERE name = ? AND gender = ? AND school = ? "
                "AND year >= ? AND year <= ? AND athlete_id IS NULL",
                (aid, member["name"], member["gender"], member["school"],
                 member["year_start"], member["year_end"])
            )
            matched += c.rowcount
        if (i + 1) % 500 == 0:
            print(f"  ...processed {i + 1}/{num_profiles} explicit profiles ({matched} rows matched)")

    conn.commit()
    print(f"  Matched {matched} rows to {num_profiles} explicit profiles")

    # Auto-assign remaining unmatched rows using stable ID map
    c.execute("""
        SELECT name, gender, school, year
        FROM results
        WHERE athlete_id IS NULL AND name IS NOT NULL AND name != 'Relay member unknown'
        ORDER BY name, gender, school, year
    """)

    groups = defaultdict(set)
    for name, gender, school, year in c.fetchall():
        groups[(name, gender, school)].add(year)

    if groups:
        id_map = {}
        if ID_MAP_PATH.exists():
            with open(ID_MAP_PATH) as f:
                id_map = json.load(f)

        max_id = max(id_map.values()) if id_map else 0
        next_id = max_id + 1
        batch = []
        map_changed = False

        for (name, gender, school), years in sorted(groups.items()):
            map_key = f"{name}|{school}|{gender}"
            if map_key in id_map:
                aid = id_map[map_key]
            else:
                aid = next_id
                next_id += 1
                id_map[map_key] = aid
                map_changed = True

            for cluster in split_by_year_gap(years):
                batch.append((aid, name, gender, school, min(cluster), max(cluster)))

        print(f"  Auto-assigning {len(batch)} clusters...")
        c.executemany(
            "UPDATE results SET athlete_id = ? "
            "WHERE name = ? AND gender = ? AND school = ? "
            "AND year >= ? AND year <= ? AND athlete_id IS NULL",
            batch
        )
        auto_matched = c.rowcount

        if map_changed:
            with open(ID_MAP_PATH, 'w') as f:
                json.dump(id_map, f, indent=2, sort_keys=True)
            print(f"  Updated {ID_MAP_PATH.name} with {next_id - max_id - 1} new triplet(s)")
    else:
        auto_matched = 0

    conn.commit()
    if auto_matched > 0:
        print(f"  Auto-assigned {auto_matched} rows to new profiles")

    # Handle remaining NULLs (relay members, etc.)
    c.execute("SELECT COUNT(*) FROM results WHERE athlete_id IS NULL")
    remaining = c.fetchone()[0]
    if remaining > 0:
        c.execute("SELECT COUNT(*) FROM results WHERE name = 'Relay member unknown' AND athlete_id IS NULL")
        relay_nulls = c.fetchone()[0]
        other_nulls = remaining - relay_nulls
        print(f"  {remaining} rows with NULL athlete_id ({relay_nulls} relay unknowns, {other_nulls} other)")

    c.execute("SELECT COUNT(DISTINCT athlete_id) FROM results WHERE athlete_id IS NOT NULL")
    total_profiles = c.fetchone()[0]
    print(f"  Total distinct athlete_ids: {total_profiles}")

    c.execute("CREATE INDEX IF NOT EXISTS idx_athlete_id ON results(athlete_id)")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(DB_PATH)
    json_path = sys.argv[2] if len(sys.argv) > 2 else str(PROFILES_PATH)
    apply_profiles(db_path, json_path)
