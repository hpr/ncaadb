#!/usr/bin/env python3
"""
Generate candidate name pairs for athlete profile disambiguation.

1. Auto-profiles all results by (name, gender, school), splitting at >5 year gaps.
2. Finds fuzzy name matches using NameComparator.
3. Applies heuristics to recommend SAME or DIFFERENT athlete.
4. Outputs data/name_candidates.json (pairs for admin review).
"""

import json
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "ncaa_history.db"
CANDIDATES_PATH = PROJECT_ROOT / "data" / "name_candidates.json"

YEAR_GAP_THRESHOLD = 5
YEAR_OVERLAP_THRESHOLD = 8

EVENT_GROUPS = {
    "sprints": {
        "100m", "200m", "400m", "60m", "100m Hurdles", "110m Hurdles",
        "400m Hurdles", "60m Hurdles", "220y Hurdles", "500m",
    },
    "relays": {"4x100m Relay", "4x400m Relay", "4x800m Relay", "DMR"},
    "horizontal_jumps": {"Long Jump", "Triple Jump"},
    "distance": {
        "800m", "1500m", "Mile", "3000m", "5000m", "10000m", "Steeplechase",
    },
    "high_jump": {"High Jump"},
    "pole_vault": {"Pole Vault"},
    "multi_events": {"Decathlon", "Heptathlon", "Pentathlon"},
    "throws": {"Shot Put", "Discus", "Hammer", "Javelin", "Weight Throw"},
}

COMPATIBILITY_MAP = {
    "sprints": {"sprints", "relays", "horizontal_jumps", "multi_events"},
    "relays": {"sprints", "relays", "multi_events"},
    "horizontal_jumps": {"sprints", "horizontal_jumps", "multi_events"},
    "distance": {"distance", "multi_events"},
    "high_jump": {"high_jump", "multi_events"},
    "pole_vault": {"pole_vault", "multi_events"},
    "multi_events": {
        "sprints", "relays", "horizontal_jumps", "distance",
        "high_jump", "pole_vault", "multi_events", "throws",
    },
    "throws": {"throws", "multi_events"},
}


def get_discipline_groups(disciplines):
    groups = set()
    for d in disciplines:
        for group_name, group_discs in EVENT_GROUPS.items():
            if d in group_discs:
                groups.add(group_name)
                break
    return groups


def groups_are_compatible(groups_a, groups_b):
    if not groups_a or not groups_b:
        return True
    for g in groups_a:
        if g in COMPATIBILITY_MAP:
            if groups_b & COMPATIBILITY_MAP[g]:
                return True
    return False


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


def load_profiles_from_db(conn):
    c = conn.cursor()
    c.execute("""
        SELECT name, gender, school, year, discipline, environment
        FROM results
        WHERE name IS NOT NULL AND name != 'Relay member unknown'
        ORDER BY name, gender, school, year
    """)

    groups = defaultdict(lambda: {"years": set(), "disciplines": set(), "seasons": set(), "env_disciplines": set()})
    for name, gender, school, year, discipline, environment in c.fetchall():
        key = (name, gender, school)
        groups[key]["years"].add(year)
        groups[key]["disciplines"].add(discipline)
        if environment:
            groups[key]["seasons"].add((year, environment))
            groups[key]["env_disciplines"].add((environment, discipline))

    profiles = []
    next_id = 1

    for (name, gender, school), data in sorted(groups.items()):
        clusters = split_by_year_gap(data["years"])
        disc_groups = get_discipline_groups(data["disciplines"])

        for cluster in clusters:
            seasons = sorted(
                [f"{y} {e.capitalize()}" for y, e in data["seasons"] if y in cluster],
                key=lambda s: s,
            )
            env_discs = sorted(
                [f"{e.capitalize()} {d}" for e, d in data["env_disciplines"]],
                key=lambda s: s,
            )
            profiles.append({
                "athlete_id": next_id,
                "canonical_name": name,
                "aliases": [name],
                "members": [{
                    "name": name,
                    "gender": gender,
                    "school": school,
                    "year_start": min(cluster),
                    "year_end": max(cluster),
                }],
                "_disciplines": sorted(data["disciplines"]),
                "_disc_groups": disc_groups,
                "_years": sorted(cluster),
                "_seasons": seasons,
                "_env_disciplines": env_discs,
            })
            next_id += 1

    return profiles


def _parse_name_parts(name):
    parts = name.strip().split()
    if len(parts) < 2:
        return name, ""
    return parts[0], " ".join(parts[1:])


def _normalize_initials(name):
    return name.replace(".", "").replace("'", "").strip()


def _is_initials(word):
    n = _normalize_initials(word)
    return len(n) <= 3 and n.isalpha() and n == n.upper()


