-- Database partitioning and optimization SQL scripts
-- For PostgreSQL 12+ with native partitioning support

-- Create schemas
CREATE SCHEMA IF NOT EXISTS raw_data;
CREATE SCHEMA IF NOT EXISTS processing;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Main partitioned articles table
CREATE TABLE IF NOT EXISTS raw_data.articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    url_hash VARCHAR(64) UNIQUE NOT NULL,
    source VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    content_summary TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    published_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    full_content_key VARCHAR(255),
    raw_html_key VARCHAR(255),
    word_count INTEGER DEFAULT 0,
    reading_time INTEGER DEFAULT 0,
    language VARCHAR(10) DEFAULT 'vi',
    quality_score NUMERIC(3,2) DEFAULT 0.0,
    processing_status VARCHAR(20) DEFAULT 'pending',
    extraction_strategy VARCHAR(20),
    extraction_metadata JSONB,
    category VARCHAR(50),
    tags JSONB,
    author VARCHAR(200),
    author_metadata JSONB
) PARTITION BY RANGE (created_at);

-- Create indexes on the partitioned table
CREATE INDEX IF NOT EXISTS idx_articles_url_hash ON raw_data.articles (url_hash);
CREATE INDEX IF NOT EXISTS idx_articles_source_created ON raw_data.articles (source, created_at);
CREATE INDEX IF NOT EXISTS idx_articles_published ON raw_data.articles (published_at);
CREATE INDEX IF NOT EXISTS idx_articles_status ON raw_data.articles (processing_status);
CREATE INDEX IF NOT EXISTS idx_articles_quality ON raw_data.articles (quality_score);
CREATE INDEX IF NOT EXISTS idx_articles_source_published ON raw_data.articles (source, published_at);

-- Function to create monthly partitions automatically
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
BEGIN
    -- Generate partition name
    partition_name := table_name || '_' || TO_CHAR(start_date, 'YYYY_MM');
    
    -- Calculate end date (first day of next month)
    end_date := date_trunc('month', start_date) + interval '1 month';
    
    -- Create partition table
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS raw_data.%I 
        PARTITION OF raw_data.%I
        FOR VALUES FROM (%L) TO (%L)',
        partition_name, table_name, start_date, end_date
    );
    
    -- Create indexes on the partition
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_url_hash ON raw_data.%I (url_hash)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_source ON raw_data.%I (source)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_published ON raw_data.%I (published_at)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_quality ON raw_data.%I (quality_score)', partition_name, partition_name);
    
    RAISE NOTICE 'Created partition: %', partition_name;
END;
$$ LANGUAGE plpgsql;

-- Function to automatically create partitions for the next N months
CREATE OR REPLACE FUNCTION create_future_partitions(months_ahead integer DEFAULT 6)
RETURNS void AS $$
DECLARE
    start_date date;
    i integer;
BEGIN
    -- Start from current month
    start_date := date_trunc('month', CURRENT_DATE);
    
    -- Create partitions for next N months  
    FOR i IN 0..months_ahead LOOP
        PERFORM create_monthly_partition('articles', start_date + (i || ' months')::interval);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create partitions for 2024 and 2025
SELECT create_monthly_partition('articles', '2024-01-01'::date);
SELECT create_monthly_partition('articles', '2024-02-01'::date);
SELECT create_monthly_partition('articles', '2024-03-01'::date);
SELECT create_monthly_partition('articles', '2024-04-01'::date);
SELECT create_monthly_partition('articles', '2024-05-01'::date);
SELECT create_monthly_partition('articles', '2024-06-01'::date);
SELECT create_monthly_partition('articles', '2024-07-01'::date);
SELECT create_monthly_partition('articles', '2024-08-01'::date);
SELECT create_monthly_partition('articles', '2024-09-01'::date);
SELECT create_monthly_partition('articles', '2024-10-01'::date);
SELECT create_monthly_partition('articles', '2024-11-01'::date);
SELECT create_monthly_partition('articles', '2024-12-01'::date);

-- Create future partitions (next 6 months)
SELECT create_future_partitions(6);

-- Auto-create partitions trigger
CREATE OR REPLACE FUNCTION auto_create_partition()
RETURNS TRIGGER AS $$
DECLARE
    partition_date date;
BEGIN
    partition_date := date_trunc('month', NEW.created_at);
    
    -- Try to create partition if it doesn't exist
    BEGIN
        PERFORM create_monthly_partition('articles', partition_date);
    EXCEPTION 
        WHEN duplicate_table THEN
            -- Partition already exists, continue
            NULL;
    END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger (only if table is not already partitioned)
-- DROP TRIGGER IF EXISTS trigger_auto_create_partition ON raw_data.articles;
-- CREATE TRIGGER trigger_auto_create_partition
--     BEFORE INSERT ON raw_data.articles
--     FOR EACH ROW EXECUTE FUNCTION auto_create_partition();

-- Function to drop old partitions (data retention)
CREATE OR REPLACE FUNCTION drop_old_partitions(months_to_keep integer DEFAULT 12)
RETURNS void AS $$
DECLARE
    cutoff_date date;
    partition_record record;
BEGIN
    cutoff_date := date_trunc('month', CURRENT_DATE) - (months_to_keep || ' months')::interval;
    
    -- Find and drop old partitions
    FOR partition_record IN 
        SELECT schemaname, tablename 
        FROM pg_tables 
        WHERE schemaname = 'raw_data' 
        AND tablename LIKE 'articles_%' 
        AND tablename ~ '^articles_\d{4}_\d{2}$'
    LOOP
        -- Extract date from partition name and check if it's old
        IF to_date(substring(partition_record.tablename from '\d{4}_\d{2}'), 'YYYY_MM') < cutoff_date THEN
            EXECUTE format('DROP TABLE IF EXISTS raw_data.%I', partition_record.tablename);
            RAISE NOTICE 'Dropped old partition: %', partition_record.tablename;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled job to maintain partitions (requires pg_cron extension)
-- SELECT cron.schedule('create_partitions', '0 0 1 * *', 'SELECT create_future_partitions(3);');
-- SELECT cron.schedule('cleanup_partitions', '0 2 1 * *', 'SELECT drop_old_partitions(12);');

-- Utility views for monitoring partitions
CREATE OR REPLACE VIEW monitoring.partition_info AS
SELECT 
    schemaname,
    tablename as partition_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    (SELECT count(*) FROM information_schema.tables t2 
     WHERE t2.table_schema = schemaname 
     AND t2.table_name = tablename) as row_estimate
FROM pg_tables 
WHERE schemaname = 'raw_data' 
AND tablename LIKE 'articles_%'
ORDER BY tablename;

-- Performance optimization settings
-- These should be set at database level
/*
ALTER TABLE raw_data.articles SET (
    parallel_workers = 4,
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);
*/

-- Table statistics update
-- Run periodically for better query planning
/*
ANALYZE raw_data.articles;
*/