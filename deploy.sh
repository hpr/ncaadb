#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

TIMESTAMP=$(date +%Y%m%d-%H%M)
REMOTE=ma.sdf.org
BACKUP_DIR=/meta/h/habs/db/backups

ssh "$REMOTE" "test -f ~/html/ncaadb/ncaa_history.db && cp ~/html/ncaadb/ncaa_history.db ${BACKUP_DIR}/ncaadb-${TIMESTAMP}.db || true"
ssh "$REMOTE" "rm -rf ~/html/ncaadb"
scp -r webapp/dist "$REMOTE":~/html/ncaadb