def _initials_match(name_a, name_b):
    parts_a = name_a.split()
    parts_b = name_b.split()
    if len(parts_a) < 2 or len(parts_b) < 2:
        return False
    norm_a = _normalize_initials(parts_a[0])
    norm_b = _normalize_initials(parts_b[0])
    if not (_is_initials(parts_a[0]) or _is_initials(parts_b[0])):
        return False
    if norm_a != norm_b:
        return False
    return parts_a[-1].lower() == parts_b[-1].lower()


def _first_name_match(name_a, name_b):
    first_a, last_a = _parse_name_parts(name_a)
    first_b, last_b = _parse_name_parts(name_b)
    if not first_a or not first_b:
        return False
    if last_a.lower() == last_b.lower():
        return False
    return first_a.lower() == first_b.lower()


def _get_last_name(name):
    parts = name.strip().split()
    return parts[-1].lower() if parts else ""


def _strip_diacritics(s):
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _get_last_name_normalized(name):
    return _strip_diacritics(_get_last_name(name))


def profiles_by_last_name(profiles):
    lookup = defaultdict(list)
    for p in profiles:
        m = p["members"][0]
        last = _get_last_name_normalized(m["name"])
        if last:
            lookup[(m["gender"], last)].append(p)
    return lookup


def profiles_by_school_gender(profiles):
    lookup = defaultdict(list)
    for p in profiles:
        m = p["members"][0]
        key = (m["gender"], m["school"])
        lookup[key].append(p)
    return lookup


def _add_candidate(candidates, seen_pairs, pa, pb, match_type, year_gap, compatible, same_school):
    pair_key = (pa["athlete_id"], pb["athlete_id"])
    if pair_key in seen_pairs:
        return
    seen_pairs.add(pair_key)

    ma, mb = pa["members"][0], pb["members"][0]
    recommendation = _recommend(
        year_gap, compatible, match_type,
        pa["_years"], pb["_years"],
        same_school,
    )

    candidates.append({
        "profile_a": {
            "athlete_id": pa["athlete_id"],
            "name": ma["name"],
            "school": ma["school"],
            "gender": ma["gender"],
            "year_start": pa["_years"][0],
            "year_end": pa["_years"][-1],
            "disciplines": pa["_disciplines"],
            "seasons": pa.get("_seasons", []),
            "env_disciplines": pa.get("_env_disciplines", []),
        },
        "profile_b": {
            "athlete_id": pb["athlete_id"],
            "name": mb["name"],
            "school": mb["school"],
            "gender": mb["gender"],
            "year_start": pb["_years"][0],
            "year_end": pb["_years"][-1],
            "disciplines": pb["_disciplines"],
            "seasons": pb.get("_seasons", []),
            "env_disciplines": pb.get("_env_disciplines", []),
        },
        "match_type": match_type,
        "year_gap": year_gap,
        "event_groups_compatible": compatible,
        "recommendation": recommendation,
        "decision": None,
    })


