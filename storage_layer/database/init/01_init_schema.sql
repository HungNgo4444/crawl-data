-- -----------------------------------------------------------------------------
-- Initial Schema for Fintech Data Project
-- -----------------------------------------------------------------------------
-- This script is executed when the PostgreSQL container starts for the first time.
-- It sets up the necessary schemas, tables, extensions, and indexes.
--
-- Schemas:
-- - raw_data: Stores raw, unmodified data collected from crawlers.
-- - processed_data: Stores cleaned, enriched, and analyzed data.
-- - system_logs: Contains logs and metadata about system operations.
-- - analytics: Stores aggregated data for reporting and dashboards.
-- -----------------------------------------------------------------------------

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- -----------------------------------------------------------------------------
-- Schemas
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS raw_data;
CREATE SCHEMA IF NOT EXISTS processed_data;
CREATE SCHEMA IF NOT EXISTS system_logs;
CREATE SCHEMA IF NOT EXISTS analytics;

-- -----------------------------------------------------------------------------
-- Table: raw_data.articles
-- Stores raw article data as soon as it is crawled.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw_data.articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source VARCHAR(50) NOT NULL,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    content TEXT,
    author VARCHAR(255),
    published_at TIMESTAMPTZ, -- Use TIMESTAMPTZ for time zone support
    crawled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Metadata
    language VARCHAR(10) DEFAULT 'vi',
    category VARCHAR(100),
    tags TEXT[],

    -- Storage reference for raw HTML/content in MinIO/S3
    raw_storage_key TEXT,

    -- Status tracking for the processing pipeline
    processing_status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT
);

-- Indexes for raw_data.articles
CREATE INDEX IF NOT EXISTS idx_articles_source_date ON raw_data.articles(source, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_status ON raw_data.articles(processing_status);
CREATE INDEX IF NOT EXISTS idx_articles_url_trgm ON raw_data.articles USING gin (url gin_trgm_ops);

COMMENT ON COLUMN raw_data.articles.raw_storage_key IS 'Key to the raw HTML file stored in MinIO/S3';
COMMENT ON COLUMN raw_data.articles.processing_status IS 'The current stage of the article in the processing pipeline';

-- -----------------------------------------------------------------------------
-- Table: processed_data.sentiment_analysis
-- Stores results from AI models (FinBERT, Gemini, etc.).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS processed_data.sentiment_analysis (
    article_id UUID PRIMARY KEY,
    
    -- FinBERT Results
    finbert_sentiment JSONB,  -- e.g., {"positive": 0.8, "negative": 0.1, "neutral": 0.1}
    finbert_label VARCHAR(10), -- positive, negative, neutral
    finbert_confidence NUMERIC(4,3),

    -- Gemini Results
    gemini_analysis JSONB,    -- Full analysis from Gemini
    gemini_summary TEXT,
    gemini_entities JSONB,    -- Extracted entities

    -- Common processed features
    engineered_features JSONB,

    -- Timestamps
    processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (article_id) REFERENCES raw_data.articles(id) ON DELETE CASCADE
);

-- Indexes for processed_data.sentiment_analysis
CREATE INDEX IF NOT EXISTS idx_sentiment_label ON processed_data.sentiment_analysis(finbert_label);
CREATE INDEX IF NOT EXISTS idx_sentiment_confidence ON processed_data.sentiment_analysis(finbert_confidence DESC);

-- -----------------------------------------------------------------------------
-- Table: system_logs.crawl_sessions
-- Logs each crawling session for monitoring and debugging.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_logs.crawl_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source VARCHAR(50),
    crawler_type VARCHAR(50),
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20), -- 'running', 'completed', 'failed'

    articles_found INTEGER DEFAULT 0,
    articles_crawled INTEGER DEFAULT 0,
    articles_failed INTEGER DEFAULT 0,

    error_details JSONB,
    performance_metrics JSONB -- e.g., { "duration_seconds": 120.5, "avg_request_time": 0.5 }
);

CREATE INDEX IF NOT EXISTS idx_crawl_sessions_status ON system_logs.crawl_sessions(status);
CREATE INDEX IF NOT EXISTS idx_crawl_sessions_source_time ON system_logs.crawl_sessions(source, started_at DESC); 