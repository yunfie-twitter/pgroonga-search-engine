# src/workers/crawler_worker.py
# Responsibility: Entry point for the RQ worker process. Consumes jobs from Redis.

import redis
from rq import Worker, Queue, Connection
import os
import sys

# Ensure project root is in python path to resolve 'src' imports correctly
sys.path.append(os.getcwd())

from src.config.settings import settings

def start_worker():
    """
    Initializes and starts a blocking RQ worker.
    Continuously polls Redis for new crawl jobs.
    """
    redis_url = settings.REDIS.URL
    queue_name = settings.REDIS.QUEUE_NAME

    try:
        conn = redis.from_url(redis_url)
        with Connection(conn):
            print(f"[Worker] Starting worker listening on queue: '{queue_name}'")
            worker = Worker([queue_name])
            worker.work()
    except Exception as e:
        print(f"[Worker] Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    start_worker()
