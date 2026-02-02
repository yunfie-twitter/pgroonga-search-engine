-- Search Logs & Intelligent Query System Schema

-- 1. Search Query Logs
-- ユーザーが検索したクエリを記録します。
CREATE TABLE IF NOT EXISTS search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    normalized_query TEXT NOT NULL, -- 正規化後のクエリ（小文字、半角統一など）
    
    -- 将来的な拡張機能用（セッションID、ユーザーIDなど）
    session_id TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_logs_norm_query ON search_logs (normalized_query);
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON search_logs (created_at);

-- 2. Click Logs (Feedback Loop)
-- 検索結果のどのURLがクリックされたかを記録します。
CREATE TABLE IF NOT EXISTS click_logs (
    id BIGSERIAL PRIMARY KEY,
    search_log_id UUID NOT NULL REFERENCES search_logs(id) ON DELETE CASCADE,
    
    url TEXT NOT NULL,
    rank INTEGER, -- 検索結果の何番目に表示されていたか
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_click_logs_url ON click_logs (url);

-- 3. Query Relations (Synonyms / Intent Graph)
-- 「学マス」->「学園アイドルマスター」のような関係を保存します。
CREATE TABLE IF NOT EXISTS query_relations (
    source_query TEXT NOT NULL,
    target_query TEXT NOT NULL,
    
    relation_type VARCHAR(20) NOT NULL DEFAULT 'synonym', -- synonym, expansion, correction
    score DOUBLE PRECISION NOT NULL DEFAULT 1.0, -- 信頼度スコア (0.0 - 1.0)
    
    source VARCHAR(50) DEFAULT 'manual', -- manual, auto_stats, auto_nlp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (source_query, target_query)
);

CREATE INDEX IF NOT EXISTS idx_query_relations_source ON query_relations (source_query);
