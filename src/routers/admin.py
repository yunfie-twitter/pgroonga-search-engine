# src/routers/admin.py
# Responsibility: Handles administration endpoints. Triggers crawls via Scheduler.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List

from src.crawler.scheduler import CrawlScheduler
from src.crawler.async_crawler import AsyncCrawlerClient

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

class CrawlRequest(BaseModel):
    urls: List[HttpUrl]

class CrawlResponse(BaseModel):
    message: str
    target_count: int

@router.post("/crawl", response_model=CrawlResponse)
def trigger_crawl_endpoint(req: CrawlRequest):
    """
    Registers seed URLs to the Crawl Scheduler.
    Actual crawling will be picked up by the autonomous worker.
    """
    url_strings = [str(u) for u in req.urls]
    
    if not url_strings:
        raise HTTPException(status_code=400, detail="No URLs provided")

    scheduler = CrawlScheduler()
    for url in url_strings:
        scheduler.schedule_initial_url(url)
        print(f"[Admin] Registered seed URL: {url}")

    return CrawlResponse(
        message="Seed URLs registered. Crawler will pick them up shortly.",
        target_count=len(url_strings)
    )

@router.get("/crawl/status")
def get_crawl_status_endpoint():
    """
    Retrieves the current status of the crawl job queue.
    """
    try:
        client = AsyncCrawlerClient()
        return client.get_queue_info()
    except Exception as e:
        raise HTTPException(status_code=503, detail="Could not retrieve queue info")
