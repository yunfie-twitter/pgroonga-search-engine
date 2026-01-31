# src/routers/crawl_status.py
# Responsibility: Read-only API to visualize the crawler's internal state.

from fastapi import APIRouter
from typing import Dict, List, Any
from psycopg2.extras import RealDictCursor
from src.services.db import DBTransaction
from src.crawler.async_crawler import AsyncCrawlerClient

router = APIRouter(
    prefix="/crawl",
    tags=["Crawl Monitor"]
)

@router.get("/status")
def get_status_counts() -> Dict[str, int]:
    """Returns count of URLs in each status."""
    sql = "SELECT status, COUNT(*) as cnt FROM crawl_urls GROUP BY status"
    counts = {}
    with DBTransaction() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            for row in cur.fetchall():
                counts[row[0]] = row[1]
    return counts

@router.get("/domains")
def get_domain_stats(limit: int = 20) -> List[Dict[str, Any]]:
    """Returns top active domains."""
    sql = """
        SELECT domain, COUNT(*) as count, MAX(last_crawled_at) as last_crawl
        FROM crawl_urls
        GROUP BY domain
        ORDER BY count DESC
        LIMIT %s
    """
    stats = []
    with DBTransaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (limit,))
            results = cur.fetchall()
            stats = [dict(row) for row in results]
    return stats

@router.get("/queue")
def get_queue_head(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns the next URLs scheduled to be crawled (Priority View)."""
    sql = """
        SELECT url, domain, depth, score, next_crawl_at, error_count
        FROM crawl_urls
        WHERE status IN ('pending', 'done', 'error')
        ORDER BY score DESC, next_crawl_at ASC
        LIMIT %s
    """
    queue = []
    with DBTransaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (limit,))
            results = cur.fetchall()
            queue = [dict(row) for row in results]
    return queue

@router.get("/rq_info")
def get_rq_info():
    """Returns raw Redis Queue stats."""
    client = AsyncCrawlerClient()
    return client.get_queue_info()
