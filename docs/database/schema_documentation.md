# Database Schema Documentation - Restructured Architecture

## Overview
This document describes the **restructured database architecture** for the AI-Powered Multi-Domain News Crawler System, designed with two separate logical concerns:

1. **Domain Management Database** - User-configurable domains for crawling
2. **News Data Storage Database** - Crawled news content from crawl4ai

## Architecture Philosophy

### Two-Database Approach
- **Separation of Concerns**: Domain configuration vs. content storage
- **Scalability**: Independent scaling for management vs. data storage
- **Performance**: Optimized queries for different access patterns
- **Maintenance**: Easier backup/recovery strategies

### Database Technology Stack
- **PostgreSQL 15+** with JSONB support
- **UUID primary keys** for all tables  
- **Connection pooling** configured per database
- **ACID compliance** with proper foreign key relationships
- **Full-text search** for news content
- **Time-series optimization** for news data

# Database 1: Domain Management System

> **Purpose**: User interface for adding/editing/deleting domains, automatic domain analysis for crawl4ai integration

## Core Domain Management Tables

### domains
**Primary table for user-managed crawlable domains**

```sql
CREATE TABLE domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Basic Domain Info
    name VARCHAR(255) NOT NULL UNIQUE, -- e.g., "vnexpress.net"
    display_name VARCHAR(255) NOT NULL, -- e.g., "VNExpress News"
    base_url TEXT NOT NULL, -- e.g., "https://vnexpress.net"
    logo_url TEXT, -- Domain logo for web interface
    language VARCHAR(10) DEFAULT 'vi', -- Language code
    country VARCHAR(10) DEFAULT 'VN', -- Country code
    
    -- Crawling Configuration
    status domain_status NOT NULL DEFAULT 'ACTIVE',
    crawl_frequency_hours INTEGER NOT NULL DEFAULT 24 CHECK (crawl_frequency_hours > 0),
    max_articles_per_crawl INTEGER DEFAULT 100 CHECK (max_articles_per_crawl > 0),
    
    -- Auto-Analysis Integration
    last_analyzed TIMESTAMP WITH TIME ZONE,
    next_analysis_scheduled TIMESTAMP WITH TIME ZONE,
    analysis_template_id UUID, -- Reference to active template
    
    -- Performance Tracking
    success_rate_24h DECIMAL(5,2) DEFAULT 0.00 CHECK (success_rate_24h >= 0.00 AND success_rate_24h <= 100.00),
    total_articles_crawled INTEGER DEFAULT 0,
    last_successful_crawl TIMESTAMP WITH TIME ZONE,
    
    -- User Management
    created_by_user_id UUID NOT NULL, -- Reference to users table
    is_user_added BOOLEAN DEFAULT true, -- User-added vs system-added
    
    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Key Features:**
- **Unique domain names** prevent duplicates
- **Status enum** tracks domain lifecycle (ACTIVE, INACTIVE, ANALYZING, FAILED)
- **Success rate tracking** for performance monitoring
- **Flexible crawl frequency** per domain
- **Automatic timestamps** with timezone support

**Indexes:**
- `idx_domain_configurations_domain_name` - Unique index on domain_name
- `idx_domain_configurations_status` - Filter by status
- `idx_domain_configurations_next_analysis` - Scheduled analysis lookup

### crawl_templates
**AI-generated parsing templates for crawl4ai integration**

```sql
CREATE TABLE crawl_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    
    -- Template Metadata
    template_name VARCHAR(255) NOT NULL, -- e.g., "vnexpress_news_v2"
    template_version INTEGER NOT NULL DEFAULT 1,
    confidence_score DECIMAL(5,4) NOT NULL CHECK (confidence_score >= 0.0000 AND confidence_score <= 1.0000),
    
    -- crawl4ai Integration
    crawl4ai_config JSONB NOT NULL, -- Complete crawl4ai configuration
    css_selectors JSONB NOT NULL, -- CSS selectors for content extraction
    extraction_rules JSONB NOT NULL, -- Content processing rules
    
    -- Template Data Structure:
    -- {
    --   "crawl4ai": {
    --     "wait_for": ".article-content",
    --     "css_selector": ".news-item",
    --     "extraction_strategy": "CosineStrategy",
    --     "chunking_strategy": "RegexChunking"
    --   },
    --   "selectors": {
    --     "title": "h1.title-detail",
    --     "content": ".fck_detail",
    --     "author": ".author",
    --     "publish_time": ".date",
    --     "category": ".breadcrumb a:last-child",
    --     "tags": ".tags a",
    --     "image": ".fig-picture img"
    --   },
    --   "rules": {
    --     "clean_html": true,
    --     "extract_images": true,
    --     "remove_ads": true,
    --     "min_content_length": 100
    --   }
    -- }
    
    -- Performance Metrics
    success_rate DECIMAL(5,4) DEFAULT 0.0000,
    avg_extraction_time_ms INTEGER DEFAULT 0,
    last_tested TIMESTAMP WITH TIME ZONE,
    
    -- Template Status
    is_active BOOLEAN NOT NULL DEFAULT false,
    generated_by_model VARCHAR(50) DEFAULT 'qwen2.5:3b', -- AI model used
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: Only one active template per domain
    CONSTRAINT unique_active_template_per_domain 
        EXCLUDE USING btree (domain_id WITH =) 
        WHERE (is_active = true)
);
```

**Key Features:**
- **JSONB template storage** for flexible GWEN-3 analysis results
- **Version control** for template updates
- **Confidence scoring** for template quality assessment
- **Structure hash** for change detection
- **Expiration support** for template refresh scheduling
- **Performance metrics** tracking extraction accuracy

**JSONB Structure Example:**
```json
{
    "selectors": {
        "title": "h1.title-detail",
        "content": ".fck_detail",
        "author": ".author",
        "publish_time": ".date"
    },
    "extraction_rules": {
        "clean_html": true,
        "extract_images": true,
        "remove_ads": true
    }
}
```

**Indexes:**
- `idx_domain_parsing_templates_domain_config` - Foreign key lookup
- `idx_domain_parsing_templates_active_expires` - Active template selection
- `idx_domain_parsing_templates_template_data` - GIN index for JSONB queries
- `idx_domain_parsing_templates_performance_metrics` - GIN index for metrics

### domain_analysis_queue
Manages daily GWEN-3 analysis scheduling for 200+ domains.

```sql
CREATE TABLE domain_analysis_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_config_id UUID NOT NULL REFERENCES domain_configurations(id) ON DELETE CASCADE,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status analysis_status NOT NULL DEFAULT 'PENDING',
    analysis_started_at TIMESTAMP WITH TIME ZONE,
    analysis_duration_seconds INTEGER CHECK (analysis_duration_seconds >= 0),
    gwen3_model_version VARCHAR(50),
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Key Features:**
- **Status enum** tracks analysis lifecycle (PENDING, RUNNING, COMPLETED, FAILED, RETRYING)
- **Priority system** (1-10) for urgent domain analysis
- **Retry logic** with automatic retry count tracking
- **Duration tracking** for performance monitoring
- **Error logging** for failed analysis debugging
- **Model version tracking** for GWEN-3 updates

