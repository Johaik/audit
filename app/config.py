from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://audit_user:audit_password@localhost:5433/audit_db"
    
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
