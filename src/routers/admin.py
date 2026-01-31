from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List

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
    job_ids: List[str]

@router.post("/crawl", response_model=CrawlResponse)
def trigger_crawl(req: CrawlRequest):
    """
    Triggers an asynchronous crawl by enqueuing jobs to Redis Queue.
    """
    url_strings = [str(u) for u in req.urls]
    
    if not url_strings:
        raise HTTPException(status_code=400, detail="No URLs provided")

    client = AsyncCrawlerClient()
    job_ids = client.enqueue_jobs(url_strings)

    return CrawlResponse(
        message="Crawl jobs queued successfully",
        target_count=len(url_strings),
        job_ids=job_ids
    )

@router.get("/crawl/status")
def get_crawl_status():
    """
    Returns the status of the crawler queue.
    """
    client = AsyncCrawlerClient()
    return client.get_queue_info()
