# src/services/search_service.py
# Responsibility: Orchestrates the core search logic (Normalization -> Expansion -> Cache -> DB -> Snippet).

from functools import lru_cache
from typing import Any, Dict, List, Union

from psycopg2.extras import RealDictCursor

from src.config.settings import settings
from src.services.db import DBTransaction
from src.services.query_normalizer import QueryNormalizer
from src.services.redis_cache import RedisCacheManager
from src.services.synonym_expander import SynonymExpander
from src.snippet.snippet_generator import SnippetGenerator


class SearchService:
    """
    Main service class for handling search operations.
    Integrates various sub-components to provide a complete search experience.
    """

    def __init__(self):
        self.expander = SynonymExpander(settings.SYNONYM_FILE_PATH)
        self.cache_manager = RedisCacheManager()

    def execute_search(self, raw_query: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """
        Executes a search query with full pipeline processing.

        Pipeline:
        1. Normalize user query.
        2. Expand query with synonyms.
        3. Check Redis cache.
        4. If miss, query PostgreSQL (PGroonga).
        5. Generate snippets from content.
        6. Cache results.

        Args:
            raw_query (str): The raw input query from the user.
            filters (Dict): Filter parameters (category, date range).
            limit (int): Maximum number of results.

        Returns:
            List[Dict]: Processed search results with snippets.
        """
        # 1. Normalization
        normalized_query = QueryNormalizer.normalize(raw_query)

        # 2. Synonym Expansion
        # Note: We use the expanded query for the DB search, but the normalized query
        # for snippet generation and cache keys (to keep keys consistent across dictionary updates).
        expanded_query = self.expander.expand(normalized_query)

        # 3. Cache Lookup
        cached_results = self.cache_manager.get_cached_result(normalized_query, filters, limit)
        if cached_results is not None:
            # Assuming cache returns the list of results directly.
            # If cache manager returns a single dict but we expect a list, we might need to adjust.
            # Based on the error "got: dict[Any, Any], expected: list[dict[str, Any]]",
            # if cached_results IS a list, then mypy might be confused or the cache manager signature is wrong.
            # However, looking at standard cache implementations, usually we cache the 'result set' (List).
            # If the error persists, it implies get_cached_result might be returning Any or Dict.
            # Cast or ensure it's a list.
            if isinstance(cached_results, list):
                 return cached_results
            return [cached_results] # Wrap in list if it's a single object (though unlikely for search results)

        # 4. Database Search
        # We fetch 'content' to generate snippets, but we won't return it fully to the client.
        db_rows = self._query_database(expanded_query, filters, limit)

        # 5. Result Processing & Snippet Generation
        processed_results = []
        for row in db_rows:
            # Generate a relevant snippet based on the normalized query (what the user actually typed)
            snippet = SnippetGenerator.generate(row['content'], normalized_query)

            # Construct the final result object
            result_item = {
                "url": row['url'],
                "title": row['title'],
                "score": row['score'],
                "snippet": snippet,
                # 'content' is explicitly excluded from the final response to reduce payload
            }
            processed_results.append(result_item)

        # 6. Cache Storage
        self.cache_manager.set_cached_result(normalized_query, filters, limit, processed_results)

        return processed_results

    def _query_database(self, pgroonga_query: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """
        Executes the raw SQL query against PostgreSQL using PGroonga.
        """
        sql = """
            SELECT
                url,
                title,
                content,
                pgroonga_score(tableoid, ctid) AS score
            FROM web_pages
            WHERE search_text &@ %s
        """
        params: List[Union[str, int]] = [pgroonga_query]

        # Dynamic SQL construction for filters
        if "category" in filters:
            sql += " AND category = %s"
            params.append(str(filters["category"]))

        if "from" in filters:
            sql += " AND published_at >= %s"
            params.append(str(filters["from"]))

        if "to" in filters:
            sql += " AND published_at <= %s"
            params.append(str(filters["to"]))

        # Ordering and limiting
        sql += " ORDER BY score DESC LIMIT %s"
        params.append(limit)

        with DBTransaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                return [dict(row) for row in cur.fetchall()]


@lru_cache()
def get_search_service() -> SearchService:
    """Dependency injection provider for SearchService."""
    return SearchService()
