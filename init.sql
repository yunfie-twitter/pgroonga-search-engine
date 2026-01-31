-- Initialize PGroonga extension
CREATE EXTENSION IF NOT EXISTS pgroonga;

-- Web Pages Table
-- Stores the crawled content. URL is unique to prevent duplicates.
CREATE TABLE IF NOT EXISTS web_pages (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Full Text Search Index using PGroonga
-- Indexes both title and content for comprehensive search.
-- 'pgroonga' index method is used for fast full-text search with Japanese support (default in pgroonga image).
CREATE INDEX IF NOT EXISTS pgroonga_search_idx ON web_pages USING pgroonga (title, content);

-- Filter Indexes
-- Index for category filtering
CREATE INDEX IF NOT EXISTS idx_web_pages_category ON web_pages (category);

-- Index for date range filtering
CREATE INDEX IF NOT EXISTS idx_web_pages_published_at ON web_pages (published_at);
