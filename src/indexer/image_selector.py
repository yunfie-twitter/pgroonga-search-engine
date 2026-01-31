# src/indexer/image_selector.py
# Responsibility: Determines the 'best' representative image for a page from a list of candidates.

from typing import List, Dict, Optional

class ImageSelector:
    """
    Encapsulates logic for selecting a representative image (e.g., for OGP/Thumbnails).
    """

    @staticmethod
    def select_best_image(images: List[Dict]) -> Optional[str]:
        """
        Selects the best image based on heuristics.
        
        Args:
            images (List[Dict]): List of image metadata dicts (must contain 'hash', 'alt', 'position').
            
        Returns:
            Optional[str]: The hash of the selected image, or None.
        """
        if not images:
            return None

        # Sort candidates based on priority rules:
        # 1. Has Alt text (prioritize semantic meaning)
        # 2. Position (earlier is usually better/more relevant)
        # Note: We don't have dimension info here easily unless passed, assuming parser filtered tiny ones.
        
        sorted_images = sorted(images, key=lambda x: (
            0 if x.get('alt') and len(x.get('alt', '')) > 5 else 1,  # Priority 1: Has meaningful ALT
            x.get('position', 9999)                                  # Priority 2: Appears early
        ))

        return sorted_images[0]['hash']
