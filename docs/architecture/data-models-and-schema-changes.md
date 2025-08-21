# Data Models and Schema Changes - Two-Database Architecture

## Architecture Overview

This document describes the **complete restructure** to a **two-database architecture** for the AI-Powered Multi-Domain News Crawler System:

### 1. Domain Management Database (OLTP)
**Purpose**: User interface for adding/editing/deleting domains, automatic domain analysis for crawl4ai integration  
**Characteristics**: 
- High transaction volume with frequent reads/writes
- Complex relationships between domains, templates, and analysis queues
- Optimized for web interface CRUD operations
- Real-time domain status updates

### 2. News Data Storage Database (OLAP)
**Purpose**: Store massive volumes of crawled news content from crawl4ai  
**Characteristics**:
- High-volume write-heavy operations from crawl4ai
- Time-series partitioned tables for efficient storage
- Full-text search capabilities
- Optimized for analytical queries and reporting

## Database 1: Domain Management System

### **domains** (Primary Table)
**Purpose:** User-configurable crawlable domains with comprehensive management features

**Schema:**
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
    crawl_frequency_hours INTEGER NOT NULL DEFAULT 24,
    max_articles_per_crawl INTEGER DEFAULT 100,
    
    -- Auto-Analysis Integration
    last_analyzed TIMESTAMP WITH TIME ZONE,
    next_analysis_scheduled TIMESTAMP WITH TIME ZONE,
    analysis_template_id UUID,
    
    -- Performance Tracking
    success_rate_24h DECIMAL(5,2) DEFAULT 0.00,
    total_articles_crawled INTEGER DEFAULT 0,
    last_successful_crawl TIMESTAMP WITH TIME ZONE,
    
    -- User Management
    created_by_user_id UUID NOT NULL,
    is_user_added BOOLEAN DEFAULT true,
    
    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Key Features:**
- **Web Interface Integration**: Supports full CRUD operations for domain management
- **Automatic Analysis Scheduling**: Integrates with GWEN-3 analysis pipeline
- **Performance Monitoring**: Real-time success rate tracking
- **User Attribution**: Tracks which admin user added each domain

### **crawl_templates**
**Purpose:** AI-generated parsing templates for crawl4ai integration

**Schema:**
```sql
CREATE TABLE crawl_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    
    -- Template Metadata
    template_name VARCHAR(255) NOT NULL,
    template_version INTEGER NOT NULL DEFAULT 1,
    confidence_score DECIMAL(5,4) NOT NULL,
    
    -- crawl4ai Integration
    crawl4ai_config JSONB NOT NULL, -- Complete crawl4ai configuration
    css_selectors JSONB NOT NULL, -- CSS selectors for content extraction
    extraction_rules JSONB NOT NULL, -- Content processing rules
    
    -- Performance Metrics
    success_rate DECIMAL(5,4) DEFAULT 0.0000,
    avg_extraction_time_ms INTEGER DEFAULT 0,
    last_tested TIMESTAMP WITH TIME ZONE,
    
    -- Template Status
    is_active BOOLEAN NOT NULL DEFAULT false,
    generated_by_model VARCHAR(50) DEFAULT 'qwen2.5:3b',
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

**Integration Features:**
- **JSONB Structure**: Flexible storage for GWEN-3 analysis results
- **crawl4ai Ready**: Direct integration with crawl4ai extraction engine
- **Version Control**: Template versioning for iterative improvements
- **Automatic Expiration**: Templates expire and trigger re-analysis

### **domain_analysis_queue**
**Purpose:** Manage daily GWEN-3 analysis scheduling for 200+ domains

**Schema:**
```sql
CREATE TABLE domain_analysis_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    
    -- Scheduling
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    
    -- Execution Tracking
    status analysis_status NOT NULL DEFAULT 'PENDING',
    analysis_started_at TIMESTAMP WITH TIME ZONE,
    analysis_duration_seconds INTEGER,
    
    -- Model Information
    gwen3_model_version VARCHAR(50),
    
    -- Error Handling
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Queue Management Features:**
- **Priority System**: 1-10 priority levels for urgent analysis
- **Retry Logic**: Automatic retry with exponential backoff
- **Performance Tracking**: Analysis duration monitoring
- **Model Version Control**: Track which AI model version was used

## Database 2: News Data Storage System

### **news_articles** (Primary Table)
**Purpose:** Store massive volumes of crawled news content with time-series optimization

