-- Monitoring Queue Table
CREATE TABLE IF NOT EXISTS monitoring_queue (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER REFERENCES domains(id),
    url TEXT NOT NULL,
    priority INTEGER DEFAULT 1,
    scheduled_at TIMESTAMP DEFAULT NOW(),
    attempts INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_queue_domain_priority ON monitoring_queue(domain_id, priority, scheduled_at);