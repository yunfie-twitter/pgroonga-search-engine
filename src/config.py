import os

# Database Configuration
# Using environment variables for secrets is a security best practice.
DB_DSN = os.getenv("DATABASE_URL", "postgresql://search_user:search_password@localhost:5432/search_db")

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# Cache TTL in seconds (Requirements: 300s)
REDIS_TTL_SECONDS = int(os.getenv("REDIS_TTL", 300))

# Application Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Path to the synonym JSON file
SYNONYM_FILE_PATH = os.getenv("SYNONYM_FILE_PATH", os.path.join(BASE_DIR, "synonyms.json"))
