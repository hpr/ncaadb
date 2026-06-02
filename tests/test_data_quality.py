#!/usr/bin/env python3
"""Sanity checks for NCAA DB data quality."""

import sqlite3
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "ncaa_history.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def check_empty_names(conn):
    print("=== EMPTY/NULL NAMES ===")
    c = conn.cursor()
    c.execute("SELECT id, year, school, discipline, gender, environment, place FROM results WHERE name IS NULL OR name = ''")
    rows = c.fetchall()
    if rows:
        for row in rows:
            print(f"  id={row[0]} year={row[1]} school={row[2]} event={row[3]} gender={row[4]} env={row[5]} place={row[6]}")
        print(f"  ({len(rows)} issues)\n")
    else:
        print("  None found.\n")
    return len(rows)


def check_single_word_names(conn):
    print("=== SINGLE-WORD NAMES (no space, likely first name only) ===")
    c = conn.cursor()
    c.execute("SELECT id, year, name, school, discipline, gender, environment, place FROM results WHERE name IS NOT NULL AND name != '' AND name NOT GLOB '* *' AND name NOT LIKE '% %' ORDER BY name")
    rows = c.fetchall()
    if rows:
        for row in rows:
            print(f"  id={row[0]} year={row[1]} name={repr(row[2])} school={row[3]} event={row[4]} gender={row[5]} env={row[6]} place={row[7]}")
        print(f"  ({len(rows)} issues)\n")
    else:
        print("  None found.\n")
    return len(rows)


def check_long_names(conn):
    print("=== LONG NAMES (>50 chars) ===")
    c = conn.cursor()
    c.execute("SELECT id, year, name, school, discipline, gender, environment, place FROM results WHERE LENGTH(name) > 50 ORDER BY LENGTH(name) DESC")
    rows = c.fetchall()
    if rows:
        for row in rows:
            print(f"  id={row[0]} year={row[1]} len={len(row[2])} name={repr(row[2][:80])} school={row[3]} place={row[7]}")
        print(f"  ({len(rows)} issues)\n")
    else:
        print("  None found.\n")
    return len(rows)


def check_parentheses_in_names(conn):
    print("=== NAMES WITH PARENTHESES ===")
    c = conn.cursor()
    c.execute("SELECT id, year, name, school, discipline, gender, environment, place FROM results WHERE name IS NOT NULL AND name != '' AND (INSTR(name, '(') > 0 OR INSTR(name, ')') > 0) ORDER BY year")
    rows = c.fetchall()
    if rows:
        for row in rows:
            print(f"  id={row[0]} year={row[1]} name={repr(row[2][:80])} school={row[3]} event={row[4]} gender={row[5]} env={row[6]} place={row[7]}")
        print(f"  ({len(rows)} issues)\n")
    else:
        print("  None found.\n")
    return len(rows)


def check_non_name_content(conn):
    print("=== NAMES WITH SUSPICIOUS CONTENT (digits, colons, dashes-as-separator, question marks, asterisks) ===")
    c = conn.cursor()
    c.execute("SELECT id, year, name, school, discipline, gender, environment, place FROM results WHERE name IS NOT NULL AND name != '' AND (name GLOB '*[0-9]*' OR name GLOB '*:*' OR name GLOB '*—*' OR name GLOB '*--*' OR name LIKE '%?%' OR name LIKE '%*%') ORDER BY year")
    rows = c.fetchall()
    if rows:
        for row in rows:
            print(f"  id={row[0]} year={row[1]} name={repr(row[2][:80])} school={row[3]} event={row[4]} gender={row[5]} env={row[6]} place={row[7]}")
        print(f"  ({len(rows)} issues)\n")
    else:
        print("  None found.\n")
    return len(rows)


