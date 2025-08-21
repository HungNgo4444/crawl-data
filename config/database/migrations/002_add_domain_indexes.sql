-- Migration: 002_add_domain_indexes.sql
-- Description: Add performance indexes for domain management queries
-- Date: 2025-08-11
-- Author: James (Dev Agent)

-- Additional performance indexes for domain_configurations
CREATE INDEX IF NOT EXISTS idx_domain_configurations_created_at 
    ON domain_configurations(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_domain_configurations_success_rate 
    ON domain_configurations(success_rate_24h DESC) 
    WHERE status = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_domain_configurations_crawl_frequency 
    ON domain_configurations(crawl_frequency_hours, next_analysis_scheduled) 
    WHERE status IN ('ACTIVE', 'ANALYZING');

-- Performance indexes for analysis queue operations
CREATE INDEX IF NOT EXISTS idx_domain_analysis_queue_completed_recent 
    ON domain_analysis_queue(domain_config_id, analysis_started_at DESC) 
    WHERE status = 'COMPLETED';

CREATE INDEX IF NOT EXISTS idx_domain_analysis_queue_failed_retry 
    ON domain_analysis_queue(retry_count, scheduled_time) 
    WHERE status = 'FAILED' AND retry_count < 3;

-- Composite index for template selection by performance
CREATE INDEX IF NOT EXISTS idx_domain_parsing_templates_performance_selection 
    ON domain_parsing_templates(domain_config_id, confidence_score DESC, created_at DESC) 
    WHERE is_active = true AND (expires_at IS NULL OR expires_at > NOW());

-- Index for template expiration cleanup
CREATE INDEX IF NOT EXISTS idx_domain_parsing_templates_expired 
    ON domain_parsing_templates(expires_at) 
    WHERE expires_at IS NOT NULL AND is_active = true;

-- Analyze tables for query planner optimization
ANALYZE domain_configurations;
ANALYZE domain_parsing_templates;
ANALYZE domain_analysis_queue;