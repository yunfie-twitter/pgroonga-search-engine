# src/crawler/parser.py
# Responsibility: Abstract parsing logic to extract structured data from raw content.

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from urllib.parse import urlparse

class BaseParser(ABC):
    """
    Abstract base class for content parsers.
    Allows for future extension to support different content types or site-specific logic.
    """
    
    @abstractmethod
    def parse(self, url: str, content: str) -> Dict[str, Any]:
        """
        Parses raw content into a structured dictionary.
        
        Args:
            url (str): The source URL.
            content (str): The raw content (e.g., HTML).
            
        Returns:
            Dict[str, Any]: Normalized data (url, title, content, etc.)
        """
        pass

class DefaultHTMLParser(BaseParser):
    """
    Standard HTML parser using BeautifulSoup.
    Optimized for generic web pages.
    """

    def parse(self, url: str, html_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Cleanup
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
            tag.decompose()

        # 2. Extraction
        title = self._extract_title(soup)
        body_text = self._extract_body(soup)
        published_at = self._extract_date(soup)
        category = self._extract_category(url, soup)

        return {
            "url": url,
            "title": title,
            "content": body_text,
            "published_at": published_at,
            "category": category
        }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        tag = soup.find('title')
        return tag.get_text(strip=True) if tag else "No Title"

    def _extract_body(self, soup: BeautifulSoup) -> str:
        # get_text with separator ensures words don't merge across tags
        text = soup.get_text(separator=' ')
        return ' '.join(text.split())

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        # Extensible list of date meta tags
        meta_targets = [
            {"property": "article:published_time"},
            {"name": "pubdate"},
            {"itemprop": "datePublished"}
        ]
        for attrs in meta_targets:
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                return tag.get("content")
        return None

    def _extract_category(self, url: str, soup: BeautifulSoup) -> str:
        # 1. Meta tag priority
        tag = soup.find("meta", {"property": "article:section"})
        if tag and tag.get("content"):
            return tag.get("content")
        
        # 2. URL path heuristic
        path = urlparse(url).path
        parts = [p for p in path.split('/') if p]
        if parts:
            # Skip likely locale prefixes (en, jp) or short codes
            candidate = parts[0]
            if len(candidate) > 2:
                return candidate
        
        return "general"

# Facade for backward compatibility
# In the future, a factory could choose the parser based on URL or Content-Type
PageParser = DefaultHTMLParser()
