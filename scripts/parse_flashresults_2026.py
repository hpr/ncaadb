#!/usr/bin/env python3
"""
Parse 2026 NCAA Indoor Championships from FlashResults.
https://flashresults.ncaa.com/Indoor/2026/index.htm
"""

import sqlite3
import re
import sys
import calendar
from pathlib import Path
from bs4 import BeautifulSoup

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from parse_indoor import fix_name_casing, parse_time_to_seconds, parse_distance_to_meters
from util.constants import clean_school_name, CLASS_MAP

DB_PATH = Path(__file__).parent.parent / "ncaa_history.db"
CACHE_DIR = Path(__file__).parent.parent / "flashresults" / "2026"
BASE_URL = "https://flashresults.ncaa.com/Indoor/2026/"

YEAR = 2026
LOCATION = "Fayetteville, AR"
ENVIRONMENT = "indoor"

APPROVED_NEW_SCHOOLS = {'East Texas A&M', 'UT-Rio Grande Valley'}

DATE_MAP = {
    'Friday': 'Friday, March 13',
    'Saturday': 'Saturday, March 14',
}


def extract_meet_end_date(soup):
    navbar = soup.find('p', class_='navbar-text')
    if not navbar:
        return None
    text = navbar.get_text()
    m = re.search(r'([A-Z][a-z]+)\s+(\d+)-(\d+),\s+(\d{4})', text)
    if m:
        month = m.group(1)
        day = m.group(3)
        year = m.group(4)
        weekday = calendar.day_name[calendar.weekday(int(year), list(calendar.month_abbr).index(month[:3]), int(day))]
        return f'{weekday}, {month} {day}'
    return None

EVENTS = [
    {'code': '001-2', 'file': '001-2_compiled.htm', 'discipline': '60m', 'gender': 'men', 'type': 'track'},
    {'code': '017-2', 'file': '017-2_compiled.htm', 'discipline': '60m', 'gender': 'women', 'type': 'track'},
    {'code': '002-2', 'file': '002-2_compiled.htm', 'discipline': '200m', 'gender': 'men', 'type': 'track'},
    {'code': '018-2', 'file': '018-2_compiled.htm', 'discipline': '200m', 'gender': 'women', 'type': 'track'},
    {'code': '003-2', 'file': '003-2_compiled.htm', 'discipline': '400m', 'gender': 'men', 'type': 'track'},
    {'code': '019-2', 'file': '019-2_compiled.htm', 'discipline': '400m', 'gender': 'women', 'type': 'track'},
    {'code': '004-2', 'file': '004-2_compiled.htm', 'discipline': '800m', 'gender': 'men', 'type': 'track'},
    {'code': '020-2', 'file': '020-2_compiled.htm', 'discipline': '800m', 'gender': 'women', 'type': 'track'},
    {'code': '005-2', 'file': '005-2_compiled.htm', 'discipline': 'Mile', 'gender': 'men', 'type': 'track'},
    {'code': '021-2', 'file': '021-2_compiled.htm', 'discipline': 'Mile', 'gender': 'women', 'type': 'track'},
    {'code': '006-1', 'file': '006-1_compiled.htm', 'discipline': '3000m', 'gender': 'men', 'type': 'track'},
    {'code': '022-1', 'file': '022-1_compiled.htm', 'discipline': '3000m', 'gender': 'women', 'type': 'track'},
    {'code': '007-1', 'file': '007-1_compiled.htm', 'discipline': '5000m', 'gender': 'men', 'type': 'track'},
    {'code': '023-1', 'file': '023-1_compiled.htm', 'discipline': '5000m', 'gender': 'women', 'type': 'track'},
    {'code': '008-2', 'file': '008-2_compiled.htm', 'discipline': '60m Hurdles', 'gender': 'men', 'type': 'track'},
    {'code': '024-2', 'file': '024-2_compiled.htm', 'discipline': '60m Hurdles', 'gender': 'women', 'type': 'track'},
    {'code': '009-1', 'file': '009-1_compiled.htm', 'discipline': '4x400m Relay', 'gender': 'men', 'type': 'relay'},
    {'code': '025-1', 'file': '025-1_compiled.htm', 'discipline': '4x400m Relay', 'gender': 'women', 'type': 'relay'},
    {'code': '010-1', 'file': '010-1_compiled.htm', 'discipline': 'DMR', 'gender': 'men', 'type': 'relay'},
    {'code': '026-1', 'file': '026-1_compiled.htm', 'discipline': 'DMR', 'gender': 'women', 'type': 'relay'},
    {'code': '015-1', 'file': '015-1_compiled.htm', 'discipline': 'Shot Put', 'gender': 'men', 'type': 'field'},
    {'code': '031-1', 'file': '031-1_compiled.htm', 'discipline': 'Shot Put', 'gender': 'women', 'type': 'field'},
    {'code': '011-1', 'file': '011-1_compiled.htm', 'discipline': 'High Jump', 'gender': 'men', 'type': 'field'},
    {'code': '027-1', 'file': '027-1_compiled.htm', 'discipline': 'High Jump', 'gender': 'women', 'type': 'field'},
    {'code': '013-1', 'file': '013-1_compiled.htm', 'discipline': 'Long Jump', 'gender': 'men', 'type': 'field'},
    {'code': '029-1', 'file': '029-1_compiled.htm', 'discipline': 'Long Jump', 'gender': 'women', 'type': 'field'},
    {'code': '014-1', 'file': '014-1_compiled.htm', 'discipline': 'Triple Jump', 'gender': 'men', 'type': 'field'},
    {'code': '030-1', 'file': '030-1_compiled.htm', 'discipline': 'Triple Jump', 'gender': 'women', 'type': 'field'},
    {'code': '012-1', 'file': '012-1_compiled.htm', 'discipline': 'Pole Vault', 'gender': 'men', 'type': 'field'},
    {'code': '028-1', 'file': '028-1_compiled.htm', 'discipline': 'Pole Vault', 'gender': 'women', 'type': 'field'},
    {'code': '016-1', 'file': '016-1_compiled.htm', 'discipline': 'Weight Throw', 'gender': 'men', 'type': 'field'},
    {'code': '032-1', 'file': '032-1_compiled.htm', 'discipline': 'Weight Throw', 'gender': 'women', 'type': 'field'},
    {'code': '033_Scores', 'file': '033_Scores.htm', 'discipline': 'Heptathlon', 'gender': 'men', 'type': 'multi'},
    {'code': '034_Scores', 'file': '034_Scores.htm', 'discipline': 'Pentathlon', 'gender': 'women', 'type': 'multi'},
]


