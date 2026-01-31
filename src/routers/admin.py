# src/routers/admin.py
# Responsibility: Handles administration endpoints, specifically for triggering crawls.

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import List, Dict

from src.crawler.async_crawler import AsyncCrawlerClient

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

# --- Pydantic Models ---
class CrawlRequest(BaseModel):
    urls: List[HttpUrl]

class CrawlResponse(BaseModel):
    message: str
    target_count: int
    job_ids: List[str]

# --- Dependency Injection ---
def get_async_client() -> AsyncCrawlerClient:
    """Provider for AsyncCrawlerClient."""
    return AsyncCrawlerClient()

# --- Endpoints ---
@router.post("/crawl", response_model=CrawlResponse)
def trigger_crawl_endpoint(
    req: CrawlRequest, 
    client: AsyncCrawlerClient = Depends(get_async_client)
):
    """
    Queues a list of URLs for asynchronous crawling.
    """
    # Convert Pydantic HttpUrl to strings
    url_strings = [str(u) for u in req.urls]
    
    if not url_strings:
        raise HTTPException(status_code=400, detail="No URLs provided")

    try:
        job_ids = client.enqueue_jobs(url_strings)
    except Exception as e:
        print(f"Failed to enqueue jobs: {e}")
        raise HTTPException(status_code=503, detail="Queue service unavailable")

    return CrawlResponse(
        message="Crawl jobs queued successfully",
        target_count=len(url_strings),
        job_ids=job_ids
    )

@router.get("/crawl/status")
def get_crawl_status_endpoint(
    client: AsyncCrawlerClient = Depends(get_async_client)
):
    """
    Retrieves the current status of the crawl job queue.
    """
    try:
        return client.get_queue_info()
    except Exception as e:
        raise HTTPException(status_code=503, detail="Could not retrieve queue info")
