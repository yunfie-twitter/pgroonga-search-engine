-- Crawler URL Management
-- クローラーの状態遷移と優先度を管理します。

-- 状態管理用ENUM
-- pending: クロール待ち
-- crawling: 実行中（ロック）
-- done: 成功
-- error: 失敗
-- blocked: robots.txtや異常検知でブロック
-- deleted: 404等で論理削除
DROP TYPE IF EXISTS crawl_status CASCADE;
CREATE TYPE crawl_status AS ENUM (
    'pending',
    'crawling',
    'done',
    'error',
    'blocked',
    'deleted'
);

CREATE TABLE IF NOT EXISTS crawl_urls (
    url TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    
    -- クロール制御
    depth INTEGER NOT NULL DEFAULT 0,
    status crawl_status NOT NULL DEFAULT 'pending',
    
    -- 優先度スコアリング (100.0を基準に加減点)
    -- Depthが浅い、更新頻度が高い、重要度が高いほど高スコア
    score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    
    -- エラーハンドリング
    error_count INTEGER NOT NULL DEFAULT 0,
    blocked_reason TEXT,
    
    -- スケジューリング
    last_crawled_at TIMESTAMP WITH TIME ZONE,
    next_crawl_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- ドメインごとの並列数制御や統計用
CREATE INDEX IF NOT EXISTS idx_crawl_urls_domain_status 
ON crawl_urls (domain, status);
