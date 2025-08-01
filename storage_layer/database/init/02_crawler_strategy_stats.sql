-- -----------------------------------------------------------------------------
-- Crawler Strategy Stats Table
-- Lưu hiệu suất các chiến lược crawler cho từng nguồn tin
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_logs.crawler_strategy_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_name VARCHAR(100) NOT NULL,
    strategy_name VARCHAR(50) NOT NULL,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    total_time NUMERIC(10,2) DEFAULT 0, -- Tổng thời gian chạy (giây)
    last_run TIMESTAMPTZ,
    avg_articles_per_run NUMERIC(6,2) DEFAULT 0,
    total_articles INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_name, strategy_name)
);

CREATE INDEX IF NOT EXISTS idx_crawler_stats_source ON system_logs.crawler_strategy_stats(source_name);
CREATE INDEX IF NOT EXISTS idx_crawler_stats_strategy ON system_logs.crawler_strategy_stats(strategy_name); 