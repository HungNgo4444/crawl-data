-- Migration: Remove expires_at column and scheduling logic
-- Description: Templates are permanent, user manages manually via web interface
-- Date: 2025-08-12
-- Author: Claude Code Assistant

-- Remove expires_at column from crawl_templates
ALTER TABLE crawl_templates DROP COLUMN IF EXISTS expires_at;

-- Remove scheduling-related columns from domains
ALTER TABLE domains DROP COLUMN IF EXISTS next_analysis_scheduled;
ALTER TABLE domains DROP COLUMN IF EXISTS analysis_template_id;

-- Add comment explaining permanent templates
COMMENT ON TABLE crawl_templates IS 'Permanent AI-generated parsing templates - user manages via web interface';
COMMENT ON COLUMN crawl_templates.is_active IS 'Template active status - controlled by user, never auto-expires';

-- Update extraction_rules comment
COMMENT ON COLUMN crawl_templates.extraction_rules IS 'Unlimited crawl4ai settings with permanent_template flag';