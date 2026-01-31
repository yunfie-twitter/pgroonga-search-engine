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
        """
        Initializes connection to Redis Queue using settings.
        """
        self.redis_conn = redis.from_url(settings.REDIS.URL)
        self.queue = Queue(settings.REDIS.QUEUE_NAME, connection=self.redis_conn)

    def enqueue_jobs(self, urls: List[str]) -> List[str]:
        """
        Submits a batch of URLs to the crawl queue.
        
        Args:
            urls (List[str]): URLs to crawl.
            
        Returns:
            List[str]: List of enqueued Job IDs.
        """
        job_ids = []
        for url in urls:
            # We explicitly pass the function object `perform_crawl_job`
            job = self.queue.enqueue(
                perform_crawl_job, 
                url, 
                job_timeout=settings.CRAWLER.JOB_TIMEOUT
            )
            job_ids.append(job.get_id())
            
        return job_ids

    def get_queue_info(self) -> Dict[str, Any]:
        """
        Returns snapshot metrics of the crawler queue.
        
        Returns:
            Dict[str, Any]: Queue statistics (count, empty status, etc.)
        """
        return {
            "queue_name": self.queue.name,
            "job_count": self.queue.count,
            "is_empty": self.queue.is_empty(),
            "connection_status": "connected" if self.redis_conn.ping() else "disconnected"
        }
