#!/bin/bash
set -e

cd "$(dirname "$0")"

PYTHON=".venv/bin/python3"
if [ ! -x "$PYTHON" ]; then
  echo "ERROR: Virtual environment not found at .venv/. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

GENERATE=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --generate-candidates) GENERATE=1; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

rm -f ncaa_history.db
$PYTHON parse_outdoor.py
$PYTHON parse_indoor.py
$PYTHON scripts/parse_flashresults_2026.py
$PYTHON scripts/import_missing_indoor.py
$PYTHON scripts/resolve_near_duplicates.py
$PYTHON scripts/resolve_missing_names.py
$PYTHON scripts/resolve_removals.py
$PYTHON scripts/resolve_missing_places.py
$PYTHON scripts/resolve_corrections.py
$PYTHON scripts/resolve_relay_members.py
$PYTHON scripts/resolve_schools.py

if [ "$GENERATE" -eq 1 ]; then
  $PYTHON scripts/generate_name_candidates.py
fi

$PYTHON scripts/generate_profiles.py
$PYTHON scripts/resolve_profiles.py
$PYTHON scripts/filter_top8.py
$PYTHON wiki/resolve_athlete_wikidata.py
$PYTHON scripts/apply_athlete_wikidata.py
cp ncaa_history.db webapp/public/
cp data/event_groups.json webapp/public/
cp data/profiles.json webapp/public/
cp data/name_candidates.json webapp/public/

cd webapp
npm run build

echo "Database regenerated and copied to webapp, webapp built"
