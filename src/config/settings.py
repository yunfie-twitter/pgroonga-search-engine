from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Using Pydantic BaseSettings ensures type safety and easy loading from .env or docker env vars.
    """
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    REDIS_TTL: int = 300  # Default 300 seconds as per requirement

    # File Paths
    # Using absolute path inside container, usually /app/data/synonyms.json
    SYNONYM_FILE_PATH: str = "/app/data/synonyms.json"

    # Server
    UVICORN_HOST: str = "0.0.0.0"
    UVICORN_PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True

# Instantiate settings
settings = Settings()
