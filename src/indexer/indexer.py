# src/indexer/indexer.py
# Responsibility: Handles persistent storage (UPSERT) of crawled web pages and their associated images.

from typing import List, Dict, Optional
from src.services.db import DBTransaction

class Indexer:
    """
    Manages database indexing operations.
    Ensures that content updates and associated image metadata are handled atomically.
    """

    def upsert_page(self, page_data: Dict) -> bool:
        """
        Updates or Inserts a single page record and its images.
        """
        return self.upsert_batch([page_data]) == 1

    def upsert_batch(self, pages: List[Dict]) -> int:
        """
        Batch UPSERTs multiple pages and their images.
        Uses a transaction to ensure data consistency.
        """
        if not pages:
            return 0

        success_count = 0
        
        # SQL for Page UPSERT
        sql_page = """
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
        
        # SQL for Image Cleanup (Differential Update Strategy)
        # We remove all existing images for the page before inserting new ones
        # to ensure the DB reflects exactly what was found in the latest crawl.
        sql_delete_images = "DELETE FROM page_images WHERE page_url = %s"

        # SQL for Image Insert
        sql_insert_image = """
            INSERT INTO page_images (page_url, image_url, alt_text, position)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (page_url, image_url) DO UPDATE SET
                alt_text = EXCLUDED.alt_text,
                position = EXCLUDED.position,
                updated_at = NOW()
        """

        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    for page in pages:
                        page_url = page['url']
                        try:
                            # 1. Upsert Page
                            cur.execute(sql_page, (
                                page_url,
                                page['title'],
                                page['content'],
                                page.get('category', 'general'),
                                page.get('published_at')
                            ))
                            
                            # 2. Sync Images
                            # Delete existing images for this page to handle removals
                            # (Strict synchronization with current crawl state)
                            cur.execute(sql_delete_images, (page_url,))
                            
                            # Insert new images
                            images = page.get('images', [])
                            for img in images:
                                cur.execute(sql_insert_image, (
                                    page_url,
                                    img['url'],
                                    img.get('alt'),
                                    img.get('position')
                                ))
                            
                            success_count += 1
                        except Exception as e:
                            print(f"[Indexer] Failed to index {page_url}: {e}")
                            # Raise to rollback the specific batch if critical, 
                            # or let the transaction block handle it.
                            raise

        except Exception as e:
            print(f"[Indexer] Batch transaction failed: {e}")
            return 0
            
        return success_count
