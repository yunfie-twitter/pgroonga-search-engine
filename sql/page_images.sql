-- Page Images Table
-- Stores metadata for images extracted from web pages.
-- Linked to web_pages via page_url.

CREATE TABLE IF NOT EXISTS page_images (
    id SERIAL PRIMARY KEY,
    page_url TEXT NOT NULL,
    image_url TEXT NOT NULL,
    alt_text TEXT,
    position INTEGER, -- Order of appearance in the DOM
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraint ensuring the page exists
    CONSTRAINT fk_page
        FOREIGN KEY (page_url) 
        REFERENCES web_pages(url)
        ON DELETE CASCADE,

    -- Ensure unique pairing of page and image to allow UPSERT
    CONSTRAINT uq_page_image 
        UNIQUE (page_url, image_url)
);

-- Index for fast retrieval of images by page
CREATE INDEX IF NOT EXISTS idx_page_images_page_url 
ON page_images (page_url);
