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

    def execute_search(self, raw_query: str, filters: Dict[str, Any], limit: int) -> Dict[str, Any]:
        """
        Executes a search query with full pipeline processing.
        """
        # 1. Normalization
        normalized_query = QueryNormalizer.normalize(raw_query)

        # 2. Log Query (Async-like via DB)
        search_id = self.log_search_query(raw_query, normalized_query)

        # 3. Intent & Synonym Expansion
        # First check explicit Intent Graph (High Precision)
        intent_query = self.expand_query_intent(normalized_query)
        # Then apply standard synonym expansion (if needed)
        expanded_query = self.expander.expand(intent_query)

        # 4. Cache Lookup (Skip for now as we changed return type structure. TODO: Update cache manager)
        # cached_results = self.cache_manager.get_cached_result(normalized_query, filters, limit)
        # if cached_results is not None and isinstance(cached_results, list):
        #      return {"results": cached_results, "keywords": []} # Quick fix for cache compatibility

        # 5. Database Search
        db_rows = self._query_database(expanded_query, filters, limit)

        # 6. Result Processing & Snippet Generation
        processed_results = []
        for row in db_rows:
            snippet = SnippetGenerator.generate(row['content'], normalized_query)
            result_item = {
                "url": row['url'],
                "title": row['title'],
                "score": row['score'],
                "snippet": snippet,
            }
            if "img_url" in row:
                result_item["img_url"] = row["img_url"]
            processed_results.append(result_item)

        # 7. Keyword Extraction
        keywords = self._extract_keywords(db_rows)

        # 8. Cache Storage (TODO: Update cache manager to store full object)
        # self.cache_manager.set_cached_result(normalized_query, filters, limit, processed_results)

        return {
            "search_id": search_id, # Return ID for click tracking
            "results": processed_results,
            "keywords": keywords,
        }

    def log_search_query(self, raw_query: str, normalized_query: str) -> str:
        """
        Logs the search query to the database and returns a generated Search ID.
        """
        sql = """
            INSERT INTO search_logs (query, normalized_query)
            VALUES (%s, %s)
            RETURNING id
        """
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (raw_query, normalized_query))
                    return str(cur.fetchone()[0])
        except Exception as e:
            print(f"Failed to log search query: {e}")
            return ""

    def log_click(self, search_id: str, url: str, rank: int) -> bool:
        """
        Logs a user click on a search result.
        """
        sql = """
            INSERT INTO click_logs (search_log_id, url, rank)
            VALUES (%s, %s, %s)
        """
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (search_id, url, rank))
            return True
        except Exception as e:
            print(f"Failed to log click: {e}")
            return False

    def expand_query_intent(self, normalized_query: str) -> str:
        """
        Checks the Query Relations graph (Intent DB) for high-confidence expansions.
        e.g. "学マス" -> "学園アイドルマスター"
        """
        sql = """
            SELECT target_query, score
            FROM query_relations
            WHERE source_query = %s AND score >= 0.8
            ORDER BY score DESC
            LIMIT 1
        """
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (normalized_query,))
                    res = cur.fetchone()
                    if res:
                        # Append the target query to the original query
                        # e.g. "学マス" -> "学マス OR 学園アイドルマスター"
                        return f"{normalized_query} OR {res[0]}"
        except Exception:
            pass
        return normalized_query

    def _query_database(self, pgroonga_query: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """
        Executes the raw SQL query against PostgreSQL using PGroonga.
        """
        select_clause = """
            SELECT
                web_pages.url,
                web_pages.title,
                web_pages.content,
                pgroonga_score(web_pages.tableoid, web_pages.ctid) AS score
        """
        
        from_clause = "FROM web_pages"
        
        if filters.get("include_images"):
            select_clause += ", images.canonical_url AS img_url"
            from_clause += " LEFT JOIN images ON web_pages.representative_image_id = images.id"

        where_clause = "WHERE web_pages.search_text &@ %s"
        
        params: List[Union[str, int]] = [pgroonga_query]

        # Dynamic SQL construction for filters
        if "category" in filters:
            where_clause += " AND web_pages.category = %s"
            params.append(str(filters["category"]))

        if "domain" in filters:
            where_clause += " AND web_pages.url LIKE %s"
            params.append(f"%{filters['domain']}%")

        if "from" in filters:
            where_clause += " AND web_pages.published_at >= %s"
            params.append(str(filters["from"]))

        if "to" in filters:
            where_clause += " AND web_pages.published_at <= %s"
            params.append(str(filters["to"]))

        # Ordering and limiting
        order_clause = "ORDER BY score DESC LIMIT %s"
        params.append(limit)
        
        sql = f"{select_clause} {from_clause} {where_clause} {order_clause}"

        with DBTransaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                return [dict(row) for row in cur.fetchall()]

    def _extract_keywords(self, rows: List[Dict[str, Any]]) -> List[str]:
        """
        Extracts frequent keywords from the titles of search results using PGroonga.
        """
        if not rows:
            return []

        # Concatenate titles
        text_corpus = " ".join([row['title'] for row in rows])
        # Truncate to avoid huge query payload
        text_corpus = text_corpus[:5000]

        sql = """
            SELECT token, count(*) as freq
            FROM pgroonga_tokenize(%s, 'TokenMecab') AS t(token text, start_offset int, end_offset int, force_prefix bool)
            WHERE length(token) > 1
            GROUP BY token
            ORDER BY freq DESC
            LIMIT 5
        """
        
        try:
             with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (text_corpus,))
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            print(f"Keyword extraction failed: {e}")
            return []


@lru_cache()
def get_search_service() -> SearchService:
    """Dependency injection provider for SearchService."""
    return SearchService()
