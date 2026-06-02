#!/usr/bin/env python3
"""
Build schools table from data/schools_wikidata.json and add school_id to results.
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "ncaa_history.db"
SCHOOLS_PATH = PROJECT_ROOT / "data" / "schools_wikidata.json"


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(DB_PATH)
    schools_path = sys.argv[2] if len(sys.argv) > 2 else str(SCHOOLS_PATH)

    with open(schools_path) as f:
        data = json.load(f)

    resolved = data.get("resolved", {})
    if not resolved:
        print("  No resolved schools found in schools_wikidata.json")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("DROP TABLE IF EXISTS schools")
    c.execute("""
        CREATE TABLE schools (
            school_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            qid TEXT,
            athletics_qid TEXT,
            category_qid TEXT,
            label TEXT,
            description TEXT,
            enwiki TEXT,
            athletics_enwiki TEXT,
            category_enwiki TEXT,
            men_nickname TEXT,
            women_nickname TEXT
        )
    """)

    c.execute("PRAGMA table_info(results)")
    columns = [row[1] for row in c.fetchall()]
    if "school_id" not in columns:
        c.execute("ALTER TABLE results ADD COLUMN school_id INTEGER")
        print("  Added school_id column")
    else:
        c.execute("UPDATE results SET school_id = NULL")
        print("  Reset school_id column")
    conn.commit()

    for name, info in resolved.items():
        nicknames = info.get("nicknames", [])
        men_nick = None
        women_nick = None
        for nick in nicknames:
            used_by = nick.get("used_by")
            if used_by == "men":
                men_nick = nick["nickname"]
            elif used_by == "women":
                women_nick = nick["nickname"]
            else:
                men_nick = nick["nickname"]
                women_nick = nick["nickname"]

        c.execute("""
            INSERT INTO schools (name, qid, athletics_qid, category_qid, label, description,
                                 enwiki, athletics_enwiki, category_enwiki,
                                 men_nickname, women_nickname)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            info.get("qid"),
            info.get("athletics_qid"),
            info.get("category_qid"),
            info.get("label"),
            info.get("description"),
            info.get("enwiki"),
            info.get("athletics_enwiki"),
            info.get("category_enwiki"),
            men_nick,
            women_nick,
        ))

    conn.commit()
    print(f"  Inserted {len(resolved)} schools")

    c.execute("""
        UPDATE results SET school_id = (
            SELECT s.school_id FROM schools s WHERE s.name = results.school
        )
    """)
    conn.commit()

    c.execute("SELECT COUNT(*) FROM results WHERE school_id IS NULL")
    unmatched = c.fetchone()[0]
    if unmatched > 0:
        print(f"  ERROR: {unmatched} results have no matching school")
        sys.exit(1)

    c.execute("CREATE INDEX IF NOT EXISTS idx_school_id ON results(school_id)")
    conn.commit()

    c.execute("SELECT COUNT(*) FROM results")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM results WHERE school_id IS NOT NULL")
    matched = c.fetchone()[0]
    print(f"  Matched {matched}/{total} results to schools")

    conn.close()


if __name__ == "__main__":
    main()
