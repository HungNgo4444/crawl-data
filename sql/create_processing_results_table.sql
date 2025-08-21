-- Create processing_results table for storing 4-method processing results
-- Run this SQL script in PostgreSQL database

CREATE TABLE IF NOT EXISTS processing_results (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    processing_type VARCHAR(20) NOT NULL CHECK (processing_type IN ('rss', 'sitemap', 'category', 'homepage')),
    success BOOLEAN NOT NULL DEFAULT FALSE,
    data JSONB DEFAULT '{}'::jsonb,
    source_url TEXT,
    processing_time REAL,
    token_usage INTEGER,
    errors JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_processing_results_domain_type ON processing_results(domain_id, processing_type);
CREATE INDEX IF NOT EXISTS idx_processing_results_processed_at ON processing_results(processed_at);
CREATE INDEX IF NOT EXISTS idx_processing_results_success ON processing_results(success);
CREATE INDEX IF NOT EXISTS idx_processing_results_type ON processing_results(processing_type);

-- Add comments to columns
COMMENT ON TABLE processing_results IS 'Store results from 4-method data processing: RSS, sitemap, category, homepage';
COMMENT ON COLUMN processing_results.processing_type IS 'Type of processing: rss, sitemap, category, homepage';
COMMENT ON COLUMN processing_results.data IS 'JSON data extracted from processing (articles, discovery results, etc.)';
COMMENT ON COLUMN processing_results.source_url IS 'URL of the source that was processed';
COMMENT ON COLUMN processing_results.processing_time IS 'Processing time in seconds';
COMMENT ON COLUMN processing_results.token_usage IS 'Number of tokens used by GWEN2.5';
COMMENT ON COLUMN processing_results.errors IS 'Array of error messages';
COMMENT ON COLUMN processing_results.warnings IS 'Array of warning messages';

-- Example query to get processing summary by domain
/* 
SELECT 
    d.name as domain,
    d.base_url,
    COUNT(*) as total_runs,
    SUM(CASE WHEN pr.success THEN 1 ELSE 0 END) as successful_runs,
    ARRAY_AGG(DISTINCT pr.processing_type) as methods_tested,
    MAX(pr.processed_at) as last_processed
FROM processing_results pr
JOIN domains d ON pr.domain_id = d.id
GROUP BY d.id, d.name, d.base_url
ORDER BY last_processed DESC;
*/