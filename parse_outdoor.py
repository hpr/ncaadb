#!/usr/bin/env python3
"""
NCAA Track & Field Championships History Parser
Parses PDFs from Track & Field News and creates a searchable SQLite database.
"""

import subprocess
import sqlite3
import re
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from util.constants import SCHOOL_TYPOS, CLASS_MAP, clean_school_name, parse_class

DB_PATH = "ncaa_history.db"

DISCIPLINES = {
    "men": {
        "ncaam100": {"name": "100m", "type": "track"},
        "ncaam200": {"name": "200m", "type": "track"},
        "ncaam400": {"name": "400m", "type": "track"},
        "ncaam800": {"name": "800m", "type": "track"},
        "ncaam1500": {"name": "1500m", "type": "track"},
        "ncaam5000": {"name": "5000m", "type": "track"},
        "ncaam10000": {"name": "10000m", "type": "track"},
        "ncaamst": {"name": "Steeplechase", "type": "track"},
        "ncaam110h": {"name": "110m Hurdles", "type": "track"},
        "ncaam400h": {"name": "400m Hurdles", "type": "track"},
        "ncaam220h": {"name": "220y Hurdles", "type": "track"},
        "ncaam4x1": {"name": "4x100m Relay", "type": "relay"},
        "ncaam4x4": {"name": "4x400m Relay", "type": "relay_splits"},
        "ncaamhj": {"name": "High Jump", "type": "field"},
        "ncaampv": {"name": "Pole Vault", "type": "field"},
        "ncaamlj": {"name": "Long Jump", "type": "field"},
        "ncaamtj": {"name": "Triple Jump", "type": "field"},
        "ncaamsp": {"name": "Shot Put", "type": "field"},
        "ncaamdt": {"name": "Discus", "type": "field"},
        "ncaamht": {"name": "Hammer", "type": "field"},
        "ncaamjt": {"name": "Javelin", "type": "field"},
        "ncaamdec": {"name": "Decathlon", "type": "multi"},
    },
    "women": {
        "ncaaw100": {"name": "100m", "type": "track"},
        "ncaaw200": {"name": "200m", "type": "track"},
        "ncaaw400": {"name": "400m", "type": "track"},
        "ncaaw800": {"name": "800m", "type": "track"},
        "ncaaw1500": {"name": "1500m", "type": "track"},
        "ncaaw5000": {"name": "5000m", "type": "track"},
        "ncaaw10000": {"name": "10000m", "type": "track"},
        "ncaawst": {"name": "Steeplechase", "type": "track"},
        "ncaaw100h": {"name": "100m Hurdles", "type": "track"},
        "ncaaw400h": {"name": "400m Hurdles", "type": "track"},
        "ncaaw4x1": {"name": "4x100m Relay", "type": "relay"},
        "ncaaw4x4": {"name": "4x400m Relay", "type": "relay_splits"},
        "ncaawhj": {"name": "High Jump", "type": "field"},
        "ncaawpv": {"name": "Pole Vault", "type": "field"},
        "ncaawlj": {"name": "Long Jump", "type": "field"},
        "ncaawtj": {"name": "Triple Jump", "type": "field"},
        "ncaawsp": {"name": "Shot Put", "type": "field"},
        "ncaawdt": {"name": "Discus", "type": "field"},
        "ncaawht": {"name": "Hammer", "type": "field"},
        "ncaawjt": {"name": "Javelin", "type": "field"},
        "ncaaw3000": {"name": "3000m", "type": "track"},
        "ncaawhept": {"name": "Heptathlon", "type": "multi"},
    }
}


