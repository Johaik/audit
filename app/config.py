from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App uses audit_app user (RLS restricted)
    DATABASE_URL: str
    
    # Admin DB URL for migrations (uses superuser/owner)
    # This is needed because 'audit_app' might not be able to change schema or bypass RLS for certain checks
    ADMIN_DATABASE_URL: str
    
    # Keycloak Settings
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "audit-realm"
    KEYCLOAK_ADMIN_USER: str = "admin"
    KEYCLOAK_ADMIN_PASSWORD: str
    
    # Admin Security
    ADMIN_API_KEY: str
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
