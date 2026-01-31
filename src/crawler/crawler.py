import httpx
from typing import List, Dict, Optional
from src.crawler.parser import PageParser

class WebCrawler:
    """
    Fetches web content and uses the Parser to extract data.
    Designed to be resilient and stateless.
    """

    def __init__(self, timeout: int = 10, user_agent: str = "PGroongaSearchEngineBot/1.0"):
        self.timeout = timeout
        self.headers = {"User-Agent": user_agent}

    def crawl(self, url: str) -> Optional[Dict]:
        """
        Crawls a single URL.
        
        Args:
            url (str): Target URL.

        Returns:
            dict or None: Extracted data or None if fetch/parse failed.
        """
        try:
            # Using httpx for modern HTTP support (HTTP/2 potential)
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()
                
                # Check content type - only crawl HTML
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    print(f"Skipping non-HTML content at {url}: {content_type}")
                    return None

                # Parse the HTML content
                return PageParser.parse(url, response.text)

        except httpx.RequestError as e:
            print(f"Network error crawling {url}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"HTTP error {e.response.status_code} crawling {url}")
            return None
        except Exception as e:
            print(f"Unexpected error crawling {url}: {e}")
            return None

    def crawl_multiple(self, urls: List[str]) -> List[Dict]:
        """
        Sequentially crawls a list of URLs.
        
        TODO: Future optimization could parallelize this using asyncio.
        """
        results = []
        for url in urls:
            data = self.crawl(url)
            if data:
                results.append(data)
        return results
