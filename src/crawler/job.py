from src.crawler.crawler import WebCrawler
from src.indexer.indexer import Indexer
from src.crawler.frequency import CrawlFrequencyManager

def perform_crawl(url: str):
    """
    The atomic task executed by RQ workers.
    Integrates Frequency Check -> Crawl -> Index -> Metadata Update.
    
    Args:
        url (str): Target URL.
    """
    print(f"[Worker] Processing job for: {url}")
    
    # 1. Check Frequency
    if not CrawlFrequencyManager.check_can_crawl(url):
        print(f"[Worker] Skipped {url} due to frequency limits.")
        return

    # 2. Execute Crawl
    crawler = WebCrawler()
    # Returns dict or None
    page_data = crawler.crawl(url)

    if not page_data:
        print(f"[Worker] Failed to crawl {url}")
        CrawlFrequencyManager.mark_crawled(url, success=False, error_msg="Network or Parser Error")
        return

    # 3. Index Data
    indexer = Indexer()
    success = indexer.index_page(page_data)

    # 4. Update Metadata
    if success:
        CrawlFrequencyManager.mark_crawled(url, success=True)
        print(f"[Worker] Successfully indexed {url}")
    else:
        CrawlFrequencyManager.mark_crawled(url, success=False, error_msg="Indexing Error")
        print(f"[Worker] Failed to index {url}")
