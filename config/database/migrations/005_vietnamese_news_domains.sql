-- Vietnamese News Domains Database Setup
-- Sample domains and crawl data for Analysis Worker testing
-- Date: 2025-08-12

-- Domain configurations table
CREATE TABLE IF NOT EXISTS domain_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_name VARCHAR(255) UNIQUE NOT NULL,
    base_url VARCHAR(512) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    crawl_priority INTEGER DEFAULT 5,
    expected_selectors JSONB,
    crawl_settings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis results table  
CREATE TABLE IF NOT EXISTS domain_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id VARCHAR(255) UNIQUE NOT NULL,
    domain_config_id UUID REFERENCES domain_configurations(id),
    domain_name VARCHAR(255) NOT NULL,
    base_url VARCHAR(512) NOT NULL,
    analysis_timestamp TIMESTAMP NOT NULL,
    analysis_duration_seconds DECIMAL(10,3),
    status VARCHAR(20) NOT NULL,
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    parsing_template JSONB,
    discovery_methods JSONB,
    content_samples JSONB,
    overall_confidence_score DECIMAL(4,3),
    language_detected VARCHAR(50),
    structure_hash VARCHAR(64),
    vietnamese_content_ratio DECIMAL(4,3),
    layout_type VARCHAR(100),
    complexity_assessment JSONB,
    tracking_strategy JSONB,
    errors TEXT[],
    warnings TEXT[],
    gwen3_analysis_time DECIMAL(10,3),
    url_discovery_time DECIMAL(10,3),
    template_generation_time DECIMAL(10,3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Discovered URLs table
CREATE TABLE IF NOT EXISTS discovered_urls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_config_id UUID REFERENCES domain_configurations(id),
    domain_name VARCHAR(255) NOT NULL,
    url VARCHAR(1024) NOT NULL,
    url_type VARCHAR(50) NOT NULL, -- rss, sitemap, category, article
    discovery_method VARCHAR(100) NOT NULL,
    confidence_score DECIMAL(4,3),
    metadata JSONB,
    last_crawled TIMESTAMP,
    crawl_status VARCHAR(20) DEFAULT 'PENDING',
    content_hash VARCHAR(64),
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crawled articles table
CREATE TABLE IF NOT EXISTS crawled_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_config_id UUID REFERENCES domain_configurations(id),
    url_id UUID REFERENCES discovered_urls(id),
    article_url VARCHAR(1024) NOT NULL,
    title TEXT,
    content TEXT,
    author VARCHAR(255),
    publish_date TIMESTAMP,
    category VARCHAR(255),
    tags TEXT[],
    extracted_metadata JSONB,
    content_quality_score DECIMAL(4,3),
    extraction_confidence DECIMAL(4,3),
    crawl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(20) DEFAULT 'PROCESSED'
);

-- Insert 20+ Vietnamese news domains
INSERT INTO domain_configurations (domain_name, base_url, display_name, category, crawl_priority, expected_selectors, crawl_settings) VALUES

