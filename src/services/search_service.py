from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from functools import lru_cache

from src.config.settings import settings
from src.services.query_normalizer import QueryNormalizer
from src.services.synonym_expander import SynonymExpander
from src.services.redis_cache import RedisCacheManager
from src.services.db import get_db_connection

class SearchService:
    """
    Orchestrates the search workflow.
    Integrates Normalization -> Expansion -> Cache -> Database.
    """

    def __init__(self):
        # Initialize dependencies
        self.expander = SynonymExpander(settings.SYNONYM_FILE_PATH)
        self.cache = RedisCacheManager()

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

        # 2. Expand Query
        expanded_query = self.expander.expand(normalized_query)

        # 3. Check Cache
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
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Base Query using PGroonga operator &@
                sql = """
                    SELECT 
                        url, 
                        title, 
                        content as snippet,
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
                
                return [dict(row) for row in rows]
        finally:
            conn.close()

@lru_cache()
def get_search_service() -> SearchService:
    """
    Singleton provider for SearchService.
    """
    return SearchService()
