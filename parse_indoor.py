#!/usr/bin/env python3
"""
Parse NCAA Indoor Championships history from USTFCCCA HTML files.
"""

import sqlite3
import re
import os
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any, Tuple
from nameparser import HumanName

from util.constants import CLASS_MAP, clean_school_name

DB_PATH = Path(__file__).parent / "ncaa_history.db"
HTML_DIR = Path(__file__).parent / "html"

EVENT_MAPPING = {
    "34": {"name": "60m", "type": "track"},
    "51": {"name": "60m Hurdles", "type": "track"},
    "1": {"name": "60m", "type": "track"},
    "13": {"name": "60m Hurdles", "type": "track"},
    "3": {"name": "200m", "type": "track"},
    "39": {"name": "300m", "type": "track"},
    "4": {"name": "400m", "type": "track"},
    "42": {"name": "500m", "type": "track"},
    "5": {"name": "500m", "type": "track"},
    "43": {"name": "600m", "type": "track"},
    "6": {"name": "800m", "type": "track"},
    "7": {"name": "1000m", "type": "track"},
    "8": {"name": "Mile", "type": "track"},
    "9": {"name": "Mile", "type": "track"},
    "10": {"name": "3000m", "type": "track"},
    "11": {"name": "5000m", "type": "track"},
    "12": {"name": "10000m", "type": "track"},
    "19": {"name": "4x400m Relay", "type": "relay"},
    "63": {"name": "4x800m Relay", "type": "relay"},
    "20": {"name": "DMR", "type": "relay"},
    "21": {"name": "High Jump", "type": "field"},
    "22": {"name": "Pole Vault", "type": "field"},
    "23": {"name": "Long Jump", "type": "field"},
    "24": {"name": "Triple Jump", "type": "field"},
    "25": {"name": "Shot Put", "type": "field"},
    "29": {"name": "Weight Throw", "type": "field"},
    "30": {"name": "Pentathlon", "type": "multi"},
    "31": {"name": "Heptathlon", "type": "multi"},
}

RELAY_EVENTS = {"19", "63", "20"}
BLANK_SIZE = 28000

INVALID_SCHOOLS = {
    "(none selected)",
    "none",
    "None",
    "(None)",
    "",
    "N/A",
    "TBD",
}


def is_valid_school(school: str) -> bool:
    """Check if school value is valid (not a placeholder)."""
    if not school:
        return False
    return school not in INVALID_SCHOOLS


def parse_time_to_seconds(mark: str) -> Optional[float]:
    """Convert time string to seconds (for track events)."""
    # Extract just the numeric time part (handles emojis, annotations after time)
    # Match: optional digits:colon, then digits with optional decimal
    time_match = re.match(r'^([\d:.]+)', mark.strip())
    if time_match:
        mark = time_match.group(1)
    else:
        return None
    
    if ':' in mark:
        parts = mark.split(':')
        try:
            if len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except ValueError:
            return None
    else:
        try:
            return float(mark)
        except ValueError:
            return None


def parse_distance_to_meters(mark: str) -> Optional[float]:
    """Convert distance string to meters (for field events)."""
    match = re.match(r'([\d.]+)m', mark)
    if match:
        return float(match.group(1))
    return None


