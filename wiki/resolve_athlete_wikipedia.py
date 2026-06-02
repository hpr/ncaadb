#!/usr/bin/env python3
"""
For each athlete profile, find matching Wikipedia articles by checking aliases
against pages in the Category:Track and field athletes and
Category:Players of American football category trees (via PetScan),
including disambiguated pages found via OpenSearch.

Output: wiki/athlete_wikipedia.json
"""

import json
import re
import sqlite3
import sys
import time
import unicodedata
from pathlib import Path

import requests
import argparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES_PATH = PROJECT_ROOT / "data" / "profiles.json"
DB_PATH = PROJECT_ROOT / "ncaa_history.db"
OUTPUT_DIR = Path(__file__).resolve().parent
CATEGORY_CACHE_PATH = OUTPUT_DIR / "category_cache.json"
OUTPUT_PATH = OUTPUT_DIR / "athlete_wikipedia.json"

PETSCAN_URL = "https://petscan.wmcloud.org/"
ENWIKI_API = "https://en.wikipedia.org/w/api.php"

CATEGORIES = {
    "track_and_field": "Track and field athletes",
    # "american_football": "Players of American football",
}
PETSCAN_DEPTH = 10

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": f"NCAAdbBot/1.0 (https://habs.sdf.org/ncaadb; habs@sdf.org) requests/{requests.__version__}",
})

MAX_RETRIES = 5
BASE_DELAY = 0


class RateLimitError(Exception):
    pass


