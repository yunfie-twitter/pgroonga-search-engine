-- Crawl URLs Table (Extended)
-- Manages crawler state, priority scoring, and error tracking.

DROP TYPE IF EXISTS crawl_status CASCADE;
CREATE TYPE crawl_status AS ENUM ('pending', 'crawling', 'done', 'error', 'blocked', 'deleted');

CREATE TABLE IF NOT EXISTS crawl_urls (
    url TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    depth INTEGER NOT NULL DEFAULT 0,
    status crawl_status NOT NULL DEFAULT 'pending',
    
    -- Scoring for priority queue
    score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    
    -- Error tracking and cleanup
    error_count INTEGER NOT NULL DEFAULT 0,
    blocked_reason TEXT, -- e.g., 'robots.txt', 'infinite_loop', 'max_errors'
    
    last_crawled_at TIMESTAMP WITH TIME ZONE,
    next_crawl_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE -- Logical deletion timestamp
);

-- Index for Priority Queue (Score DESC, Due Date ASC)
CREATE INDEX IF NOT EXISTS idx_crawl_priority 
ON crawl_urls (score DESC, next_crawl_at ASC) 
WHERE status IN ('pending', 'done', 'error');

-- Index for Domain Statistics
CREATE INDEX IF NOT EXISTS idx_crawl_domain_stats 
ON crawl_urls (domain, status);
