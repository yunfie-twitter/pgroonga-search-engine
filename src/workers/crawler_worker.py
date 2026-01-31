import redis
from rq import Worker, Queue, Connection
import os
import sys

# Ensure project root is in path for module resolution
sys.path.append(os.getcwd())

from src.config.settings import settings

def start_worker():
    """
    Starts an RQ worker to process the 'crawler_queue'.
    This script is intended to be run as a separate process/container.
    """
    redis_url = settings.REDIS_URL
    conn = redis.from_url(redis_url)

    with Connection(conn):
        queue_name = 'crawler_queue'
        worker = Worker([queue_name])
        print(f"Starting worker for queue: {queue_name}")
        worker.work()

if __name__ == '__main__':
    start_worker()
