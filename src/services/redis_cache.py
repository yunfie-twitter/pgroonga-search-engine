# src/services/redis_cache.py
# Responsibility: Handles all Redis-based caching operations for search results.

import hashlib
import json
from typing import Any, Dict, Optional

import redis

from src.config.settings import settings


class RedisCacheManager:
    """
    Manages caching of search results in Redis to reduce database load.
    Ensures deterministic key generation based on query parameters.
    """

    def __init__(self):
        """
        Initializes Redis connection using centralized settings.
        decode_responses=True ensures we get strings back, not bytes.
        """
        self.client = redis.from_url(settings.REDIS.URL, decode_responses=True)
        self.ttl_seconds = settings.REDIS.TTL_SECONDS

    def get_cached_result(self, query: str, filters: Dict[str, Any], limit: int) -> Optional[Dict]:
        """
        Retrieves a search result from cache if it exists.

        Args:
            query (str): The normalized search query.
            filters (dict): Dictionary of applied filters.
            limit (int): The maximum number of results requested.

        Returns:
            Optional[Dict]: The cached result dict, or None if cache miss.
        """
        cache_key = self._generate_key(query, filters, limit)
        try:
            cached_data = self.client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except (redis.RedisError, json.JSONDecodeError) as e:
            # Log error but don't crash; treat as cache miss
            print(f"[Redis] Cache fetch error: {e}")

        return None

    def set_cached_result(self, query: str, filters: Dict[str, Any], limit: int, result: Any) -> None:
        """
        Stores a search result in Redis with a configured TTL.

        Args:
            query (str): The normalized search query.
            filters (dict): Dictionary of applied filters.
            limit (int): The maximum number of results requested.
            result (Any): The JSON-serializable result object to cache.
        """
        cache_key = self._generate_key(query, filters, limit)
        try:
            json_data = json.dumps(result)
            self.client.setex(cache_key, self.ttl_seconds, json_data)
        except (redis.RedisError, TypeError) as e:
            print(f"[Redis] Cache write error: {e}")

    def _generate_key(self, query: str, filters: Dict[str, Any], limit: int) -> str:
        """
        Generates a deterministic, unique cache key based on search parameters.

        Key Format: "search:{sha256_hash}"
        The hash is derived from a sorted JSON representation of input params.

        Args:
            query (str): Normalized query.
            filters (dict): Filters.
            limit (int): Limit.

        Returns:
            str: The SHA256 hash-based Redis key.
        """
        payload = {
            "q": query,
            "f": filters,
            "l": limit
        }
        # sort_keys=True is critical for deterministic hashing of dictionaries
        serialized_payload = json.dumps(payload, sort_keys=True)
        hash_digest = hashlib.sha256(serialized_payload.encode('utf-8')).hexdigest()

        return f"search:{hash_digest}"