def download_page(filename: str) -> Path:
    cache_path = CACHE_DIR / filename
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path
    url = BASE_URL + filename
    print(f"  Downloading {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(resp.content)
    return cache_path


def extract_date(soup):
    header = soup.find('table', id='headerevent')
    if not header:
        return None
    for tr in header.find_all('tr'):
        text = tr.get_text()
        for day, date in DATE_MAP.items():
            if day in text:
                return date
    return None


def parse_athlete_cell(td):
    a = td.find('a', class_='openStats')
    if a:
        name = fix_name_casing(a.get_text(strip=True))
    else:
        b = td.find('b')
        name = fix_name_casing(b.get_text(strip=True)) if b else ''

    school = ''
    athlete_class = None
    small = td.find('small')
    if small:
        text = small.get_text(strip=True).replace('\xa0', ' ').strip()
        m = re.search(r'(.+?)\s*\[([A-Z]+)\]', text)
        if m:
            school = m.group(1).strip()
            athlete_class = CLASS_MAP.get(m.group(2))
        else:
            school = text
    return name, school, athlete_class


def parse_team_cell(td):
    small = td.find('small')
    if small:
        return small.get_text(strip=True).replace('\xa0', ' ').strip()
    return ''


def parse_individual(filepath, discipline, gender, event_type):
    results = []
    html = filepath.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    date = extract_date(soup)

    table = soup.find('table', id='events')
    if not table:
        return results

    tbody = table.find('tbody')
    if not tbody:
        return results

    for tr in tbody.find_all('tr'):
        tds = tr.find_all('td', recursive=False)
        if len(tds) < 4:
            continue

        place_str = tds[0].get_text(strip=True)
        if not place_str:
            continue
        try:
            place = int(place_str)
        except ValueError:
            continue
        if place > 8:
            continue

        name, school, athlete_class = parse_athlete_cell(tds[2])

        mark_raw = tds[3].get_text(strip=True)
        if event_type == 'field':
            m = re.match(r'([\d.]+m)', mark_raw)
            if not m:
                continue
            mark_str = m.group(1)
            mark_num = parse_distance_to_meters(mark_str)
        else:
            m = re.match(r'([\d:.]+)', mark_raw)
            mark_str = m.group(1) if m else mark_raw
            mark_num = parse_time_to_seconds(mark_str)

        school = clean_school_name(school, YEAR)

        results.append({
            'year': YEAR, 'date': date, 'name': name, 'school': school,
            'discipline': discipline, 'gender': gender,
            'mark_num': mark_num, 'mark_str': mark_str,
            'class': athlete_class, 'place': place,
            'is_dq': 0, 'is_dnf': 0, 'is_dns': 0,
            'is_relay': 0, 'leg_idx': None, 'split_time': None,
            'location': LOCATION, 'environment': ENVIRONMENT,
            'is_converted': 0, 'source_url': BASE_URL + filepath.name,
        })

    return results


def parse_relay(code, filepath, discipline, gender):
    results = []
    html = filepath.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    date = extract_date(soup)

    section_pages = set()
    for a in soup.find_all('a', href=True):
        if re.match(rf'{re.escape(code)}-\d+\.htm$', a['href']):
            section_pages.add(a['href'])
    section_pages = sorted(section_pages)

    table = soup.find('table', id='events')
    if not table:
        return results

    compiled = {}
    tbody = table.find('tbody')
    if not tbody:
        return results

    for tr in tbody.find_all('tr'):
        tds = tr.find_all('td', recursive=False)
        if len(tds) < 4:
            continue

        place_str = tds[0].get_text(strip=True)
        if not place_str:
            continue
        try:
            place = int(place_str)
        except ValueError:
            continue
        if place > 8:
            continue

        school = parse_team_cell(tds[2])
        school = clean_school_name(school, YEAR)

        time_raw = tds[3].get_text(strip=True)
        m = re.match(r'([\d:.]+)', time_raw)
        mark_str = m.group(1) if m else time_raw
        mark_num = parse_time_to_seconds(mark_str)

        compiled[school] = {'place': place, 'mark_str': mark_str, 'mark_num': mark_num}

    splits_by_school = {}
    athletes_by_school = {}

    for sp in section_pages:
        sp_path = download_page(sp)
        sp_html = sp_path.read_text(encoding='utf-8')
        sp_soup = BeautifulSoup(sp_html, 'html.parser')

        splits_table = sp_soup.find('table', id='splits')
        if splits_table:
            for tr in splits_table.find_all('tr'):
                tds = tr.find_all('td', recursive=False)
                if len(tds) < 6:
                    continue

                pl = tds[0].get_text(strip=True)
                if not pl or pl == 'DQ':
                    continue

                school = parse_team_cell(tds[3])
                school = clean_school_name(school, YEAR)

                splits = []
                for td in tds[5:9]:
                    bracket = re.search(r'\[([^\]]+)\]', td.get_text())
                    if bracket:
                        splits.append(bracket.group(1))

                if school not in splits_by_school:
                    splits_by_school[school] = splits

        for tbl in sp_soup.find_all('table'):
            thead = tbl.find('thead', class_='thead-dark')
            if not thead:
                continue
            th_texts = [th.get_text(strip=True) for th in thead.find_all('th')]
            if len(th_texts) < 2 or th_texts[0] != 'Team' or th_texts[1] != 'Athletes':
                continue
            tbl_body = tbl.find('tbody')
            if not tbl_body:
                continue
            for row in tbl_body.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                team = cells[0].get_text(strip=True)
                team = clean_school_name(team, YEAR)
                names_text = cells[1].get_text(strip=True)
                names = [fix_name_casing(n.strip()) for n in names_text.split(',') if n.strip()]
                athletes_by_school[team] = names

    for school, info in compiled.items():
        team_splits = splits_by_school.get(school, [])
        team_athletes = athletes_by_school.get(school, [])

        if not team_athletes:
            for leg in range(1, 5):
                results.append({
                    'year': YEAR, 'date': date, 'name': 'Relay member unknown',
                    'school': school, 'discipline': discipline, 'gender': gender,
                    'mark_num': info['mark_num'], 'mark_str': info['mark_str'],
                    'class': None, 'place': info['place'],
                    'is_dq': 0, 'is_dnf': 0, 'is_dns': 0,
                    'is_relay': 1, 'leg_idx': leg,
                    'split_time': team_splits[leg - 1] if leg - 1 < len(team_splits) else None,
                    'location': LOCATION, 'environment': ENVIRONMENT,
                    'is_converted': 0, 'source_url': BASE_URL + filepath.name,
                })
        else:
            for idx, athlete_name in enumerate(team_athletes):
                results.append({
                    'year': YEAR, 'date': date, 'name': athlete_name,
                    'school': school, 'discipline': discipline, 'gender': gender,
                    'mark_num': info['mark_num'], 'mark_str': info['mark_str'],
                    'class': None, 'place': info['place'],
                    'is_dq': 0, 'is_dnf': 0, 'is_dns': 0,
                    'is_relay': 1, 'leg_idx': idx + 1,
                    'split_time': team_splits[idx] if idx < len(team_splits) else None,
                    'location': LOCATION, 'environment': ENVIRONMENT,
                    'is_converted': 0, 'source_url': BASE_URL + filepath.name,
                })

    return results


def parse_multi(filepath, discipline, gender):
    results = []
    html = filepath.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    date = extract_date(soup) or extract_meet_end_date(soup)

    table = soup.find('table', id='multitotalscores')
    if not table:
        return results

    tbody = table.find('tbody')
    if not tbody:
        return results

    for tr in tbody.find_all('tr'):
        tds = tr.find_all('td', recursive=False)
        if len(tds) < 4:
            continue

        place_str = tds[0].get_text(strip=True)
        if not place_str or place_str in ('DNF', 'DNS', 'DQ', 'NH'):
            continue
        try:
            place = int(place_str)
        except ValueError:
            continue
        if place > 8:
            continue

        a = tds[2].find('a', class_='openStats')
        if a:
            name = fix_name_casing(a.get_text(strip=True))
        else:
            b = tds[2].find('b')
            name = fix_name_casing(b.get_text(strip=True)) if b else ''

        full_text = tds[2].get_text(separator='\n', strip=True)
        school = ''
        athlete_class = None
        for line in full_text.split('\n'):
            m = re.search(r'(.+?)\s*\[([A-Z]+)\]', line)
            if m:
                school = m.group(1).strip()
                athlete_class = CLASS_MAP.get(m.group(2))
                break

        if not school:
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            if len(lines) >= 2:
                school = lines[1]

        points_text = tds[3].get_text(strip=True)
        pm = re.match(r'(\d+)', points_text)
        if not pm:
            continue
        mark_num = float(pm.group(1))
        mark_str = pm.group(1)

        school = clean_school_name(school, YEAR)

        results.append({
            'year': YEAR, 'date': date, 'name': name, 'school': school,
            'discipline': discipline, 'gender': gender,
            'mark_num': mark_num, 'mark_str': mark_str,
            'class': athlete_class, 'place': place,
            'is_dq': 0, 'is_dnf': 0, 'is_dns': 0,
            'is_relay': 0, 'leg_idx': None, 'split_time': None,
            'location': LOCATION, 'environment': ENVIRONMENT,
            'is_converted': 0, 'source_url': BASE_URL + filepath.name,
        })

    return results


def validate_schools(schools, conn):
    c = conn.cursor()
    c.execute("SELECT DISTINCT school FROM results WHERE school IS NOT NULL")
    db_schools = {row[0] for row in c.fetchall()}

    unknown = set()
    for school in schools:
        if school in db_schools or school in APPROVED_NEW_SCHOOLS:
            continue
        unknown.add(school)

    if unknown:
        print("ERROR: Unknown schools not in DB or APPROVED_NEW_SCHOOLS:")
        for s in sorted(unknown):
            print(f"  '{s}'")
        sys.exit(1)


def insert_results(conn, results):
    c = conn.cursor()
    for r in results:
        c.execute('''
            INSERT INTO results (
                year, date, name, school, discipline, gender,
                mark_num, mark_str, class, place,
                is_dq, is_dnf, is_dns, is_relay, leg_idx,
                split_time, location, environment, is_converted, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            r['year'], r['date'], r['name'], r['school'], r['discipline'], r['gender'],
            r['mark_num'], r['mark_str'], r['class'], r['place'],
            r['is_dq'], r['is_dnf'], r['is_dns'], r['is_relay'], r['leg_idx'],
            r['split_time'], r['location'], r['environment'], r['is_converted'], r['source_url'],
        ))
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    all_schools = set()

    for ev in EVENTS:
        print(f"Parsing {ev['discipline']} ({ev['gender']})...")
        filepath = download_page(ev['file'])

        if ev['type'] in ('track', 'field'):
            results = parse_individual(filepath, ev['discipline'], ev['gender'], ev['type'])
        elif ev['type'] == 'relay':
            results = parse_relay(ev['code'], filepath, ev['discipline'], ev['gender'])
        elif ev['type'] == 'multi':
            results = parse_multi(filepath, ev['discipline'], ev['gender'])
        else:
            continue

        for r in results:
            if r['school']:
                all_schools.add(r['school'])

        print(f"  {len(results)} results")
        all_results.extend(results)

    validate_schools(all_schools, conn)
    insert_results(conn, all_results)
    conn.close()

    print(f"\nDone! Inserted {len(all_results)} results from FlashResults 2026.")


if __name__ == '__main__':
    main()
