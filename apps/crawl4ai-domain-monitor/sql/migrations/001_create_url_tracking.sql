-- Create URL tracking table for deduplication
CREATE TABLE IF NOT EXISTS url_tracking (
    id SERIAL PRIMARY KEY,
    url_hash VARCHAR(64) UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    domain_id INTEGER REFERENCES domains(id),
    status VARCHAR(20) DEFAULT 'discovered',
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    expires_at TIMESTAMP,
    processing_attempts INTEGER DEFAULT 0,
    last_error TEXT,
    metadata JSONB DEFAULT '{}'
);