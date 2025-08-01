-- Fix database schema by adding missing columns
-- This aligns SQL schema with SQLAlchemy models

-- Add missing columns to raw_data.articles
ALTER TABLE raw_data.articles 
ADD COLUMN IF NOT EXISTS url_hash VARCHAR(64) UNIQUE,
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS meta_description TEXT,
ADD COLUMN IF NOT EXISTS meta_keywords TEXT,
ADD COLUMN IF NOT EXISTS word_count INTEGER,
ADD COLUMN IF NOT EXISTS reading_time INTEGER,
ADD COLUMN IF NOT EXISTS images JSONB,
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS quality_score NUMERIC(3,2),
ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS duplicate_of UUID REFERENCES raw_data.articles(id),
ADD COLUMN IF NOT EXISTS crawler_strategy VARCHAR(50),
ADD COLUMN IF NOT EXISTS crawl_duration NUMERIC(10,3);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_articles_url_hash ON raw_data.articles(url_hash);
CREATE INDEX IF NOT EXISTS idx_articles_content_hash ON raw_data.articles(content_hash);
CREATE INDEX IF NOT EXISTS idx_articles_quality ON raw_data.articles(quality_score);

-- Update existing records to have url_hash
UPDATE raw_data.articles 
SET url_hash = md5(url)
WHERE url_hash IS NULL AND url IS NOT NULL;