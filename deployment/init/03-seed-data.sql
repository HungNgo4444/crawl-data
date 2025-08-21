-- Migration: 004_initial_seed_data.sql
-- Description: Initial seed data for development and testing
-- Date: 2025-08-11
-- Author: James (Dev Agent)

-- Insert sample Vietnamese news domains for development
INSERT INTO domains 
(id, name, display_name, base_url, logo_url, language, country, status, crawl_frequency_hours, max_articles_per_crawl, success_rate_24h, created_by_user_id, is_user_added) 
VALUES 
-- Major Vietnamese news sources
(uuid_generate_v4(), 'vnexpress.net', 'VnExpress', 'https://vnexpress.net', 'https://s1.vnecdn.net/vnexpress/restruct/i/v9526/v2_2019/pc/graphics/logo.svg', 'vi', 'VN', 'ACTIVE', 6, 150, 95.20, uuid_generate_v4(), false),
(uuid_generate_v4(), 'tuoitre.vn', 'Tuổi Trẻ', 'https://tuoitre.vn', 'https://cdn1.tuoitre.vn/zoom/48_48/2019/6/3/logott-1559549716444.png', 'vi', 'VN', 'ACTIVE', 8, 120, 92.50, uuid_generate_v4(), false),
(uuid_generate_v4(), 'thanhnien.vn', 'Thanh Niên', 'https://thanhnien.vn', 'https://static.thanhnien.vn/v2/App_Themes/images/logo-tn-2.png', 'vi', 'VN', 'ACTIVE', 8, 100, 88.70, uuid_generate_v4(), false),
(uuid_generate_v4(), 'dantri.com.vn', 'Dân Trí', 'https://dantri.com.vn', 'https://cdnmedia.dantri.com.vn/dist/img/logo-dt.svg', 'vi', 'VN', 'ACTIVE', 12, 80, 91.30, uuid_generate_v4(), false),
(uuid_generate_v4(), 'vietnamnet.vn', 'VietnamNet', 'https://vietnamnet.vn', 'https://static-images.vnncdn.net/files/publish/2023/7/24/logo-vietnamnet-794.png', 'vi', 'VN', 'ACTIVE', 12, 90, 89.10, uuid_generate_v4(), false),
(uuid_generate_v4(), 'cafef.vn', 'CafeF', 'https://cafef.vn', 'https://cafef.vn/content/logo.png', 'vi', 'VN', 'ACTIVE', 24, 60, 86.40, uuid_generate_v4(), false),
(uuid_generate_v4(), 'kenh14.vn', 'Kênh 14', 'https://kenh14.vn', 'https://kenh14cdn.com/2020/logo-kenh14-update.svg', 'vi', 'VN', 'INACTIVE', 24, 50, 78.20, uuid_generate_v4(), false),
(uuid_generate_v4(), 'soha.vn', 'Soha', 'https://soha.vn', 'https://soha.vn/favicon.ico', 'vi', 'VN', 'INACTIVE', 24, 40, 82.60, uuid_generate_v4(), false)
ON CONFLICT (name) DO NOTHING;

