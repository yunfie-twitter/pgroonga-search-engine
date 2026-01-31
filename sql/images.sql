-- Images Table
-- Stores unique image assets normalized by URL hash.
-- Prevents duplication when the same image is used across multiple pages.

CREATE TABLE IF NOT EXISTS images (
    id SERIAL PRIMARY KEY,
    image_hash CHAR(64) UNIQUE NOT NULL, -- SHA256 of normalized URL
    canonical_url TEXT NOT NULL,         -- The representative URL for this image
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_images_hash ON images (image_hash);
