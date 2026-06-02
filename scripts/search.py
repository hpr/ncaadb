#!/usr/bin/env python3
"""
NCAA Track & Field Championships History Database Search Interface
"""

import sqlite3
import argparse
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "ncaa_history.db")


def search(
    query: Optional[str] = None,
    year: Optional[int] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    name: Optional[str] = None,
    school: Optional[str] = None,
    discipline: Optional[str] = None,
    gender: Optional[str] = None,
    place: Optional[int] = None,
    place_max: Optional[int] = None,
    is_dq: Optional[bool] = None,
    is_dnf: Optional[bool] = None,
    is_dns: Optional[bool] = None,
    is_wind_aided: Optional[bool] = None,
    is_international: Optional[bool] = None,
    is_relay: Optional[bool] = None,
    environment: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "year",
    order_dir: str = "ASC",
) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    conditions = []
    params = []
    
    if query:
        conditions.append("(name LIKE ? OR school LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    
    if year is not None:
        conditions.append("year = ?")
        params.append(year)
    
    if year_min is not None:
        conditions.append("year >= ?")
        params.append(year_min)
    
    if year_max is not None:
        conditions.append("year <= ?")
        params.append(year_max)
    
    if name:
        conditions.append("name LIKE ?")
        params.append(f"%{name}%")
    
    if school:
        conditions.append("school LIKE ?")
        params.append(f"%{school}%")
    
    if discipline:
        conditions.append("discipline LIKE ?")
        params.append(f"%{discipline}%")
    
    if gender:
        conditions.append("gender = ?")
        params.append(gender.lower())
    
    if place is not None:
        conditions.append("place = ?")
        params.append(place)
    
    if place_max is not None:
        conditions.append("place <= ?")
        params.append(place_max)
    
    if is_dq is not None:
        conditions.append("is_dq = ?")
        params.append(1 if is_dq else 0)
    
    if is_dnf is not None:
        conditions.append("is_dnf = ?")
        params.append(1 if is_dnf else 0)
    
    if is_dns is not None:
        conditions.append("is_dns = ?")
        params.append(1 if is_dns else 0)
    
    if is_wind_aided is not None:
        conditions.append("is_wind_aided = ?")
        params.append(1 if is_wind_aided else 0)
    
    if is_international is not None:
        conditions.append("is_international = ?")
        params.append(1 if is_international else 0)
    
    if is_relay is not None:
        conditions.append("is_relay = ?")
        params.append(1 if is_relay else 0)
    
    if environment:
        conditions.append("environment = ?")
        params.append(environment.lower())
    
    valid_order_cols = ["year", "name", "school", "discipline", "place", "mark_num", "gender"]
    if order_by not in valid_order_cols:
        order_by = "year"
    
    order_dir = "ASC" if order_dir.upper() == "ASC" else "DESC"
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"""
        SELECT * FROM results
        WHERE {where_clause}
        ORDER BY {order_by} {order_dir}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    
    c.execute(sql, params)
    rows = c.fetchall()
    
    results = [dict(row) for row in rows]
    conn.close()
    
    return results


def count(
    query: Optional[str] = None,
    year: Optional[int] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    name: Optional[str] = None,
    school: Optional[str] = None,
    discipline: Optional[str] = None,
    gender: Optional[str] = None,
    is_dq: Optional[bool] = None,
    is_dnf: Optional[bool] = None,
    is_dns: Optional[bool] = None,
    is_wind_aided: Optional[bool] = None,
    is_international: Optional[bool] = None,
    is_relay: Optional[bool] = None,
    environment: Optional[str] = None,
) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    conditions = []
    params = []
    
    if query:
        conditions.append("(name LIKE ? OR school LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    
    if year is not None:
        conditions.append("year = ?")
        params.append(year)
    
    if year_min is not None:
        conditions.append("year >= ?")
        params.append(year_min)
    
    if year_max is not None:
        conditions.append("year <= ?")
        params.append(year_max)
    
    if name:
        conditions.append("name LIKE ?")
        params.append(f"%{name}%")
    
    if school:
        conditions.append("school LIKE ?")
        params.append(f"%{school}%")
    
    if discipline:
        conditions.append("discipline LIKE ?")
        params.append(f"%{discipline}%")
    
    if gender:
        conditions.append("gender = ?")
        params.append(gender.lower())
    
    if is_dq is not None:
        conditions.append("is_dq = ?")
        params.append(1 if is_dq else 0)
    
    if is_dnf is not None:
        conditions.append("is_dnf = ?")
        params.append(1 if is_dnf else 0)
    
    if is_dns is not None:
        conditions.append("is_dns = ?")
        params.append(1 if is_dns else 0)
    
    if is_wind_aided is not None:
        conditions.append("is_wind_aided = ?")
        params.append(1 if is_wind_aided else 0)
    
    if is_international is not None:
        conditions.append("is_international = ?")
        params.append(1 if is_international else 0)
    
    if is_relay is not None:
        conditions.append("is_relay = ?")
        params.append(1 if is_relay else 0)
    
    if environment:
        conditions.append("environment = ?")
        params.append(environment.lower())
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"SELECT COUNT(*) FROM results WHERE {where_clause}"
    c.execute(sql, params)
    count = c.fetchone()[0]
    conn.close()
    
    return count


def get_disciplines() -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT discipline FROM results ORDER BY discipline")
    return [row[0] for row in c.fetchall()]


def get_schools() -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT school FROM results ORDER BY school")
    return [row[0] for row in c.fetchall()]


def format_result(r: Dict[str, Any]) -> str:
    parts = [f"{r['year']}", f"{r['date']}" if r.get('date') else "", f"{r['place'] or '?'}." if r['place'] else ""]
    
    parts.append(f"{r['name']}")
    
    if r['school']:
        parts.append(f"({r['school']})")
    
    parts.append(f"[{r['discipline']}]")
    
    if r['is_relay'] and r['leg_idx']:
        parts.append(f"Leg {r['leg_idx']}")
        if r['split_time']:
            parts.append(f"({r['split_time']})")
    
    if r['mark_str']:
        mark = r['mark_str']
        if r['is_wind_aided']:
            mark += 'w'
        parts.append(mark)
    
    if r['wind'] is not None:
        parts.append(f"wind {r['wind']:+.1f}")
    
    if r['class']:
        parts.append(f"({r['class']})")
    
    flags = []
    if r['is_dq']:
        flags.append("DQ")
    if r['is_dnf']:
        flags.append("DNF")
    if r['is_dns']:
        flags.append("DNS")
    if r['is_international']:
        flags.append("INT")
    if r['is_wind_aided']:
        flags.append("W")
    
    if flags:
        parts.append(f"[{', '.join(flags)}]")
    
    if r.get('location'):
        parts.append(f"@ {r['location']}")
    
    return " ".join(str(p) for p in parts if p)


def main():
    parser = argparse.ArgumentParser(
        description="Search NCAA Track & Field Championships History Database"
    )
    
    parser.add_argument("query", nargs="?", help="Search query (searches name and school)")
    parser.add_argument("--year", type=int, help="Filter by specific year")
    parser.add_argument("--year-min", type=int, help="Filter by minimum year")
    parser.add_argument("--year-max", type=int, help="Filter by maximum year")
    parser.add_argument("--name", help="Filter by athlete/team name")
    parser.add_argument("--school", help="Filter by school")
    parser.add_argument("--discipline", help="Filter by discipline (e.g., '100m', 'High Jump')")
    parser.add_argument("--gender", choices=["men", "women"], help="Filter by gender")
    parser.add_argument("--place", type=int, help="Filter by place")
    parser.add_argument("--place-max", type=int, help="Filter by maximum place (e.g., 3 for podium)")
    parser.add_argument("--dq", action="store_true", help="Show only DQ results")
    parser.add_argument("--dnf", action="store_true", help="Show only DNF results")
    parser.add_argument("--dns", action="store_true", help="Show only DNS results")
    parser.add_argument("--wind-aided", action="store_true", help="Show only wind-aided results")
    parser.add_argument("--international", action="store_true", help="Show only international athletes")
    parser.add_argument("--relay", action="store_true", help="Show only relay results")
    parser.add_argument("--environment", choices=["indoor", "outdoor"], help="Filter by environment (indoor/outdoor)")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of results (default: 50)")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    parser.add_argument("--order-by", default="year", help="Order by column (default: year)")
    parser.add_argument("--order-dir", default="ASC", choices=["ASC", "DESC"], help="Order direction")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--count", action="store_true", help="Show count of matching results")
    parser.add_argument("--list-disciplines", action="store_true", help="List all disciplines")
    parser.add_argument("--list-schools", action="store_true", help="List all schools")
    
    args = parser.parse_args()
    
    if args.list_disciplines:
        print("Disciplines:")
        for d in get_disciplines():
            print(f"  {d}")
        return
    
    if args.list_schools:
        print("Schools:")
        for s in get_schools():
            print(f"  {s}")
        return
    
    if args.count:
        total = count(
            query=args.query,
            year=args.year,
            year_min=args.year_min,
            year_max=args.year_max,
            name=args.name,
            school=args.school,
            discipline=args.discipline,
            gender=args.gender,
            is_dq=args.dq or None,
            is_dnf=args.dnf or None,
            is_dns=args.dns or None,
            is_wind_aided=args.wind_aided or None,
            is_international=args.international or None,
            is_relay=args.relay or None,
            environment=args.environment,
        )
        print(f"Total matching results: {total}")
        return
    
    results = search(
        query=args.query,
        year=args.year,
        year_min=args.year_min,
        year_max=args.year_max,
        name=args.name,
        school=args.school,
        discipline=args.discipline,
        gender=args.gender,
        place=args.place,
        place_max=args.place_max,
        is_dq=args.dq or None,
        is_dnf=args.dnf or None,
        is_dns=args.dns or None,
        is_wind_aided=args.wind_aided or None,
        is_international=args.international or None,
        is_relay=args.relay or None,
        environment=args.environment,
        limit=args.limit,
        offset=args.offset,
        order_by=args.order_by,
        order_dir=args.order_dir,
    )
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(format_result(r))
        
        print(f"\nShowing {len(results)} results")


if __name__ == "__main__":
    main()
