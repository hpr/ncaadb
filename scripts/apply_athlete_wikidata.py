#!/usr/bin/env python3
"""
Enrich profiles.json with Wikidata QIDs from wiki/athlete_wikidata.json.

Matches profiles by stable key (canonical_name|schools|gender|start|end)
and adds a "qid" field to each matching profile.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES_PATH = PROJECT_ROOT / "data" / "profiles.json"
WIKIDATA_PATH = PROJECT_ROOT / "wiki" / "athlete_wikidata.json"


def make_stable_key(profile: dict) -> str:
    canonical = profile["canonical_name"]
    schools = set()
    gender = None
    start_year = None
    end_year = None
    for m in profile["members"]:
        if m["school"]:
            schools.add(m["school"])
        if gender is None:
            gender = m["gender"]
        ys = m.get("year_start")
        ye = m.get("year_end")
        if ys is not None:
            if start_year is None or ys < start_year:
                start_year = ys
        if ye is not None:
            if end_year is None or ye > end_year:
                end_year = ye
    schools_str = ";".join(sorted(schools))
    return f"{canonical}|{schools_str}|{gender}|{start_year}|{end_year}"


def main():
    with open(WIKIDATA_PATH) as f:
        qid_map = json.load(f)
    print(f"Loaded {len(qid_map)} QID mappings")

    with open(PROFILES_PATH) as f:
        profiles = json.load(f)
    print(f"Loaded {len(profiles)} profiles")

    enriched = 0
    for profile in profiles:
        key = make_stable_key(profile)
        qid = qid_map.get(key)
        if qid:
            profile["qid"] = qid
            enriched += 1

    with open(PROFILES_PATH, "w") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)

    print(f"Enriched {enriched}/{len(profiles)} profiles with QIDs")
    print(f"Output: {PROFILES_PATH}")


if __name__ == "__main__":
    main()
