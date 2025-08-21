-- Migration: 001_initial_domain_schema.sql
-- Description: Create domain management tables for AI-Powered Multi-Domain News Crawler System
-- Date: 2025-08-11
-- Author: James (Dev Agent)

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create domain_status ENUM type
DO $$ BEGIN
    CREATE TYPE domain_status AS ENUM (
        'ACTIVE', 
        'INACTIVE', 
        'ANALYZING', 
        'FAILED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create analysis_status ENUM type for queue management
DO $$ BEGIN
    CREATE TYPE analysis_status AS ENUM (
        'PENDING', 
        'RUNNING', 
        'COMPLETED', 
        'FAILED', 
        'RETRYING'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Task 1: Create domains table (Domain Management Database)
-- Purpose: User-configurable crawlable domains with comprehensive management features
CREATE TABLE IF NOT EXISTS domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Basic Domain Info
    name VARCHAR(255) NOT NULL UNIQUE, -- e.g., "vnexpress.net"
    display_name VARCHAR(255) NOT NULL, -- e.g., "VNExpress News"
    base_url TEXT NOT NULL, -- e.g., "https://vnexpress.net"
    logo_url TEXT, -- Domain logo for web interface
    language VARCHAR(10) DEFAULT 'vi', -- Language code
    country VARCHAR(10) DEFAULT 'VN', -- Country code
    
    -- Crawling Configuration
    status domain_status NOT NULL DEFAULT 'ACTIVE',
    crawl_frequency_hours INTEGER NOT NULL DEFAULT 24 CHECK (crawl_frequency_hours > 0),
    max_articles_per_crawl INTEGER DEFAULT 100 CHECK (max_articles_per_crawl > 0),
    
    -- Auto-Analysis Integration
    last_analyzed TIMESTAMP WITH TIME ZONE,
    next_analysis_scheduled TIMESTAMP WITH TIME ZONE,
    analysis_template_id UUID, -- Reference to active template
    
    -- Performance Tracking
    success_rate_24h DECIMAL(5,2) DEFAULT 0.00 CHECK (success_rate_24h >= 0.00 AND success_rate_24h <= 100.00),
    total_articles_crawled INTEGER DEFAULT 0,
    last_successful_crawl TIMESTAMP WITH TIME ZONE,
    
    -- User Management
    created_by_user_id UUID NOT NULL, -- Reference to users table
    is_user_added BOOLEAN DEFAULT true, -- User-added vs system-added
    
    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for domains table
CREATE INDEX IF NOT EXISTS idx_domains_name 
    ON domains(name);
    
CREATE INDEX IF NOT EXISTS idx_domains_status 
    ON domains(status);
    
CREATE INDEX IF NOT EXISTS idx_domains_next_analysis 
    ON domains(next_analysis_scheduled) 
    WHERE status IN ('ACTIVE', 'ANALYZING');
    
CREATE INDEX IF NOT EXISTS idx_domains_language 
    ON domains(language);
    
CREATE INDEX IF NOT EXISTS idx_domains_created_by_user 
    ON domains(created_by_user_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for domains
DROP TRIGGER IF EXISTS update_domains_updated_at ON domains;
CREATE TRIGGER update_domains_updated_at 
    BEFORE UPDATE ON domains 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE domains IS 'Domain Management Database - User-configurable crawlable domains with comprehensive management features';
COMMENT ON COLUMN domains.id IS 'Unique domain identifier';
COMMENT ON COLUMN domains.name IS 'Domain name (e.g., "vnexpress.net")';
COMMENT ON COLUMN domains.display_name IS 'Human-readable domain name (e.g., "VNExpress News")';
COMMENT ON COLUMN domains.base_url IS 'Root URL for crawling operations';
COMMENT ON COLUMN domains.logo_url IS 'Domain logo URL for web interface';
COMMENT ON COLUMN domains.language IS 'Language code (default: vi for Vietnamese)';
COMMENT ON COLUMN domains.country IS 'Country code (default: VN for Vietnam)';
COMMENT ON COLUMN domains.status IS 'Current domain status: ACTIVE, INACTIVE, ANALYZING, FAILED';
COMMENT ON COLUMN domains.crawl_frequency_hours IS 'How often to crawl this domain (in hours)';
COMMENT ON COLUMN domains.max_articles_per_crawl IS 'Maximum articles to crawl per session';
COMMENT ON COLUMN domains.last_analyzed IS 'Last analysis completion time';
COMMENT ON COLUMN domains.next_analysis_scheduled IS 'Next scheduled analysis';
COMMENT ON COLUMN domains.analysis_template_id IS 'Reference to active crawl template';
COMMENT ON COLUMN domains.success_rate_24h IS 'Recent crawling success percentage (0.00-100.00)';
COMMENT ON COLUMN domains.total_articles_crawled IS 'Total articles crawled from this domain';
COMMENT ON COLUMN domains.last_successful_crawl IS 'Timestamp of last successful crawl';
COMMENT ON COLUMN domains.created_by_user_id IS 'Admin user ID who added domain';
COMMENT ON COLUMN domains.is_user_added IS 'Whether domain was added by user (vs system-added)';

-- Task 2: Create crawl_templates table (AI-generated parsing templates for crawl4ai integration)
CREATE TABLE IF NOT EXISTS crawl_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    
    -- Template Metadata
    template_name VARCHAR(255) NOT NULL, -- e.g., "vnexpress_news_v2"
    template_version INTEGER NOT NULL DEFAULT 1,
    confidence_score DECIMAL(5,4) NOT NULL CHECK (confidence_score >= 0.0000 AND confidence_score <= 1.0000),
    
    -- crawl4ai Integration
    crawl4ai_config JSONB NOT NULL, -- Complete crawl4ai configuration
    css_selectors JSONB NOT NULL, -- CSS selectors for content extraction
    extraction_rules JSONB NOT NULL, -- Content processing rules
    
    -- Performance Metrics
    success_rate DECIMAL(5,4) DEFAULT 0.0000,
    avg_extraction_time_ms INTEGER DEFAULT 0,
    last_tested TIMESTAMP WITH TIME ZONE,
    
    -- Template Status
    is_active BOOLEAN NOT NULL DEFAULT false,
    generated_by_model VARCHAR(50) DEFAULT 'qwen2.5:3b', -- AI model used
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: Only one active template per domain
    CONSTRAINT unique_active_template_per_domain 
        EXCLUDE USING btree (domain_id WITH =) 
        WHERE (is_active = true)
);

-- Create indexes for crawl_templates table
CREATE INDEX IF NOT EXISTS idx_crawl_templates_domain_id 
    ON crawl_templates(domain_id);

CREATE INDEX IF NOT EXISTS idx_crawl_templates_active_expires 
    ON crawl_templates(domain_id, is_active, expires_at) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_crawl_templates_confidence 
    ON crawl_templates(confidence_score DESC);

CREATE INDEX IF NOT EXISTS idx_crawl_templates_template_name 
    ON crawl_templates(template_name);

CREATE INDEX IF NOT EXISTS idx_crawl_templates_generated_by_model 
    ON crawl_templates(generated_by_model);

-- Create GIN indexes for JSONB columns for efficient querying
CREATE INDEX IF NOT EXISTS idx_crawl_templates_crawl4ai_config 
    ON crawl_templates USING GIN (crawl4ai_config);

CREATE INDEX IF NOT EXISTS idx_crawl_templates_css_selectors 
    ON crawl_templates USING GIN (css_selectors);

CREATE INDEX IF NOT EXISTS idx_crawl_templates_extraction_rules 
    ON crawl_templates USING GIN (extraction_rules);

-- Create trigger for crawl_templates
DROP TRIGGER IF EXISTS update_crawl_templates_updated_at ON crawl_templates;
CREATE TRIGGER update_crawl_templates_updated_at 
    BEFORE UPDATE ON crawl_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE crawl_templates IS 'AI-generated parsing templates for crawl4ai integration';
COMMENT ON COLUMN crawl_templates.id IS 'Unique template identifier';
COMMENT ON COLUMN crawl_templates.domain_id IS 'Foreign key to domains table';
COMMENT ON COLUMN crawl_templates.template_name IS 'Template name (e.g., vnexpress_news_v2)';
COMMENT ON COLUMN crawl_templates.template_version IS 'Version number for template updates';
COMMENT ON COLUMN crawl_templates.confidence_score IS 'AI confidence in parsing accuracy (0.0000-1.0000)';
COMMENT ON COLUMN crawl_templates.crawl4ai_config IS 'Complete crawl4ai configuration (JSONB)';
COMMENT ON COLUMN crawl_templates.css_selectors IS 'CSS selectors for content extraction (JSONB)';
COMMENT ON COLUMN crawl_templates.extraction_rules IS 'Content processing rules (JSONB)';
COMMENT ON COLUMN crawl_templates.success_rate IS 'Template success rate (0.0000-1.0000)';
COMMENT ON COLUMN crawl_templates.avg_extraction_time_ms IS 'Average extraction time in milliseconds';
COMMENT ON COLUMN crawl_templates.last_tested IS 'When template was last tested';
COMMENT ON COLUMN crawl_templates.is_active IS 'Whether this template is currently in use';
COMMENT ON COLUMN crawl_templates.generated_by_model IS 'AI model that generated this template';
COMMENT ON COLUMN crawl_templates.expires_at IS 'When template should be refreshed';

-- Task 3: Create domain_analysis_queue table
CREATE TABLE IF NOT EXISTS domain_analysis_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status analysis_status NOT NULL DEFAULT 'PENDING',
    analysis_started_at TIMESTAMP WITH TIME ZONE,
    analysis_duration_seconds INTEGER CHECK (analysis_duration_seconds >= 0),
    model_version VARCHAR(50) DEFAULT 'qwen2.5:3b',
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Prevent duplicate pending/running jobs for same domain
    CONSTRAINT unique_pending_running_per_domain 
        EXCLUDE (domain_id WITH =) WHERE (status IN ('PENDING', 'RUNNING'))
);

-- Create indexes for domain_analysis_queue table
CREATE INDEX IF NOT EXISTS idx_domain_analysis_queue_scheduled_time 
    ON domain_analysis_queue(scheduled_time);

CREATE INDEX IF NOT EXISTS idx_domain_analysis_queue_status 
    ON domain_analysis_queue(status);

CREATE INDEX IF NOT EXISTS idx_domain_analysis_queue_priority_scheduled 
    ON domain_analysis_queue(priority DESC, scheduled_time ASC) 
    WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_domain_analysis_queue_domain_id 
    ON domain_analysis_queue(domain_id);

CREATE INDEX IF NOT EXISTS idx_domain_analysis_queue_retry_count 
    ON domain_analysis_queue(retry_count) 
    WHERE status = 'FAILED' AND retry_count < 3;

-- Create trigger for domain_analysis_queue
DROP TRIGGER IF EXISTS update_domain_analysis_queue_updated_at ON domain_analysis_queue;
CREATE TRIGGER update_domain_analysis_queue_updated_at 
    BEFORE UPDATE ON domain_analysis_queue 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE domain_analysis_queue IS 'Manage daily GWEN-3 analysis scheduling for 200+ domains';
COMMENT ON COLUMN domain_analysis_queue.id IS 'Unique queue entry identifier';
COMMENT ON COLUMN domain_analysis_queue.domain_id IS 'Domain to analyze';
COMMENT ON COLUMN domain_analysis_queue.scheduled_time IS 'When analysis should run';
COMMENT ON COLUMN domain_analysis_queue.status IS 'Current status: PENDING, RUNNING, COMPLETED, FAILED, RETRYING';
COMMENT ON COLUMN domain_analysis_queue.analysis_started_at IS 'Actual analysis start time';
COMMENT ON COLUMN domain_analysis_queue.analysis_duration_seconds IS 'How long analysis took';
COMMENT ON COLUMN domain_analysis_queue.model_version IS 'AI model version used (default: qwen2.5:3b)';
COMMENT ON COLUMN domain_analysis_queue.error_message IS 'Error details if analysis failed';
COMMENT ON COLUMN domain_analysis_queue.retry_count IS 'Number of retry attempts';
COMMENT ON COLUMN domain_analysis_queue.priority IS 'Analysis priority (1-10, higher = more urgent)';