def check_exact_duplicates(conn):
    print("=== EXACT DUPLICATES (same name/school/place/discipline/gender/year/environment/leg_idx) ===")
    c = conn.cursor()
    c.execute("""
        SELECT name, school, place, discipline, gender, year, environment, leg_idx, COUNT(*) as cnt
        FROM results
        WHERE name IS NOT NULL AND name != ''
        GROUP BY name, school, place, discipline, gender, year, environment, leg_idx
        HAVING cnt > 1
        ORDER BY year, cnt DESC
    """)
    rows = c.fetchall()
    if rows:
        for row in rows:
            print(f"  {row[7]}x: {row[0]} ({row[1]}) place={row[2]} {row[3]} {row[4]} {row[5]} {row[6]}")
        print(f"  ({len(rows)} groups)\n")
    else:
        print("  None found.\n")
    return len(rows)


def check_near_duplicates(conn):
    print("=== NEAR-DUPLICATES (same name/school/discipline/gender/year/environment, different place) ===")
    c = conn.cursor()
    c.execute("""
        SELECT name, school, discipline, gender, year, environment, COUNT(DISTINCT place) as place_count, GROUP_CONCAT(DISTINCT place) as places
        FROM results
        WHERE name IS NOT NULL AND name != '' AND place IS NOT NULL
        GROUP BY name, school, discipline, gender, year, environment
        HAVING place_count > 1
        ORDER BY year
    """)
    rows = c.fetchall()
    if rows:
        for row in rows:
            print(f"  {row[0]} ({row[1]}) {row[2]} {row[3]} {row[4]} {row[5]} places=[{row[7]}]")
        print(f"  ({len(rows)} issues)\n")
    else:
        print("  None found.\n")
    return len(rows)


def check_near_duplicates_different_school(conn):
    print("=== NEAR-DUPLICATES (same name/discipline/gender/year/environment, different school) ===")
    c = conn.cursor()
    c.execute("""
        SELECT name, year, discipline, gender, environment,
               GROUP_CONCAT(DISTINCT school) as schools,
               COUNT(DISTINCT school) as school_count,
               GROUP_CONCAT(DISTINCT place) as places
        FROM results
        WHERE name IS NOT NULL AND name != '' AND name != 'Relay member unknown'
        GROUP BY name, year, discipline, gender, environment
        HAVING school_count > 1
        ORDER BY year, discipline
    """)
    rows = c.fetchall()

    if rows:
        for row in rows:
            print(f"  {row[0]} {row[1]} {row[2]} {row[3]} {row[4]} schools=[{row[5]}] places=[{row[7]}]")
        print(f"  ({len(rows)} issues)\n")
    else:
        print("  None found.\n")
    return len(rows)


def check_missing_places(conn):
    print("=== MISSING PLACES (gaps in place sequence) ===")
    c = conn.cursor()
    c.execute("""
        SELECT year, discipline, gender, environment, GROUP_CONCAT(place ORDER BY place) as places
        FROM results
        WHERE place IS NOT NULL AND place != 999 AND is_dq = 0 AND is_dnf = 0 AND is_dns = 0
          AND (is_relay = 0 OR leg_idx IS NULL OR leg_idx = 1)
        GROUP BY year, discipline, gender, environment
        HAVING COUNT(*) > 1
        ORDER BY year, discipline, gender, environment
    """)
    groups = c.fetchall()
    issues = []
    for row in groups:
        year, discipline, gender, environment, places_str = row
        if not places_str:
            continue
        places = [int(p) for p in places_str.split(",")]
        expected = 1
        i = 0
        sorted_places = sorted(places)
        while i < len(sorted_places):
            place = sorted_places[i]
            if place != expected:
                issues.append((year, discipline, gender, environment, expected, place, sorted_places))
                break
            count = 0
            while i < len(sorted_places) and sorted_places[i] == place:
                count += 1
                i += 1
            expected = place + count

    if issues:
        for year, discipline, gender, environment, expected, got, all_places in issues:
            print(f"  {year} {discipline} {gender} {environment}: expected place {expected}, got {got} (all: {all_places})")
        print(f"  ({len(issues)} issues)\n")
    else:
        print("  None found.\n")
    return len(issues)


