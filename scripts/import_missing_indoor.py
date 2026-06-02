#!/usr/bin/env python3
"""
Import missing indoor entries from missing_indoor.json into the database.
"""

import sqlite3
import json
import re
import sys
import os
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from util.constants import clean_school_name

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RELAY_EVENTS = ['4x400m Relay', '4x800m Relay', 'DMR']


def parse_mark(mark_str: str) -> Tuple[Optional[float], str, bool, bool]:
    """Parse a mark string into numeric value."""
    if not mark_str or mark_str.strip() == '?':
        return None, mark_str, False, False
    
    original = mark_str.strip()
    s = original
    
    is_wind_aided = s.endswith('A') or s.endswith('(A)')
    s = re.sub(r'\s*\(?A\)?$', '', s)
    
    is_converted = s.endswith('+') or s.endswith('c')
    s = s.rstrip('+c').rstrip('y').strip()
    
    # Handle time formats (mm:ss.xx or ss.xx)
    time_match = re.match(r'^(\d+):(\d+\.?\d*)$', s)
    if time_match:
        minutes = int(time_match.group(1))
        seconds = float(time_match.group(2))
        return minutes * 60 + seconds, original, is_wind_aided, is_converted
    
    # Handle distance/height (meters or feet-inches)
    dist_match = re.match(r'^(\d+\.?\d*)(m|cm)?$', s)
    if dist_match:
        val = float(dist_match.group(1))
        if dist_match.group(2) == 'cm':
            val = val / 100
        return val, original, is_wind_aided, is_converted
    
    # Handle feet-inches format (e.g., "6-0.75" or "18-10.25")
    ft_in_match = re.match(r'^(\d+)-(\d+\.?\d*)$', s)
    if ft_in_match:
        feet = int(ft_in_match.group(1))
        inches = float(ft_in_match.group(2))
        return feet * 0.3048 + inches * 0.0254, original, is_wind_aided, is_converted
    
    # Try to parse as plain number
    try:
        return float(s), original, is_wind_aided, is_converted
    except ValueError:
        return None, original, is_wind_aided, is_converted


def import_missing_entries(db_path: str, json_path: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    with open(json_path) as f:
        data = json.load(f)
    
    inserted = 0
    skipped = 0
    
    for year_str, year_data in data.items():
        year = int(year_str)
        for gender, gender_data in year_data.items():
            for discipline, entries in gender_data.items():
                is_relay = discipline in RELAY_EVENTS

                for entry in entries:
                    if entry.get('skip', False):
                        skipped += 1
                        continue

                    name = entry.get('name')
                    school_raw = entry.get('school', '')
                    school_clean = clean_school_name(school_raw, year) if school_raw else ''
                    place = entry.get('place')
                    leg_idx = entry.get('leg_idx')
                    source_url = entry.get('source_url')
                    mark_str = entry.get('mark_str')
                    mark_num, _, _, is_converted = parse_mark(mark_str) if mark_str else (None, None, False, False)

                    if not name and is_relay:
                        if not school_clean:
                            skipped += 1
                            continue
                        c.execute(
                            'SELECT 1 FROM results WHERE name=? AND school=? AND place IS ? AND discipline=? AND gender=? AND year=? AND environment=? AND leg_idx IS ?',
                            ('Relay member unknown', school_clean, place, discipline, gender, year, 'indoor', leg_idx)
                        )
                        if c.fetchone():
                            skipped += 1
                            continue
                        c.execute('''
                            INSERT INTO results (
                                year, name, school, discipline, gender,
                                mark_num, mark_str, place, is_relay, leg_idx, split_time,
                                environment, is_converted
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, 0)
                        ''', (
                            year, 'Relay member unknown', school_clean,
                            discipline, gender, mark_num, mark_str,
                            place, leg_idx, entry.get('split_time'),
                            'indoor'
                        ))
                        inserted += 1
                        continue

                    if not name:
                        skipped += 1
                        continue
                    
                    is_international = name.endswith("'") or name.endswith("\u2019")
                    if is_international:
                        name = name.rstrip("'\u2019").strip()

                    if is_relay and leg_idx is not None:
                        c.execute(
                            "DELETE FROM results WHERE name='Relay member unknown' AND school=? AND place IS ? AND discipline=? AND gender=? AND year=? AND environment=? AND leg_idx IS ?",
                            (school_clean, place, discipline, gender, year, 'indoor', leg_idx)
                        )
                        if c.rowcount:
                            print(f"  Replaced 'Relay member unknown' leg {leg_idx} for {school_clean} {year} {discipline} place={place}")

                    c.execute(
                        'SELECT 1 FROM results WHERE name=? AND school=? AND place=? AND discipline=? AND gender=? AND year=? AND environment=?',
                        (name, school_clean, place, discipline, gender, year, 'indoor')
                    )
                    if c.fetchone():
                        skipped += 1
                        continue

                    c.execute('''
                        INSERT INTO results (
                            year, name, school, discipline, gender,
                            mark_num, mark_str, place, is_international,
                            is_relay, leg_idx, split_time,
                            environment, source_url, is_converted
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        year, name, school_clean, discipline, gender,
                        mark_num, mark_str, place,
                        1 if is_international else 0,
                        1 if is_relay else 0, leg_idx, entry.get('split_time'),
                        'indoor', source_url, 1 if is_converted else 0
                    ))
                    inserted += 1
    
    conn.commit()
    conn.close()
    
    print(f"Imported {inserted} missing indoor entries")
    print(f"Skipped {skipped} entries (marked skip=True or no name)")
    return inserted


def remove_country_duplicates(db_path: str):
    # All 5 cases (GBR: Great Britain x2, JAM: Jamaica x3) were verified as
    # duplicates that already had a matching row with the athlete's actual school,
    # so there is no loss of information from deleting these.
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM results WHERE school IN ('GBR: Great Britain', 'JAM: Jamaica')")
    deleted = c.rowcount
    conn.commit()
    conn.close()
    print(f"Deleted {deleted} rows with country-based school entries (GBR/JAM)")
    return deleted


if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT / 'ncaa_history.db')
    json_path = sys.argv[2] if len(sys.argv) > 2 else str(PROJECT_ROOT / 'data' / 'missing_indoor.json')
    import_missing_entries(db_path, json_path)
    remove_country_duplicates(db_path)