def parse_mark(mark: str, event_type: str) -> Tuple[Optional[float], Optional[str], bool]:
    """Parse mark string into numeric value and original string."""
    if ' = ' in mark:
        mark = mark.split(' = ')[0]
    
    mark_clean = re.sub(r'\s+', '', mark)
    
    # Handle placeholder marks like "---AA", "---A", "---b", "--h", "---0-0" etc.
    if re.match(r'^[-0]+[A-Za-z]*$', mark_clean):
        return None, None, False
    
    is_converted = mark_clean.endswith('c')
    
    mark_num = None
    
    if event_type == "multi":
        # Multi-events use points, e.g., "6,013" or "6013"
        mark_clean = mark_clean.replace(',', '')
        # Extract just the numeric part (handles emojis, annotations after score)
        match = re.match(r'^([\d]+)', mark_clean)
        if match:
            mark_clean = match.group(1)
            try:
                mark_num = float(mark_clean)
            except ValueError:
                pass
    elif event_type in ("track", "relay"):
        mark_num = parse_time_to_seconds(mark)
        # For track/relay, just keep the time (remove trailing b/A for banked/altitude)
        match = re.match(r'^[\d:.]+', mark_clean)
        if match:
            mark_clean = match.group(0)
    elif event_type == "field":
        mark_num = parse_distance_to_meters(mark)
        # For field, keep only the metric measurement (e.g., "4.45m" from "4.45m14-7¼")
        match = re.match(r'^[\d.]+m', mark_clean)
        if match:
            mark_clean = match.group(0)
    
    return mark_num, mark_clean, is_converted


def parse_place(place_str: str) -> Tuple[Optional[int], bool, bool, bool]:
    """Parse place string, return (place, is_dq, is_dnf, is_dns)."""
    place_str = place_str.strip()
    
    paren_match = re.match(r'^\(([^)]*)\)', place_str)
    if paren_match:
        paren_content = paren_match.group(1).upper()
        if re.search(r'\bDQ\b', paren_content):
            digit = re.search(r'\d+', paren_content)
            return (int(digit.group()) if digit else None, True, False, False)
        if re.search(r'\bDNF\b', paren_content):
            digit = re.search(r'\d+', paren_content)
            return (int(digit.group()) if digit else None, False, True, False)
        if re.search(r'\bDNS\b', paren_content):
            digit = re.search(r'\d+', paren_content)
            return (int(digit.group()) if digit else None, False, False, True)
    
    match = re.match(r'\((\d+)\)', place_str)
    if match:
        place = int(match.group(1))
        # Place 0 means DNF (not a valid placing)
        if place == 0:
            return (None, False, True, False)
        return (place, False, False, False)
    return (None, False, False, False)


def check_999_status(place: Optional[int], mark_str: str) -> Tuple[bool, bool]:
    """Check if place 999 should be DQ or DNF based on mark presence.
    Returns (is_dq, is_dnf).
    """
    if place == 999:
        if mark_str and mark_str.strip():
            return (True, False)
        return (False, True)
    return (False, False)


def parse_name_class(name_str: str) -> Tuple[str, Optional[str]]:
    """Parse name and class from combined string like 'Jordan ANTHONYJR'."""
    name_str = name_str.strip()
    
    for class_code in ['SR', 'JR', 'SO', 'FR']:
        if name_str.endswith(class_code):
            name = name_str[:-2].strip()
            return (name, CLASS_MAP.get(class_code))
    
    return (name_str, None)


def fix_name_casing(name: str) -> str:
    """Fix name casing when last name is ALL CAPS (e.g., 'Jordan ANTHONY' -> 'Jordan Anthony').
    Only preserves first name casing, capitalizes middle and last names.
    Also removes trailing question marks from names."""
    if not name:
        return name
    
    name = name.rstrip('*?')
    
    # Only fix if there's an ALL CAPS word (last name in caps)
    # Use Unicode uppercase range to handle accented characters like Í, Ó, etc.
    if not re.search(r'\b[A-ZÀ-Ý]{2,}\b', name):
        return name
    
    parsed = HumanName(name)
    
    # Save original first name only
    orig_first = parsed.first
    
    # Capitalize (this fixes middle and last name casing)
    parsed.capitalize(force=True)
    
    # Restore original first name only
    if orig_first:
        parsed.first = orig_first
    
    return str(parsed)


