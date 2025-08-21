-- Sample Crawl Data for Vietnamese News Domains
-- Real-world sample data for testing Analysis Worker
-- Date: 2025-08-12

-- Insert discovered URLs for major Vietnamese news sites
INSERT INTO discovered_urls (domain_config_id, domain_name, url, url_type, discovery_method, confidence_score, metadata) 
SELECT 
    dc.id,
    dc.domain_name,
    sample_urls.url,
    sample_urls.url_type,
    sample_urls.discovery_method,
    sample_urls.confidence_score,
    sample_urls.metadata
FROM domain_configurations dc
CROSS JOIN (
    VALUES 
    -- VnExpress URLs
    ('vnexpress.net', 'https://vnexpress.net/rss/tin-moi-nhat.rss', 'rss', 'rss_discovery', 0.95, '{"feed_type": "latest_news", "update_frequency": "5_minutes"}'),
    ('vnexpress.net', 'https://vnexpress.net/rss/thoi-su.rss', 'rss', 'rss_discovery', 0.95, '{"feed_type": "politics", "update_frequency": "15_minutes"}'),
    ('vnexpress.net', 'https://vnexpress.net/rss/kinh-doanh.rss', 'rss', 'rss_discovery', 0.95, '{"feed_type": "business", "update_frequency": "15_minutes"}'),
    ('vnexpress.net', 'https://vnexpress.net/sitemap.xml', 'sitemap', 'sitemap_discovery', 0.90, '{"sitemap_type": "main", "last_modified": "2025-08-12"}'),
    ('vnexpress.net', 'https://vnexpress.net/thoi-su', 'category', 'navigation_analysis', 0.85, '{"category_type": "politics", "article_count": 50}'),
    ('vnexpress.net', 'https://vnexpress.net/kinh-doanh', 'category', 'navigation_analysis', 0.85, '{"category_type": "business", "article_count": 45}'),
    ('vnexpress.net', 'https://vnexpress.net/the-thao', 'category', 'navigation_analysis', 0.85, '{"category_type": "sports", "article_count": 40}'),
    
    -- Dantri URLs  
    ('dantri.com.vn', 'https://dantri.com.vn/rss/trangchu.rss', 'rss', 'rss_discovery', 0.95, '{"feed_type": "homepage", "update_frequency": "5_minutes"}'),
    ('dantri.com.vn', 'https://dantri.com.vn/rss/suckhoedoisong.rss', 'rss', 'rss_discovery', 0.92, '{"feed_type": "health", "update_frequency": "30_minutes"}'),
    ('dantri.com.vn', 'https://dantri.com.vn/sitemap.xml', 'sitemap', 'sitemap_discovery', 0.88, '{"sitemap_type": "main", "last_modified": "2025-08-12"}'),
    ('dantri.com.vn', 'https://dantri.com.vn/xa-hoi.htm', 'category', 'navigation_analysis', 0.82, '{"category_type": "society", "article_count": 55}'),
    ('dantri.com.vn', 'https://dantri.com.vn/kinh-doanh.htm', 'category', 'navigation_analysis', 0.82, '{"category_type": "business", "article_count": 35}'),
    
    -- Tuoi Tre URLs
    ('tuoitre.vn', 'https://tuoitre.vn/rss/tt-thoi-su.rss', 'rss', 'rss_discovery', 0.93, '{"feed_type": "news", "update_frequency": "10_minutes"}'),
    ('tuoitre.vn', 'https://tuoitre.vn/rss/tt-kinh-te.rss', 'rss', 'rss_discovery', 0.93, '{"feed_type": "economy", "update_frequency": "20_minutes"}'),
    ('tuoitre.vn', 'https://tuoitre.vn/sitemap_index.xml', 'sitemap', 'sitemap_discovery', 0.87, '{"sitemap_type": "index", "last_modified": "2025-08-12"}'),
    ('tuoitre.vn', 'https://tuoitre.vn/thoi-su.htm', 'category', 'navigation_analysis', 0.80, '{"category_type": "current_affairs", "article_count": 60}'),
    
    -- Thanh Nien URLs
    ('thanhnien.vn', 'https://thanhnien.vn/rss/home.rss', 'rss', 'rss_discovery', 0.91, '{"feed_type": "homepage", "update_frequency": "10_minutes"}'),
    ('thanhnien.vn', 'https://thanhnien.vn/rss/thoi-su.rss', 'rss', 'rss_discovery', 0.91, '{"feed_type": "politics", "update_frequency": "15_minutes"}'),
    ('thanhnien.vn', 'https://thanhnien.vn/sitemap.xml', 'sitemap', 'sitemap_discovery', 0.85, '{"sitemap_type": "main", "last_modified": "2025-08-12"}'),
    ('thanhnien.vn', 'https://thanhnien.vn/thoi-su', 'category', 'navigation_analysis', 0.78, '{"category_type": "politics", "article_count": 48}'),
    
    -- CafeF URLs
    ('cafef.vn', 'https://cafef.vn/thi-truong-chung-khoan.rss', 'rss', 'rss_discovery', 0.94, '{"feed_type": "stock_market", "update_frequency": "5_minutes"}'),
    ('cafef.vn', 'https://cafef.vn/kinh-te-vi-mo.rss', 'rss', 'rss_discovery', 0.94, '{"feed_type": "macro_economy", "update_frequency": "30_minutes"}'),
    ('cafef.vn', 'https://cafef.vn/sitemap.xml', 'sitemap', 'sitemap_discovery', 0.88, '{"sitemap_type": "main", "last_modified": "2025-08-12"}'),
    
    -- VTC News URLs
    ('vtv.vn', 'https://vtv.vn/trong-nuoc.rss', 'rss', 'rss_discovery', 0.89, '{"feed_type": "domestic", "update_frequency": "15_minutes"}'),
    ('vtv.vn', 'https://vtv.vn/the-gioi.rss', 'rss', 'rss_discovery', 0.89, '{"feed_type": "world", "update_frequency": "30_minutes"}'),
    ('vtv.vn', 'https://vtv.vn/sitemap.xml', 'sitemap', 'sitemap_discovery', 0.83, '{"sitemap_type": "main", "last_modified": "2025-08-12"}')
    
) AS sample_urls(domain_name, url, url_type, discovery_method, confidence_score, metadata)
WHERE dc.domain_name = sample_urls.domain_name;

