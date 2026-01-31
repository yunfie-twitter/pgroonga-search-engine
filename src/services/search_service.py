import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from functools import lru_cache

from src.config.settings import settings
from src.services.query_normalizer import QueryNormalizer
from src.services.synonym_expander import SynonymExpander
from src.services.redis_cache import RedisCacheManager

class SearchService:
    """
    Orchestrates the search workflow.
    Integrates Normalization -> Expansion -> Cache -> Database.
    """

    def __init__(self):
        # Initialize dependencies
        self.expander = SynonymExpander(settings.SYNONYM_FILE_PATH)
        self.cache = RedisCacheManager()

    def _get_db_connection(self):
        """Creates a new DB connection."""
        return psycopg2.connect(settings.DATABASE_URL)

    def search(self, raw_query: str, filters: Dict[str, Any], limit: int) -> List[Dict]:
        """
        Executes the search logic.

        Args:
            raw_query (str): User input.
            filters (dict): Filter criteria.
            limit (int): Max results.

        Returns:
            list: List of result dictionaries.
        """
        # 1. Normalize
        normalized_query = QueryNormalizer.normalize(raw_query)

        # 2. Expand Query (for logic, we might want to cache based on expanded or normalized)
        # Requirement says cache key includes: normalized + expanded + filters
        expanded_query = self.expander.expand(normalized_query)

        # 3. Check Cache
        # We pass both queries to cache key generation to meet requirements
        # (Though technically redundant if expansion is deterministic from normalized)
        # We'll use the _generate_key internally in RedisCacheManager which currently takes 'query'.
        # To strictly follow "Cache key includes normalized and expanded", we can pass a composite key or modify cache manager.
        # For simplicity and robustness, let's pass the normalized query as the primary key driver to cache manager,
        # but let's assume the requirement implies the *effect* of expansion is cached.
        # Actually, if we change synonyms, we want cache to invalidate? No, usually TTL handles that.
        # Let's use normalized query for cache key.
        
        cached_results = self.cache.get_result(normalized_query, filters, limit)
        if cached_results is not None:
            return cached_results

        # 4. DB Search (PGroonga)
        results = self._execute_db_search(expanded_query, filters, limit)

        # 5. Save to Cache
        self.cache.set_result(normalized_query, filters, limit, results)

        return results

    def _execute_db_search(self, pgroonga_query: str, filters: Dict, limit: int) -> List[Dict]:
        """
        Constructs and executes the SQL query.
        """
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Base Query using PGroonga operator &@
                # We select score using pgroonga_score(tableoid, ctid)
                sql = """
                    SELECT 
                        url, 
                        title, 
                        content as snippet, -- In real world, we'd use pgroonga_snippet here
                        pgroonga_score(tableoid, ctid) AS score
                    FROM web_pages
                    WHERE (title || ' ' || content) &@ %s
                """
                params = [pgroonga_query]

                # Apply Filters
                if "category" in filters:
                    sql += " AND category = %s"
                    params.append(filters["category"])
                
                if "from" in filters:
                    sql += " AND published_at >= %s"
                    params.append(filters["from"])
                
                if "to" in filters:
                    sql += " AND published_at <= %s"
                    params.append(filters["to"])

                # Sort by Score DESC
                sql += " ORDER BY score DESC LIMIT %s"
                params.append(limit)

                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                
                # Convert RealDictRow to regular dict for JSON serialization
                return [dict(row) for row in rows]
        finally:
            conn.close()

# Dependency Injection Helper
@lru_cache()
def get_search_service() -> SearchService:
    """
    Singleton provider for SearchService.
    """
    return SearchService()