**Schema:**
```sql
CREATE TABLE news_articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Content Identification
    url TEXT NOT NULL,
    url_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA-256 for deduplication
    canonical_url TEXT,
    
    -- Domain Reference (Links to Domain Management DB)
    domain_name VARCHAR(255) NOT NULL, -- Indexed for cross-db queries
    source_domain_id UUID, -- Optional reference to domains.id
    
    -- Article Content
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_html TEXT,
    summary TEXT,
    
    -- Metadata
    author VARCHAR(255),
    publish_time TIMESTAMP WITH TIME ZONE,
    crawl_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Classification
    category VARCHAR(100),
    tags TEXT[], -- Array of tags
    language VARCHAR(10) DEFAULT 'vi',
    
    -- Content Analysis
    word_count INTEGER,
    reading_time_minutes INTEGER,
    sentiment_score DECIMAL(3,2), -- -1.00 to 1.00
    
    -- Technical Metadata
    crawl_method VARCHAR(50), -- "rss", "sitemap", "category", "manual"
    template_used UUID, -- Reference to crawl_templates.id
    extraction_confidence DECIMAL(5,4),
    
    -- Full-text Search
    content_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('vietnamese', COALESCE(title, '') || ' ' || COALESCE(content, ''))
    ) STORED,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Time-series partitioning by month for performance
CREATE TABLE news_articles_y2025m01 PARTITION OF news_articles
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE news_articles_y2025m02 PARTITION OF news_articles
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Indexes for high-performance queries
CREATE INDEX idx_news_articles_domain_crawl_time ON news_articles (domain_name, crawl_time DESC);
CREATE INDEX idx_news_articles_publish_time ON news_articles (publish_time DESC);
CREATE INDEX idx_news_articles_url_hash ON news_articles (url_hash);
CREATE INDEX idx_news_articles_content_vector ON news_articles USING gin (content_vector);
CREATE INDEX idx_news_articles_tags ON news_articles USING gin (tags);
```

**Key Features:**
- **Time-series Partitioning**: Monthly partitions for efficient large-scale storage
- **Full-text Search**: Built-in Vietnamese text search capabilities
- **Deduplication**: URL hash-based duplicate detection
- **Cross-database Linking**: Optional references to Domain Management database
- **Content Analysis**: Sentiment analysis and reading time estimation

### **crawl_sessions**
**Purpose:** Track individual crawl sessions for debugging and monitoring

**Schema:**
```sql
CREATE TABLE crawl_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Session Metadata
    domain_name VARCHAR(255) NOT NULL,
    crawl_method VARCHAR(50) NOT NULL, -- "rss", "sitemap", "category"
    template_id UUID, -- Reference to crawl_templates.id
    
    -- Session Execution
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'RUNNING', -- RUNNING, COMPLETED, FAILED
    
    -- Results
    articles_discovered INTEGER DEFAULT 0,
    articles_extracted INTEGER DEFAULT 0,
    articles_stored INTEGER DEFAULT 0,
    
    -- Performance
    total_duration_seconds INTEGER,
    avg_extraction_time_ms INTEGER,
    
    -- Error Tracking
    errors JSONB,
    warnings JSONB,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

## Cross-Database Integration Strategy

### **Connection Architecture**
- **Separate Connection Pools**: Independent pools for each database
- **Cross-Database Queries**: Join operations through application layer
- **Data Consistency**: Domain name as shared identifier between databases

### **Migration from Current Schema**
1. **Phase 1**: Create new Domain Management database with full schema
2. **Phase 2**: Migrate existing domain configurations to new structure
3. **Phase 3**: Create News Data Storage database with partitioned tables
4. **Phase 4**: Migrate existing news articles to time-series partitioned structure
5. **Phase 5**: Update Analysis Worker to use new two-database architecture
6. **Phase 6**: Implement web interface for domain CRUD operations

### **Backward Compatibility Strategy**
- **Graceful Migration**: Existing crawler continues during schema migration
- **Dual-Write Period**: Write to both old and new schemas during transition
- **Rollback Support**: Complete rollback scripts for each migration phase
- **Data Validation**: Comprehensive validation between old and new schemas

## Performance Optimization

### **Domain Management Database (OLTP)**
- **Connection Pool**: 10-20 connections for transactional workload
- **Indexes**: Optimized for web interface queries
- **Query Patterns**: Primary key lookups, status filtering, user-based queries

### **News Data Storage Database (OLAP)**
- **Connection Pool**: 30-50 connections for high-throughput writes
- **Partitioning**: Time-series partitioning by month for efficient querying
- **Indexes**: Optimized for time-range queries, full-text search, domain filtering
- **Archival Strategy**: Automated archival of articles older than 2 years

## Web Interface Integration

### **Domain Management Features**
- **Add Domain**: User submits domain → automatic GWEN-3 analysis → template generation
- **Edit Domain**: Update crawl frequency, status, configuration
- **Delete Domain**: Soft delete with cascade to templates and queue entries
- **Monitor Performance**: Real-time success rates, article counts, error tracking

### **Analytics Dashboard**
- **Cross-Database Queries**: Combine domain configuration with news data
- **Performance Metrics**: Crawl success rates, content volume trends
- **Content Analysis**: Tag clouds, sentiment trends, language distribution
- **System Health**: Template performance, queue status, error rates

---
