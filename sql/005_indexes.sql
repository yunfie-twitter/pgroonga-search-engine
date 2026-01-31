-- Performance Tuning & Indexes

-- 1. クローラースケジューリング用インデックス
-- 「スコアが高く」かつ「クロール予定時刻を過ぎている」ものを高速に取得
-- statusによるフィルタリングも含めた複合インデックス
CREATE INDEX IF NOT EXISTS idx_crawl_priority 
ON crawl_urls (score DESC, next_crawl_at ASC) 
WHERE status IN ('pending', 'done', 'error');

-- 2. PGroonga 全文検索インデックス (Web Pages)
-- タイトルとコンテンツを同時に検索対象にします。
-- 重み付け: タイトル(A) > コンテンツ(B) のような調整はクエリ側で行いますが、
-- ここでは両方をターゲットにします。
CREATE INDEX IF NOT EXISTS pgroonga_search_idx 
ON web_pages 
USING pgroonga (title, content);

-- 3. フィルタリング用インデックス
CREATE INDEX IF NOT EXISTS idx_web_pages_category 
ON web_pages (category);

CREATE INDEX IF NOT EXISTS idx_web_pages_published 
ON web_pages (published_at DESC);

-- 4. 画像検索用（Altテキスト）
-- 画像検索を行いたい場合、ここにもPGroongaインデックスを貼ります
CREATE INDEX IF NOT EXISTS pgroonga_image_alt_idx 
ON page_images 
USING pgroonga (alt_text);