def find_candidates(profiles):
    try:
        from NameComparator import NameComparator
        use_nc = True
        print("  NameComparator: available")
    except ImportError:
        print("ERROR: NameComparator is not available. Activate the venv: source .venv/bin/activate")
        sys.exit(1)

    try:
        from Levenshtein import distance as lev_dist
        has_lev = True
    except ImportError:
        has_lev = False

    candidates = []
    seen_pairs = set()
    exact_count = 0
    initials_count = 0
    fuzzy_count = 0

    # Strategy 1: Same last name bucketing (exact, initials, fuzzy within same last name)
    by_last = profiles_by_last_name(profiles)
    total_buckets = len(by_last)
    processed = 0

    # Build set of last names per gender for cross-last-name matching
    last_names_by_gender = defaultdict(set)
    for (gender, last), _ in by_last.items():
        last_names_by_gender[gender].add(last)

    for key, group in sorted(by_last.items()):
        processed += 1
        if processed % 500 == 0:
            print(f"    Processed {processed}/{total_buckets} same-last-name buckets, "
                  f"{exact_count} exact, {initials_count} initials, {fuzzy_count} fuzzy so far")

        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                pa, pb = group[i], group[j]
                ma, mb = pa["members"][0], pb["members"][0]

                if ma["name"] == mb["name"] and ma["school"] == mb["school"]:
                    continue

                name_a, name_b = ma["name"], mb["name"]
                match_type = None

                if name_a == name_b:
                    match_type = "exact"
                    exact_count += 1
                elif _initials_match(name_a, name_b):
                    match_type = "initials"
                    initials_count += 1
                elif use_nc:
                    try:
                        result = NameComparator.compareTwoNames(name_a, name_b)
                        if not result.match or result.tooShort:
                            continue
                        match_type = "fuzzy"
                        fuzzy_count += 1
                    except Exception:
                        continue
                else:
                    continue

                year_gap = _year_gap(pa, pb)
                compatible = groups_are_compatible(pa["_disc_groups"], pb["_disc_groups"])
                same_school = ma["school"] == mb["school"]
                _add_candidate(candidates, seen_pairs, pa, pb, match_type, year_gap, compatible, same_school)

    print(f"  Strategy 1 totals: {exact_count} exact, {initials_count} initials, {fuzzy_count} fuzzy")

    # Strategy 1b: Cross last-name fuzzy matching (nearby last names only)
    cross_fuzzy_count = 0
    if use_nc and has_lev:
        print("  Running cross-last-name fuzzy matching...")
        for gender in last_names_by_gender:
            sorted_lasts = sorted(last_names_by_gender[gender])
            for i in range(len(sorted_lasts)):
                if i % 100 == 0 and i > 0:
                    print(f"    Cross-fuzzy: checked {i}/{len(sorted_lasts)} last names for {gender}")
                la = sorted_lasts[i]
                group_a = by_last.get((gender, la), [])
                for j in range(i + 1, len(sorted_lasts)):
                    lb = sorted_lasts[j]
                    if la[0] != lb[0]:
                        break
                    if abs(len(la) - len(lb)) > 2:
                        continue
                    if lev_dist(la, lb) > 1:
                        continue
                    group_b = by_last.get((gender, lb), [])
                    for pa in group_a:
                        for pb in group_b:
                            name_a = pa["members"][0]["name"]
                            name_b = pb["members"][0]["name"]
                            try:
                                result = NameComparator.compareTwoNames(name_a, name_b)
                                if not result.match or result.tooShort:
                                    continue
                            except Exception:
                                continue
                            year_gap = _year_gap(pa, pb)
                            compatible = groups_are_compatible(pa["_disc_groups"], pb["_disc_groups"])
                            same_school = pa["members"][0]["school"] == pb["members"][0]["school"]
                            _add_candidate(candidates, seen_pairs, pa, pb, "fuzzy", year_gap, compatible, same_school)
                            cross_fuzzy_count += 1
        print(f"  Strategy 1b totals: {cross_fuzzy_count} cross-last-name fuzzy")

    # Strategy 2: Maiden/married name (women, same school, same first name, different last name)
    maiden_count = 0
    by_school = profiles_by_school_gender(profiles)
    for (gender, school), group in sorted(by_school.items()):
        if gender != "women":
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                pa, pb = group[i], group[j]
                ma, mb = pa["members"][0], pb["members"][0]

                if ma["name"] == mb["name"]:
                    continue
                if not _first_name_match(ma["name"], mb["name"]):
                    continue

                year_gap = _year_gap(pa, pb)
                if year_gap > YEAR_OVERLAP_THRESHOLD:
                    continue

                compatible = groups_are_compatible(pa["_disc_groups"], pb["_disc_groups"])
                _add_candidate(candidates, seen_pairs, pa, pb, "maiden_married", year_gap, compatible, True)
                maiden_count += 1

    print(f"  Strategy 2 totals: {maiden_count} maiden/married")

    _sort_candidates(candidates)
    return candidates


def _year_gap(pa, pb):
    a_min, a_max = pa["_years"][0], pa["_years"][-1]
    b_min, b_max = pb["_years"][0], pb["_years"][-1]
    if a_max < b_min:
        return b_min - a_max
    if b_max < a_min:
        return a_min - b_max
    return 0


def _recommend(year_gap, compatible, match_type, years_a, years_b, same_school):
    if match_type == "exact" and same_school and year_gap == 0:
        return "same_high"

    if year_gap > YEAR_OVERLAP_THRESHOLD:
        if compatible and match_type == "fuzzy":
            return "different_likely"
        return "different"

    if not compatible:
        if match_type == "fuzzy":
            return "different_likely"
        return "different"

    return "same"


def _sort_candidates(candidates):
    order = {
        "same_high": 0,
        "same": 1,
        "different_likely": 2,
        "different": 3,
    }
    candidates.sort(key=lambda c: (order.get(c["recommendation"], 9), c["profile_a"]["name"]))


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(DB_PATH)
    candidates_path = sys.argv[2] if len(sys.argv) > 2 else str(CANDIDATES_PATH)

    print("Loading results from database...")
    conn = sqlite3.connect(db_path)
    profiles = load_profiles_from_db(conn)
    conn.close()
    print(f"  Created {len(profiles)} auto-profiles")

    print("Finding candidate name pairs...")
    candidates = find_candidates(profiles)
    print(f"  Found {len(candidates)} candidate pairs")

    rec_counts = defaultdict(int)
    for c in candidates:
        rec_counts[c["recommendation"]] += 1
    for rec, count in sorted(rec_counts.items()):
        print(f"    {rec}: {count}")

    print(f"Writing candidates to {candidates_path}...")
    with open(candidates_path, "w") as f:
        json.dump(candidates, f, indent=2)

    print("Done!")


if __name__ == "__main__":
    main()