-- Insert sample analysis results
INSERT INTO domain_analysis_results (
    analysis_id, domain_config_id, domain_name, base_url, analysis_timestamp, 
    analysis_duration_seconds, status, model_name, model_version,
    parsing_template, discovery_methods, content_samples, overall_confidence_score,
    language_detected, structure_hash, vietnamese_content_ratio, layout_type,
    complexity_assessment, tracking_strategy, errors, warnings,
    gwen3_analysis_time, url_discovery_time, template_generation_time
)
SELECT 
    'analysis-' || substr(md5(random()::text), 1, 8),
    dc.id,
    dc.domain_name,
    dc.base_url,
    CURRENT_TIMESTAMP - (random() * interval '7 days'),
    2.5 + (random() * 8.0), -- Random duration between 2.5-10.5 seconds
    'COMPLETED',
    'gwen-2.5:3b',
    '2.5.0',
    CASE dc.domain_name
        WHEN 'vnexpress.net' THEN '{
            "headline_selectors": ["h1.title-news", ".title-detail h1"],
            "content_selectors": [".fck_detail", ".Normal"],
            "metadata_selectors": {"author": ".author", "date": ".date", "category": ".breadcrumb a"},
            "navigation_selectors": ["nav.navigation", ".menu-list"],
            "article_link_selectors": ["a[href*=\"/tin-tuc/\"]", ".item-news a"],
            "confidence_score": 0.92
        }'::jsonb
        WHEN 'dantri.com.vn' THEN '{
            "headline_selectors": ["h1.title-page", ".dt-text-title"],
            "content_selectors": [".singular-content", ".dt-news__content"],
            "metadata_selectors": {"author": ".dt-news__author", "date": ".dt-news__time", "category": ".breadcrumb"},
            "navigation_selectors": [".main-nav", ".menu"],
            "article_link_selectors": ["a[href*=\".htm\"]", ".news-item a"],
            "confidence_score": 0.88
        }'::jsonb
        WHEN 'tuoitre.vn' THEN '{
            "headline_selectors": ["h1.article-title", ".detail-title h1"],
            "content_selectors": [".detail-content", "#main-detail-body"],
            "metadata_selectors": {"author": ".detail-author", "date": ".detail-time", "category": ".breadcrumb"},
            "navigation_selectors": [".main-menu", ".navigation"],
            "article_link_selectors": ["a[href*=\"/tin-tuc/\"]", ".box-category-item a"],
            "confidence_score": 0.85
        }'::jsonb
        ELSE '{
            "headline_selectors": ["h1", ".title", ".headline"],
            "content_selectors": [".content", ".article-content", ".main-content"],
            "metadata_selectors": {"author": ".author", "date": ".date"},
            "navigation_selectors": ["nav", ".menu"],
            "article_link_selectors": ["a"],
            "confidence_score": 0.75
        }'::jsonb
    END,
    '[
        {
            "method_type": "rss",
            "urls": ["' || dc.base_url || '/rss/tin-moi-nhat.rss"],
            "confidence_score": 0.95,
            "metadata": {"feed_count": 1, "discovery_source": "automated"}
        },
        {
            "method_type": "sitemap", 
            "urls": ["' || dc.base_url || '/sitemap.xml"],
            "confidence_score": 0.85,
            "metadata": {"sitemap_count": 1, "discovery_source": "automated"}
        }
    ]'::jsonb,
    '[
        {
            "url": "' || dc.base_url || '",
            "content_type": "homepage",
            "size_bytes": ' || (1000 + floor(random() * 3000))::text || ',
            "fetch_timestamp": "' || (CURRENT_TIMESTAMP - interval '1 hour')::text || '"
        }
    ]'::jsonb,
    0.75 + (random() * 0.20), -- Confidence between 0.75-0.95
    'vietnamese',
    substr(md5(dc.domain_name || random()::text), 1, 12),
    0.85 + (random() * 0.10), -- Vietnamese ratio 0.85-0.95
    CASE 
        WHEN dc.category = 'National News' THEN 'standard_news'
        WHEN dc.category = 'Business' THEN 'business_layout'
        WHEN dc.category = 'Sports' THEN 'sports_layout'
        ELSE 'generic_news'
    END,
    '{
        "template_complexity": ' || (1 + floor(random() * 4))::text || ',
        "selector_count": ' || (5 + floor(random() * 10))::text || ',
        "confidence_level": "high"
    }'::jsonb,
    '{
        "multi_source_monitoring": {
            "rss_feeds": ["' || dc.base_url || '/rss/tin-moi-nhat.rss"],
            "monitoring_enabled": true
        },
        "update_frequencies": {
            "rss_monitoring": "5_minutes",
            "homepage_monitoring": "15_minutes"
        }
    }'::jsonb,
    '{}', -- No errors for successful analysis
    CASE 
        WHEN random() < 0.3 THEN ARRAY['Low confidence on some selectors']
        ELSE '{}'
    END,
    1.0 + (random() * 3.0), -- GWEN analysis time 1-4 seconds
    0.5 + (random() * 1.5), -- URL discovery time 0.5-2 seconds  
    0.3 + (random() * 0.7)  -- Template generation time 0.3-1 seconds
