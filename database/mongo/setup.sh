#!/usr/bin/env bash
# Create the MongoDB collection and fill it from the MariaDB menu. (Mann)
# Run from the project root after loading the MariaDB schema + seed:
#   database/mongo/setup.sh
# Uses Podman; set ENGINE=docker if you use Docker instead.
set -e
cd "$(dirname "$0")/../.."
ENGINE="${ENGINE:-podman}"
CONTAINER="${CONTAINER:-campuseats-mongo}"

"$ENGINE" cp database/mongo/init.js "$CONTAINER":/tmp/init.js
"$ENGINE" exec "$CONTAINER" mongosh --quiet campuseats --file /tmp/init.js
venv/bin/python database/mongo/seed_mongo.py
