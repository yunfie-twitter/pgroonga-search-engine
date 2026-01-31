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
    
    # Depth and Frequency
    MAX_DEPTH: int = 3
    DEFAULT_INTERVAL_SECONDS: int = 86400  # 24h
    ERROR_INTERVAL_SECONDS: int = 21600    # 6h
    DOMAIN_LOCK_TTL_SECONDS: int = 60
    
    # Priority Scoring
    BASE_SCORE: float = 100.0
    DEPTH_PENALTY: float = 10.0
    ERROR_PENALTY: float = 20.0
    
    # Reliability & Cleanup
    MAX_RETRIES: int = 5  # Max failures before marking as 'deleted'
    ROBOTS_CACHE_TTL: int = 86400 # 24h cache for robots.txt
    
    # Anomaly Detection
    MAX_URLS_PER_DOMAIN: int = 1000 # Stop crawling domain after this many URLs
    MAX_URL_LENGTH: int = 256
    MAX_PATH_SEGMENT_REPEATS: int = 3 # e.g. /a/a/a/a -> blocked

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