FROM domain_configurations dc
WHERE dc.status = 'ACTIVE'
ORDER BY random()
LIMIT 15; -- Create 15 sample analysis results

-- Insert sample crawled articles
INSERT INTO crawled_articles (
    domain_config_id, url_id, article_url, title, content, author, 
    publish_date, category, tags, extracted_metadata, content_quality_score,
    extraction_confidence, crawl_timestamp, processing_status
)
SELECT 
    dc.id,
    du.id,
    dc.base_url || '/tin-tuc/sample-article-' || generate_random_uuid(),
    CASE dc.domain_name
        WHEN 'vnexpress.net' THEN 'Tin tức mới nhất về kinh tế Việt Nam ' || floor(random() * 1000)
        WHEN 'dantri.com.vn' THEN 'Phát triển kinh tế xã hội năm 2025 ' || floor(random() * 1000)
        WHEN 'tuoitre.vn' THEN 'Cập nhật tình hình chính trị trong nước ' || floor(random() * 1000)
        WHEN 'thanhnien.vn' THEN 'Thông tin xã hội mới nhất hôm nay ' || floor(random() * 1000)
        ELSE 'Tin tức từ ' || dc.display_name || ' số ' || floor(random() * 1000)
    END,
    'Nội dung bài viết tiếng Việt với thông tin chi tiết về chủ đề được đề cập. '
    || 'Bài viết bao gồm các thông tin cập nhật và phân tích sâu sắc về tình hình hiện tại. '
    || 'Đây là nội dung mẫu được tạo tự động để test hệ thống crawl data. '
    || 'Thông tin được cập nhật thường xuyên từ các nguồn tin đáng tin cậy.',
    CASE floor(random() * 5)
        WHEN 0 THEN 'Nguyễn Văn An'
        WHEN 1 THEN 'Trần Thị Bình' 
        WHEN 2 THEN 'Lê Minh Chính'
        WHEN 3 THEN 'Phạm Thu Dung'
        ELSE 'Hoàng Văn Việt'
    END,
    CURRENT_TIMESTAMP - (random() * interval '30 days'),
    dc.category,
    ARRAY[
        CASE floor(random() * 4)
            WHEN 0 THEN 'tin-tuc'
            WHEN 1 THEN 'thoi-su'
            WHEN 2 THEN 'kinh-te'
            ELSE 'xa-hoi'
        END,
        'vietnam', 'news'
    ],
    '{
        "word_count": ' || (200 + floor(random() * 800))::text || ',
        "reading_time": ' || (1 + floor(random() * 5))::text || ',
        "language": "vietnamese",
        "source": "' || dc.domain_name || '"
    }'::jsonb,
    0.70 + (random() * 0.25), -- Quality score 0.70-0.95
    0.80 + (random() * 0.15), -- Extraction confidence 0.80-0.95
    CURRENT_TIMESTAMP - (random() * interval '7 days'),
    'PROCESSED'
