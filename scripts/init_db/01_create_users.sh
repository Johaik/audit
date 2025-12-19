#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create application user
    CREATE USER audit_app WITH PASSWORD 'audit_app_password';
    
    -- Grant permissions to app user
    -- Note: Schema might not exist yet if created by Alembic later.
    -- But we can grant on database
    GRANT CONNECT ON DATABASE audit_db TO audit_app;
    GRANT USAGE, CREATE ON SCHEMA public TO audit_app;
    
    -- Ensure admin user has BYPASSRLS
    ALTER ROLE audit_admin WITH BYPASSRLS;
    
    -- Grant future table permissions to app user
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO audit_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO audit_app;
EOSQL

