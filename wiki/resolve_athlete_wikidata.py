#!/usr/bin/env python3
"""
Read wiki/athlete_wikipedia.json and extract Wikidata QIDs for athlete profiles
that have unambiguous school-category matches.

For each profile, finds the single Wikipedia page with all expected school team
categories and extracts its QID. Outputs a flat map keyed by stable profile
identity (survives DB regenerations that shift athlete_ids).

Output:
  wiki/athlete_wikidata.json        - { "stable_key": "Q12345", ... }
  wiki/athlete_wikidata_errors.json - ambiguous cases for manual review
"""

import json
import re
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = Path(__file__).resolve().parent
INPUT_PATH = WIKI_DIR / "athlete_wikipedia.json"
OUTPUT_PATH = WIKI_DIR / "athlete_wikidata.json"
ERRORS_PATH = WIKI_DIR / "athlete_wikidata_errors.json"


def normalize_page(title: str) -> str:
    return re.sub(r'\s+', ' ', unicodedata.normalize("NFC", title)).strip()


def make_stable_key(entry: dict) -> str:
    canonical = entry["canonical_name"]
    schools = ";".join(sorted(entry.get("schools", [])))
    gender = entry.get("gender", "")
    start = entry.get("start_year", "")
    end = entry.get("end_year", "")
    return f"{canonical}|{schools}|{gender}|{start}|{end}"


def main():
    with open(INPUT_PATH) as f:
        data = json.load(f)

    print(f"Loaded {len(data)} entries from {INPUT_PATH.name}")

    resolved = {}
    errors = []
    no_match = 0
    no_qid = 0

    for entry in data:
        stable_key = make_stable_key(entry)
        matches = entry.get("matches", [])

        school_cat_matches = [m for m in matches if m.get("existing_school_categories")]

        if not school_cat_matches:
            no_match += 1
            continue

        by_page = {}
        for m in school_cat_matches:
            page = normalize_page(m.get("redirects_to", m["enwiki"]))
            qid = m.get("qid")
            if page not in by_page:
                by_page[page] = {"match": m, "qid": qid}
            else:
                if not by_page[page]["qid"] and qid:
                    by_page[page]["qid"] = qid

        if len(by_page) == 1:
            page, info = next(iter(by_page.items()))
            qid = info["qid"]
            if qid:
                resolved[stable_key] = qid
            else:
                no_qid += 1
        else:
            pages = {page: info["qid"] for page, info in by_page.items()}
            errors.append({
                "stable_key": stable_key,
                "canonical_name": entry["canonical_name"],
                "schools": entry.get("schools", []),
                "gender": entry.get("gender"),
                "pages": pages,
            })

    with open(OUTPUT_PATH, "w") as f:
        json.dump(resolved, f, indent=2, ensure_ascii=False)

    with open(ERRORS_PATH, "w") as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)

    print(f"Resolved: {len(resolved)}")
    print(f"No school-cat match: {no_match}")
    print(f"Has school-cat but no QID: {no_qid}")
    print(f"Ambiguous (multiple pages): {len(errors)}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Errors: {ERRORS_PATH}")


if __name__ == "__main__":
    main()
