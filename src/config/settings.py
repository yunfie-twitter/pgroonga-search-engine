from pydantic_settings import BaseSettings
import os

class DatabaseSettings(BaseSettings):
    """Configuration for PostgreSQL connection."""
    URL: str = os.getenv("DATABASE_URL", "postgresql://search_user:search_password@db:5432/search_db")

class RedisSettings(BaseSettings):
    """Configuration for Redis connection and caching behavior."""
    URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    TTL_SECONDS: int = 300  # Default 300 seconds (5 minutes)
    QUEUE_NAME: str = "crawler_queue"

class ServerSettings(BaseSettings):
    """Configuration for the API server."""
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

class CrawlerSettings(BaseSettings):
    """Configuration for the web crawler."""
    USER_AGENT: str = "PGroongaSearchEngineBot/1.0"
    REQUEST_TIMEOUT: int = 10
    JOB_TIMEOUT: int = 60

class AppSettings(BaseSettings):
    """
    Centralized application configuration.
    Groups specific settings into logical sub-categories.
    """
    DB: DatabaseSettings = DatabaseSettings()
    REDIS: RedisSettings = RedisSettings()
    SERVER: ServerSettings = ServerSettings()
    CRAWLER: CrawlerSettings = CrawlerSettings()
    
    # Absolute path inside container
    SYNONYM_FILE_PATH: str = "/app/data/synonyms.json"

    class Config:
        env_file = ".env"
        case_sensitive = True
        # Allow nested environment variable loading if needed
        # e.g., DB__URL overrides DB.URL

settings = AppSettings()
