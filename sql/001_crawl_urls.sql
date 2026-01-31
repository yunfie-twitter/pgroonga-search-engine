-- Crawler URL Management
-- クローラーの状態遷移と優先度を管理します。

-- 1. ENUM Type Definition (Idempotent)
DO $$ BEGIN
    CREATE TYPE crawl_status AS ENUM (
        'pending',
        'crawling',
        'done',
        'error',
        'blocked',
        'deleted'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Create Table (if not exists)
CREATE TABLE IF NOT EXISTS crawl_urls (
    url TEXT PRIMARY KEY,
    domain TEXT NOT NULL
);

-- 3. Add Columns Idempotently (Migration logic)
-- This ensures that if the table exists but is missing columns, they get added.

-- depth
DO $$ BEGIN
    ALTER TABLE crawl_urls ADD COLUMN depth INTEGER NOT NULL DEFAULT 0;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- status
DO $$ BEGIN
    ALTER TABLE crawl_urls ADD COLUMN status crawl_status NOT NULL DEFAULT 'pending';
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- score
DO $$ BEGIN
    ALTER TABLE crawl_urls ADD COLUMN score DOUBLE PRECISION NOT NULL DEFAULT 100.0;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- error_count
DO $$ BEGIN
    ALTER TABLE crawl_urls ADD COLUMN error_count INTEGER NOT NULL DEFAULT 0;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- blocked_reason
DO $$ BEGIN
    ALTER TABLE crawl_urls ADD COLUMN blocked_reason TEXT;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- last_crawled_at
DO $$ BEGIN
    ALTER TABLE crawl_urls ADD COLUMN last_crawled_at TIMESTAMP WITH TIME ZONE;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- next_crawl_at
DO $$ BEGIN
    ALTER TABLE crawl_urls ADD COLUMN next_crawl_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- created_at
DO $$ BEGIN
    ALTER TABLE crawl_urls ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- updated_at
DO $$ BEGIN
    ALTER TABLE crawl_urls ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- deleted_at
DO $$ BEGIN
    ALTER TABLE crawl_urls ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- 4. Create Indexes (Idempotent)
CREATE INDEX IF NOT EXISTS idx_crawl_urls_domain_status 
ON crawl_urls (domain, status);

CREATE INDEX IF NOT EXISTS idx_crawl_priority 
ON crawl_urls (score DESC, next_crawl_at ASC) 
WHERE status IN ('pending', 'done', 'error');