-- Major National News
('vnexpress.net', 'https://vnexpress.net', 'VnExpress', 'National News', 1, '{
    "headline": ["h1.title-news", ".title-detail h1", "h1.title_news_detail"],
    "content": [".fck_detail", ".Normal", ".content_detail"],
    "author": [".author", ".byline", ".author_mail"],
    "date": [".date", ".time", ".publish_time"],
    "category": [".breadcrumb a", ".section-name", ".category"]
}', '{
    "max_depth": 3,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('dantri.com.vn', 'https://dantri.com.vn', 'Dân Trí', 'National News', 1, '{
    "headline": ["h1.title-page", ".article-title h1", "h1.dt-text-title"],
    "content": [".singular-content", ".dt-news__content", ".article-content"],
    "author": [".author-name", ".byline", ".dt-news__author"],
    "date": [".news-time", ".date-time", ".dt-news__time"],
    "category": [".breadcrumb", ".category-name"]
}', '{
    "max_depth": 3,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('tuoitre.vn', 'https://tuoitre.vn', 'Tuổi Trẻ', 'National News', 1, '{
    "headline": ["h1.article-title", ".detail-title h1", "h1.title-news"],
    "content": [".detail-content", ".article-content", "#main-detail-body"],
    "author": [".author", ".detail-author", ".byline"],
    "date": [".date-time", ".detail-time", ".publish-time"],
    "category": [".breadcrumb", ".cate-news"]
}', '{
    "max_depth": 3,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('thanhnien.vn', 'https://thanhnien.vn', 'Thanh Niên', 'National News', 1, '{
    "headline": ["h1.details__headline", ".article-title", "h1.title"],
    "content": [".details__content", ".article-body", ".content-detail"],
    "author": [".details__author", ".author-name"],
    "date": [".details__meta-time", ".publish-time"],
    "category": [".breadcrumb", ".category"]
}', '{
    "max_depth": 3,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('vietnamnet.vn', 'https://vietnamnet.vn', 'VietnamNet', 'National News', 2, '{
    "headline": ["h1.title", ".article-title", "h1.newsTitle"],
    "content": [".ArticleContent", ".article-content", ".maincontent"],
    "author": [".author", ".ArticleAuthor"],
    "date": [".time", ".ArticleDate"],
    "category": [".breadcrumb", ".cate"]
}', '{
    "max_depth": 3,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('vtv.vn', 'https://vtv.vn', 'VTV News', 'Television News', 2, '{
    "headline": ["h1.title", ".tlq-headline", ".news-title"],
    "content": [".ta-justify", ".content-news", ".article-content"],
    "author": [".author", ".news-author"],
    "date": [".time", ".news-time"],
    "category": [".breadcrumb", ".cate-link"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 2
}'),

-- Business & Economy
('cafef.vn', 'https://cafef.vn', 'CafeF', 'Business', 2, '{
    "headline": ["h1.title", ".sapo-detail h1", "h1.baiviet-title"],
    "content": [".content-detail", ".baiviet-content", ".detail-content"],
    "author": [".author-name", ".tacgia"],
    "date": [".time", ".ngay-dang"],
    "category": [".breadcrumb", ".chuyenmuc"]
}', '{
    "max_depth": 3,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('nguoiduatin.vn', 'https://nguoiduatin.vn', 'Người Dua Tin', 'Business', 3, '{
    "headline": ["h1.title-detail", ".article-title"],
    "content": [".detail-content", ".article-body"],
    "author": [".author-name"],
    "date": [".time-update"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('tienphong.vn', 'https://tienphong.vn', 'Tiền Phong', 'General News', 2, '{
    "headline": ["h1.article__title", ".detail-title"],
    "content": [".article__content", ".detail-content"],
    "author": [".article__author", ".author"],
    "date": [".article__time", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 3,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('laodong.vn', 'https://laodong.vn', 'Lao Động', 'Labor & Society', 2, '{
    "headline": ["h1.article-title", ".detail-title h1"],
    "content": [".article-content", ".detail-content"],
    "author": [".author-info", ".author"],
    "date": [".article-time", ".publish-time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 3,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

-- Regional News
('24h.com.vn', 'https://24h.com.vn', '24H News', 'General News', 3, '{
    "headline": ["h1.baiviet-title", ".article-title"],
    "content": [".baiviet-content", ".article-content"],
    "author": [".tacgia", ".author"],
    "date": [".capnhat", ".time"],
    "category": [".chuyenmuc"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('soha.vn', 'https://soha.vn', 'Soha News', 'Entertainment & News', 3, '{
    "headline": ["h1.story-title", ".article-title"],
    "content": [".story-content", ".article-body"],
    "author": [".story-author", ".author"],
    "date": [".story-time", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('nld.com.vn', 'https://nld.com.vn', 'Người Lao Động', 'Labor News', 2, '{
    "headline": ["h1.news-title", ".article-title"],
    "content": [".news-content", ".article-content"],
    "author": [".news-author", ".author"],
    "date": [".news-time", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 3,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('baomoi.com', 'https://baomoi.com', 'Báo Mới', 'News Aggregator', 4, '{
    "headline": ["h1.article-title", ".story-title"],
    "content": [".article-content", ".story-content"],
    "author": [".article-author", ".author"],
    "date": [".article-time", ".time"],
    "category": [".category"]
}', '{
    "max_depth": 2,
    "follow_external": true,
    "respect_robots": true,
    "crawl_delay": 2
}'),

('zing.vn', 'https://zing.vn', 'Zing News', 'Technology & Lifestyle', 3, '{
    "headline": ["h1.the-article-title", ".article-title"],
    "content": [".the-article-body", ".article-content"],
    "author": [".the-article-credit", ".author"],
    "date": [".the-article-publish", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

-- Sports
('thethao247.vn', 'https://thethao247.vn', 'Thể Thao 247', 'Sports', 3, '{
    "headline": ["h1.article-title", ".news-title"],
    "content": [".article-content", ".news-content"],
    "author": [".author-name", ".author"],
    "date": [".article-time", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('bongda24h.vn', 'https://bongda24h.vn', 'Bóng Đá 24H', 'Football', 3, '{
    "headline": ["h1.title-detail", ".article-title"],
    "content": [".content-detail", ".article-content"],
    "author": [".author", ".nguon"],
    "date": [".time-detail", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

-- Technology
('genk.vn', 'https://genk.vn', 'Genk', 'Technology', 3, '{
    "headline": ["h1.knswli-title", ".article-title"],
    "content": [".knswli-content", ".article-content"],
    "author": [".knswli-author", ".author"],
    "date": [".knswli-time", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('ictnews.vn', 'https://ictnews.vn', 'ICTNews', 'Technology', 3, '{
    "headline": ["h1.detail-title", ".article-title"],
    "content": [".detail-content", ".article-content"],
    "author": [".detail-author", ".author"],
    "date": [".detail-time", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

-- Health & Education
('suckhoedoisong.vn', 'https://suckhoedoisong.vn', 'Sức Khỏe Đời Sống', 'Health', 3, '{
    "headline": ["h1.detail-title", ".article-title"],
    "content": [".detail-content", ".article-content"],
    "author": [".detail-author", ".author"],
    "date": [".detail-time", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('giaoduc.net.vn', 'https://giaoduc.net.vn', 'Giáo Dục Việt Nam', 'Education', 3, '{
    "headline": ["h1.article-title", ".news-title"],
    "content": [".article-content", ".news-content"],
    "author": [".article-author", ".author"],
    "date": [".article-time", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

-- Entertainment
('kenh14.vn', 'https://kenh14.vn', 'Kênh 14', 'Entertainment', 4, '{
    "headline": ["h1.kbwc-title", ".article-title"],
    "content": [".knc-content", ".article-content"],
    "author": [".kbwc-author", ".author"],
    "date": [".kbwc-time", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}'),

('eva.vn', 'https://eva.vn', 'Eva.vn', 'Women & Lifestyle', 4, '{
    "headline": ["h1.article-title", ".news-title"],
    "content": [".article-content", ".news-content"],
    "author": [".author-name", ".author"],
    "date": [".article-time", ".time"],
    "category": [".breadcrumb"]
}', '{
    "max_depth": 2,
    "follow_external": false,
    "respect_robots": true,
    "crawl_delay": 1
}');

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_domain_configurations_domain_name ON domain_configurations(domain_name);
CREATE INDEX IF NOT EXISTS idx_domain_configurations_status ON domain_configurations(status);
CREATE INDEX IF NOT EXISTS idx_domain_configurations_category ON domain_configurations(category);
CREATE INDEX IF NOT EXISTS idx_domain_analysis_results_domain_name ON domain_analysis_results(domain_name);
CREATE INDEX IF NOT EXISTS idx_domain_analysis_results_timestamp ON domain_analysis_results(analysis_timestamp);
CREATE INDEX IF NOT EXISTS idx_discovered_urls_domain_name ON discovered_urls(domain_name);
CREATE INDEX IF NOT EXISTS idx_discovered_urls_type ON discovered_urls(url_type);
CREATE INDEX IF NOT EXISTS idx_crawled_articles_domain_id ON crawled_articles(domain_config_id);
CREATE INDEX IF NOT EXISTS idx_crawled_articles_publish_date ON crawled_articles(publish_date);

-- Update timestamps trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_domain_configurations_updated_at 
    BEFORE UPDATE ON domain_configurations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();