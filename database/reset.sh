#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi
DB_NAME="${DB_NAME:-campuseats}"
DB_USER="${DB_USER:-campuseats}"
DB_CLIENT="$(command -v mariadb || command -v mysql || true)"
if [[ -z "$DB_CLIENT" ]]; then
  echo "Neither the MariaDB nor MySQL client was found on PATH." >&2
  exit 1
fi
DB_ARGS=(-u "$DB_USER")
if [[ -n "${DB_PASSWORD:-}" ]]; then
  DB_ARGS+=("--password=$DB_PASSWORD")
else
  DB_ARGS+=(-p)
fi
"$DB_CLIENT" "${DB_ARGS[@]}" "$DB_NAME" < "$ROOT_DIR/database/schema.sql"
"$DB_CLIENT" "${DB_ARGS[@]}" "$DB_NAME" < "$ROOT_DIR/database/seed.sql"
"$ROOT_DIR/database/mongo/setup.sh"
echo "MariaDB and MongoDB demo data reloaded."
