# src/crawler/link_extractor.py
# Responsibility: Extract, filter, and normalize links from parsed HTML.

from typing import List, Set
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from src.config.settings import settings


class LinkExtractor:
    """
    Extracts internal navigation links from HTML content.
    Enforces rules like 'same domain only' and exclusion patterns.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_depth = settings.CRAWLER.MAX_DEPTH

    def extract_links(self, html_content: str) -> List[str]:
        """
        Parses HTML and returns a list of unique, normalized, same-domain URLs.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        return self.extract_links_from_soup(soup)

    def extract_links_from_soup(self, soup: BeautifulSoup) -> List[str]:
        """
        Extracts links directly from a BeautifulSoup object.
        Avoids re-parsing if the caller already has a soup object.
        """
        links: Set[str] = set()

        for a_tag in soup.find_all('a', href=True):
            raw_href = a_tag['href']

            # 1. Skip obvious non-links
            if self._is_ignored_scheme(raw_href):
                continue

            # 2. Normalize to Absolute URL
            abs_url = urljoin(self.base_url, raw_href)

            # 3. Validation Rules
            if not self._is_valid_target(abs_url):
                continue

            # 4. Final Normalization (Fragment removal, etc)
            normalized_url = self._normalize(abs_url)

            links.add(normalized_url)

        return list(links)

    def _is_ignored_scheme(self, href: str) -> bool:
        href = href.lower().strip()
        return href.startswith(('mailto:', 'tel:', 'javascript:', '#'))

    def _is_valid_target(self, url: str) -> bool:
        parsed = urlparse(url)

        # Rule: Same Domain Only
        if parsed.netloc != self.domain:
            return False

        # Rule: Skip specific paths (Login/Logout)
        path = parsed.path.lower()
        if any(keyword in path for keyword in ['/login', '/logout', '/signout', '/admin']):
            return False

        # Rule: Skip non-http schemes
        if parsed.scheme not in ('http', 'https'):
            return False

        return True

    def _normalize(self, url: str) -> str:
        """
        Removes fragment and sorts query params for consistency.
        """
        parsed = urlparse(url)

        # Sort query params? Simplification: Remove fragment only for now
        # Ideally, we should sort query params to avoid duplication like ?a=1&b=2 vs ?b=2&a=1
        # But standardizing on urlunparse is a good start.

        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query, # Keeping query as is, assuming order matters unless proved otherwise
            '' # Fragment removed
        ))
