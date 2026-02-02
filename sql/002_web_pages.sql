-- Search Content (Web Pages)
-- 検索エンジンが検索対象とするページ情報を格納します。

CREATE TABLE IF NOT EXISTS web_pages (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE, -- crawl_urls.url と対応
    
    -- 表示用メタデータ
    title TEXT NOT NULL DEFAULT '',
    description TEXT,
    
    -- 全文検索対象
    -- HTMLタグ除去済みの本文を想定
    content TEXT NOT NULL DEFAULT '',
    
    -- 検索用統合テキスト (Title + Content + AltText)
    search_text TEXT NOT NULL DEFAULT '',
    
    -- フィルタリング用
    category TEXT DEFAULT 'general',
    published_at TIMESTAMP WITH TIME ZONE,
    language VARCHAR(10) DEFAULT 'ja',
    
    -- 代表画像（OGP画像など）への参照
    -- images.id へのFK (循環参照防止のためALTERで後付けも可だが、ここでは単純化)
    representative_image_id BIGINT, 
    
    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
