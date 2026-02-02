-- Page Images Table (Updated)
-- Links web pages to unique image assets stored in the 'images' table.

-- Drop old definition if it exists to allow clean migration in this hypothetical context
DROP TABLE IF EXISTS page_images;

CREATE TABLE IF NOT EXISTS page_images (
    id SERIAL PRIMARY KEY,
    page_url TEXT NOT NULL,
    image_id INTEGER NOT NULL, -- FK to images table
    alt_text TEXT,
    position INTEGER, -- Order of appearance in the DOM
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key to web_pages
    CONSTRAINT fk_page
        FOREIGN KEY (page_url) 
        REFERENCES web_pages(url)
        ON DELETE CASCADE,

    -- Foreign key to images
    CONSTRAINT fk_image
        FOREIGN KEY (image_id)
        REFERENCES images(id)
        ON DELETE CASCADE,

    -- Unique pairing of page and image_id
    CONSTRAINT uq_page_image_ref
        UNIQUE (page_url, image_id)
);

CREATE INDEX IF NOT EXISTS idx_page_images_page_url 
ON page_images (page_url);
