-- Enable PGroonga extension for full text search
CREATE EXTENSION IF NOT EXISTS pgroonga;

-- Web Pages Table
-- Stores crawled web content. URL must be unique.
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

-- Full Text Search Index
-- Indexes title and content using pgroonga operator class.
-- This enables fast '&@' operator searches.
CREATE INDEX IF NOT EXISTS pgroonga_content_index 
ON web_pages 
USING pgroonga (title, content);

-- Filter Indexes
-- Standard B-Tree indexes for efficient filtering on exact matches and ranges.
CREATE INDEX IF NOT EXISTS idx_category ON web_pages (category);
CREATE INDEX IF NOT EXISTS idx_published_at ON web_pages (published_at);
