# src/crawler/crawler.py
# Responsibility: Fetches raw content from a given URL using HTTP and delegates parsing.

import httpx
from typing import Optional, Dict
from src.crawler.parser import PageParser, BaseParser
from src.config.settings import settings

class WebCrawler:
    """
    Component responsible for network IO and content retrieval.
    Designed to be parser-agnostic through dependency injection (defaults to PageParser).
    """

    def __init__(self, parser: BaseParser = PageParser):
        """
        Args:
            parser (BaseParser): Strategy for parsing content. Defaults to DefaultHTMLParser.
        """
        self.timeout = settings.CRAWLER.REQUEST_TIMEOUT
        self.headers = {"User-Agent": settings.CRAWLER.USER_AGENT}
        self.parser = parser

    def fetch_and_parse(self, url: str) -> Optional[Dict]:
        """
        Fetches the page and parses it using the configured parser.
        
        Args:
            url (str): Target URL.
            
        Returns:
            Optional[Dict]: Parsed page data, or None on failure.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()
                
                # Check for HTML content before parsing
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type:
                    print(f"[Crawler] Skipped {url}: Non-HTML content ({content_type})")
                    return None

                # Delegate parsing to the injected strategy
                return self.parser.parse(url, response.text)

        except httpx.RequestError as e:
            print(f"[Crawler] Network error on {url}: {e}")
        except httpx.HTTPStatusError as e:
            print(f"[Crawler] HTTP {e.response.status_code} on {url}")
        except Exception as e:
            print(f"[Crawler] Unexpected error on {url}: {e}")
            
        return None