**Indexes:**
- `idx_domain_analysis_queue_scheduled_time` - Time-based scheduling
- `idx_domain_analysis_queue_priority_scheduled` - Priority queue processing
- `idx_domain_analysis_queue_retry_count` - Failed job retry lookup

## Enums

### domain_status
```sql
CREATE TYPE domain_status AS ENUM (
    'ACTIVE',    -- Domain is actively crawled
    'INACTIVE',  -- Domain is disabled
    'ANALYZING', -- Domain is being analyzed by GWEN-3
    'FAILED'     -- Domain analysis/crawling failed
);
```

### analysis_status
```sql
CREATE TYPE analysis_status AS ENUM (
    'PENDING',   -- Analysis scheduled but not started
    'RUNNING',   -- Analysis currently in progress
    'COMPLETED', -- Analysis finished successfully
    'FAILED',    -- Analysis failed with error
    'RETRYING'   -- Analysis being retried after failure
);
```

## Relationships

### Foreign Key Constraints
- `domain_parsing_templates.domain_config_id` → `domain_configurations.id`
- `domain_analysis_queue.domain_config_id` → `domain_configurations.id`

### Cascade Behavior
- **ON DELETE CASCADE** - Deleting a domain configuration removes all related templates and queue entries
- **Data integrity** maintained through proper constraint definitions

