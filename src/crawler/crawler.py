# src/crawler/crawler.py
# Responsibility: Fetches raw HTML content from a given URL using HTTP.

import httpx
from typing import Optional, Dict
from src.crawler.parser import PageParser
from src.config.settings import settings

class WebCrawler:
    """
    Stateful crawler class (can hold session/config).
    Fetches content and delegates parsing.
    """

    def __init__(self):
        self.timeout = settings.CRAWLER.REQUEST_TIMEOUT
        self.headers = {"User-Agent": settings.CRAWLER.USER_AGENT}

    def fetch_and_parse(self, url: str) -> Optional[Dict]:
        """
        Fetches the page and parses it if successful.
        
        Args:
            url (str): Target URL.
            
        Returns:
            Optional[Dict]: Parsed page data, or None on failure.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()
                
                # Basic Content-Type validation
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type:
                    print(f"[Crawler] Skipped {url}: Non-HTML content ({content_type})")
                    return None

                # Delegate to Parser
                return PageParser.parse(url, response.text)

        except httpx.RequestError as e:
            print(f"[Crawler] Network error on {url}: {e}")
        except httpx.HTTPStatusError as e:
            print(f"[Crawler] HTTP {e.response.status_code} on {url}")
        except Exception as e:
            print(f"[Crawler] Unexpected error on {url}: {e}")
            
        return None
