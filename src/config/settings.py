from pydantic_settings import BaseSettings
import os

class DatabaseSettings(BaseSettings):
    URL: str = os.getenv("DATABASE_URL", "postgresql://search_user:search_password@db:5432/search_db")

class RedisSettings(BaseSettings):
    URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    TTL_SECONDS: int = 300
    QUEUE_NAME: str = "crawler_queue"

class ServerSettings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

class CrawlerSettings(BaseSettings):
    USER_AGENT: str = "PGroongaSearchEngineBot/1.0"
    REQUEST_TIMEOUT: int = 10
    JOB_TIMEOUT: int = 60
    
    # New Settings for Depth and Frequency
    MAX_DEPTH: int = 3
    DEFAULT_INTERVAL_SECONDS: int = 86400  # 24 hours
    ERROR_INTERVAL_SECONDS: int = 21600    # 6 hours
    DOMAIN_LOCK_TTL_SECONDS: int = 60      # Lock duration to prevent rapid-fire on same domain

class AppSettings(BaseSettings):
    DB: DatabaseSettings = DatabaseSettings()
    REDIS: RedisSettings = RedisSettings()
    SERVER: ServerSettings = ServerSettings()
    CRAWLER: CrawlerSettings = CrawlerSettings()
    
    SYNONYM_FILE_PATH: str = "/app/data/synonyms.json"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = AppSettings()
