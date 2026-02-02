-- Crawl Metadata Table
-- Manages crawl scheduling and status for each URL to prevent over-crawling.
CREATE TABLE IF NOT EXISTS crawl_metadata (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    last_crawled_at TIMESTAMP WITH TIME ZONE,
    next_crawl_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    crawl_interval_minutes INTEGER DEFAULT 60, -- Default retry interval: 1 hour
    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for finding jobs ready to process
CREATE INDEX IF NOT EXISTS idx_crawl_metadata_schedule 
ON crawl_metadata (next_crawl_at, status);
