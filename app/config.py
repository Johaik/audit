from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App uses audit_app user (RLS restricted)
    DATABASE_URL: str = "postgresql+asyncpg://audit_app:audit_app_password@localhost:5433/audit_db"
    
    # Admin DB URL for migrations (uses superuser/owner)
    # This is needed because 'audit_app' might not be able to change schema or bypass RLS for certain checks
    ADMIN_DATABASE_URL: str = "postgresql+asyncpg://audit_admin:audit_admin_password@localhost:5433/audit_db"
    
    # Keycloak Settings
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "audit-realm"
    KEYCLOAK_ADMIN_USER: str = "admin"
    KEYCLOAK_ADMIN_PASSWORD: str = "admin"
    
    # Admin Security
    ADMIN_API_KEY: str = "dev-admin-key"  # Change in production
    
    class Config:
        env_file = ".env"

settings = Settings()
