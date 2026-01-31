# src/indexer/indexer.py
# Responsibility: Handles persistent storage (UPSERT) of web pages, unique images, and representative selection.

from typing import List, Dict, Optional
from src.services.db import DBTransaction
from src.indexer.image_selector import ImageSelector

class Indexer:
    """
    Manages database indexing operations.
    Coordinatse page data, image assets, and search text consolidation.
    """

    def upsert_page(self, page_data: Dict) -> bool:
        return self.upsert_batch([page_data]) == 1

    def upsert_batch(self, pages: List[Dict]) -> int:
        if not pages: return 0
        success_count = 0
        
        # 1. Image Asset Upsert (Global unique check)
        sql_image_asset = """
            INSERT INTO images (image_hash, canonical_url)
            VALUES (%s, %s)
            ON CONFLICT (image_hash) DO NOTHING
        """

        # 2. Page Upsert (with representative_image_id placeholder logic)
        # Note: We compute search_text by concatenating Title + Content + Alt Texts
        sql_page = """
            INSERT INTO web_pages (
                url, title, content, category, published_at, updated_at, crawled_at,
                representative_image_id, search_text
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s, %s)
            ON CONFLICT (url) 
            DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                category = EXCLUDED.category,
                published_at = COALESCE(EXCLUDED.published_at, web_pages.published_at),
                updated_at = NOW(),
                crawled_at = NOW(),
                representative_image_id = EXCLUDED.representative_image_id,
                search_text = EXCLUDED.search_text
        """

        # 3. Page-Image Link Upsert
        sql_link_image = """
            INSERT INTO page_images (page_url, image_id, alt_text, position)
            VALUES (%s, (SELECT id FROM images WHERE image_hash = %s), %s, %s)
            ON CONFLICT (page_url, image_id) DO UPDATE SET
                alt_text = EXCLUDED.alt_text,
                position = EXCLUDED.position,
                updated_at = NOW()
        """
        
        # 4. Cleanup old links
        sql_delete_links = "DELETE FROM page_images WHERE page_url = %s"

        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    for page in pages:
                        page_url = page['url']
                        images = page.get('images', [])

                        # A. Register Unique Images
                        for img in images:
                            cur.execute(sql_image_asset, (img['hash'], img['url']))

                        # B. Select Representative Image Hash
                        rep_hash = ImageSelector.select_best_image(images)
                        rep_id = None
                        if rep_hash:
                            # Resolve Hash to ID immediately for FK
                            cur.execute("SELECT id FROM images WHERE image_hash = %s", (rep_hash,))
                            res = cur.fetchone()
                            if res: rep_id = res[0]

                        # C. Construct Search Text (Title + Content + Alts)
                        alt_texts = [img['alt'] for img in images if img.get('alt')]
                        search_text_body = f"{page['title']}\n{page['content']}\n{' '.join(alt_texts)}"

                        # D. Upsert Page
                        cur.execute(sql_page, (
                            page_url,
                            page['title'],
                            page['content'],
                            page.get('category', 'general'),
                            page.get('published_at'),
                            rep_id,
                            search_text_body
                        ))

                        # E. Sync Page-Image Links
                        cur.execute(sql_delete_links, (page_url,))
                        for img in images:
                            cur.execute(sql_link_image, (
                                page_url,
                                img['hash'],
                                img.get('alt'),
                                img.get('position')
                            ))
                        
                        success_count += 1

        except Exception as e:
            print(f"[Indexer] Batch transaction failed: {e}")
            return 0
            
        return success_count
