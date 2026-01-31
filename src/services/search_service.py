from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any
from functools import lru_cache

from src.config.settings import settings
from src.services.query_normalizer import QueryNormalizer
from src.services.synonym_expander import SynonymExpander
from src.services.redis_cache import RedisCacheManager
from src.services.db import get_db_connection
from src.snippet.snippet_generator import SnippetGenerator

class SearchService:
    """
    Orchestrates the search workflow.
    Integrates Normalization -> Expansion -> Cache -> Database -> Snippet Generation.
    """

    def __init__(self):
        # Initialize dependencies
        self.expander = SynonymExpander(settings.SYNONYM_FILE_PATH)
        self.cache = RedisCacheManager()

    def search(self, raw_query: str, filters: Dict[str, Any], limit: int) -> List[Dict]:
        """
        Executes the search logic.
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
        raw_results = self._execute_db_search(expanded_query, filters, limit)

        # 5. Process Snippets dynamically
        results = []
        for row in raw_results:
            row['snippet'] = SnippetGenerator.generate(row['content'], normalized_query)
            # Remove full content to reduce payload size if desired, 
            # though caching might want full content? 
            # Requirements say "Response... snippet". Usually we don't return full text.
            del row['content']
            results.append(row)

        # 6. Save to Cache
        self.cache.set_result(normalized_query, filters, limit, results)

        return results

    def _execute_db_search(self, pgroonga_query: str, filters: Dict, limit: int) -> List[Dict]:
        """
        Constructs and executes the SQL query.
        """
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Select full content to generate snippet in Python
                sql = """
                    SELECT 
                        url, 
                        title, 
                        content,
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
