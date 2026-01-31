# src/crawler/job.py
# Responsibility: Defines the atomic crawl task executed by RQ workers.

from src.crawler.crawler import WebCrawler
from src.indexer.indexer import Indexer
from src.crawler.scheduler import CrawlScheduler

def perform_crawl_job(url: str, depth: int = 0) -> None:
    """
    Executes the full crawl pipeline for a single URL.
    
    Args:
        url (str): The target URL to crawl.
        depth (int): Current depth of the URL in the crawl tree.
    """
    print(f"[Worker] Starting job for: {url} (Depth: {depth})")
    
    scheduler = CrawlScheduler()
    # Note: Frequency check is done by Scheduler before dispatch, 
    # so we assume if we are here, we are allowed to crawl.

    # 1. Web Crawling
    crawler = WebCrawler()
    page_data = crawler.fetch_and_parse(url)

    if not page_data:
        print(f"[Worker] Failed to fetch/parse {url}")
        scheduler.mark_crawled(url, success=False)
        return

    # 2. Indexing
    indexer = Indexer()
    try:
        success = indexer.upsert_page(page_data)
    except Exception as e:
        print(f"[Worker] Indexing exception for {url}: {e}")
        success = False

    # 3. Recursive Link Discovery (Auto-Crawl)
    if success:
        links = page_data.get('links', [])
        scheduler.process_discovered_links(links, parent_depth=depth)

    # 4. Status Update
    scheduler.mark_crawled(url, success=success)
    print(f"[Worker] Finished {url}. Success: {success}")

# Alias for compatibility
perform_crawl = perform_crawl_job