def parse_header(header: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """Parse year/location/date from header like '2025 * Virginia Beach, Va. * Saturday, March 15'."""
    parts = [p.strip() for p in header.split('*')]
    
    year = None
    location = None
    date = None
    
    for part in parts:
        if re.match(r'^\d{4}$', part):
            year = int(part)
        elif re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', part, re.I):
            date = part
        else:
            location = part
    
    return year, location, date


def parse_team_members(members_str: str) -> List[Dict[str, Any]]:
    """Parse team member names from relay string, extracting split times and classes.
    Format: 'FirstName LASTNAME (SO) 46.91' or 'FirstName LASTNAME 46.91 (SO)'
    """
    members_str = members_str.strip()
    if not members_str:
        return []
    
    # Remove leading annotations like "hc(" or stray "("
    members_str = re.sub(r'^[a-z]*\(', '', members_str, flags=re.IGNORECASE)
    
    # Remove leading record annotations like "then-WB, CR, MR -- "
    # These are record notations with known abbreviations (WB, CR, MR, AR, etc.)
    # Match: start of string, then abbreviations like WB, CR, MR, AR, SR, etc. with optional "then-" prefix
    members_str = re.sub(r'^(?:then-)?(?:[A-Z]{2,}(?:,?\s*)?)+--\s*', '', members_str)
    
    # Remove trailing notes after " -- " (e.g., "questionable course length")
    # These are not part of the member names
    if ' -- ' in members_str:
        members_str = members_str.split(' -- ')[0]
    
    # Check if this looks like a note-only string (no actual member names)
    # Notes typically don't have commas and don't match name patterns
    # A name pattern would be: Capitalized word(s) possibly followed by uppercase last name
    if ',' not in members_str:
        # Check if it looks like a name: at least one capitalized word followed by another word
        # If not, it's probably a note like "questionable course length"
        if not re.match(r'^[A-Z][a-z]+\s+[A-Z]', members_str):
            return []
    
    # Remove trailing closing parenthesis if unmatched
    if members_str.endswith(')') and members_str.count('(') < members_str.count(')'):
        members_str = members_str.rstrip(')').strip()
    
    suffixes = ['Jr.', 'Sr.', 'JR.', 'SR.', 'Jr', 'Sr', 'JR', 'SR', 'III', 'II', 'IV']
    temp = members_str
    for suffix in suffixes:
        temp = re.sub(r', ' + re.escape(suffix) + r'\b', f'<<SUFFIX:{suffix}>>', temp)
    
    parts = []
    for p in temp.split(','):
        for suffix in suffixes:
            p = p.replace(f'<<SUFFIX:{suffix}>>', f', {suffix}')
        parts.append(p)
    
    members = []
    for m in parts:
        m = m.strip()
        if not m:
            continue
        
        name = m
        split_time = None
        athlete_class = None
        
        # Extract class in parentheses like (SO), (JR), etc.
        class_match = re.search(r'\(([A-Z]{2})\)', m)
        if class_match:
            athlete_class = CLASS_MAP.get(class_match.group(1))
        
        # Extract split time - number that looks like a relay split
        # Formats: "Name (SO) 46.91", "Name 46.91", "Name 46.91 (SO)", "Name 46.2 (SR)"
        # Match a number that could be a split time (seconds or m:ss)
        time_match = re.search(r'\s(\d{1,2}(?::\d+)?\.\d+)\s*', m)
        if time_match:
            split_time = time_match.group(1)
            name = m[:time_match.start()].strip()
        
        # Remove class from name if present
        if class_match:
            name = name[:class_match.start()].strip()
        
        members.append({
            'name': fix_name_casing(name),
            'split_time': split_time,
            'class': athlete_class,
        })
    
    return members


def parse_html_file(filepath: Path, gender: str, event_id: str, environment: str = "indoor") -> List[Dict[str, Any]]:
    """Parse a single HTML file and return list of results."""
    results = []
    
    event_info = EVENT_MAPPING.get(event_id)
    if not event_info:
        return results
    
    event_name = event_info["name"]
    event_type = event_info["type"]
    is_relay = event_id in RELAY_EVENTS
    
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    if len(html) < BLANK_SIZE:
        return results
    
    soup = BeautifulSoup(html, 'html.parser')
    
    current_year = None
    current_location = None
    current_date = None
    
    for table in soup.find_all('table'):
        if table.find('table'):
            for td in table.find_all('td', colspan=True):
                header_text = td.get_text(strip=True)
                if re.match(r'^\d{4}', header_text):
                    current_year, current_location, current_date = parse_header(header_text)
            continue
        
        rows = table.find_all('tr')
        
        i = 0
        while i < len(rows):
            row = rows[i]
            tds = row.find_all('td', recursive=False)
            
            if len(tds) >= 4:
                first_col = tds[0].get_text(strip=True)
                
                if not first_col or not first_col.startswith('('):
                    i += 1
                    continue
                
                place, is_dq, is_dnf, is_dns = parse_place(first_col)
                
                name_part = tds[0].get_text(strip=True)
                match = re.match(r'\(\d+\)\s*(.+)', name_part)
                if match:
                    name_part = match.group(1)
                else:
                    i += 1
                    continue
                
                if is_relay:
                    assert current_year is not None
                    school = clean_school_name(name_part, current_year)
                    mark_str = tds[3].get_text(strip=True) if len(tds) > 3 else ""
                    
                    # Check for place 999 (DQ/DNF indicator)
                    dq_999, dnf_999 = check_999_status(place, mark_str)
                    if dq_999:
                        is_dq = True
                    elif dnf_999:
                        is_dnf = True
                    
                    team_members_str = ""
                    if i + 1 < len(rows):
                        next_row = rows[i + 1]
                        next_tds = next_row.find_all('td', recursive=False)
                        if len(next_tds) == 1 and next_tds[0].get('colspan'):
                            team_members_str = next_tds[0].get_text(strip=True)
                            i += 1
                    
                    mark_num, mark_str, is_converted = parse_mark(mark_str, event_type)
                    
                    team_members = parse_team_members(team_members_str)
                    
                    if not team_members:
                        for leg in range(1, 5):
                            result = {
                                "year": current_year,
                                "date": current_date,
                                "name": "Relay member unknown",
                                "school": school,
                                "discipline": event_name,
                                "gender": gender,
                                "mark_num": mark_num,
                                "mark_str": mark_str,
                                "class": None,
                                "place": place,
                                "is_dq": is_dq,
                                "is_dnf": is_dnf,
                                "is_dns": is_dns,
                                "is_relay": 1,
                                "leg_idx": leg,
                                "split_time": None,
                                "location": current_location,
                                "environment": environment,
                                "is_converted": is_converted,
                            }
                            results.append(result)
                    else:
                        for idx, member in enumerate(team_members):
                            result = {
                                "year": current_year,
                                "date": current_date,
                                "name": member['name'],
                                "school": school,
                                "discipline": event_name,
                                "gender": gender,
                                "mark_num": mark_num,
                                "mark_str": mark_str,
                                "class": member['class'],
                                "place": place,
                                "is_dq": is_dq,
                                "is_dnf": is_dnf,
                                "is_dns": is_dns,
                                "is_relay": 1,
                                "leg_idx": idx + 1,
                                "split_time": member['split_time'],
                                "location": current_location,
                                "environment": environment,
                                "is_converted": is_converted,
                            }
                            results.append(result)
                else:
                    assert current_year is not None
                    school = clean_school_name(tds[2].get_text(strip=True), current_year) if len(tds) > 2 else ""
                    
                    if not is_valid_school(school):
                        i += 1
                        continue
                    
                    mark_str = tds[3].get_text(strip=True) if len(tds) > 3 else ""
                    
                    # Check for place 999 (DQ/DNF indicator)
                    dq_999, dnf_999 = check_999_status(place, mark_str)
                    if dq_999:
                        is_dq = True
                    elif dnf_999:
                        is_dnf = True
                    
                    mark_num, mark_str, is_converted = parse_mark(mark_str, event_type)
                    name, athlete_class = parse_name_class(name_part)
                    
                    result = {
                        "year": current_year,
                        "date": current_date,
                        "name": fix_name_casing(name),
                        "school": school,
                        "discipline": event_name,
                        "gender": gender,
                        "mark_num": mark_num,
                        "mark_str": mark_str,
                        "class": athlete_class,
                        "place": place,
                        "is_dq": is_dq,
                        "is_dnf": is_dnf,
                        "is_dns": is_dns,
                        "is_relay": 0,
                        "leg_idx": None,
                        "location": current_location,
                        "environment": environment,
                        "is_converted": is_converted,
                    }
                    results.append(result)
            
            i += 1
    
    return results


def add_environment_column(conn: sqlite3.Connection):
    """Add environment column if it doesn't exist and set existing rows to 'outdoor'."""
    c = conn.cursor()
    
    c.execute("PRAGMA table_info(results)")
    columns = [row[1] for row in c.fetchall()]
    
    if "environment" not in columns:
        print("Adding environment column...")
        c.execute("ALTER TABLE results ADD COLUMN environment TEXT DEFAULT 'outdoor'")
        c.execute("UPDATE results SET environment = 'outdoor' WHERE environment IS NULL")
        conn.commit()
        print("Added environment column and set existing rows to 'outdoor'")


def insert_results(conn: sqlite3.Connection, results: List[Dict[str, Any]]):
    """Insert results into database, skipping exact duplicates."""
    seen = set()
    deduped = []
    for r in results:
        if r["year"] is None:
            continue
        key = (r["name"], r["school"], r["place"], r["discipline"],
               r["gender"], r["year"], r["environment"], r.get("leg_idx"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    
    c = conn.cursor()
    for r in deduped:
        
        c.execute('''
            INSERT INTO results (
                year, date, name, school, discipline, gender,
                mark_num, mark_str, class, place,
                is_dq, is_dnf, is_dns, is_relay, leg_idx,
                split_time, location, environment, is_converted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            r["year"], r["date"], r["name"], r["school"], r["discipline"], r["gender"],
            r["mark_num"], r["mark_str"], r["class"], r["place"],
            1 if r["is_dq"] else 0, 1 if r["is_dnf"] else 0, 1 if r["is_dns"] else 0,
            r["is_relay"], r["leg_idx"], r.get("split_time"), r["location"], r["environment"],
            1 if r.get("is_converted") else 0
        ))
    
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    
    add_environment_column(conn)
    
    print("Parsing NCAA Championships HTML files...")
    
    total_results = 0
    
    for filename in sorted(os.listdir(HTML_DIR)):
        if not filename.endswith('.html'):
            continue
        
        stem = filename.replace('.html', '')
        parts = stem.split('_')
        
        if len(parts) == 3 and parts[0] == 'outdoor':
            _, gender, event_id = parts
            environment = 'outdoor'
        elif len(parts) == 2:
            gender, event_id = parts
            environment = 'indoor'
        else:
            continue
        
        if event_id not in EVENT_MAPPING:
            continue
        
        filepath = HTML_DIR / filename
        results = parse_html_file(filepath, gender, event_id, environment=environment)
        
        # The HTML source lists the 1994 women's relay under both event 63
        # (4x800m) and event 20 (DMR). It was actually a DMR, so skip the
        # 4x800m version to avoid duplicates.
        if event_id == "63" and gender == "women":
            results = [r for r in results if r.get('year') != 1994]
        
        if results:
            insert_results(conn, results)
            total_results += len(results)
            event_name = EVENT_MAPPING[event_id]["name"]
            print(f"  {environment}/{gender}/{event_name}: {len(results)} results")
    
    conn.close()
    
    print(f"\nDone! Inserted {total_results} HTML results.")


if __name__ == "__main__":
    main()
