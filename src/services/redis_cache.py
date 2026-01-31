import redis
import json
import hashlib
from typing import Dict, Any, Optional

from src.config.settings import settings

class RedisCacheManager:
    """
    Manages caching of search results in Redis.
    Uses deterministic key generation to ensure cache hits for identical queries.
    """

    def __init__(self):
        """
        Initialize Redis connection using settings.
        """
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ttl = settings.REDIS_TTL

    def _generate_key(self, query: str, filters: Dict[str, Any], limit: int) -> str:
        """
        Generates a unique cache key based on all search parameters.
        
        Format: search:{hash_of_params}
        
        Args:
            query (str): Normalized query string.
            filters (dict): Filter parameters.
            limit (int): Pagination limit.

        Returns:
            str: Redis key.
        """
        payload = {
            "q": query,
            "f": filters,
            "l": limit
        }
        # sort_keys=True is CRITICAL for deterministic JSON serialization
        serialized = json.dumps(payload, sort_keys=True)
        key_hash = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        
        return f"search:{key_hash}"

    def get_result(self, query: str, filters: Dict[str, Any], limit: int) -> Optional[Dict]:
        """
        Retrieves result from cache.
        
        Returns:
            dict or None: Deserialized result if hit, else None.
        """
        key = self._generate_key(query, filters, limit)
        data = self.client.get(key)
        
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    def set_result(self, query: str, filters: Dict[str, Any], limit: int, result: Any) -> None:
        """
        Saves result to cache with TTL.
        """
        key = self._generate_key(query, filters, limit)
        # Assuming 'result' is a list of dicts (search results)
        data = json.dumps(result)
        self.client.setex(key, self.ttl, data)
