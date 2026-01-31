-- Page - Image Relation
-- どのページにどの画像が含まれているかを管理します。
-- Altテキストは「ページ内での文脈」なのでここに持たせます。

CREATE TABLE IF NOT EXISTS page_images (
    page_id BIGINT REFERENCES web_pages(id) ON DELETE CASCADE,
    image_id BIGINT REFERENCES images(id) ON DELETE CASCADE,
    
    -- 検索対象としても利用可能なテキスト
    alt_text TEXT,
    
    -- 記事の上部にある画像を優先するなど、重み付けに利用
    position_order INTEGER NOT NULL DEFAULT 0,
    
    PRIMARY KEY (page_id, image_id)
);
