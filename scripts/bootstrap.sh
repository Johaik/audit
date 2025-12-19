#!/bin/bash
# Bootstrap the entire dev environment
set -e

./scripts/dev_up.sh

echo "Waiting for Postgres to be ready for migrations..."
sleep 5 # dev_up has a sleep, but maybe we need more for DB to accept connections

# We might need to wait for DB specifically. 
# A robust way is to try running alembic until it works or use pg_isready if available (requires postgres client installed)
# For now, sleep is simple.

./scripts/migrate.sh
./scripts/init_keycloak.sh

echo "Environment bootstrapped successfully."
echo "Run ./scripts/server.sh to start the API."

