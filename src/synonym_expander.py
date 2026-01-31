import json
import os
from typing import Dict, List

class SynonymExpander:
    """
    Handles the expansion of search terms using a predefined synonym dictionary.
    """
    
    def __init__(self, dictionary_path: str):
        """
        Initializes the expander by loading the dictionary from a JSON file.
        
        Args:
            dictionary_path (str): File path to the synonyms.json.
        """
        self.synonyms: Dict[str, List[str]] = self._load_dictionary(dictionary_path)

    def _load_dictionary(self, path: str) -> Dict[str, List[str]]:
        """
        Loads the synonym map. Returns empty dict if file missing or invalid.
        """
        if not os.path.exists(path):
            print(f"WARN: Synonym file not found at {path}")
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
        - Split query into terms.
        - For each term, look up synonyms.
        - Combine term and synonyms with OR logic: (term OR synonym1 OR synonym2)
        - Join groups with space (AND logic in PGroonga default).
        
        Args:
            normalized_query (str): The pre-processed query.
            
        Returns:
            str: The expanded query string for PGroonga.
        """
        if not normalized_query:
            return ""

        terms = normalized_query.split()
        expanded_groups = []

        for term in terms:
            # Retrieve synonyms, default to empty list if none found
            # Use get() to be safe
            # The dictionary keys should ideally be normalized too, 
            # assuming synonyms.json keys match the normalization output (lowercase).
            syn_list = self.synonyms.get(term, [])
            
            # Create a set of all variants (original + synonyms) to remove duplicates
            variants = set([term] + syn_list)
            sorted_variants = sorted(list(variants))
            
            if len(sorted_variants) > 1:
                # PGroonga syntax: (A OR B)
                # We use Python string formatting to build this.
                group_str = f"({' OR '.join(sorted_variants)})"
                expanded_groups.append(group_str)
            else:
                expanded_groups.append(term)

        # Join all groups. Space implies AND in standard search queries.
        return " ".join(expanded_groups)
