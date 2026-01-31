import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
import time

from .config import DB_DSN, SYNONYM_FILE_PATH, REDIS_TTL_SECONDS
from .query_normalizer import normalize_query
from .synonym_expander import SynonymExpander
from .redis_cache import RedisCacheManager

class SearchService:
    """
    Core service class orchestrating the search flow.
    """
    
    def __init__(self):
        # Initialize helper components
        self.expander = SynonymExpander(SYNONYM_FILE_PATH)
        self.cache = RedisCacheManager(ttl_seconds=REDIS_TTL_SECONDS)
        print("SearchService initialized.")

    def _get_db_connection(self):
        """Helper to get a new DB connection."""
        return psycopg2.connect(DB_DSN)

    def search(self, raw_query: str, filters: Optional[Dict[str, str]] = None) -> Dict:
        """
        Executes the full search pipeline.
        
        Flow:
        1. Normalize Query
        2. Check Cache (Hit -> Return)
        3. Expand Query (Miss -> Continue)
        4. Execute PGroonga Search
        5. Save to Cache
        6. Return Result
        
        Args:
            raw_query (str): User input.
            filters (dict, optional): Filters like {'category': 'tech', 'from': '...', 'to': '...'}
            
        Returns:
            Dict: Search response containing results and metadata.
        """
        if filters is None:
            filters = {}
            
        # 1. User Input Normalization
        normalized_query = normalize_query(raw_query)
        
        # 2. Redis Cache Check
        # Using normalized query + filters as key basis
        cached = self.cache.get_result(normalized_query, filters)
        if cached:
            print(f"[INFO] Cache Hit for query: '{normalized_query}'")
            cached['source'] = 'cache'
            return cached

        print(f"[INFO] Cache Miss for query: '{normalized_query}' - Querying DB")

        # 3. Synonym Expansion
        # e.g., "AI" -> "(AI OR artificial intelligence)"
        expanded_query = self.expander.expand(normalized_query)
        
        # 4. PGroonga Full Text Search
        start_time = time.time()
        results = self._execute_db_query(expanded_query, filters)
        duration = time.time() - start_time

        response = {
            "query": raw_query,
            "normalized_query": normalized_query,
            "expanded_query": expanded_query,
            "result_count": len(results),
            "duration_seconds": round(duration, 4),
            "results": results,
            "source": "database"
        }

        # 5. Save to Redis
        # Only cache if we got results? Or cache empty too?
        # Usually cache empty too to prevent slamming DB on known empty queries.
        self.cache.set_result(normalized_query, filters, response)

        return response

    def _execute_db_query(self, pgroonga_query: str, filters: Dict) -> List[Dict]:
        """
        Constructs SQL and queries PostgreSQL.
        """
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Base Query
                # Using &@ operator for PGroonga keyword search.
                # It searches for keywords in the target columns.
                # We concat title and content for the index target.
                sql = """
                    SELECT 
                        id, 
                        url, 
                        title, 
                        category, 
                        published_at,
                        pgroonga_score(tableoid, ctid) AS score
                    FROM web_pages
                    WHERE (title || ' ' || content) &@ %s
                """
                params = [pgroonga_query]

                # Append Filters
                if filters.get("category"):
                    sql += " AND category = %s"
                    params.append(filters["category"])
                
                # Date filtering (ISO strings assumed)
                if filters.get("from"):
                    sql += " AND published_at >= %s"
                    params.append(filters["from"])
                
                if filters.get("to"):
                    sql += " AND published_at <= %s"
                    params.append(filters["to"])

                # Ordering and Limiting
                # Order by PGroonga score (relevance)
                sql += " ORDER BY score DESC LIMIT 50"

                cur.execute(sql, tuple(params))
                return cur.fetchall()
        except Exception as e:
            print(f"ERROR: DB Query failed: {e}")
            return []
        finally:
            conn.close()

if __name__ == "__main__":
    # Demonstration / Test Entry Point
    service = SearchService()
    
    # Example inputs
    test_queries = [
        ("AI", {"category": "tech"}),
        ("Python search", {}),
        ("速い 検索", {})
    ]
    
    print("--- Starting Search Service Demo ---")
    for q, f in test_queries:
        print(f"\nSearching for: '{q}' with filters: {f}")
        try:
            res = service.search(q, f)
            print(f"Result: Found {res['result_count']} items in {res['duration_seconds']}s (Source: {res['source']})")
            print(f"Expanded Query used: {res['expanded_query']}")
        except Exception as e:
            print(f"Search failed (Check DB connection): {e}")
