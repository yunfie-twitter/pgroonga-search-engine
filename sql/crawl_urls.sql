-- Crawl URLs Table
-- Manages the state of the crawler, including depth and scheduling.

CREATE TYPE crawl_status AS ENUM ('pending', 'crawling', 'done', 'error');

CREATE TABLE IF NOT EXISTS crawl_urls (
    url TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    depth INTEGER NOT NULL DEFAULT 0,
    status crawl_status NOT NULL DEFAULT 'pending',
    
    last_crawled_at TIMESTAMP WITH TIME ZONE,
    next_crawl_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for finding pending jobs efficiently
CREATE INDEX IF NOT EXISTS idx_crawl_urls_status_next 
ON crawl_urls (status, next_crawl_at);

-- Index for domain-based frequency control
CREATE INDEX IF NOT EXISTS idx_crawl_urls_domain 
ON crawl_urls (domain);
