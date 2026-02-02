# src/crawler/parser.py
# Responsibility: Extract structured data from web pages, optimized for search indexing.

import hashlib
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl

from bs4 import BeautifulSoup, Tag, NavigableString

from src.crawler.link_extractor import LinkExtractor


# -------------------------------
# Constants
# -------------------------------
DEFAULT_CATEGORY = "general"
MIN_IMAGE_SIZE = 32
NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg"]
COMMON_NOISE_CLASSES = (
    "breadcrumb", "breadcrumbs", "related", "recommend", "share", "social", "cookie", "consent"
)
IMPORTANT_QUERY_KEYS = {"w", "h", "width", "height"}


# -------------------------------
# TypedDicts
# -------------------------------
class ImageInfo(TypedDict):
    url: str
    hash: str
    alt: Optional[str]
    position: int


class ParsedPage(TypedDict):
    url: str
    title: str
    content: str
    images: List[ImageInfo]
    links: List[str]
    published_at: Optional[str]
    category: str


# -------------------------------
# Base Parser
# -------------------------------
class BaseParser(ABC):
    @abstractmethod
    def parse(self, url: str, content: str) -> ParsedPage:
        pass


# -------------------------------
# Default HTML Parser
# -------------------------------
class DefaultHTMLParser(BaseParser):
    """
    Search-optimized HTML parser using BeautifulSoup.
    - Text extraction scoring
    - Noise removal
    - Image extraction (lazy-load / srcset)
    - Link extraction
    - Meta data extraction
    """

    def parse(self, url: str, html_content: str) -> ParsedPage:
        soup = BeautifulSoup(html_content, "html.parser")

        # 0. Extract Links (before cleaning)
        extractor = LinkExtractor(base_url=url)
        links = extractor.extract_links_from_soup(soup)

        # 1. Remove noise from DOM
        self._remove_noise(soup)

        # 2. Extract fields
        title = self._extract_title(soup)
        content = self._extract_content(soup)
        images = self._extract_images(url, soup)
        published_at = self._extract_date(soup)
        category = self._extract_category(url, soup)

        return ParsedPage(
            url=url,
            title=title,
            content=content,
            images=images,
            links=links,
            published_at=published_at,
            category=category,
        )

    # ---------------------------
    # Noise Removal
    # ---------------------------
    def _remove_noise(self, soup: BeautifulSoup) -> None:
        # Remove tags
        for tag_name in NOISE_TAGS:
            for tag in soup.find_all(tag_name):
                if isinstance(tag, Tag):
                    tag.decompose()

        # Remove elements by common class names
        pattern = re.compile("|".join(COMMON_NOISE_CLASSES), re.I)
        for tag in soup.find_all(True, class_=pattern):
            tag.decompose()

    # ---------------------------
    # Title
    # ---------------------------
    def _extract_title(self, soup: BeautifulSoup) -> str:
        # OpenGraph title first
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            return og["content"].strip()
        # Fallback: h1
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            return h1.get_text(strip=True)
        # Fallback: title tag
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            return title_tag.get_text(strip=True)
        return "No Title"

    # ---------------------------
    # Content Extraction
    # ---------------------------
    def _extract_content(self, soup: BeautifulSoup) -> str:
        target = self._find_best_content_node(soup)
        if not target:
            return ""
        text = target.get_text(separator=" ")
        normalized = re.sub(r"\s+", " ", text).strip()
        return normalized

    def _find_best_content_node(self, soup: BeautifulSoup) -> Optional[Tag]:
        candidates = soup.find_all(["article", "main", "section", "div"])
        best = soup.body or soup
        max_len = 0
        for c in candidates:
            if not isinstance(c, Tag):
                continue
            text_len = len(c.get_text(strip=True))
            if text_len > max_len:
                max_len = text_len
                best = c
        return best

    # ---------------------------
    # Images
    # ---------------------------
    def _extract_images(self, base_url: str, soup: BeautifulSoup) -> List[ImageInfo]:
        images: List[ImageInfo] = []
        seen_hashes = set()
        img_tags = soup.find_all("img")
        position_counter = 0

        for img in img_tags:
            if not isinstance(img, Tag):
                continue

            # Lazy-load support
            src = (
                img.get("data-src")
                or img.get("data-original")
                or img.get("data-lazy")
                or img.get("src")
            )

            # srcset support
            if not src and img.get("srcset"):
                src = img.get("srcset").split(",")[0].split()[0]

            if not src:
                continue

            abs_url = self._normalize_url(base_url, src)
            if not abs_url:
                continue

            width = self._parse_dimension(img.get("width"))
            height = self._parse_dimension(img.get("height"))

            if (width and width < MIN_IMAGE_SIZE) or (height and height < MIN_IMAGE_SIZE):
                continue

            img_hash = self._generate_image_hash(abs_url)
            if img_hash in seen_hashes:
                continue
            seen_hashes.add(img_hash)

            alt_val = img.get("alt", "")
            if isinstance(alt_val, list):
                alt_val = " ".join(alt_val)
            alt = alt_val.strip() if alt_val else None

            position_counter += 1
            images.append(ImageInfo(url=abs_url, hash=img_hash, alt=alt, position=position_counter))

        return images

    def _normalize_url(self, base_url: str, raw_url: str) -> Optional[str]:
        raw_url = raw_url.strip()
        if raw_url.startswith("data:"):
            return None
        try:
            full_url = urljoin(base_url, raw_url)
            parsed = urlparse(full_url)
            if parsed.scheme not in ("http", "https"):
                return None

            # Optional: filter query params for hash consistency
            query_items = parse_qsl(parsed.query)
            filtered_query = "&".join(f"{k}={v}" for k, v in query_items if k in IMPORTANT_QUERY_KEYS)
            normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", filtered_query, ""))
            return normalized
        except Exception:
            return None

    def _generate_image_hash(self, image_url: str) -> str:
        try:
            parsed = urlparse(image_url)
            clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
            return hashlib.sha256(clean_url.encode("utf-8")).hexdigest()
        except Exception:
            return hashlib.sha256(image_url.encode("utf-8")).hexdigest()

    def _parse_dimension(self, val: Any) -> Optional[int]:
        if not val:
            return None
        try:
            if isinstance(val, list):
                val = val[0]
            return int(str(val).lower().replace("px", ""))
        except (ValueError, IndexError):
            return None

    # ---------------------------
    # Published date
    # ---------------------------
    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        meta_targets = [
            {"property": "article:published_time"},
            {"property": "og:published_time"},
            {"name": "pubdate"},
            {"name": "date"},
            {"name": "DC.date.issued"},
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

    # ---------------------------
    # Category
    # ---------------------------
    def _extract_category(self, url: str, soup: BeautifulSoup) -> str:
        tag = soup.find("meta", {"property": "article:section"})
        if isinstance(tag, Tag):
            content = tag.get("content")
            if isinstance(content, list):
                return " ".join(content)
            if content:
                return content

        path = urlparse(url).path
        parts = [p for p in path.split("/") if p]
        if parts:
            candidate = parts[0]
            if len(candidate) > 2 and candidate not in ("en", "ja", "v1", "api"):
                return candidate
        return DEFAULT_CATEGORY


# -------------------------------
# Singleton Parser
# -------------------------------
PageParser = DefaultHTMLParser()
