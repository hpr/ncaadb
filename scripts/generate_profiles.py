#!/usr/bin/env python3
"""
Generate profiles.json from the database and athlete_decisions.json.

Uses Union-Find to group athlete clusters based on user decisions:
  - same / same_a / same_b / same_custom:X -> merge clusters
  - different -> keep separate (and verify no contradiction)
  - skip -> ignore

Outputs profiles.json with athlete_id, canonical_name, aliases, members.
"""

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "ncaa_history.db"
DECISIONS_PATH = PROJECT_ROOT / "data" / "athlete_decisions.json"
PROFILES_PATH = PROJECT_ROOT / "data" / "profiles.json"


class UnionFind:
    def __init__(self):
        self.parent = {}
        self.rank = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1


def parse_node(s):
    parts = s.split('|')
    return (normalize_name(parts[0]), parts[1], parts[2], int(parts[3]), int(parts[4]))


def normalize_name(name: str) -> str:
    return name.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')


def main():
    with open(DECISIONS_PATH) as f:
        data = json.load(f)
    decisions = data.get('decisions', {})

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT name, gender, school, year FROM results "
        "WHERE name IS NOT NULL AND name != 'Relay member unknown'"
    ).fetchall()
    conn.close()

    cluster_years = defaultdict(set)
    cluster_row_counts = Counter()
    for name, gender, school, year in rows:
        name = normalize_name(name)
        key = (name, school, gender)
        cluster_years[key].add(year)
        cluster_row_counts[key] += 1

    nodes = {}
    node_lookup = {}
    for (name, school, gender), years in cluster_years.items():
        node_key = (name, school, gender, min(years), max(years))
        nodes[node_key] = len(years)
        node_lookup[(name, school, gender)] = node_key

    def resolve_node(s):
        parts = s.split('|')
        name, school, gender = normalize_name(parts[0]), parts[1], parts[2]
        lookup = (name, school, gender)
        if lookup in node_lookup:
            return node_lookup[lookup]
        return (name, school, gender, int(parts[3]), int(parts[4]))

    print(f"  {len(rows)} rows -> {len(nodes)} clusters, {len(decisions)} decisions")

    uf = UnionFind()
    for node_key in nodes:
        uf.find(node_key)

    different_pairs = []
    same_edges = []

    for key, decision in decisions.items():
        if decision == 'skip':
            continue

        parts = key.split('::')
        node_a = resolve_node(parts[0])
        node_b = resolve_node(parts[1])

        if decision == 'different':
            different_pairs.append((node_a, node_b))
        else:
            same_edges.append((node_a, node_b, decision))

    all_hints = []

    for node_a, node_b, decision in same_edges:
        if node_a not in nodes and node_b not in nodes:
            continue

        uf.find(node_a)
        uf.find(node_b)
        uf.union(node_a, node_b)

        if decision == 'same_a':
            all_hints.append((node_a, node_b, node_a[0], False))
        elif decision == 'same_b':
            all_hints.append((node_a, node_b, node_b[0], False))
        elif decision.startswith('same_custom:'):
            custom_name = decision.split(':', 1)[1]
            all_hints.append((node_a, node_b, custom_name, True))

    contradictions = []
    for node_a, node_b in different_pairs:
        if node_a in uf.parent and node_b in uf.parent:
            if uf.find(node_a) == uf.find(node_b):
                contradictions.append((node_a, node_b))
    if contradictions:
        for node_a, node_b in contradictions:
            print(f"  CONTRADICTION: {node_a[0]}|{node_a[1]} ({node_a[3]}-{node_a[4]}) "
                  f"vs {node_b[0]}|{node_b[1]} ({node_b[3]}-{node_b[4]})")
        sys.exit(f"  ERROR: {len(contradictions)} contradictions in decisions!")

    hints_by_root = defaultdict(list)
    for na, nb, hint_name, is_custom in all_hints:
        root = uf.find(na)
        hints_by_root[root].append((hint_name, is_custom))

    components = defaultdict(list)
    for node_key in nodes:
        root = uf.find(node_key)
        components[root].append(node_key)

    profiles = []
    for root, comp_nodes in sorted(components.items()):
        hints = hints_by_root.get(root, [])
        custom_names = [name for name, ic in hints if ic]
        regular_names = [name for name, ic in hints if not ic]

        if custom_names:
            canonical = Counter(custom_names).most_common(1)[0][0]
        elif regular_names:
            canonical = Counter(regular_names).most_common(1)[0][0]
        else:
            comp_name_counts = Counter()
            for n in comp_nodes:
                comp_name_counts[n[0]] += cluster_row_counts.get((n[0], n[1], n[2]), 0)
            canonical = comp_name_counts.most_common(1)[0][0]

        aliases = sorted(set(n[0] for n in comp_nodes))
        if canonical not in aliases:
            aliases.append(canonical)
            aliases.sort()

        members = []
        for node_key in comp_nodes:
            name, school, gender, year_start, year_end = node_key
            members.append({
                'name': name,
                'gender': gender,
                'school': school,
                'year_start': year_start,
                'year_end': year_end,
            })

        profiles.append({
            'athlete_id': 0,
            'canonical_name': canonical,
            'aliases': aliases,
            'members': members,
        })

    profiles.sort(key=lambda p: (
        min(m['year_start'] for m in p['members']),
        p['canonical_name'].lower(),
    ))
    for i, p in enumerate(profiles, 10001):
        p['athlete_id'] = i

    with open(PROFILES_PATH, 'w') as f:
        json.dump(profiles, f, indent=2)

    print(f"  Generated {len(profiles)} profiles")


if __name__ == '__main__':
    main()
