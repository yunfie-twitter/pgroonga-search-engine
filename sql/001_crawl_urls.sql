-- Crawler URL Management (Definitive Migration)
-- アプリ起動前に crawl_urls テーブルのスキーマを完全に保証するスクリプト。
-- 途中まで作成されたテーブル、カラム不足、インデックス不足など、あらゆる状態から復旧します。

-- 1. ENUM Type Definition (Safe & Idempotent)
-- 既存のENUM型がある場合は何もしない（エラーを出さない）
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'crawl_status') THEN
        CREATE TYPE crawl_status AS ENUM (
            'pending',
            'crawling',
            'done',
            'error',
            'blocked',
            'deleted'
        );
    END IF;
END $$;

-- 2. Create Table (Minimal Base)
-- 主キーとなる url と domain だけを持つ最小構成で作成。
-- すでにテーブルがある場合は何もしない。
CREATE TABLE IF NOT EXISTS crawl_urls (
    url TEXT PRIMARY KEY,
    domain TEXT NOT NULL
);

-- 3. Add Columns Safely (Migration Logic)
-- 各カラムについて「存在しなければ追加する」処理を実行します。
-- これにより、status カラムが無い古いDBも自動的に修復されます。

DO $$ 
BEGIN
    -- depth
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='depth') THEN
        ALTER TABLE crawl_urls ADD COLUMN depth INTEGER NOT NULL DEFAULT 0;
    END IF;

    -- status (Vital Column)
    -- アプリケーションの動作に必須なため、必ず NOT NULL DEFAULT 'pending' で追加します。
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='status') THEN
        -- ENUM型 'crawl_status' を使用
        ALTER TABLE crawl_urls ADD COLUMN status crawl_status NOT NULL DEFAULT 'pending';
    END IF;

    -- score
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='score') THEN
        ALTER TABLE crawl_urls ADD COLUMN score DOUBLE PRECISION NOT NULL DEFAULT 100.0;
    END IF;

    -- error_count
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='error_count') THEN
        ALTER TABLE crawl_urls ADD COLUMN error_count INTEGER NOT NULL DEFAULT 0;
    END IF;

    -- blocked_reason
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='blocked_reason') THEN
        ALTER TABLE crawl_urls ADD COLUMN blocked_reason TEXT;
    END IF;

    -- last_crawled_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='last_crawled_at') THEN
        ALTER TABLE crawl_urls ADD COLUMN last_crawled_at TIMESTAMP WITH TIME ZONE;
    END IF;

    -- next_crawl_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='next_crawl_at') THEN
        ALTER TABLE crawl_urls ADD COLUMN next_crawl_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;

    -- created_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='created_at') THEN
        ALTER TABLE crawl_urls ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;

    -- updated_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='updated_at') THEN
        ALTER TABLE crawl_urls ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;

    -- deleted_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='deleted_at') THEN
        ALTER TABLE crawl_urls ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
    END IF;

END $$;

-- 4. Create Indexes (Safe & Dependent on Columns)
-- カラム追加が確実に行われた後にインデックスを作成します。
-- 部分インデックス (WHERE status IN ...) は status カラムが必須なため、このタイミングで行うのが安全です。

-- Domain Status Index
CREATE INDEX IF NOT EXISTS idx_crawl_urls_domain_status 
ON crawl_urls (domain, status);

-- Priority Queue Index
-- 既に同名のインデックスがある場合はスキップします
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'crawl_urls' AND indexname = 'idx_crawl_priority'
    ) THEN
        CREATE INDEX idx_crawl_priority 
        ON crawl_urls (score DESC, next_crawl_at ASC) 
        WHERE status IN ('pending', 'done', 'error');
    END IF;
END $$;