def create_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''DROP TABLE IF EXISTS results''')
    
    c.execute('''
        CREATE TABLE results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            date TEXT,
            name TEXT NOT NULL,
            school TEXT,
            discipline TEXT NOT NULL,
            wind REAL,
            gender TEXT NOT NULL,
            mark_num REAL,
            mark_str TEXT,
            class TEXT,
            place INTEGER,
            is_dq INTEGER DEFAULT 0,
            is_dnf INTEGER DEFAULT 0,
            is_dns INTEGER DEFAULT 0,
            is_wind_aided INTEGER DEFAULT 0,
            is_international INTEGER DEFAULT 0,
            split_time TEXT,
            leg_idx INTEGER,
            is_relay INTEGER DEFAULT 0,
            is_converted INTEGER DEFAULT 0,
            location TEXT,
            notes TEXT,
            source_url TEXT DEFAULT NULL
        )
    ''')
    
    c.execute('CREATE INDEX idx_year ON results(year)')
    c.execute('CREATE INDEX idx_date ON results(date)')
    c.execute('CREATE INDEX idx_name ON results(name)')
    c.execute('CREATE INDEX idx_school ON results(school)')
    c.execute('CREATE INDEX idx_discipline ON results(discipline)')
    c.execute('CREATE INDEX idx_gender ON results(gender)')
    
    conn.commit()
    return conn


def pdf_to_text(pdf_path: str) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True,
        text=True
    )
    return result.stdout


def parse_wind(text: str) -> Optional[float]:
    match = re.search(r'wind\s+([+-]?\d+\.?\d*)', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def parse_mark(mark_str: str) -> Tuple[Optional[float], Optional[str], bool, bool]:
    if not mark_str or mark_str.strip() == '?' or mark_str.lower() in ['nt', 'n']:
        return None, None, False, False
    
    is_wind_aided = 'w' in mark_str.lower()
    is_converted = mark_str.rstrip().endswith('+')
    
    cleaned = mark_str.replace('w', '').replace('W', '')
    if cleaned.startswith('c') or cleaned.startswith('C'):
        cleaned = cleaned[1:]
    cleaned = cleaned.replace('+', '').replace('*', '').replace(';', '').replace('?', '').replace('¶', '').replace('h', '').replace('H', '').replace('i', '').replace('I', '').replace('y', '').replace('Y', '').strip()
    
    # Take first part if there's a slash (e.g., "9.9/10.0" -> "9.9")
    if '/' in cleaned:
        cleaned = cleaned.split('/')[0]
    
    # Strip altitude annotation (A) or (A)
    cleaned = re.sub(r'\([Aa]\)$', '', cleaned).strip()
    
    # Normalize various hyphen characters to regular hyphen
    # U+2010 HYPHEN, U+2011 NON-BREAKING HYPHEN, U+2012 FIGURE DASH, U+2013 EN DASH, U+2014 EM DASH
    cleaned = cleaned.replace('\u2010', '-').replace('\u2011', '-').replace('\u2012', '-')
    cleaned = cleaned.replace('\u2013', '-').replace('\u2014', '-')
    
    # Normalize fraction characters (replace with decimal, handling context)
    # When fraction follows a number, it should be decimal (e.g., "8¼" -> "8.25")
    # When fraction is standalone, it's the whole number
    cleaned = cleaned.replace('\u00BD', '.5').replace('\u00BC', '.25').replace('\u00BE', '.75')
    cleaned = cleaned.replace('½', '.5').replace('¼', '.25').replace('¾', '.75')
    
    numeric = None
    try:
        if ':' in cleaned:
            parts = cleaned.split(':')
            if len(parts) == 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                numeric = minutes * 60 + seconds
        elif '-' in cleaned and not cleaned.startswith('-'):
            parts = cleaned.split('-')
            if len(parts) == 2:
                try:
                    feet = float(parts[0])
                    inches = float(parts[1])
                    numeric = feet * 0.3048 + inches * 0.0254
                except ValueError:
                    pass
            elif len(parts) == 3:
                # Handle format like "6-6-.25" (feet-inches-fraction)
                try:
                    feet = float(parts[0])
                    inches = float(parts[1])
                    fraction = float(parts[2]) if parts[2] else 0
                    numeric = feet * 0.3048 + (inches + fraction) * 0.0254
                except ValueError:
                    pass
        else:
            numeric = float(cleaned.replace('m', '').replace('y', ''))
    except ValueError:
        pass
    
    return numeric, cleaned, is_wind_aided, is_converted


def parse_result_line(line: str, is_relay: bool = False) -> Optional[Dict[str, Any]]:
    line = line.strip()
    if not line:
        return None
    
    tie = line.startswith('=')
    if tie:
        line = line[1:].strip()
    
    is_converted_place = line.startswith('+')
    line = line.lstrip('+').strip()
    
    place_match = re.match(r'^(\d+)[\.,]\s*', line)
    if not place_match:
        return None
    
    place = int(place_match.group(1))
    if tie:
        place = -place
    
    rest = line[place_match.end():]
    
    if is_relay:
        result = parse_relay_line(place, rest)
    else:
        result = parse_individual_line(place, rest)
    
    if result and is_converted_place:
        result['is_converted'] = True
    return result


NOTE_KEYWORDS = ['died', 'injured', 'injury', 'illness', 'sick', ' deceased']


def is_note_paren(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in NOTE_KEYWORDS)


def parse_individual_line(place: int, line: str) -> Optional[Dict[str, Any]]:
    paren_groups = list(re.finditer(r'\(([^)]+)\)', line))
    if not paren_groups:
        fallback = re.search(r'\(([A-Za-z][A-Za-z\s&\'\-\.\/]+?)\s*\.{2,}', line)
        if not fallback:
            return None
        school = clean_school_name(fallback.group(1).strip())
        name = line[:fallback.start()].strip()
        rest = line[fallback.end():]
    elif len(paren_groups) >= 2 and is_note_paren(paren_groups[-1].group(1)):
        school_paren = paren_groups[-2]
        school = clean_school_name(school_paren.group(1))
        name = line[:school_paren.start()].strip()
        rest = paren_groups[-1].end()
        rest = line[rest:]
    else:
        last_paren = paren_groups[-1]
        school = clean_school_name(last_paren.group(1))
        name = line[:last_paren.start()].strip()
        rest = line[last_paren.end():]
    
    # Strip leading period that sometimes appears after school paren
    rest = rest.lstrip('.')
    
    is_international = name.endswith("'") or name.endswith("\u2019")
    if is_international:
        name = name.rstrip("'\u2019").strip()
    
    name = re.sub(r'^\*+|\*+$', '', name).strip()
    
    parts = re.split(r'\.{2,}|\s+', rest)
    parts = [p for p in parts if p]
    
    class_val = None
    mark_str = None
    
    for i, part in enumerate(parts):
        class_parsed = parse_class(part)
        if class_parsed:
            class_val = class_parsed
        elif not mark_str and part not in ['MR', 'CR', 'WR', 'WJR', 'AJR', 'AmCR', '(MR)', '(CR)', '(WR)', '(A)', '*', '¶', 'HS', 'in']:
            # Skip year references like '41, '42, ’41, ’42
            if not re.match(r"^['\u2019]\d{2}$", part):
                mark_str = part
    
    if not mark_str and len(parts) > 0:
        for part in reversed(parts):
            if not parse_class(part):
                mark_str = part
                break
    
    mark_num, mark_str_clean, is_wind_aided, is_converted = parse_mark(mark_str) if mark_str else (None, None, False, False)
    
    return {
        'place': abs(place),
        'name': name,
        'school': school,
        'class': class_val,
        'mark_num': mark_num,
        'mark_str': mark_str_clean,
        'is_wind_aided': is_wind_aided,
        'is_international': is_international,
        'is_dq': False,
        'is_dnf': False,
        'is_dns': False,
        'is_relay': False,
        'split_time': None,
        'leg_idx': None,
        'is_converted': is_converted,
    }


def parse_relay_line(place: int, line: str) -> Optional[Dict[str, Any]]:
    # First try: dots followed by time
    match = re.match(r'^(.+?)\s*\.{2,}\s*(\S+)', line)
    if match:
        school = clean_school_name(match.group(1))
        mark_str = match.group(2).strip()
    else:
        # Second try: check if line ends with a valid time/mark pattern (with or without space)
        # Valid marks: time like 3:05.53, distance like 45.6, or DQ/DNF
        time_match = re.match(r'^(.+?)\s+(\d+:\d+\.?\d*[+]?\s*|\d+\.?\d*[+w]?|DQ|DNF|DNS)$', line, re.IGNORECASE)
        if time_match:
            school = clean_school_name(time_match.group(1))
            mark_str = time_match.group(2).strip()
        else:
            # Third try: time concatenated to school name (e.g., "BYU3:02.51")
            concat_match = re.match(r'^(.+?)(\d+:\d+\.?\d*[+]?)$', line)
            if concat_match:
                school = clean_school_name(concat_match.group(1))
                mark_str = concat_match.group(2).strip()
            else:
                # No time found - just school name
                school = clean_school_name(line)
                mark_str = None
    
    mark_num, mark_str_clean, is_wind_aided, is_converted = parse_mark(mark_str) if mark_str else (None, None, False, False)
    
    is_dq = 'dq' in mark_str.lower() if mark_str else False
    is_dnf = 'dnf' in mark_str.lower() if mark_str else False
    
    return {
        'place': abs(place),
        'school': school,
        'mark_num': mark_num,
        'mark_str': mark_str_clean,
        'is_wind_aided': is_wind_aided,
        'is_dq': is_dq,
        'is_dnf': is_dnf,
        'is_converted': is_converted,
    }


def is_relay_dq_line(line: str) -> bool:
    """Check if a line is a relay DQ/DNF/DNS entry like '[1]Texas Tech [37.93]'"""
    stripped = line.strip()
    if re.match(r'^\[\d+\].+\[.+\]', stripped):
        return True
    if re.match(r'^[A-Za-z].+\[.+\]\s*\.{2,}', stripped):
        return True
    return False


def parse_relay_dq_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a relay DQ/DNF/DNS line.
    Format: '[original_place]Team Name [original_time]' or 'Team Name [original_time]' or 'Team Name .....'
    """
    stripped = line.strip()
    
    match = re.match(r'^\[(\d+)\](.+?)\s*\.{2,}\s*\[([^\]]+)\]', stripped)
    if match:
        original_place = int(match.group(1))
        school = match.group(2).strip()
        mark_str = match.group(3).strip()
        
        mark_num, mark_str_clean, _, _ = parse_mark(mark_str) if mark_str else (None, None, False, False)
        
        return {
            'school': clean_school_name(school),
            'mark_num': mark_num,
            'mark_str': mark_str_clean,
            'original_place': original_place,
        }
    
    match = re.match(r'^\[(\d+)\](.+?)\s*\[([^\]]+)\]\s*\.{2,}', stripped)
    if match:
        original_place = int(match.group(1))
        school = match.group(2).strip()
        mark_str = match.group(3).strip()
        
        mark_num, mark_str_clean, _, _ = parse_mark(mark_str) if mark_str else (None, None, False, False)
        
        return {
            'school': clean_school_name(school),
            'mark_num': mark_num,
            'mark_str': mark_str_clean,
            'original_place': original_place,
        }
    
    match = re.match(r'^([A-Za-z][A-Za-z\s&\'\-\.\/]+?)\s*\[([^\]]+)\]\s*\.{2,}', stripped)
    if match:
        school = match.group(1).strip()
        mark_str = match.group(2).strip()
        
        mark_num, mark_str_clean, _, _ = parse_mark(mark_str) if mark_str else (None, None, False, False)
        
        return {
            'school': clean_school_name(school),
            'mark_num': mark_num,
            'mark_str': mark_str_clean,
            'original_place': None,
        }
    
    match = re.match(r'^([A-Za-z][A-Za-z\s&\'\-]+?)\s*\.{2,}\s*$', stripped)
    if match:
        school = match.group(1).strip()
        return {
            'school': clean_school_name(school),
            'mark_num': None,
            'mark_str': None,
            'original_place': None,
        }
    
    match = re.match(r'^([A-Za-z][A-Za-z\s&\'\-]+?)\s*\(personnel unknown\)\.?\s*$', stripped, re.IGNORECASE)
    if match:
        school = match.group(1).strip()
        return {
            'school': clean_school_name(school),
            'mark_num': None,
            'mark_str': None,
            'original_place': None,
        }
    
    return None


def parse_team_members_line(line: str) -> Tuple[Optional[str], bool]:
    """
    Parse a line that may contain team members.
    Returns (content, is_complete) where is_complete is True if the line ends with ')'
    """
    if re.search(r'\[\d+\]', line) or re.search(r'\[\d+\.\d+\]', line):
        return None, False
    
    match = re.match(r'^\s*\(([^)]*)(\)?)\s*[;.]?\s*$', line)
    if match:
        content = match.group(1).strip()
        has_close = match.group(2) == ')'
        
        if not content:
            return None, has_close
        
        if re.match(r'^[\d\.y\+\-\sMRWRCRAJWJ:]+$', content, re.IGNORECASE):
            return None, True
        if re.match(r'^\d{4}\.\d+y?\s*MR$', content, re.IGNORECASE):
            return None, True
        if re.match(r'^\d{1,2} contestants', content, re.IGNORECASE):
            return None, True
        if re.match(r'^\d+ finalists', content, re.IGNORECASE):
            return None, True
        if re.match(r'^\d+\s*teams', content, re.IGNORECASE):
            return None, True
        if content == '?':
            return None, True
        
        return content, has_close
    
    match = re.match(r'^\s+([A-Za-z][A-Za-z\s\'\-\.]+(?:,\s*[A-Za-z][A-Za-z\s\'\-\.]+)*)\s*$', line)
    if match:
        content = match.group(1).strip()
        if content:
            return content, False
    
    match = re.match(r'^\s+([^()]+)(\)?)\s*[;.]?\s*$', line)
    if match:
        content = match.group(1).strip()
        has_close = match.group(2) == ')'
        
        if not content:
            return None, has_close
        
        if has_close:
            return content, True
        elif re.search(r'[A-Za-z]', content):
            return content, False
    
    return None, False


def is_note_line(line: str) -> bool:
    if re.match(r'^\s*\([\d\.y\+\-\sMRWRCRAJWJ:,]+\)\s*$', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(\d+:\d+\.?\d*[y\+]?\s*[A-Z]*\)\s*$', line):
        return True
    if re.match(r'^\s*\(\d{4}\.\d+y?\s*MR\)\s*$', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\*\s*=', line):
        return True
    if re.match(r'^\s*¶\s*=', line):
        return True
    if re.match(r'^\s*\(also under', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(first school to win', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(low[-\u2010\u2011]altitude', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\([\d\.]+y?\s*low[-\u2010\u2011]altitude', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(officially\s', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(.*officially\s', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(superior to', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(event not contested', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(but its', line, re.IGNORECASE):
        return True
    if re.search(r'but its \w+ leading runners', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(auto lo[-\u2010\u2011]alt', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(note:', line, re.IGNORECASE):
        return True
    if re.match(r'^\s*\(North Carolina Central set CR', line, re.IGNORECASE):
        return True
    return False


def parse_team_members_with_splits(content: str) -> List[Dict[str, Any]]:
    """
    Parse team members with optional split times.
    Formats:
    - "Name1, Name2, Name3, Name4" (no splits)
    - "Name1 48.3, Name2 47.1, Name3 45.3, Name4 45.5" (with splits)
    - "in heats: Name1, Name2, Name3, Name4" (DNS entries)
    """
    members = []
    
    content = re.sub(r',\s*$', '', content.strip())
    
    content = re.sub(r'^in\s+heats:\s*', '', content, flags=re.IGNORECASE)
    
    # Strip bracket annotations before splitting (e.g., [fell], [drop])
    # But first convert bracket annotations between names to commas
    # e.g., "Marvin Stevenson [miss] Robert Parham" → "Marvin Stevenson, Robert Parham"
    content = re.sub(r'\s*\[\s*[^\]]*\s*\]\s+(?=[A-Z])', ', ', content)
    content = re.sub(r'\s*\[[^\]]*\]', '', content).strip()
    
    # Strip em-dash notes (e.g., "43.1—fastest carry in history: 21.5y/21.9y")
    content = re.sub(r'\u2014.*', '', content).strip()
    
    parts = re.split(r',\s*(?=[A-Za-z])', content)
    
    # If 5 parts in a 4-leg relay, one was incorrectly split.
    # Merge the only part without a split time with the next part.
    if len(parts) == 5:
        for j in range(len(parts) - 1):
            if not re.search(r'\d', parts[j]):
                parts[j] = parts[j].replace(',', '') + ' ' + parts[j + 1]
                parts.pop(j + 1)
                break
    
    # Split on pattern where split time is followed by next name with no comma
    # e.g., "Krystin Lacy 53.65 Nicole Leach 51.25"
    new_parts = []
    for part in parts:
        sub_parts = re.split(r'(?<=\d)\s+(?=[A-Z])', part)
        new_parts.extend(sub_parts)
    parts = new_parts
    
    # If only 3 members, try splitting on apostrophe (PDF typo fix)
    if len(parts) == 3:
        new_parts = []
        for part in parts:
            # Split on apostrophe followed by space and capital letter
            sub_parts = re.split(r"'\s*(?=[A-Z])", part)
            new_parts.extend(sub_parts)
        parts = new_parts
    
    for i, part in enumerate(parts):
        part = part.strip().rstrip(',')
        if not part:
            continue
        
        # Handle curly apostrophe (U+2019) same as regular apostrophe
        part_normalized = part.replace('\u2019', "'")
        
        # Strip annotations like [fell], [pull], [push], etc. before matching
        part_cleaned = re.sub(r'\s*\[[^\]]*\]', '', part_normalized).strip()
        
        # Strip leading dots (continuation indicator)
        part_cleaned = re.sub(r'^\.{2,}\s*', '', part_cleaned).strip()
        
        # Strip trailing apostrophe before matching (international marker)
        pre_stripped = part_cleaned.rstrip("'").rstrip('.')
        
        match = re.match(r"^([\w][\w\s'\-\.]+?)\s+(\d+:\d+\.?\d*(?:\s*y)?)$", pre_stripped, re.UNICODE)
        if match:
            name = match.group(1).strip()
            split_time = match.group(2).replace('y', '')
        else:
            match = re.match(r"^([\w][\w\s'\-\.]+?)\s+(\d+\.?\d*(?:\s*y)?)$", pre_stripped, re.UNICODE)
            if match:
                name = match.group(1).strip()
                split_time = match.group(2).replace('y', '')
            else:
                match = re.match(r"^([\w][\w\s'\-\.]+?)'?\s+c?(\d+\.?\d*)$", pre_stripped, re.UNICODE)
                if match:
                    name = match.group(1).strip()
                    split_time = match.group(2)
                else:
                    match = re.match(r"^([\w][\w\s'\-\.]+?)(\d{2}\.\d+)$", pre_stripped, re.UNICODE)
                    if match:
                        name = match.group(1).strip()
                        split_time = match.group(2)
                    else:
                        name = part_cleaned
                        split_time = None
        
        # Then check for international marker (trailing apostrophe)
        is_international = name.endswith("'") or name.endswith("\u2019")
        if is_international:
            name = name.rstrip("'\u2019").strip()
        
        name = re.sub(r'^\*+|\*+$', '', name).strip()
        
        if ';' in part_cleaned:
            continue
        
        members.append({
            'name': name,
            'leg_idx': i + 1,
            'split_time': split_time,
            'is_international': is_international,
        })
    
    return members


def combine_multiline_team_members(lines: List[str], start_idx: int) -> Tuple[str, int]:
    """
    Combine multi-line team members into a single string.
    Returns (combined_content, end_idx) where end_idx is the index of the last team member line.
    """
    content_parts = []
    idx = start_idx
    last_content_idx = None
    
    while idx < len(lines):
        line = lines[idx]
        
        if re.match(r'^\x0c?\d{4}$', line.strip()):
            break
        
        if re.match(r'^\s*Section\s+(I|II|1|2)\s*:?\s*$', line, re.IGNORECASE):
            break
        
        if is_note_line(line):
            idx += 1
            continue
        
        team_members, is_complete = parse_team_members_line(line)
        
        if team_members is not None:
            content_parts.append(team_members)
            last_content_idx = idx
            if is_complete:
                break
        elif is_complete and not content_parts:
            break
        elif content_parts and line.strip().endswith(')'):
            # Continuation line starting at column 0 with closing paren (e.g., "Name 45.5)")
            content = line.strip().rstrip(')')
            if content and re.search(r'[A-Za-z]', content):
                content_parts.append(content)
                last_content_idx = idx
                break
        elif line.strip() and not line.startswith(' ') and not line.startswith('\t'):
            if content_parts:
                break
        elif not line.strip():
            break
        idx += 1
    
    # Join parts, adding commas where needed between member entries
    result_parts = []
    for i, part in enumerate(content_parts):
        if i > 0:
            prev_part = content_parts[i - 1]
            # Add comma if previous part doesn't end with comma and current doesn't start with comma
            if not prev_part.rstrip().endswith(',') and not part.lstrip().startswith(','):
                result_parts.append(',')
        result_parts.append(part)
    
    return ' '.join(result_parts), last_content_idx if last_content_idx is not None else idx


def is_athlete_line(line: str) -> bool:
    stripped = line.strip()
    if re.match(r'^[\.\s]*[A-Z][^()]*\([^)]+\)', stripped):
        return True
    return False


def parse_athlete_from_line(line: str) -> Optional[Dict[str, Any]]:
    stripped = line.strip()
    stripped = re.sub(r'^[\.\s]+', '', stripped)
    
    personnel_match = re.match(r'^([A-Za-z][A-Za-z\s&\'\-]+?)\s*\(personnel unknown\)\.?$', stripped, re.IGNORECASE)
    if personnel_match:
        return {
            'name': 'Relay members unknown',
            'school': clean_school_name(personnel_match.group(1)),
            'is_international': False,
        }
    
    paren_groups = list(re.finditer(r'\(([^)]+)\)', stripped))
    if not paren_groups:
        return None
    
    if len(paren_groups) >= 2 and is_note_paren(paren_groups[-1].group(1)):
        school_paren = paren_groups[-2]
        school = clean_school_name(school_paren.group(1))
        name = stripped[:school_paren.start()].strip()
    else:
        last_paren = paren_groups[-1]
        school = clean_school_name(last_paren.group(1))
        name = stripped[:last_paren.start()].strip()
    
    is_international = name.endswith("'") or name.endswith("\u2019")
    if is_international:
        name = name.rstrip("'\u2019").strip()
    
    name = re.sub(r'^\*+', '', name).strip()
    
    return {
        'name': name,
        'school': school,
        'is_international': is_international,
    }


def parse_pdf(pdf_path: str, gender: str, discipline_key: str, discipline_info: Dict) -> List[Dict[str, Any]]:
    text = pdf_to_text(pdf_path)
    lines = text.split('\n')
    
    results = []
    current_year = None
    current_date = None
    current_wind = None
    current_location = None
    event_type = discipline_info['type']
    is_relay = event_type in ['relay', 'relay_splits']
    has_splits = event_type == 'relay_splits'
    
    last_relay_result = None
    pending_status = None
    in_section = False
    composite_relay_results = None
    page_num = 0
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if line.startswith('\x0c'):
            page_num += 1
        
        if discipline_key == 'ncaawht' and page_num == 0 and current_year == 2025:
            i += 1
            continue
        
        if re.match(r'^\x0c?\d{4}$', stripped):
            current_year = int(stripped)
            current_date = None
            current_wind = None
            current_location = None
            last_relay_result = None
            pending_status = None
            in_section = False
            composite_relay_results = None
            i += 1
            continue
        
        if current_year is None:
            i += 1
            continue
        
        if stripped == "(meet not held)" or stripped == "(meet not held":
            i += 1
            continue
        
        wind = parse_wind(stripped)
        if wind is not None:
            current_wind = wind
        
        loc_match = re.match(r'^\(([A-Za-z][A-Za-z\s\.\[\]]+(?:,\s*[A-Za-z][A-Za-z\s\.]+)?),\s*(June|July|May|August|January|February|March|April|September|October|November|December)\s+(\d{1,2})(?:[–\-]\d+)?', stripped)
        if loc_match:
            current_location = loc_match.group(1).strip()
            current_date = f"{loc_match.group(2)} {loc_match.group(3)}"
        else:
            date_match = re.match(r'^\((June|July|May|August|January|February|March|April|September|October|November|December)\s+(\d{1,2})(?:[–\-]\d+)?(?:\)|;)', stripped)
            if date_match:
                current_date = f"{date_match.group(1)} {date_match.group(2)}"
            else:
                loc_semi_match = re.match(r'^\(([A-Za-z][A-Za-z\s\.]+);\s*(June|July|May|August|January|February|March|April|September|October|November|December)\s+(\d{1,2})', stripped)
                if loc_semi_match:
                    current_location = loc_semi_match.group(1).strip()
                    current_date = f"{loc_semi_match.group(2)} {loc_semi_match.group(3)}"
        
        if re.match(r'^\(\d+\s+(contestants|teams|finalists)', stripped):
            pass
        
        if stripped.startswith('…') or stripped.lower().startswith('...'):
            status = None
            lower = stripped.lower()
            if 'dnf' in lower:
                status = 'dnf'
            elif 'dq' in lower:
                status = 'dq'
            elif 'dns' in lower:
                status = 'dns'
            elif 'dnc' in lower:
                status = 'dns'
            
            if status:
                pending_status = status
            i += 1
            continue
        
        if pending_status and is_athlete_line(line):
            athlete = parse_athlete_from_line(line)
            if athlete:
                school_name = clean_school_name(athlete['school'], current_year)
                if athlete['name'] == 'Relay members unknown':
                    for leg in range(1, 5):
                        results.append({
                            'year': current_year,
                            'date': current_date,
                            'gender': gender,
                            'discipline': discipline_info['name'],
                            'wind': current_wind,
                            'location': current_location,
                            'place': None,
                            'name': 'Relay member unknown',
                            'school': school_name,
                            'class': None,
                            'mark_num': None,
                            'mark_str': None,
                            'is_wind_aided': False,
                            'is_international': athlete['is_international'],
                            'is_dq': pending_status == 'dq',
                            'is_dnf': pending_status == 'dnf',
                            'is_dns': pending_status == 'dns',
                            'is_relay': is_relay,
                            'split_time': None,
                            'leg_idx': leg,
                            'is_converted': False,
                        })
                else:
                    results.append({
                        'year': current_year,
                        'date': current_date,
                        'gender': gender,
                        'discipline': discipline_info['name'],
                        'wind': current_wind,
                        'location': current_location,
                        'place': None,
                        'name': athlete['name'],
                        'school': school_name,
                        'class': None,
                        'mark_num': None,
                        'mark_str': None,
                        'is_wind_aided': False,
                        'is_international': athlete['is_international'],
                        'is_dq': pending_status == 'dq',
                        'is_dnf': pending_status == 'dnf',
                        'is_dns': pending_status == 'dns',
                        'is_relay': is_relay,
                        'split_time': None,
                        'leg_idx': None,
                        'is_converted': False,
                    })
            pending_status = None
            i += 1
            continue
        
        if is_relay and pending_status:
            relay_dq = parse_relay_dq_line(stripped)
            if relay_dq:
                team_members_str, end_idx = combine_multiline_team_members(lines, i + 1)
                
                if team_members_str:
                    members = parse_team_members_with_splits(team_members_str)
                    
                    for member in members:
                        result = {
                            'year': current_year,
                            'date': current_date,
                            'gender': gender,
                            'discipline': discipline_info['name'],
                            'wind': current_wind,
                            'location': current_location,
                            'place': relay_dq['original_place'],
                            'name': member['name'],
                            'school': clean_school_name(relay_dq['school'], current_year),
                            'class': None,
                            'mark_num': relay_dq['mark_num'],
                            'mark_str': relay_dq['mark_str'],
                            'is_wind_aided': False,
                            'is_international': member['is_international'],
                            'is_dq': pending_status == 'dq',
                            'is_dnf': pending_status == 'dnf',
                            'is_dns': pending_status == 'dns',
                            'is_relay': True,
                            'split_time': member['split_time'],
                            'leg_idx': member['leg_idx'],
                            'is_converted': False,
                        }
                        results.append(result)
                    
                    pending_status = None
                    last_relay_result = None
                    i = end_idx + 1
                    continue
                else:
                    result = {
                        'year': current_year,
                        'date': current_date,
                        'gender': gender,
                        'discipline': discipline_info['name'],
                        'wind': current_wind,
                        'location': current_location,
                        'place': relay_dq['original_place'],
                        'name': relay_dq['school'],
                        'school': clean_school_name(relay_dq['school'], current_year),
                        'class': None,
                        'mark_num': relay_dq['mark_num'],
                        'mark_str': relay_dq['mark_str'],
                        'is_wind_aided': False,
                        'is_international': False,
                        'is_dq': pending_status == 'dq',
                        'is_dnf': pending_status == 'dnf',
                        'is_dns': pending_status == 'dns',
                        'is_relay': True,
                        'split_time': None,
                        'leg_idx': None,
                        'is_converted': False,
                    }
                    results.append(result)
                    pending_status = None
                    last_relay_result = None
                    i += 1
                    continue
        
        pending_status = None
        
        if is_relay and last_relay_result is not None:
            if composite_relay_results is not None and not in_section:
                last_relay_result = None
            else:
                team_members_str, end_idx = combine_multiline_team_members(lines, i)
                
                if team_members_str:
                    members = parse_team_members_with_splits(team_members_str)
                    
                    for member in members:
                        result = {
                            'year': current_year,
                            'date': current_date,
                            'gender': gender,
                            'discipline': discipline_info['name'],
                            'wind': current_wind,
                            'location': current_location,
                            'place': last_relay_result['place'],
                            'name': member['name'],
                            'school': last_relay_result['school'],
                            'class': None,
                            'mark_num': last_relay_result['mark_num'],
                            'mark_str': last_relay_result['mark_str'],
                            'is_wind_aided': last_relay_result['is_wind_aided'],
                            'is_international': member['is_international'],
                            'is_dq': last_relay_result['is_dq'],
                            'is_dnf': last_relay_result['is_dnf'],
                            'is_dns': False,
                            'is_relay': True,
                            'split_time': member['split_time'],
                            'leg_idx': member['leg_idx'],
                            'is_converted': last_relay_result.get('is_converted', False),
                        }
                        results.append(result)
                    
                    last_relay_result = None
                    i = end_idx + 1
                    continue
                else:
                    for leg in range(1, 5):
                        results.append({
                            'year': current_year,
                            'date': current_date,
                            'gender': gender,
                            'discipline': discipline_info['name'],
                            'wind': current_wind,
                            'location': current_location,
                            'place': last_relay_result['place'],
                            'name': 'Relay member unknown',
                            'school': last_relay_result['school'],
                            'class': None,
                            'mark_num': last_relay_result['mark_num'],
                            'mark_str': last_relay_result['mark_str'],
                            'is_wind_aided': last_relay_result['is_wind_aided'],
                            'is_international': False,
                            'is_dq': last_relay_result['is_dq'],
                            'is_dnf': last_relay_result['is_dnf'],
                            'is_dns': False,
                            'is_relay': True,
                            'split_time': None,
                            'leg_idx': leg,
                            'is_converted': last_relay_result.get('is_converted', False),
                        })
                    last_relay_result = None
        
        if re.match(r'^Composite finish\s*:?\s*$', stripped, re.IGNORECASE):
            in_section = False
            composite_relay_results = {}
            i += 1
            continue
        
        if re.match(r'^Section\s+(I|II|1|2)\s*:?\s*$', stripped, re.IGNORECASE):
            in_section = True
            last_relay_result = None
            i += 1
            continue
        
        result = parse_result_line(stripped, is_relay)
        if result:
            if is_relay:
                school_clean = clean_school_name(result['school'], current_year)
                result['year'] = current_year
                result['date'] = current_date
                result['gender'] = gender
                result['discipline'] = discipline_info['name']
                result['wind'] = current_wind
                result['location'] = current_location
                result['school'] = school_clean
                
                if in_section:
                    composite_entry = composite_relay_results.get(school_clean) if composite_relay_results else None
                    if composite_entry:
                        result['place'] = composite_entry['place']
                        result['mark_num'] = composite_entry['mark_num']
                        result['mark_str'] = composite_entry['mark_str']
                        result['is_wind_aided'] = composite_entry['is_wind_aided']
                        result['is_dq'] = composite_entry['is_dq']
                        result['is_dnf'] = composite_entry['is_dnf']
                        result['is_converted'] = composite_entry.get('is_converted', False)
                    else:
                        result['place'] = None
                    last_relay_result = result
                else:
                    if composite_relay_results is not None:
                        composite_relay_results[school_clean] = result
                    last_relay_result = result
            else:
                result['year'] = current_year
                result['date'] = current_date
                result['gender'] = gender
                result['discipline'] = discipline_info['name']
                result['wind'] = current_wind
                result['location'] = current_location
                result['school'] = clean_school_name(result['school'], current_year)
                results.append(result)
        
        i += 1
    
    return results


def insert_results(conn: sqlite3.Connection, results: List[Dict[str, Any]]):
    c = conn.cursor()
    
    for r in results:
        c.execute('''
            INSERT INTO results (
                year, date, name, school, discipline, wind, gender,
                mark_num, mark_str, class, place,
                is_dq, is_dnf, is_dns, is_wind_aided, is_international,
                split_time, leg_idx, is_relay, is_converted, location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            r.get('year'),
            r.get('date'),
            r.get('name'),
            r.get('school'),
            r.get('discipline'),
            r.get('wind'),
            r.get('gender'),
            r.get('mark_num'),
            r.get('mark_str'),
            r.get('class'),
            r.get('place'),
            1 if r.get('is_dq') else 0,
            1 if r.get('is_dnf') else 0,
            1 if r.get('is_dns') else 0,
            1 if r.get('is_wind_aided') else 0,
            1 if r.get('is_international') else 0,
            r.get('split_time'),
            r.get('leg_idx'),
            1 if r.get('is_relay') else 0,
            1 if r.get('is_converted') else 0,
            r.get('location'),
        ))
    
    conn.commit()


