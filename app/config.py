from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://audit_user:audit_password@localhost:5433/audit_db"
    
    class Config:
        env_file = ".env"

settings = Settings()

