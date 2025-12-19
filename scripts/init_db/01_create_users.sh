#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create application user
    CREATE USER ${APP_DB_USER:-audit_app} WITH PASSWORD '${APP_DB_PASSWORD:-audit_app_password}';
    
    -- Grant permissions to app user
    -- Note: Schema might not exist yet if created by Alembic later.
    -- But we can grant on database
    GRANT CONNECT ON DATABASE ${POSTGRES_DB:-audit_db} TO ${APP_DB_USER:-audit_app};
    GRANT USAGE, CREATE ON SCHEMA public TO ${APP_DB_USER:-audit_app};
    
    -- Ensure admin user has BYPASSRLS
    ALTER ROLE ${POSTGRES_USER:-audit_admin} WITH BYPASSRLS;
    
    -- Grant future table permissions to app user
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${APP_DB_USER:-audit_app};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${APP_DB_USER:-audit_app};
EOSQL

