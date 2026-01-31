import redis
from rq import Queue
from typing import List, Optional
from src.config.settings import settings
from src.crawler.job import perform_crawl

class AsyncCrawlerClient:
    """
    Client interface for submitting crawl jobs to the Redis Queue.
    Decouples the API from the actual execution logic.
    """

    def __init__(self):
        # Initialize Redis connection for RQ
        self.redis_conn = redis.from_url(settings.REDIS_URL)
        self.queue = Queue('crawler_queue', connection=self.redis_conn)

    def enqueue_jobs(self, urls: List[str]) -> List[str]:
        """
        Submits multiple URLs for processing.
        
        Args:
            urls (list): List of URLs.
            
        Returns:
            list: List of Job IDs.
        """
        job_ids = []
        for url in urls:
            # Enqueue the 'perform_crawl' function
            # job_timeout can be adjusted for long pages
            job = self.queue.enqueue(perform_crawl, url, job_timeout=60)
            job_ids.append(job.get_id())
            
        return job_ids

    def get_queue_info(self) -> dict:
        """
        Returns basic status of the queue.
        """
        return {
            "name": self.queue.name,
            "count": self.queue.count,
            "is_empty": self.queue.is_empty()
        }
