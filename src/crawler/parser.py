from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Optional, Any
from urllib.parse import urlparse

class PageParser:
    """
    Responsible for extracting structured data from raw HTML.
    Separated from the crawler logic to allow easier testing and future parser improvements.
    """

    @staticmethod
    def parse(url: str, html_content: str) -> Dict[str, Any]:
        """
        Parses HTML content to extract title, body content, published date, and category.

        Args:
            url (str): The URL of the page (used for heuristic category guessing).
            html_content (str): Raw HTML string.

        Returns:
            dict: Structured data containing:
                  - url
                  - title
                  - content (text only)
                  - published_at (ISO formatted string or None)
                  - category
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Extract Title
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else "No Title"

        # 2. Extract Main Content
        # Remove script and style elements for clean text
        for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
            script_or_style.decompose()
        
        # Get text and clean it up
        text = soup.get_text(separator=' ')
        # Collapse multiple spaces into one
        content = ' '.join(text.split())

        # 3. Extract Published Date
        # Heuristics: Look for meta tags often used for dates
        published_at = PageParser._extract_date(soup)

        # 4. Extract Category
        # Heuristics: URL path segment or meta tags
        category = PageParser._extract_category(url, soup)

        return {
            "url": url,
            "title": title,
            "content": content,
            "published_at": published_at,
            "category": category
        }

    @staticmethod
    def _extract_date(soup: BeautifulSoup) -> Optional[str]:
        """
        Attempts to find a published date from meta tags.
        """
        # Common meta tags for publication dates
        meta_tags = [
            {"property": "article:published_time"},
            {"name": "pubdate"},
            {"name": "date"},
            {"itemprop": "datePublished"}
        ]

        for attrs in meta_tags:
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                # Ideally we'd parse and normalize this date to a datetime object
                # For now, returning the string as found (Postgres usually handles ISO strings well)
                return tag.get("content")
        
        # Fallback: Return current time as default (or None if strict)
        # Requirement says "published_at (if obtainable)". 
        # If not found, returning None is safer than faking it.
        return None

    @staticmethod
    def _extract_category(url: str, soup: BeautifulSoup) -> str:
        """
        Guesses category from URL structure or meta tags.
        """
        # 1. Try meta tag
        category_tag = soup.find("meta", {"property": "article:section"})
        if category_tag and category_tag.get("content"):
            return category_tag.get("content")

        # 2. Heuristic: First significant path segment
        # e.g., example.com/news/article -> 'news'
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if path_parts:
            # Skip 'en', 'jp' language codes if they appear first
            candidate = path_parts[0]
            if len(candidate) > 2: 
                return candidate
        
        return "general"
