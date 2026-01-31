# src/crawler/job.py
# Responsibility: Defines the atomic crawl task executed by RQ workers.

from src.crawler.crawler import WebCrawler
from src.indexer.indexer import Indexer
from src.crawler.frequency import CrawlFrequencyManager

def perform_crawl_job(url: str) -> None:
    """
    Executes the full crawl pipeline for a single URL.
    This function is the entry point for the RQ worker.
    
    Pipeline:
    1. Check Frequency limits.
    2. Fetch & Parse Page.
    3. Index content.
    4. Update Metadata status.
    
    Args:
        url (str): The target URL to crawl.
    """
    print(f"[Worker] Starting job for: {url}")
    
    # 1. Frequency Check
    if not CrawlFrequencyManager.is_crawl_allowed(url):
        print(f"[Worker] Skipped {url} due to frequency limits.")
        return

    # 2. Web Crawling
    crawler = WebCrawler()
    page_data = crawler.fetch_and_parse(url)

    if not page_data:
        print(f"[Worker] Failed to fetch/parse {url}")
        CrawlFrequencyManager.update_crawl_status(
            url, success=False, error_message="Network or Parser Error"
        )
        return

    # 3. Indexing
    indexer = Indexer()
    try:
        success = indexer.upsert_page(page_data)
    except Exception as e:
        print(f"[Worker] Indexing exception for {url}: {e}")
        success = False

    # 4. Status Update
    if success:
        print(f"[Worker] Successfully indexed {url}")
        CrawlFrequencyManager.update_crawl_status(url, success=True)
    else:
        print(f"[Worker] Failed to index {url}")
        CrawlFrequencyManager.update_crawl_status(
            url, success=False, error_message="Indexing Error"
        )

# Alias for backward compatibility if needed by existing queued jobs (though queue is transient)
perform_crawl = perform_crawl_job
