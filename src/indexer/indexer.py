# src/indexer/indexer.py
# Responsibility: Handles persistent storage (UPSERT) of crawled web pages into the database.

from typing import List, Dict, Optional
from src.services.db import DBTransaction

class Indexer:
    """
    Manages database indexing operations.
    Ensures that content updates are handled atomically where possible.
    """

    def upsert_page(self, page_data: Dict) -> bool:
        """
        Updates or Inserts a single page record.
        
        Args:
            page_data: Dictionary containing url, title, content, etc.
        
        Returns:
            bool: True if operation was successful.
        """
        return self.upsert_batch([page_data]) == 1

    def upsert_batch(self, pages: List[Dict]) -> int:
        """
        Batch UPSERTs multiple pages.
        
        Args:
            pages: List of page data dictionaries.
            
        Returns:
            int: Number of pages successfully processed.
        """
        if not pages:
            return 0

        success_count = 0
        
        # SQL for UPSERT (On Conflict Update)
        sql = """
            INSERT INTO web_pages (
                url, title, content, category, published_at, updated_at, crawled_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (url) 
            DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                category = EXCLUDED.category,
                published_at = COALESCE(EXCLUDED.published_at, web_pages.published_at),
                updated_at = NOW(),
                crawled_at = NOW()
        """

        # We use a single transaction for the batch.
        # Note: If one fails, the whole block rolls back in strict mode.
        # For a crawler, we might prefer partial success, but for simplicity/integrity,
        # we treat a batch as a unit or iterate inside. 
        # Here we iterate inside the transaction context.
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    for page in pages:
                        try:
                            cur.execute(sql, (
                                page['url'],
                                page['title'],
                                page['content'],
                                page.get('category', 'general'),
                                page.get('published_at')
                            ))
                            success_count += 1
                        except Exception as e:
                            # In a real transaction block, a failed execute invalidates the transaction.
                            # So we cannot "continue" after a PG error in the same transaction easily without SAVEPOINTs.
                            # For simplicity in this refactor, we let the first error roll back the batch.
                            # This encourages fixing data issues rather than ignoring them.
                            print(f"[Indexer] Failed to index {page.get('url')}: {e}")
                            raise
        except Exception as e:
            print(f"[Indexer] Batch transaction failed: {e}")
            return 0
            
        return success_count
