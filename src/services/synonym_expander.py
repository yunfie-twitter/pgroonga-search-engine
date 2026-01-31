import json
import os
from typing import Dict, List

class SynonymExpander:
    """
    Handles expansion of search queries using a synonym dictionary.
    """

    def __init__(self, dictionary_path: str):
        """
        Args:
            dictionary_path (str): Absolute path to the JSON dictionary file.
        """
        self.synonyms: Dict[str, List[str]] = self._load_dictionary(dictionary_path)

    def _load_dictionary(self, path: str) -> Dict[str, List[str]]:
        """
        Loads the synonym dictionary from JSON.
        Returns empty dict if file not found, to ensure app doesn't crash on missing config.
        """
        if not os.path.exists(path):
            # In production, you might want to log this as a warning
            print(f"WARNING: Synonym file not found: {path}")
            return {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"ERROR: Failed to load synonyms: {e}")
            return {}

    def expand(self, normalized_query: str) -> str:
        """
        Expands keywords in the query.
        
        Logic:
        1. Split query into terms.
        2. Look up each term in the dictionary.
        3. If found, create OR group: (term OR synonym1 OR synonym2).
        4. Join groups with spaces (AND search).

        Args:
            normalized_query (str): The pre-processed query.

        Returns:
            str: Query string formatted for PGroonga (e.g., "(A OR B) (C OR D)").
        """
        if not normalized_query:
            return ""

        terms = normalized_query.split()
        expanded_groups = []

        for term in terms:
            # Get synonyms list (or empty list if none)
            # Assuming dictionary keys are also normalized (lowercase)
            syn_list = self.synonyms.get(term, [])
            
            # Combine original term + synonyms, remove duplicates, sort for determinism
            variants = sorted(list(set([term] + syn_list)))
            
            if len(variants) > 1:
                # Format as (A OR B) for PGroonga
                group = f"({' OR '.join(variants)})"
                expanded_groups.append(group)
            else:
                expanded_groups.append(term)

        # Join groups. Space in PGroonga implies AND.
        return " ".join(expanded_groups)