FIELD_DISCIPLINES = {
    "Long Jump", "Triple Jump", "High Jump", "Pole Vault",
    "Shot Put", "Discus", "Javelin", "Hammer", "Weight Throw",
    "Decathlon", "Heptathlon", "Pentathlon",
}


def check_mark_ordering(conn):
    print("=== MARK ORDERING (running: ascending, field: descending by place) ===")
    c = conn.cursor()
    c.execute("""
        SELECT year, discipline, gender, environment, place, mark_num
        FROM results
        WHERE mark_num IS NOT NULL
          AND place IS NOT NULL AND place != 999
          AND is_dq = 0 AND is_dnf = 0 AND is_dns = 0
          AND NOT (is_relay = 1 AND leg_idx IS NOT NULL)
        ORDER BY year, discipline, gender, environment, place
    """)
    issues = []
    prev_key = None
    prev_place = None
    prev_mark = None
    is_field = False
    for year, discipline, gender, environment, place, mark_num in c:
        key = (year, discipline, gender, environment)
        if key != prev_key:
            prev_key = key
            prev_place = place
            prev_mark = mark_num
            is_field = discipline in FIELD_DISCIPLINES
            continue
        if is_field:
            if prev_mark < mark_num:
                issues.append((year, discipline, gender, environment,
                               prev_place, prev_mark, place, mark_num, "field"))
        else:
            if prev_mark > mark_num:
                issues.append((year, discipline, gender, environment,
                               prev_place, prev_mark, place, mark_num, "running"))
        prev_place = place
        prev_mark = mark_num

    if issues:
        for year, disc, gender, env, p1, m1, p2, m2, kind in issues:
            arrow = "<" if kind == "field" else ">"
            print(f"  {year} {disc} {gender} {env}: place {p1} mark {m1} {arrow} place {p2} mark {m2} ({kind})")
        print(f"  ({len(issues)} issues)\n")
    else:
        print("  None found.\n")
    return len(issues)


def check_relay_member_count(conn):
    print("=== RELAY TEAMS WITHOUT 4 MEMBERS ===")
    c = conn.cursor()
    c.execute("""
        SELECT year, school, discipline, gender, environment, place, COUNT(*) as members
        FROM results
        WHERE is_relay = 1
        GROUP BY year, school, discipline, gender, environment, place
        HAVING members != 4
        ORDER BY year, discipline
    """)
    rows = c.fetchall()
    if rows:
        for row in rows:
            year, school, discipline, gender, environment, place, _ = row
            print(f"  {row[6]} members: {school} {year} {discipline} {gender} {environment} place={place}")
            c2 = conn.cursor()
            c2.execute(
                "SELECT name, leg_idx, split_time FROM results "
                "WHERE year=? AND school=? AND discipline=? AND gender=? AND environment=? AND place IS ? AND is_relay=1 "
                "ORDER BY leg_idx",
                (year, school, discipline, gender, environment, place),
            )
            for member in c2.fetchall():
                name, leg_idx, split_time = member
                split_str = f" {split_time}" if split_time else ""
                print(f"    leg {leg_idx}: {name}{split_str}")
        print(f"  ({len(rows)} issues)\n")
    else:
        print("  None found.\n")
    return len(rows)


def main():
    conn = get_conn()
    total = 0

    total += check_empty_names(conn)
    total += check_single_word_names(conn)
    total += check_long_names(conn)
    total += check_parentheses_in_names(conn)
    total += check_non_name_content(conn)
    total += check_exact_duplicates(conn)
    total += check_near_duplicates(conn)
    total += check_near_duplicates_different_school(conn)
    total += check_missing_places(conn)
    total += check_mark_ordering(conn)
    total += check_relay_member_count(conn)

    conn.close()

    if total:
        print(f"TOTAL: {total} issues found")
    else:
        print("ALL CHECKS PASSED")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