def main():
    print("Creating database...")
    conn = create_database()
    
    total_results = 0
    
    for gender in ['men', 'women']:
        print(f"\nProcessing {gender}'s PDFs...")
        pdf_dir = Path(f"pdfs/{gender}")
        
        for discipline_key, discipline_info in DISCIPLINES[gender].items():
            pdf_path = pdf_dir / f"{discipline_key}.pdf"
            
            if not pdf_path.exists():
                print(f"  Warning: {pdf_path} not found")
                continue
            
            print(f"  Parsing {discipline_info['name']}...")
            
            if discipline_key == "ncaaw10000":
                print(f"    Skipped (parsed from HTML source instead)")
                continue
            
            results = parse_pdf(str(pdf_path), gender, discipline_key, discipline_info)
            
            if results:
                if gender == 'men' and discipline_info['name'] == '5000m':
                    ACTUAL_5000M_YEARS = {1936, 1948, 1952, 1956}
                    for r in results:
                        if r['year'] < 1959 and r['year'] not in ACTUAL_5000M_YEARS:
                            r['discipline'] = '3000m'
                
                insert_results(conn, results)
                total_results += len(results)
                print(f"    Inserted {len(results)} results")
            else:
                print(f"    No results found")
    
    conn.close()
    print(f"\nDone! Total results: {total_results}")
    print(f"Database saved to: {DB_PATH}")


if __name__ == "__main__":
    main()
