from datetime import datetime, timedelta, timezone
from typing import Optional
from src.services.db import get_db_connection

class CrawlFrequencyManager:
    """
    Manages crawl schedules and status to prevent over-crawling.
    """
    
    @staticmethod
    def check_can_crawl(url: str) -> bool:
        """
        Checks if the URL is eligible for crawling based on metadata.
        
        Rules:
        - If record doesn't exist -> eligible (and created).
        - If exists, next_crawl_at <= NOW -> eligible.
        - If exists, next_crawl_at > NOW -> skip.
        
        Args:
            url (str): Target URL.
            
        Returns:
            bool: True if allowed to crawl.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Upsert initial record if not exists to track it
                # Set default next_crawl_at to NOW so it's picked up
                sql_upsert = """
                    INSERT INTO crawl_metadata (url, next_crawl_at, status)
                    VALUES (%s, NOW(), 'pending')
                    ON CONFLICT (url) DO NOTHING
                """
                cur.execute(sql_upsert, (url,))
                conn.commit()

                # Check schedule
                sql_check = """
                    SELECT next_crawl_at 
                    FROM crawl_metadata 
                    WHERE url = %s
                """
                cur.execute(sql_check, (url,))
                row = cur.fetchone()
                
                if not row:
                    return True # Should exist due to insert above
                
                next_at = row[0]
                # Compare timezone-aware datetimes
                if next_at <= datetime.now(timezone.utc):
                    return True
                else:
                    print(f"Skipping {url}: Next crawl at {next_at}")
                    return False
        except Exception as e:
            print(f"Frequency Check Error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def mark_crawled(url: str, success: bool, error_msg: Optional[str] = None):
        """
        Updates metadata after a crawl attempt.
        Calculates next_crawl_at based on interval.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                status = 'completed' if success else 'failed'
                
                # Update logic
                # If success, next time = now + interval
                # If fail, maybe retry sooner? For now, stick to interval to avoid spamming errors.
                
                sql = """
                    UPDATE crawl_metadata
                    SET 
                        last_crawled_at = NOW(),
                        next_crawl_at = NOW() + (crawl_interval_minutes * INTERVAL '1 minute'),
                        status = %s,
                        error_message = %s,
                        updated_at = NOW()
                    WHERE url = %s
                """
                cur.execute(sql, (status, error_msg, url))
                conn.commit()
        except Exception as e:
            print(f"Metadata Update Error: {e}")
            conn.rollback()
        finally:
            conn.close()
