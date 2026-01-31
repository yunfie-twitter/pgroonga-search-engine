-- Image Master
-- 画像URLの正規化と重複排除を行います。

CREATE TABLE IF NOT EXISTS images (
    id BIGSERIAL PRIMARY KEY,
    
    -- 画像の一意性保証
    -- コンテンツハッシュ（SHA256等）を用いて同一画像を束ねる
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    
    -- CDN等の正規URL
    canonical_url TEXT NOT NULL,
    
    width INTEGER,
    height INTEGER,
    mime_type VARCHAR(50),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
