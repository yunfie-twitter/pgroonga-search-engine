from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List

from src.crawler.crawler import WebCrawler
from src.indexer.indexer import Indexer

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

class CrawlRequest(BaseModel):
    urls: List[HttpUrl]

class CrawlResponse(BaseModel):
    message: str
    target_count: int

def background_crawl_task(urls: List[str]):
    """
    Background task to execute crawling and indexing without blocking the API response.
    """
    print(f"Starting background crawl for {len(urls)} URLs...")
    
    # 1. Crawl
    crawler = WebCrawler()
    results = crawler.crawl_multiple(urls)
    
    if not results:
        print("No content crawled.")
        return

    # 2. Index
    indexer = Indexer()
    count = indexer.index_batch(results)
    
    print(f"Background crawl finished. Indexed {count} pages.")

@router.post("/crawl", response_model=CrawlResponse)
def trigger_crawl(req: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Triggers an asynchronous crawl for the specified URLs.
    
    The actual crawling happens in the background to ensure immediate API response.
    """
    # Convert HttpUrl objects to strings
    url_strings = [str(u) for u in req.urls]
    
    if not url_strings:
        raise HTTPException(status_code=400, detail="No URLs provided")

    # Add to background tasks
    background_tasks.add_task(background_crawl_task, url_strings)

    return CrawlResponse(
        message="Crawl task accepted",
        target_count=len(url_strings)
    )