FROM domain_configurations dc
JOIN discovered_urls du ON dc.id = du.domain_config_id
WHERE dc.status = 'ACTIVE' 
    AND du.url_type IN ('category', 'rss')
    AND random() < 0.3 -- Only 30% of URLs have articles
ORDER BY random()
LIMIT 50; -- Create 50 sample articles

-- Update crawl status for some discovered URLs
UPDATE discovered_urls 
SET 
    last_crawled = CURRENT_TIMESTAMP - (random() * interval '24 hours'),
    crawl_status = CASE 
        WHEN random() < 0.7 THEN 'SUCCESS'
        WHEN random() < 0.9 THEN 'PENDING'
        ELSE 'FAILED'
    END,
    content_hash = substr(md5(random()::text), 1, 16)
WHERE id IN (
    SELECT id FROM discovered_urls ORDER BY random() LIMIT 30
);

-- Create some analysis results with errors (for testing error handling)
INSERT INTO domain_analysis_results (
    analysis_id, domain_config_id, domain_name, base_url, analysis_timestamp,
    analysis_duration_seconds, status, model_name, model_version,
    overall_confidence_score, language_detected, structure_hash,
    vietnamese_content_ratio, layout_type, errors, warnings,
    gwen3_analysis_time, url_discovery_time, template_generation_time
)
SELECT 
    'failed-analysis-' || substr(md5(random()::text), 1, 8),
    dc.id,
    dc.domain_name,
    dc.base_url,
    CURRENT_TIMESTAMP - (random() * interval '7 days'),
    15.0 + (random() * 30.0), -- Longer duration for failed analysis
    'FAILED',
    'gwen-2.5:3b',
    '2.5.0',
    0.0,
    'unknown',
    '',
    0.0,
    'unknown',
    ARRAY[
        CASE floor(random() * 4)
            WHEN 0 THEN 'Connection timeout to domain'
            WHEN 1 THEN 'Invalid HTML structure detected'
            WHEN 2 THEN 'GWEN model processing error'
            ELSE 'Domain not accessible'
        END
    ],
    ARRAY['Low confidence due to errors', 'Retry recommended'],
    0.0,
    0.0,
    0.0
FROM domain_configurations dc
WHERE dc.status = 'ACTIVE'
ORDER BY random()
LIMIT 3; -- Create 3 failed analysis examples