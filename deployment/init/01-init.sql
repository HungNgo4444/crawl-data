-- Initial database setup for crawler system
-- This runs automatically when PostgreSQL container starts

-- Grant permissions to crawler_user
GRANT ALL PRIVILEGES ON DATABASE crawler_db TO crawler_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO crawler_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO crawler_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO crawler_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO crawler_user;

-- Create extension for UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Log completion
\echo 'Database initialization completed successfully!'