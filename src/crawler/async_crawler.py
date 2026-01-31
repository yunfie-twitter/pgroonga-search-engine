# src/crawler/async_crawler.py
# Responsibility: Client interface for enqueueing crawl jobs to Redis Queue (RQ).

import redis
from rq import Queue
from typing import List, Dict, Any
from src.config.settings import settings
from src.crawler.job import perform_crawl_job

class AsyncCrawlerClient:
    """
    Facade for interacting with the asynchronous crawler queue.
    Abstracts away the details of Redis/RQ connection.
    """

    def __init__(self):
        self.redis_conn = redis.from_url(settings.REDIS.URL)
        self.queue = Queue(settings.REDIS.QUEUE_NAME, connection=self.redis_conn)

    def enqueue_jobs(self, urls: List[str]) -> List[str]:
        """
        Legacy batch enqueue (Depth 0 assumed).
        Used by Admin API manually.
        """
        job_ids = []
        for url in urls:
            job_ids.append(self.enqueue_job(url, depth=0))
        return job_ids

    def enqueue_job(self, url: str, depth: int) -> str:
        """
        Enqueues a single job with depth context.
        """
        job = self.queue.enqueue(
            perform_crawl_job, 
            url, 
            depth, # Argument 2 for job function
            job_timeout=settings.CRAWLER.JOB_TIMEOUT
        )
        return job.get_id()

    def get_queue_info(self) -> Dict[str, Any]:
        return {
            "queue_name": self.queue.name,
            "job_count": self.queue.count,
            "is_empty": self.queue.is_empty(),
            "connection_status": "connected" if self.redis_conn.ping() else "disconnected"
        }