## Integration Points

### Existing Schema Integration
- **Optional foreign key** from `news_articles` to `domain_configurations` 
- **Backward compatibility** maintained with existing crawler functionality
- **Graceful degradation** if domain management features are disabled

### View for Monitoring
```sql
CREATE VIEW domain_crawling_stats AS
SELECT 
    dc.id,
    dc.domain_name,
    dc.status,
    dc.success_rate_24h,
    COUNT(dpt.id) as template_count,
    MAX(dpt.confidence_score) as best_template_confidence,
    COUNT(daq.id) FILTER (WHERE daq.status = 'PENDING') as pending_analyses
FROM domain_configurations dc
LEFT JOIN domain_parsing_templates dpt ON dc.id = dpt.domain_config_id
LEFT JOIN domain_analysis_queue daq ON dc.id = daq.domain_config_id
GROUP BY dc.id, dc.domain_name, dc.status, dc.success_rate_24h;
```

## Performance Optimization

### Connection Pooling Configuration
- **Pool size**: 20 base connections
- **Max overflow**: 30 additional connections
- **Total capacity**: 50 concurrent connections
- **Memory efficient** within 16GB system constraint

### Query Optimization
- **Composite indexes** for multi-column queries
- **Partial indexes** with WHERE clauses for filtered queries
- **GIN indexes** for JSONB column searches
- **Regular ANALYZE** for query planner optimization

### Monitoring Queries
```sql
-- Active domain analysis status
SELECT domain_name, status, COUNT(*) as pending_analyses
FROM domain_configurations dc
LEFT JOIN domain_analysis_queue daq ON dc.id = daq.domain_config_id
WHERE daq.status = 'PENDING'
GROUP BY domain_name, status;

-- Template performance metrics
SELECT domain_name, confidence_score, 
       performance_metrics->>'success_rate' as success_rate
FROM domain_configurations dc
JOIN domain_parsing_templates dpt ON dc.id = dpt.domain_config_id
WHERE dpt.is_active = true
ORDER BY confidence_score DESC;
```

## Migration Management

### Migration Files
1. `001_initial_domain_schema.sql` - Core table creation
2. `002_add_domain_indexes.sql` - Performance indexes
3. `003_foreign_key_constraints.sql` - Integration constraints
4. `004_initial_seed_data.sql` - Development seed data

### Migration Tracking
- **schema_migrations** table tracks applied migrations
- **Rollback support** with automated rollback scripts
- **Version control** with description and timestamp

## Security Considerations

### Access Control
- **Database user permissions** restrict table access
- **Connection encryption** with SSL/TLS
- **Input validation** prevents SQL injection
- **Parameterized queries** in all application code

### Data Privacy
- **No sensitive data** stored in JSONB fields
- **Audit logging** for configuration changes
- **Secure backup procedures** with encryption

## Backup and Recovery

### Backup Strategy
- **Full database backups** include all domain tables
- **Point-in-time recovery** supported
- **Schema-only backups** for development setup
- **Data-only backups** for production data migration

### Recovery Procedures
- **Migration rollback** scripts for schema issues
- **Data recovery** from backup files
- **Partial recovery** for individual domain configurations
- **Testing procedures** in staging environment

## Development Guidelines

### Code Standards
- **UUID primary keys** for all new tables
- **TIMESTAMP WITH TIME ZONE** for all time fields
- **JSONB validation** for flexible data structures
- **Proper indexing** for query performance
- **Comprehensive testing** with 85% coverage target

### Common Patterns
- **Enum types** for status fields
- **Check constraints** for data validation
- **Foreign key cascades** for data consistency
- **Automatic timestamps** with triggers
- **GIN indexes** for JSONB columns