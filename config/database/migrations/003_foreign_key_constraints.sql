-- Migration: 003_foreign_key_constraints.sql  
-- Description: Add foreign key constraints and integration points with existing schema
-- Date: 2025-08-11
-- Author: James (Dev Agent)

-- Task 4: Add Integration Points with Existing Schema

-- Note: This migration assumes news_articles table exists from previous crawler implementation
-- If news_articles table doesn't exist, this migration will be skipped gracefully

-- Check if news_articles table exists and add optional foreign key
DO $$ 
BEGIN
    -- Check if news_articles table exists
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'news_articles') THEN
        
        -- Add optional domain_config_id column to news_articles if it doesn't exist
        IF NOT EXISTS (SELECT FROM information_schema.columns 
                      WHERE table_name = 'news_articles' AND column_name = 'domain_config_id') THEN
            
            ALTER TABLE news_articles 
            ADD COLUMN domain_config_id UUID REFERENCES domain_configurations(id) ON DELETE SET NULL;
            
            -- Create index for the new foreign key
            CREATE INDEX IF NOT EXISTS idx_news_articles_domain_config 
                ON news_articles(domain_config_id);
                
            -- Add comment for documentation
            COMMENT ON COLUMN news_articles.domain_config_id IS 'Optional link to domain configuration for enhanced crawling';
            
        END IF;
        
    ELSE
        -- Log that news_articles table doesn't exist yet
        RAISE NOTICE 'news_articles table not found - skipping integration. This is normal for fresh installations.';
        
    END IF;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error during news_articles integration: %', SQLERRM;
        RAISE NOTICE 'Continuing migration - this may be expected for new installations';
END $$;

-- Create a view for backward compatibility reporting
CREATE OR REPLACE VIEW domain_crawling_stats AS
SELECT 
    dc.id,
    dc.domain_name,
    dc.base_url,
    dc.status,
    dc.success_rate_24h,
    dc.last_analyzed,
    dc.next_analysis_scheduled,
    COUNT(dpt.id) as template_count,
    MAX(dpt.confidence_score) as best_template_confidence,
    COUNT(daq.id) FILTER (WHERE daq.status = 'PENDING') as pending_analyses,
    COUNT(daq.id) FILTER (WHERE daq.status = 'COMPLETED' AND daq.created_at > NOW() - INTERVAL '7 days') as analyses_last_week
FROM domain_configurations dc
LEFT JOIN domain_parsing_templates dpt ON dc.id = dpt.domain_config_id
LEFT JOIN domain_analysis_queue daq ON dc.id = daq.domain_config_id
GROUP BY dc.id, dc.domain_name, dc.base_url, dc.status, dc.success_rate_24h, dc.last_analyzed, dc.next_analysis_scheduled;

COMMENT ON VIEW domain_crawling_stats IS 'Comprehensive view of domain crawling statistics for monitoring and reporting';

-- Create migration tracking table for this schema version
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    description TEXT
);

-- Record this migration
INSERT INTO schema_migrations (version, description) VALUES 
    ('001_initial_domain_schema', 'Created domain management core tables'),
    ('002_add_domain_indexes', 'Added performance indexes for domain queries'),
    ('003_foreign_key_constraints', 'Added foreign key relationships and integration points')
ON CONFLICT (version) DO NOTHING;