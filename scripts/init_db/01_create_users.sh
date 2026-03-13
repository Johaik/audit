#!/bin/bash
set -e

if [ -z "${APP_DB_PASSWORD}" ]; then
    echo "ERROR: APP_DB_PASSWORD environment variable is not set or empty. A secure password must be provided."
    exit 1
fi

if [ -z "${POSTGRES_USER}" ] || [ -z "${POSTGRES_DB}" ] || [ -z "${APP_DB_USER}" ]; then
    echo "ERROR: Required environment variables (POSTGRES_USER, POSTGRES_DB, APP_DB_USER) must be set."
    exit 1
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create application user
    CREATE USER ${APP_DB_USER} WITH PASSWORD '${APP_DB_PASSWORD}';
    
    -- Grant permissions to app user
    -- Note: Schema might not exist yet if created by Alembic later.
    -- But we can grant on database
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${APP_DB_USER};
    GRANT USAGE, CREATE ON SCHEMA public TO ${APP_DB_USER};
    
    -- Ensure admin user has BYPASSRLS
    ALTER ROLE ${POSTGRES_USER} WITH BYPASSRLS;
    
    -- Grant future table permissions to app user
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${APP_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${APP_DB_USER};
EOSQL

