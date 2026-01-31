# src/crawler/parser.py
# Responsibility: Abstract parsing logic to extract structured data from raw content.

import hashlib
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup, Tag

from src.crawler.link_extractor import LinkExtractor


class BaseParser(ABC):
    @abstractmethod
    def parse(self, url: str, content: str) -> Dict[str, Any]:
        pass


class DefaultHTMLParser(BaseParser):
    """
    Standard HTML parser using BeautifulSoup.
    Optimized for generic web pages with enhanced image extraction and link discovery.
    """

    NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg"]

    def parse(self, url: str, html_content: str) -> Dict[str, Any]:
        # Note: We parse twice (once here, once in LinkExtractor) or share soup.
        # Sharing soup is better for performance.
        soup = BeautifulSoup(html_content, 'html.parser')

        # 0. Extract Links BEFORE cleanup (nav/footer links are valid for crawling)
        extractor = LinkExtractor(base_url=url)
        # We pass the raw string or a fresh soup to extractor if we want full links.
        # Often nav links are good for crawling but bad for 'content' indexing.
        # So we extract links from the raw content or a full soup first.
        links = extractor.extract_links(html_content)

        # 1. DOM Cleanup for Content Extraction
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
            "links": links,  # New field for crawler
            "published_at": published_at,
            "category": category,
        }

    def _remove_noise(self, soup: BeautifulSoup) -> None:
        for tag_name in self.NOISE_TAGS:
            for tag in soup.find_all(tag_name):
                if isinstance(tag, Tag):
                    tag.decompose()

    def _extract_title(self, soup: BeautifulSoup) -> str:
        tag = soup.find('title')
        if isinstance(tag, Tag):
            return tag.get_text(strip=True)
        return "No Title"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        target = soup.find('main') or soup.find('article') or soup.find('body') or soup
        # target can be Tag or BeautifulSoup (which is strictly not Tag but behaves like one for get_text)
        # However, for mypy safety with 'find', we assume it returns Tag | NavigableString | None.
        if target and not isinstance(target, (Tag, BeautifulSoup)):
            return ""
            
        text = target.get_text(separator=' ')
        normalized = re.sub(r'\s+', ' ', text).strip()
        return normalized

    def _extract_images(self, base_url: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        images = []
        img_tags = soup.find_all('img')
        position_counter = 0

        for img in img_tags:
            if not isinstance(img, Tag):
                continue
                
            src = img.get('data-src') or img.get('src')
            # Normalize src if it is a list (e.g. from some parsers/attrs)
            if isinstance(src, list):
                src = " ".join(src)
                
            if not src:
                continue

            abs_url = self._normalize_url(base_url, src)
            if not abs_url:
                continue

            width = self._parse_dimension(img.get('width'))
            height = self._parse_dimension(img.get('height'))

            # Filter out small tracking pixels or icons
            if (width and width < 32) or (height and height < 32):
                continue

            img_hash = self._generate_image_hash(abs_url)
            
            alt_val = img.get('alt', '')
            if isinstance(alt_val, list):
                alt_val = " ".join(alt_val)
            alt = alt_val.strip() if alt_val else None

            position_counter += 1
            images.append({
                "url": abs_url,
                "hash": img_hash,
                "alt": alt,
                "position": position_counter,
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
        try:
            parsed = urlparse(image_url)
            clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
            return hashlib.sha256(clean_url.encode('utf-8')).hexdigest()
        except Exception:
            return hashlib.sha256(image_url.encode('utf-8')).hexdigest()

    def _parse_dimension(self, val: Any) -> Optional[int]:
        if not val:
            return None
        try:
            val_str = str(val)
            if isinstance(val, list):
                val_str = str(val[0])
            return int(val_str.lower().replace('px', ''))
        except (ValueError, IndexError):
            return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        meta_targets = [
            {"property": "article:published_time"},
            {"name": "pubdate"},
            {"itemprop": "datePublished"},
        ]
        for attrs in meta_targets:
            tag = soup.find("meta", attrs=attrs)
            if isinstance(tag, Tag):
                content = tag.get("content")
                if isinstance(content, list):
                    return " ".join(content)
                if content:
                    return content
        return None

    def _extract_category(self, url: str, soup: BeautifulSoup) -> str:
        tag = soup.find("meta", {"property": "article:section"})
        if isinstance(tag, Tag):
            content = tag.get("content")
            if isinstance(content, list):
                return " ".join(content)
            if content:
                return content

        path = urlparse(url).path
        parts = [p for p in path.split('/') if p]
        if parts:
            candidate = parts[0]
            # Simple heuristic to exclude typical non-content path segments
            if len(candidate) > 2 and candidate not in ('en', 'ja', 'v1', 'api'):
                return candidate
        return "general"


PageParser = DefaultHTMLParser()
