import re
from typing import List

class SnippetGenerator:
    """
    Generates high-quality snippets from search results without using LLMs.
    Focuses on extracting sentences that contain search terms.
    """

    MAX_LENGTH = 120
    
    @staticmethod
    def generate(content: str, query: str) -> str:
        """
        Creates a snippet from the content based on the query.

        Args:
            content (str): Full text content (already cleaned of HTML).
            query (str): Normalized search query.

        Returns:
            str: Truncated snippet.
        """
        if not content:
            return ""

        # Normalize query terms for matching
        # Split by space and filter out empty strings
        terms = [t for t in query.lower().split() if t]

        if not terms:
            return SnippetGenerator._truncate(content)

        # Split content into sentences (naive split by delimiters)
        # Using regex to handle punctuation like . ! ? and Japanese 。
        # This regex splits but keeps delimiters attached or separate depending on grouping.
        # Simple approach: Split by punctuation.
        sentences = re.split(r'(?<=[.!。])\s+', content)

        # Score sentences
        # Score = number of unique query terms present
        best_sentence = ""
        max_score = -1

        for sentence in sentences:
            score = 0
            s_lower = sentence.lower()
            for term in terms:
                if term in s_lower:
                    score += 1
            
            if score > max_score:
                max_score = score
                best_sentence = sentence
            
            # Optimization: If we find a sentence with all terms, break early?
            # Maybe not, just finding the first best one is okay.

        # If no terms found in any sentence, return the beginning
        if max_score <= 0:
            return SnippetGenerator._truncate(content)

        return SnippetGenerator._truncate(best_sentence)

    @staticmethod
    def _truncate(text: str) -> str:
        """
        Truncates text to MAX_LENGTH with ellipsis.
        """
        if len(text) <= SnippetGenerator.MAX_LENGTH:
            return text
        return text[:SnippetGenerator.MAX_LENGTH] + "..."