def api_get(url: str, params: dict, timeout: int = 15) -> requests.Response:
    for attempt in range(MAX_RETRIES):
        resp = SESSION.get(url, params=params, timeout=timeout)
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                wait = float(retry_after)
            else:
                wait = BASE_DELAY * (2 ** attempt)
            print(f"      429 rate limited, waiting {wait:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    raise RateLimitError(f"429 rate limit exceeded after {MAX_RETRIES} retries for {url}")


def strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def normalize_title(title: str) -> str:
    return title.replace("_", " ").strip()


def fetch_petscan_category(category: str, depth: int) -> set[str]:
    params = {
        "format": "json",
        "depth": depth,
        "categories": category,
        "combination": "subset",
        "ns[0]": "1",
        "project": "wikipedia",
        "language": "en",
        "interface_language": "en",
        "doit": "",
    }
    print(f"  Fetching PetScan: Category:{category} (depth={depth})...")
    resp = SESSION.get(PETSCAN_URL, params=params, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("*", [{}])[0].get("a", {}).get("*", [])
    result = {normalize_title(i["title"]) for i in items if isinstance(i, dict) and "title" in i}
    if not result:
        raw_titles = [i for i in items if isinstance(i, str)]
        result = {normalize_title(t) for t in raw_titles}
    print(f"    Got {len(result)} pages")
    return result


def load_category_sets() -> dict[str, set[str]]:
    if CATEGORY_CACHE_PATH.exists():
        print(f"Loading cached category sets from {CATEGORY_CACHE_PATH}")
        with open(CATEGORY_CACHE_PATH) as f:
            cache = json.load(f)
        sets = {}
        for key, titles in cache.items():
            sets[key] = set(titles)
            print(f"  {key}: {len(sets[key])} pages")
        if set(sets.keys()) == set(CATEGORIES.keys()):
            return sets
        print("  Cache incomplete, re-fetching missing categories")

    sets = {}
    for key, category in CATEGORIES.items():
        sets[key] = fetch_petscan_category(category, PETSCAN_DEPTH)
        cache_data = {k: sorted(v) for k, v in sets.items()}
        with open(CATEGORY_CACHE_PATH, "w") as f:
            json.dump(cache_data, f)
        time.sleep(1)

    return sets


def build_candidate_names(aliases: list[str]) -> list[str]:
    seen = set()
    candidates = []
    for name in aliases:
        for variant in (name, strip_diacritics(name)):
            if variant not in seen:
                seen.add(variant)
                candidates.append(variant)
    return candidates


def disambig_search(name: str) -> list[str]:
    titles = []
    apfrom = None
    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apprefix": f"{name} (",
            "apnamespace": "0",
            "aplimit": "500",
            "format": "json",
        }
        if apfrom is not None:
            params["apfrom"] = apfrom
        try:
            resp = api_get(ENWIKI_API, params=params)
            data = resp.json()
            for page in data.get("query", {}).get("allpages", []):
                titles.append(page["title"])
            if "continue" not in data:
                break
            apfrom = data["continue"]["apcontinue"]
        except Exception as e:
            print(f"    allpages error for '{name}': {e}")
            break
    return titles


def classify_title(title: str, cat_sets: dict[str, set[str]]) -> list[str]:
    cats = []
    for key, titles in cat_sets.items():
        if title in titles:
            cats.append(key)
    return cats


def fetch_page_categories(title: str) -> tuple[list[str], str | None, str | None]:
    params = {
        "action": "query",
        "titles": title,
        "prop": "categories|pageprops",
        "cllimit": "500",
        "ppprop": "wikibase_item",
        "redirects": "1",
        "format": "json",
    }
    try:
        resp = api_get(ENWIKI_API, params=params)
        data = resp.json()
        redirects = data.get("query", {}).get("redirects", [])
        redirect_target = redirects[-1]["to"] if redirects else None
        pages = data.get("query", {}).get("pages", {})
        cats = []
        qid = None
        for page in pages.values():
            for cat in page.get("categories", []):
                cats.append(cat["title"])
            pp = page.get("pageprops", {})
            if "wikibase_item" in pp:
                qid = pp["wikibase_item"]
        return cats, redirect_target, qid
    except Exception as e:
        print(f"    categories error for '{title}': {e}")
        return [], None, None


def load_school_categories() -> dict[str, dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT name, men_nickname, women_nickname, category_enwiki FROM schools "
        "WHERE category_enwiki IS NOT NULL"
    )
    result = {}
    for name, men_nick, women_nick, cat in cur.fetchall():
        result[name] = {
            "men_nickname": men_nick,
            "women_nickname": women_nick,
            "category": cat,
        }
    conn.close()
    return result


def build_expected_categories(schools: list[str], gender: str, school_cats: dict[str, dict]) -> set[str]:
    expected = set()
    for school in schools:
        info = school_cats.get(school)
        if not info:
            continue
        cat = info["category"]
        men_nick = info["men_nickname"]
        women_nick = info["women_nickname"]
        if men_nick and women_nick and men_nick != women_nick:
            if gender == "men":
                cat = cat.replace(f" and {women_nick}", "")
            else:
                cat = cat.replace(f"{men_nick} and ", "")
            expected.add(f"{cat} track and field athletes")
        else:
            gender_label = "men's" if gender == "men" else "women's"
            expected.add(f"{cat} {gender_label} track and field athletes")
    return expected


def find_matches_for_profile(
    profile: dict,
    cat_sets: dict[str, set[str]],
    all_titles: set[str],
    school_cats: dict[str, dict],
    disciplines_map: dict[int, list[str]],
) -> dict:
    athlete_id = profile["athlete_id"]
    canonical = profile["canonical_name"]
    aliases = list(set(profile["aliases"]))

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
    expected_cats = build_expected_categories(sorted(schools), gender, school_cats)

    candidates = build_candidate_names(aliases)

    found = {}
    for name in candidates:
        cats = classify_title(name, cat_sets)
        if cats and name not in found:
            found[name] = {
                "enwiki": name,
                "source": "exact",
                "categories": cats,
            }
        elif name not in found:
            found[name] = {
                "enwiki": name,
                "source": "exact",
                "categories": [],
            }

        disambig_titles = disambig_search(name)
        for dt in disambig_titles:
            dt_norm = normalize_title(dt)
            cats = classify_title(dt_norm, cat_sets)
            if dt_norm not in found:
                found[dt_norm] = {
                    "enwiki": dt_norm,
                    "source": "disambig",
                    "categories": cats,
                }

        time.sleep(0.1)

    matches = list(found.values())

    for match in matches:
        page_cats, redirect_target, qid = fetch_page_categories(match["enwiki"])
        matched_cats = [c for c in page_cats if any(
            c.lower() == ec.lower() for ec in expected_cats
        )]
        match["existing_school_categories"] = matched_cats
        if qid:
            match["qid"] = qid
        if redirect_target:
            match["redirects_to"] = redirect_target
            if not match["categories"]:
                match["categories"] = classify_title(redirect_target, cat_sets)
        time.sleep(0.1)

    matches = [m for m in matches if m["categories"] or m["existing_school_categories"]]

    by_target = {}
    for match in matches:
        key = match.get("redirects_to", match["enwiki"])
        if "redirects_to" in match:
            match["enwiki"] = match["redirects_to"]
        if key not in by_target:
            by_target[key] = match
        else:
            existing = by_target[key]
            if match["source"] == "exact":
                existing["source"] = "exact"
            existing["categories"] = sorted(set(existing["categories"] + match["categories"]))
            existing["existing_school_categories"] = sorted(
                set(existing.get("existing_school_categories", []) + match.get("existing_school_categories", []))
            )
            if "redirects_to" in match:
                existing["redirects_to"] = match["redirects_to"]
    matches = list(by_target.values())

    needs_review = len(matches) > 1

    return {
        "athlete_id": athlete_id,
        "canonical_name": canonical,
        "aliases": profile["aliases"],
        "gender": gender,
        "schools": sorted(schools),
        "disciplines": disciplines_map.get(athlete_id, []),
        "start_year": start_year,
        "end_year": end_year,
        "matches": matches,
        "needs_review": needs_review,
    }


def load_school_nicknames() -> dict[str, str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT name, men_nickname, women_nickname FROM schools")
    result = {}
    for name, men, women in cur.fetchall():
        nicknames = [n for n in (men, women) if n]
        if nicknames:
            result[name] = nicknames[0]
        else:
            result[name] = name
    conn.close()
    return result


def format_schools(profile: dict, nicknames: dict[str, str]) -> str:
    seen = set()
    parts = []
    for m in profile["members"]:
        school = m["school"]
        if school in seen:
            continue
        seen.add(school)
        nick = nicknames.get(school, school)
        parts.append(f"{school} {nick}" if nick != school else school)
    return ", ".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reverse", action="store_true", help="Process profiles in reverse order (Z to A)")
    args = parser.parse_args()

    cat_sets = load_category_sets()
    all_titles = set()
    for s in cat_sets.values():
        all_titles |= s
    print(f"Total unique category pages: {len(all_titles)}")

    nicknames = load_school_nicknames()
    school_cats = load_school_categories()
    print(f"Loaded {len(nicknames)} school nicknames, {len(school_cats)} school categories")

    conn = sqlite3.connect(DB_PATH)
    disciplines_map = {}
    for aid, disc in conn.execute("SELECT athlete_id, GROUP_CONCAT(DISTINCT discipline) FROM results GROUP BY athlete_id").fetchall():
        disciplines_map[aid] = sorted(disc.split(","))
    conn.close()
    print(f"Loaded disciplines for {len(disciplines_map)} athletes")

    with open(PROFILES_PATH) as f:
        profiles = json.load(f)

    valid_ids = set(disciplines_map.keys())
    profiles = [p for p in profiles if p["athlete_id"] in valid_ids]
    print(f"Loaded {len(profiles)} profiles (with top-8 results)")

    if args.reverse:
        profiles.reverse()

    results = []
    processed_ids = set()
    review_count = 0
    match_count = 0

    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            results = json.load(f)
        for r in results:
            processed_ids.add(r["athlete_id"])
        match_count = sum(1 for r in results if r["matches"])
        review_count = sum(1 for r in results if r["needs_review"])
        print(f"Resuming from {len(results)} already processed profiles")

    remaining = sum(1 for p in profiles if p["athlete_id"] not in processed_ids)
    processed_this_run = 0
    run_start = time.time()

    for i, profile in enumerate(profiles):
        if profile["athlete_id"] in processed_ids:
            continue

        processed_this_run += 1
        if processed_this_run > 1 and processed_this_run % 100 == 0:
            elapsed = time.time() - run_start
            rate = processed_this_run / elapsed
            eta_left = (remaining - processed_this_run) / rate
            h, m = int(eta_left // 3600), int(eta_left % 3600 // 60)
            print(f"  --- {processed_this_run}/{remaining} processed, ~{h}h{m:02d}m remaining ---")

        canonical = profile["canonical_name"]
        schools_str = format_schools(profile, nicknames)
        print(f"  [{len(results)+1}/{len(profiles)}] {canonical} ({schools_str})...", end=" ", flush=True)

        try:
            result = find_matches_for_profile(profile, cat_sets, all_titles, school_cats, disciplines_map)
        except RateLimitError as e:
            print(f"\n    ERROR: {e}")
            print(f"    Skipping save — will retry on next run")
            break

        results.append(result)

        n_matches = len(result["matches"])
        if n_matches > 0:
            match_count += 1
        if result["needs_review"]:
            review_count += 1

        if n_matches == 0:
            print("0 matches")
        else:
            urls = ", ".join(
                f"https://en.wikipedia.org/wiki/{m['enwiki'].replace(' ', '_')}"
                for m in result["matches"]
            )
            print(f"{n_matches} match{'es' if n_matches != 1 else ''}: {urls}")

        with open(OUTPUT_PATH, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone!")
    print(f"  Profiles:          {len(profiles)}")
    print(f"  With matches:      {match_count}")
    print(f"  Needs review:      {review_count}")
    print(f"  No match:          {len(profiles) - match_count}")
    print(f"  Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
