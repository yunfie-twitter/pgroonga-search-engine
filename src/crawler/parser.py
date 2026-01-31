# src/crawler/parser.py
# Responsibility: Abstract parsing logic to extract structured data from raw content.

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup, Tag
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, urlunparse
import re
import hashlib

class BaseParser(ABC):
    """
    Abstract base class for content parsers.
    """
    
    @abstractmethod
    def parse(self, url: str, content: str) -> Dict[str, Any]:
        pass

class DefaultHTMLParser(BaseParser):
    """
    Standard HTML parser using BeautifulSoup.
    Optimized for generic web pages with enhanced image extraction and hashing.
    """

    NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg"]

    def parse(self, url: str, html_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. DOM Cleanup
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
        for tag_name in self.NOISE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

    def _extract_title(self, soup: BeautifulSoup) -> str:
        tag = soup.find('title')
        return tag.get_text(strip=True) if tag else "No Title"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        target = soup.find('main') or soup.find('article') or soup.find('body') or soup
        text = target.get_text(separator=' ')
        normalized = re.sub(r'\s+', ' ', text).strip()
        return normalized

    def _extract_images(self, base_url: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extracts valid image metadata and generates a hash for deduplication.
        """
        images = []
        img_tags = soup.find_all('img')

        position_counter = 0
        for img in img_tags:
            # 1. Resolve Image URL
            src = img.get('data-src') or img.get('src')
            if not src:
                continue

            # 2. Normalize URL (Absolute)
            abs_url = self._normalize_url(base_url, src)
            if not abs_url:
                continue

            # 3. Size Heuristic
            width = self._parse_dimension(img.get('width'))
            height = self._parse_dimension(img.get('height'))
            if (width and width < 32) or (height and height < 32):
                continue
                
            # 4. Generate Hash
            img_hash = self._generate_image_hash(abs_url)

            # 5. Extract Metadata
            alt = img.get('alt', '').strip() or None
            
            position_counter += 1
            images.append({
                "url": abs_url,
                "hash": img_hash,
                "alt": alt,
                "position": position_counter
            })

        return images

    def _normalize_url(self, base_url: str, raw_url: str) -> Optional[str]:
        raw_url = raw_url.strip()
        if raw_url.startswith('data:'):
            return None

        try:
            full_url = urljoin(base_url, raw_url)
            parsed = urlparse(full_url)
            if parsed.scheme not in ('http', 'https'):
                return None
            return full_url
        except Exception:
            return None

    def _generate_image_hash(self, image_url: str) -> str:
        """
        Generates a SHA256 hash of the normalized image URL (excluding query params).
        Why: To treat the same image asset as identical even if accessed via different tracking parameters.
        """
        try:
            parsed = urlparse(image_url)
            # Reconstruct URL without query and fragment for hashing
            # scheme://netloc/path
            clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
            return hashlib.sha256(clean_url.encode('utf-8')).hexdigest()
        except Exception:
            # Fallback to full URL hash if parsing fails (unlikely due to prior checks)
            return hashlib.sha256(image_url.encode('utf-8')).hexdigest()

    def _parse_dimension(self, val: Any) -> Optional[int]:
        if not val: return None
        try:
            return int(str(val).lower().replace('px', ''))
        except ValueError:
            return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
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
        tag = soup.find("meta", {"property": "article:section"})
        if tag and tag.get("content"):
            return tag.get("content")
        
        path = urlparse(url).path
        parts = [p for p in path.split('/') if p]
        if parts:
            candidate = parts[0]
            if len(candidate) > 2 and candidate not in ('en', 'ja', 'v1', 'api'):
                return candidate
        
        return "general"

PageParser = DefaultHTMLParser()
