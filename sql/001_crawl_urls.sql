-- Crawler URL Management (Sequential Idempotent Migration)
-- 順序依存性を完全に解決し、どの状態からでも復旧可能なマイグレーションスクリプト。
-- インデックス作成は全てのカラムが存在することを保証した後にのみ行います。

-- [Step 1] ENUM Type Definition (Safe)
-- 既存のENUM型がある場合は何もしない（エラーを出さない）
-- DROP CASCADEは禁止。既存データを破壊するため。
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

-- [Step 2] Create Table (Minimal Base)
-- 主キーの url のみで作成。カラム追加は後続のステップで個別に行う。
CREATE TABLE IF NOT EXISTS crawl_urls (
    url TEXT PRIMARY KEY
);

-- [Step 3] Add Columns Sequentially (Idempotent)
-- 各カラムの存在を確認し、なければ追加します。
-- domain, depth, status, score などアプリ動作に必須なカラムを確実に作成します。

DO $$ 
BEGIN
    -- domain
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='domain') THEN
        ALTER TABLE crawl_urls ADD COLUMN domain TEXT NOT NULL DEFAULT '';
    END IF;

    -- depth
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='depth') THEN
        ALTER TABLE crawl_urls ADD COLUMN depth INTEGER NOT NULL DEFAULT 0;
    END IF;

    -- status (Vital Column)
    -- ここで status カラムが確実に作成されます。
    -- crawl_status 型へのキャストが必要な場合に備え、明示的に型指定します。
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='crawl_urls' AND column_name='status') THEN
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

-- [Step 4] Create Indexes (Safe & Dependent on Columns)
-- この時点で status, domain, score, next_crawl_at が存在することはStep 3により保証されています。
-- したがって、status を参照する PARTIAL INDEX を作成してもエラーになりません。

-- Domain Status Index
CREATE INDEX IF NOT EXISTS idx_crawl_urls_domain_status 
ON crawl_urls (domain, status);

-- Priority Queue Index
-- status カラムを用いた部分インデックス
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
