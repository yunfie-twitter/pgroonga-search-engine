import redis
import json
import hashlib
from typing import Dict, Any, Optional
from .config import REDIS_URL

class RedisCacheManager:
    """
    Manages caching of search results to reduce DB load.
    """
    
    def __init__(self, redis_url: str = REDIS_URL, ttl_seconds: int = 300):
        """
        Initialize Redis connection.
        
        Args:
            redis_url (str): Connection URL.
            ttl_seconds (int): Cache Time-To-Live (default 300s).
        """
        self.client = redis.from_url(redis_url)
        self.ttl = ttl_seconds

    def _generate_key(self, query: str, filters: Dict[str, Any]) -> str:
        """
        Generates a unique, deterministic cache key.
        
        Composition:
        - Prefix 'search:'
        - SHA256 hash of (Query + Sorted Filters)
        
        This ensures that 'A, B' and 'B, A' in filters result in the same key if sorted.
        """
        # Create a payload representing the unique request
        payload = {
            "q": query,
            "f": filters
        }
        # sort_keys=True is CRITICAL for deterministic hashing of dictionaries
        serialized = json.dumps(payload, sort_keys=True)
        
        # Hash it to keep keys manageable size
        key_hash = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        
        return f"search:{key_hash}"

    def get_result(self, query: str, filters: Dict[str, Any]) -> Optional[Dict]:
        """
        Try to fetch a result from Redis.
        
        Returns:
            Dict: The deserialized search result if found.
            None: If cache miss.
        """
        key = self._generate_key(query, filters)
        data = self.client.get(key)
        
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    def set_result(self, query: str, filters: Dict[str, Any], result: Dict) -> None:
        """
        Stores the result in Redis with TTL.
        """
        key = self._generate_key(query, filters)
        data = json.dumps(result)
        self.client.setex(key, self.ttl, data)
