#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_NAME="${DB_NAME:-campuseats}"
mariadb "$DB_NAME" < "$ROOT_DIR/database/schema.sql"
mariadb "$DB_NAME" < "$ROOT_DIR/database/seed.sql"
echo "CampusEats schema and sample data reloaded in $DB_NAME."