-- Insert sample crawl templates for active domains
WITH domain_ids AS (
    SELECT id, name FROM domains WHERE status = 'ACTIVE'
)
INSERT INTO crawl_templates 
(id, domain_id, template_name, template_version, confidence_score, crawl4ai_config, css_selectors, extraction_rules, is_active, generated_by_model)
SELECT 
    uuid_generate_v4(),
    d.id,
    d.name || '_template_v1',
    1,
    CASE d.name
        WHEN 'vnexpress.net' THEN 0.9580
        WHEN 'tuoitre.vn' THEN 0.9230
        WHEN 'thanhnien.vn' THEN 0.8890
        ELSE 0.8500
    END,
    -- crawl4ai_config
    CASE d.name
        WHEN 'vnexpress.net' THEN '{
            "wait_for": ".article-content",
            "css_selector": ".news-item",
            "extraction_strategy": "CosineStrategy",
            "chunking_strategy": "RegexChunking",
            "word_count_threshold": 100,
            "excluded_tags": ["script", "style", "nav", "footer", "ads"]
        }'::jsonb
        WHEN 'tuoitre.vn' THEN '{
            "wait_for": ".article-body",
            "css_selector": ".article-wrapper",
            "extraction_strategy": "CosineStrategy",
            "chunking_strategy": "RegexChunking",
            "word_count_threshold": 80,
            "excluded_tags": ["script", "style", "nav", "footer"]
        }'::jsonb
        ELSE '{
            "wait_for": ".content",
            "css_selector": ".main-content",
            "extraction_strategy": "CosineStrategy",
            "chunking_strategy": "RegexChunking",
            "word_count_threshold": 50,
            "excluded_tags": ["script", "style", "nav", "footer"]
        }'::jsonb
    END,
    -- css_selectors
    CASE d.name
        WHEN 'vnexpress.net' THEN '{
            "title": "h1.title-detail",
            "content": ".fck_detail",
            "author": ".author",
            "publish_time": ".date",
            "category": ".breadcrumb a:last-child",
            "tags": ".tags a",
            "image": ".fig-picture img"
        }'::jsonb
        WHEN 'tuoitre.vn' THEN '{
            "title": "h1.article-title",
            "content": ".article-content",
            "author": ".author-info",
            "publish_time": ".date-time",
            "category": ".breadcrumb-item",
            "tags": ".keyword-tags a",
            "image": ".article-image img"
        }'::jsonb
        ELSE '{
            "title": "h1",
            "content": ".content, .article-body",
            "author": ".author",
            "publish_time": ".time, .date",
            "category": ".category",
            "tags": ".tags a",
            "image": ".main-image img"
        }'::jsonb
    END,
    -- extraction_rules
    '{
        "clean_html": true,
        "extract_images": true,
        "remove_ads": true,
        "min_content_length": 100,
        "language": "vi",
        "encoding": "utf-8"
    }'::jsonb,
    true, -- is_active
    'qwen2.5:3b' -- generated_by_model
FROM domain_ids d
ON CONFLICT DO NOTHING;

-- Insert sample analysis queue entries for testing
WITH domain_ids AS (
    SELECT id, name FROM domains WHERE status = 'ACTIVE' LIMIT 3
)
INSERT INTO domain_analysis_queue 
(id, domain_id, scheduled_time, status, priority, model_version)
SELECT 
    uuid_generate_v4(),
    d.id,
    NOW() + (ROW_NUMBER() OVER () || ' hours')::interval,
    'PENDING',
    CASE 
        WHEN d.name = 'vnexpress.net' THEN 9
        WHEN d.name = 'tuoitre.vn' THEN 8
        ELSE 7
    END,
    'qwen2.5:3b'
FROM domain_ids d
ON CONFLICT DO NOTHING;

-- Update next_analysis_scheduled for active domains
UPDATE domains 
SET next_analysis_scheduled = NOW() + (crawl_frequency_hours || ' hours')::interval
WHERE status = 'ACTIVE' AND next_analysis_scheduled IS NULL;

-- Create a completed analysis example
WITH completed_domain AS (
    SELECT id FROM domains WHERE name = 'vnexpress.net' LIMIT 1
)
INSERT INTO domain_analysis_queue 
(id, domain_id, scheduled_time, status, analysis_started_at, analysis_duration_seconds, model_version, priority)
SELECT 
    uuid_generate_v4(),
    cd.id,
    NOW() - INTERVAL '2 hours',
    'COMPLETED',
    NOW() - INTERVAL '1 hour 45 minutes',
    180, -- 3 minutes
    'qwen2.5:3b',
    8
FROM completed_domain cd;

-- Add comments for seed data tracking
COMMENT ON TABLE domains IS 'Seed data includes 8 Vietnamese news sources for development and testing - Two-Database Architecture';
COMMENT ON TABLE crawl_templates IS 'Seed data includes sample qwen2.5:3b templates for major Vietnamese news sites - crawl4ai ready';
COMMENT ON TABLE domain_analysis_queue IS 'Seed data includes sample analysis queue entries for testing workflow';