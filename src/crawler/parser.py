# src/crawler/parser.py
# Responsibility: Abstract parsing logic to extract structured data from raw content.

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup, Tag
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, urljoin
import re

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
            Dict[str, Any]: Normalized data (url, title, content, images, etc.)
        """
        pass

class DefaultHTMLParser(BaseParser):
    """
    Standard HTML parser using BeautifulSoup.
    Optimized for generic web pages with enhanced image extraction.
    """

    # Elements to remove before parsing to reduce noise
    NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg"]

    def parse(self, url: str, html_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. DOM Cleanup (mutates soup)
        self._remove_noise(soup)

        # 2. Field Extraction
        title = self._extract_title(soup)
        content = self._extract_content(soup)
        images = self._extract_images(url, soup)
        published_at = self._extract_date(soup)
        category = self._extract_category(url, soup)

        return {
            "url": url,
            "title": title,
            "content": content,
            "images": images,
            "published_at": published_at,
            "category": category
        }

    def _remove_noise(self, soup: BeautifulSoup) -> None:
        """Removes unnecessary tags to prevent noise in extraction."""
        for tag_name in self.NOISE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extracts the page title."""
        tag = soup.find('title')
        return tag.get_text(strip=True) if tag else "No Title"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """
        Extracts main text content.
        Prioritizes semantic tags like <main> or <article>.
        """
        target = soup.find('main') or soup.find('article') or soup.find('body') or soup
        
        # get_text with separator avoids joining words from adjacent block tags
        text = target.get_text(separator=' ')
        
        # Normalize whitespace: replace newlines/tabs/multi-spaces with single space
        normalized = re.sub(r'\s+', ' ', text).strip()
        return normalized

    def _extract_images(self, base_url: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extracts valid image metadata from the DOM.
        
        Rules:
        - <img> tags only
        - Prefer data-src over src
        - Convert relative URLs to absolute
        - Filter out base64, tiny images, etc.
        """
        images = []
        # Find all images in document order
        img_tags = soup.find_all('img')

        position_counter = 0
        for img in img_tags:
            # 1. Resolve Image URL
            src = img.get('data-src') or img.get('src')
            if not src:
                continue

            # 2. Normalize and Filter URL
            abs_url = self._normalize_url(base_url, src)
            if not abs_url:
                continue

            # 3. Size Heuristic (Skip icons/pixels if dimensions are explicit and small)
            width = self._parse_dimension(img.get('width'))
            height = self._parse_dimension(img.get('height'))
            if (width and width < 32) or (height and height < 32):
                continue
                
            # 4. Extract Metadata
            alt = img.get('alt', '').strip() or None
            
            position_counter += 1
            images.append({
                "url": abs_url,
                "alt": alt,
                "position": position_counter
            })

        return images

    def _normalize_url(self, base_url: str, raw_url: str) -> Optional[str]:
        """
        Converts relative URLs to absolute and filters invalid schemes.
        """
        raw_url = raw_url.strip()
        
        # Filter data URIs
        if raw_url.startswith('data:'):
            return None

        try:
            full_url = urljoin(base_url, raw_url)
            parsed = urlparse(full_url)
            
            # Only allow http/https
            if parsed.scheme not in ('http', 'https'):
                return None
                
            return full_url
        except Exception:
            return None

    def _parse_dimension(self, val: Any) -> Optional[int]:
        """Parses width/height attributes to int."""
        if not val:
            return None
        try:
            # Handle "100px" or "100"
            return int(str(val).lower().replace('px', ''))
        except ValueError:
            return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Attempts to find publication date in meta tags."""
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
        """Guesses category from meta tags or URL structure."""
        # 1. Meta tag priority
        tag = soup.find("meta", {"property": "article:section"})
        if tag and tag.get("content"):
            return tag.get("content")
        
        # 2. URL path heuristic
        path = urlparse(url).path
        parts = [p for p in path.split('/') if p]
        if parts:
            candidate = parts[0]
            # Skip likely locale prefixes or short codes
            if len(candidate) > 2 and candidate not in ('en', 'ja', 'v1', 'api'):
                return candidate
        
        return "general"

# Default instance
PageParser = DefaultHTMLParser()
