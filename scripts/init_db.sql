-- PostgreSQL Initialization Script for News Crawler
-- Creates database user and necessary permissions

-- Create crawler user if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'crawler_user') THEN
        CREATE ROLE crawler_user WITH LOGIN PASSWORD 'crawler_secure_123';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE news_crawler_db TO crawler_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO crawler_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO crawler_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO crawler_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO crawler_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO crawler_user;

-- Make sure the user can create tables
ALTER ROLE crawler_user CREATEDB;