import re
import unicodedata


class QueryNormalizer:
    """
    Responsible for normalizing search queries to standard format.
    Ensures that minor variations in input (case, width) yield the same search results.
    """

    @staticmethod
    def normalize(query: str) -> str:
        """
        Normalizes the user search query.

        Steps:
        1. NFKC Normalization: Unifies full-width/half-width characters.
        2. Lowercasing: Ensures case-insensitive matching.
        3. Whitespace cleanup: Trims and collapses multiple spaces.

        Args:
            query (str): Raw user query.

        Returns:
            str: Normalized query.
        """
        if not query:
            return ""

        # 1. Unicode Normalization (NFKC)
        # Handles full-width/half-width (e.g., Ａ -> A)
        normalized = unicodedata.normalize('NFKC', query)

        # 2. Lowercase
        normalized = normalized.lower()

        # 3. Whitespace cleanup
        # Replace sequence of whitespace with single space, remove leading/trailing
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized
