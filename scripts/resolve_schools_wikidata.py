#!/usr/bin/env python3
"""
Resolve school names to Wikidata entities using SPARQL for exact label matching,
filtering for matches that have an athletics program (P10607) property.

Output: data/schools_wikidata.json with structure:
{
  "resolved": { "School Name": { "qid": "Q1234", "label": "...", "description": "...", "athletics_qid": "Q...", "nicknames": [...] }, ... },
  "ambiguous": { "School Name": [ { "qid": "Q1234", ... }, ... ], ... },
  "no_athletics": ["School Name", ...],
  "not_found": ["School Name", ...]
}
"""

import json
import sqlite3
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "ncaa_history.db"
OUTPUT_PATH = PROJECT_ROOT / "data" / "schools_wikidata.json"

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

P_ATHLETICS = "P10607"
P_NICKNAME = "P1449"
P_USED_BY = "P1535"
P_MAIN_CATEGORY = "P910"
Q_MENS_SPORTS = "Q22808963"
Q_WOMENS_SPORTS = "Q61740358"
Q_WOMENS_BASKETBALL = "Q60336621"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": f"NCAAdbBot/1.0 (https://habs.sdf.org/ncaadb; habs@sdf.org) requests/{requests.__version__}",
    "Accept": "application/sparql-results+json",
})


def sparql_exact_with_p10607(label: str) -> list[dict]:
    escaped = label.replace('\\', '\\\\').replace('"', '\\"')
    query = f"""SELECT ?item ?itemLabel ?itemDescription WHERE {{
  VALUES ?labelProp {{ rdfs:label skos:altLabel }}
  {{ ?item ?labelProp "{escaped}"@en . }} UNION {{ ?item ?labelProp "{escaped}"@mul . }}
  ?item wdt:{P_ATHLETICS} ?ath .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}"""
    resp = SESSION.get(SPARQL_ENDPOINT, params={"query": query}, timeout=60)
    resp.raise_for_status()
    seen = set()
    results = []
    for binding in resp.json().get("results", {}).get("bindings", []):
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        if qid in seen:
            continue
        seen.add(qid)
        results.append({
            "qid": qid,
            "label": binding.get("itemLabel", {}).get("value", ""),
            "description": binding.get("itemDescription", {}).get("value", ""),
        })
    return results


def sparql_exact_without_p10607(label: str) -> list[dict]:
    escaped = label.replace('\\', '\\\\').replace('"', '\\"')
    query = f"""SELECT ?item ?itemLabel ?itemDescription WHERE {{
  VALUES ?labelProp {{ rdfs:label skos:altLabel }}
  {{ ?item ?labelProp "{escaped}"@en . }} UNION {{ ?item ?labelProp "{escaped}"@mul . }}
  FILTER NOT EXISTS {{ ?item wdt:{P_ATHLETICS} ?ath . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}"""
    resp = SESSION.get(SPARQL_ENDPOINT, params={"query": query}, timeout=60)
    resp.raise_for_status()
    seen = set()
    results = []
    for binding in resp.json().get("results", {}).get("bindings", []):
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        if qid in seen:
            continue
        seen.add(qid)
        results.append({
            "qid": qid,
            "label": binding.get("itemLabel", {}).get("value", ""),
            "description": binding.get("itemDescription", {}).get("value", ""),
        })
    return results


