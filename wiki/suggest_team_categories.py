#!/usr/bin/env python3
"""
Read wiki/athlete_wikipedia.json and suggest Wikipedia team categories
to add to matched athlete pages.

For each athlete with matches, looks up their school(s) and constructs
the appropriate team category name based on gender.

Output: printed lines like:
  Name (evt, years): <Wiki URL(s)>, <team category to add>
"""

import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "ncaa_history.db"
WIKI_DIR = Path(__file__).resolve().parent
WIKI_RESULTS_PATH = WIKI_DIR / "athlete_wikipedia.json"
REVIEWED_PATH = WIKI_DIR / "reviewed_wiki_matches.tsv"

ENWIKI_BASE = "https://en.wikipedia.org/wiki/"


def load_reviewed():
    reviewed = set()
    if not REVIEWED_PATH.exists():
        return reviewed
    with open(REVIEWED_PATH) as f:
        header = f.readline()
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                reviewed.add((parts[0], parts[1]))
    return reviewed


def main():
    with open(WIKI_RESULTS_PATH) as f:
        wiki_results = json.load(f)
    reviewed = load_reviewed()

    matched = [r for r in wiki_results if r["matches"]]
    skipped = 0
    skipped_reviewed = 0
    print(f" {len(matched)} athletes with Wikipedia matches ({len(reviewed)} reviewed pairs)\n")

    conn = sqlite3.connect(DB_PATH)

    cur = conn.execute(
        "SELECT name, men_nickname, women_nickname, category_enwiki FROM schools "
        "WHERE category_enwiki IS NOT NULL"
    )
    school_cats = {}
    for name, men_nick, women_nick, cat in cur.fetchall():
        school_cats[name] = {
            "men_nickname": men_nick,
            "women_nickname": women_nick,
            "category": cat,
        }

    conn.close()

    for entry in matched:
        aid = entry["athlete_id"]
        gender = entry.get("gender")
        disciplines = entry.get("disciplines", [])
        schools = entry.get("schools", [])
        start_year = entry.get("start_year")
        end_year = entry.get("end_year")

        if not gender or not schools:
            continue

        evt_str = ", ".join(disciplines)
        years = str(start_year) if start_year else ""
        if start_year and end_year and start_year != end_year:
            years = f"{start_year}\u2013{end_year}"

        unreviewed = [m for m in entry["matches"] if (entry["canonical_name"], m["enwiki"]) not in reviewed]
        if not unreviewed:
            skipped_reviewed += 1
            continue

        urls = ", ".join(
            ENWIKI_BASE + m["enwiki"].replace(" ", "_")
            for m in unreviewed
        )

        cat_names = []
        for school in schools:
            info = school_cats.get(school)
            if not info:
                continue
            cat = info["category"]
            men_nick = info["men_nickname"]
            women_nick = info["women_nickname"]
            gender_label = "men's" if gender == "men" else "women's"

            if men_nick and women_nick and men_nick != women_nick:
                if gender == "men":
                    cat = cat.replace(f" and {women_nick}", "")
                else:
                    cat = cat.replace(f"{men_nick} and ", "")
                cat += " track and field athletes"
                cat_names.append((cat, True))
            else:
                cat += f" {gender_label} track and field athletes"
                cat_names.append((cat, False))

        if not cat_names:
            continue

        expected = {c.lower() for c, _ in cat_names}

        skip = False
        for m in unreviewed:
            page_cats = {ec.lower() for ec in m.get("existing_school_categories", [])}
            if expected.issubset(page_cats):
                skip = True
                break

        if skip:
            skipped += 1
            continue

        last_name = entry["canonical_name"].rsplit(" ", 1)[-1]

        print(f"{entry['canonical_name']} ({evt_str}, {years}): {urls}")
        for cat, has_gender_nick in cat_names:
            cat_no_prefix = cat.replace("Category:", "")
            if has_gender_nick:
                team_wiki = cat_no_prefix.replace(" track and field athletes", " track and field")
            else:
                team_wiki = cat_no_prefix.replace(" track and field athletes", "").replace(f" {gender_label}", "") + " track and field"
            print(f"[[:{cat}]]")
            print(f"<pre><nowiki>{last_name} competed for the [[{team_wiki}]] team in the [[NCAA]].<ref>{{{{cite web|url=|title=|website=}}}}</ref></nowiki></pre>")
        print()

    print(f" {skipped} athletes skipped (already have team category)")
    print(f" {skipped_reviewed} athletes skipped (all matches already reviewed)")


if __name__ == "__main__":
    main()
