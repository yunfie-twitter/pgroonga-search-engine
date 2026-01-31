# src/workers/crawler_worker.py
# Responsibility: Runs the RQ Worker AND the autonomous dispatch loop.

import redis
from rq import Worker, Queue, Connection
import os
import sys
import time
import threading

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.config.settings import settings
from src.crawler.scheduler import CrawlScheduler

def run_scheduler_loop():
    """
    Background thread that periodically checks the DB for due jobs
    and pushes them to the Redis Queue.
    """
    scheduler = CrawlScheduler()
    print("[Scheduler Thread] Started.")
    
    while True:
        try:
            # Dispatch jobs
            scheduler.dispatch_pending_jobs(limit=20)
            
            # Wait before next check to avoid hammering DB
            # 10 seconds is a reasonable balance for responsiveness vs load
            time.sleep(10)
        except Exception as e:
            print(f"[Scheduler Thread] Error: {e}")
            time.sleep(30) # Backoff on error

def start_worker():
    """
    Starts the Scheduler thread and the RQ Worker.
    """
    redis_url = settings.REDIS.URL
    queue_name = settings.REDIS.QUEUE_NAME

    # Start Scheduler in background
    t = threading.Thread(target=run_scheduler_loop, daemon=True)
    t.start()

    # Start RQ Worker (Blocking)
    try:
        conn = redis.from_url(redis_url)
        with Connection(conn):
            print(f"[Worker] Starting worker on queue: '{queue_name}'")
            worker = Worker([queue_name])
            worker.work()
    except Exception as e:
        print(f"[Worker] Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    start_worker()