def get_entity(qid: str) -> dict | None:
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "labels|descriptions|claims|sitelinks",
        "languages": "en|mul",
        "sitefilter": "enwiki",
        "format": "json",
    }
    resp = SESSION.get(WIKIDATA_API, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("entities", {}).get(qid)


def extract_athletics_qid(entity: dict) -> str | None:
    claims = entity.get("claims", {}).get(P_ATHLETICS, [])
    if not claims:
        return None
    mainsnak = claims[0].get("mainsnak", {})
    if mainsnak.get("datatype") == "wikibase-item":
        return mainsnak.get("datavalue", {}).get("value", {}).get("id")
    return None


def extract_main_category_qid(entity: dict) -> str | None:
    claims = entity.get("claims", {}).get(P_MAIN_CATEGORY, [])
    if not claims:
        return None
    mainsnak = claims[0].get("mainsnak", {})
    if mainsnak.get("datatype") == "wikibase-item":
        return mainsnak.get("datavalue", {}).get("value", {}).get("id")
    return None


def extract_nicknames(entity: dict) -> list[dict]:
    nicknames = []
    for claim in entity.get("claims", {}).get(P_NICKNAME, []):
        mainsnak = claim.get("mainsnak", {})
        nick_value = mainsnak.get("datavalue", {}).get("value", {})
        nick_text = nick_value.get("text", "") if isinstance(nick_value, dict) else ""
        if not nick_text:
            continue
        used_by = None
        skip = False
        for qual in claim.get("qualifiers", {}).get(P_USED_BY, []):
            qual_qid = qual.get("datavalue", {}).get("value", {}).get("id", "")
            if qual_qid == Q_MENS_SPORTS:
                used_by = "men"
            elif qual_qid == Q_WOMENS_SPORTS:
                used_by = "women"
            elif qual_qid == Q_WOMENS_BASKETBALL:
                skip = True
        if skip:
            continue
        entry = {"nickname": nick_text}
        if used_by:
            entry["used_by"] = used_by
        nicknames.append(entry)
    return nicknames


def expand_qid(qid: str) -> dict | None:
    entity = get_entity(qid)
    if not entity:
        return None
    label = entity.get("labels", {}).get("en", {}).get("value", "") or entity.get("labels", {}).get("mul", {}).get("value", "")
    description = entity.get("descriptions", {}).get("en", {}).get("value", "")
    has_p10607 = P_ATHLETICS in entity.get("claims", {})
    athletics_qid = extract_athletics_qid(entity)
    enwiki = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
    nicknames = []
    athletics_enwiki = None
    category_qid = None
    category_enwiki = None
    if athletics_qid:
        ath_entity = get_entity(athletics_qid)
        if ath_entity:
            nicknames = extract_nicknames(ath_entity)
            athletics_enwiki = ath_entity.get("sitelinks", {}).get("enwiki", {}).get("title")
            category_qid = extract_main_category_qid(ath_entity)
            if category_qid:
                cat_entity = get_entity(category_qid)
                if cat_entity:
                    category_enwiki = cat_entity.get("sitelinks", {}).get("enwiki", {}).get("title")
    return {
        "qid": qid,
        "label": label,
        "description": description,
        "has_p10607": has_p10607,
        "athletics_qid": athletics_qid,
        "enwiki": enwiki,
        "athletics_enwiki": athletics_enwiki,
        "category_qid": category_qid,
        "category_enwiki": category_enwiki,
        "nicknames": nicknames,
    }


def needs_enrichment(entry) -> bool:
    if isinstance(entry, str):
        return True
    if not isinstance(entry, dict):
        return False
    if "athletics_qid" not in entry:
        return True
    if "enwiki" not in entry:
        return True
    if "athletics_enwiki" not in entry:
        return True
    if "category_enwiki" not in entry:
        return True
    if "category_qid" not in entry:
        return True
    if not entry.get("nicknames"):
        return True
    return False


def enrich_entry(entry: dict) -> dict:
    enriched = {"qid": entry["qid"], "label": entry["label"], "description": entry["description"]}
    entity = get_entity(entry["qid"])
    if entity:
        athletics_qid = extract_athletics_qid(entity)
        enriched["athletics_qid"] = athletics_qid
        enriched["enwiki"] = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
        nicknames = []
        enriched["athletics_enwiki"] = None
        enriched["category_qid"] = None
        enriched["category_enwiki"] = None
        if athletics_qid:
            ath_entity = get_entity(athletics_qid)
            if ath_entity:
                nicknames = extract_nicknames(ath_entity)
                enriched["athletics_enwiki"] = ath_entity.get("sitelinks", {}).get("enwiki", {}).get("title")
                cat_qid = extract_main_category_qid(ath_entity)
                if cat_qid:
                    cat_entity = get_entity(cat_qid)
                    if cat_entity:
                        enriched["category_qid"] = cat_qid
                        enriched["category_enwiki"] = cat_entity.get("sitelinks", {}).get("enwiki", {}).get("title")
        enriched["nicknames"] = nicknames
    else:
        enriched["athletics_qid"] = None
        enriched["nicknames"] = []
        enriched["enwiki"] = None
        enriched["athletics_enwiki"] = None
        enriched["category_qid"] = None
        enriched["category_enwiki"] = None
    return enriched


def save(output_path, resolved, ambiguous, no_athletics, not_found):
    with open(output_path, "w") as f:
        json.dump({
            "resolved": resolved,
            "ambiguous": ambiguous,
            "no_athletics": no_athletics,
            "not_found": not_found,
        }, f, indent=2, ensure_ascii=False)


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else str(OUTPUT_PATH)

    existing: dict = {}
    if Path(output_path).exists():
        with open(output_path) as f:
            existing = json.load(f)
        print(f"Loaded existing: {len(existing.get('resolved', {}))} resolved, "
              f"{len(existing.get('ambiguous', {}))} ambiguous, "
              f"{len(existing.get('no_athletics', []))} no_athletics, "
              f"{len(existing.get('not_found', []))} not found")

    conn = sqlite3.connect(str(DB_PATH))
    schools = [row[0] for row in conn.execute(
        "SELECT DISTINCT school FROM results WHERE school IS NOT NULL AND school != '' ORDER BY school"
    ).fetchall()]
    conn.close()
    print(f"Found {len(schools)} distinct schools in database")

    resolved = dict(existing.get("resolved", {}))
    ambiguous = dict(existing.get("ambiguous", {}))
    no_athletics = list(existing.get("no_athletics", []))
    not_found = list(existing.get("not_found", []))

    string_resolved = [(k, v) for k, v in resolved.items() if isinstance(v, str)]
    if string_resolved:
        print(f"\nExpanding {len(string_resolved)} manually-added QIDs...")
        for school, qid in string_resolved:
            print(f"  {school}: ", end="", flush=True)
            try:
                info = expand_qid(qid)
            except Exception as e:
                print(f"ERROR fetching {qid}: {e}")
                continue
            if info is None:
                print(f"QID {qid} not found on Wikidata")
                continue
            if not info["has_p10607"]:
                print(f"{qid} ({info['label']}) MISSING {P_ATHLETICS}")
            else:
                nicks = ", ".join(n["nickname"] for n in info["nicknames"]) or "none"
                print(f"{qid} ({info['label']}) OK, athletics={info['athletics_qid']}, nicknames: {nicks}")
            resolved[school] = {
                "qid": info["qid"],
                "label": info["label"],
                "description": info["description"],
                "athletics_qid": info.get("athletics_qid"),
                "enwiki": info.get("enwiki"),
                "athletics_enwiki": info.get("athletics_enwiki"),
                "category_qid": info.get("category_qid"),
                "category_enwiki": info.get("category_enwiki"),
                "nicknames": info.get("nicknames", []),
            }
            time.sleep(0.5)
            save(output_path, resolved, ambiguous, no_athletics, not_found)

    to_enrich = [(k, v) for k, v in resolved.items() if isinstance(v, dict) and needs_enrichment(v)]
    if to_enrich:
        print(f"\nEnriching {len(to_enrich)} existing resolved entries...")
        for school, entry in to_enrich:
            print(f"  {school}: ", end="", flush=True)
            try:
                enriched = enrich_entry(entry)
            except Exception as e:
                print(f"ERROR: {e}")
                continue
            nicks = ", ".join(n["nickname"] for n in enriched["nicknames"]) or "none"
            print(f"{enriched['qid']} athletics={enriched['athletics_qid']}, nicknames: {nicks}")
            resolved[school] = enriched
            time.sleep(0.5)
            save(output_path, resolved, ambiguous, no_athletics, not_found)

    already_done = set(resolved.keys()) | set(ambiguous.keys()) | set(no_athletics) | set(not_found)
    todo = [s for s in schools if s not in already_done]
    print(f"\n  {len(todo)} schools to process ({len(already_done)} already done)")

    for i, school in enumerate(todo):
        print(f"  [{i+1}/{len(todo)}] {school}...", end=" ", flush=True)

        try:
            matches = sparql_exact_with_p10607(school)
        except Exception as e:
            print(f"SPARQL ERROR: {e}")
            time.sleep(10)
            continue

        if len(matches) == 1:
            m = matches[0]
            try:
                enriched = enrich_entry(m)
            except Exception as e:
                print(f"{m['qid']} ({m['label']}) RESOLVED but enrichment failed: {e}")
                resolved[school] = m
                save(output_path, resolved, ambiguous, no_athletics, not_found)
                time.sleep(1.5)
                continue
            nicks = ", ".join(n["nickname"] for n in enriched["nicknames"]) or "none"
            print(f"RESOLVED -> {m['qid']} ({m['label']}) athletics={enriched['athletics_qid']}, nicknames: {nicks}")
            resolved[school] = enriched
        elif len(matches) > 1:
            ambiguous[school] = matches
            print(f"AMBIGUOUS ({len(matches)} matches)")
            for m in matches:
                print(f"      {m['qid']} - {m['label']} ({m['description']})")
        else:
            try:
                no_p = sparql_exact_without_p10607(school)
            except Exception as e:
                print(f"SPARQL ERROR (fallback): {e}")
                time.sleep(10)
                continue

            if no_p:
                no_athletics.append(school)
                qids = ", ".join(m["qid"] for m in no_p)
                print(f"NO {P_ATHLETICS} ({len(no_p)} exact match{'es' if len(no_p) > 1 else ''}: {qids})")
            else:
                not_found.append(school)
                print("NOT FOUND (no exact label match)")

        save(output_path, resolved, ambiguous, no_athletics, not_found)
        time.sleep(1.5)

    print(f"\nDone!")
    print(f"  Resolved:      {len(resolved)}")
    print(f"  Ambiguous:     {len(ambiguous)}")
    print(f"  No athletics:  {len(no_athletics)}")
    print(f"  Not found:     {len(not_found)}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()
