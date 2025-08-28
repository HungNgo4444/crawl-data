-- Performance indexes for url_tracking table
CREATE INDEX IF NOT EXISTS idx_url_hash ON url_tracking(url_hash);
CREATE INDEX IF NOT EXISTS idx_domain_created ON url_tracking(domain_id, created_at);
CREATE INDEX IF NOT EXISTS idx_status_expires ON url_tracking(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_processing ON url_tracking(status, processing_attempts);