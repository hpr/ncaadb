#!/usr/bin/env python3
"""
Enrich existing wiki/athlete_wikipedia.json entries with gender, disciplines,
schools, start_year, end_year fields from the DB and profiles.
"""

import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "ncaa_history.db"
PROFILES_PATH = PROJECT_ROOT / "data" / "profiles.json"
WIKI_DIR = Path(__file__).resolve().parent
INPUT_PATH = WIKI_DIR / "athlete_wikipedia.json"


def main():
    with open(INPUT_PATH) as f:
        entries = json.load(f)

    with open(PROFILES_PATH) as f:
        profiles = json.load(f)
    profiles_by_id = {p["athlete_id"]: p for p in profiles}

    conn = sqlite3.connect(DB_PATH)

    disciplines_map = {}
    for aid, disc in conn.execute("SELECT athlete_id, GROUP_CONCAT(DISTINCT discipline) FROM results GROUP BY athlete_id").fetchall():
        disciplines_map[aid] = sorted(disc.split(","))

    conn.close()

    enriched = 0
    for entry in entries:
        if "gender" in entry:
            continue

        aid = entry["athlete_id"]
        profile = profiles_by_id.get(aid)
        if not profile:
            continue

        gender = None
        schools = set()
        start_year = None
        end_year = None
        for m in profile["members"]:
            gender = m["gender"]
            if m["school"]:
                schools.add(m["school"])
            if m.get("year_start") is not None:
                if start_year is None or m["year_start"] < start_year:
                    start_year = m["year_start"]
            if m.get("year_end") is not None:
                if end_year is None or m["year_end"] > end_year:
                    end_year = m["year_end"]

        entry["gender"] = gender
        entry["schools"] = sorted(schools)
        entry["disciplines"] = disciplines_map.get(aid, [])
        entry["start_year"] = start_year
        entry["end_year"] = end_year
        enriched += 1

    with open(INPUT_PATH, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    print(f"Enriched {enriched} entries ({len(entries)} total)")


if __name__ == "__main__":
    main()
