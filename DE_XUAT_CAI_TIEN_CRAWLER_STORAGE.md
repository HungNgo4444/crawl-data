# 🚀 ĐỀ XUẤT CẢI TIẾN CRAWLER & STORAGE LAYER

## 🎯 **MỤC TIÊU CẢI TIẾN**

### **Focus Areas**:
1. **Crawler Layer**: Tăng tốc độ crawl news sites (bỏ qua social media)
2. **Storage Layer**: Tối ưu hóa lưu trữ và truy xuất data

---

## 🏗️ **1. CRAWLER LAYER - KIẾN TRÚC MỚI**

### **🔥 Vấn đề hiện tại**:
- Playwright quá chậm cho việc crawl news sites
- Chỉ có 1 strategy → không tối ưu cho từng loại site
- Không có pre-crawling để thu thập links

### **💡 Giải pháp: Multi-Stage Hybrid Crawler**

```
┌─────────────────────────────────────────────────────────────┐
│                 NEW CRAWLER ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│  STAGE 1: LINK DISCOVERY                                   │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │ Fast Scrapy     │───▶│ Link Extractor  │               │
│  │ - RSS Feeds     │    │ - Filter URLs   │               │
│  │ - Sitemap.xml   │    │ - Deduplicate   │               │
│  │ - Category Page │    │ - Priority Score│               │
│  └─────────────────┘    └─────────────────┘               │
│           │                       │                        │
│           ▼                       ▼                        │
│  STAGE 2: CONTENT EXTRACTION                               │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │ Strategy Router │───▶│ Content Engine  │               │
│  │ - Detect Type   │    │ - Fast Scrapy   │               │
│  │ - Select Tool   │    │ - Playwright    │               │
│  │ - Load Balance  │    │ - Hybrid Mode   │               │
│  └─────────────────┘    └─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### **🛠️ Implementation Plan**

#### **A. Stage 1: Fast Link Discovery**

```python
# crawler_layer/link_discovery/
├── rss_crawler.py          # Crawl RSS feeds (fastest)
├── sitemap_crawler.py      # Parse sitemap.xml 
├── category_crawler.py     # Crawl category pages
├── link_processor.py       # Filter & prioritize links
└── link_queue.py          # Manage crawl queue
```

**File: `crawler_layer/link_discovery/rss_crawler.py`**
```python
class RSSCrawler:
    """Ultra-fast RSS feed crawler for link discovery"""
    
    async def crawl_feeds(self, sources: List[str]) -> List[ArticleLink]:
        """
        Crawl multiple RSS feeds concurrently
        Target: 1000+ links trong <30 seconds
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self._crawl_single_feed(session, source) for source in sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and return prioritized links
        return self._process_feed_results(results)
```

**File: `crawler_layer/link_discovery/link_processor.py`**
```python
class LinkProcessor:
    """Smart link filtering and prioritization"""
    
    def filter_and_prioritize(self, raw_links: List[str]) -> List[ArticleLink]:
        """
        - Remove duplicates
        - Filter by content type (news, finance)
        - Score by freshness and source reliability
        - Return sorted by priority
        """
        pass
```

#### **B. Stage 2: Smart Content Extraction**

```python
# crawler_layer/content_extraction/
├── strategy_router.py      # Decide which tool to use
├── scrapy_engine.py       # Fast static content
├── playwright_engine.py   # Dynamic content only
├── hybrid_engine.py       # Best of both worlds
└── content_processor.py   # Clean and normalize
```

**File: `crawler_layer/content_extraction/strategy_router.py`**
```python
class StrategyRouter:
    """Intelligently route requests to optimal crawler"""
    
    def select_strategy(self, url: str, site_profile: dict) -> str:
        """
        Decision logic:
        - Static news sites → Scrapy (5x faster)
        - Dynamic content → Playwright  
        - Mixed content → Hybrid approach
        """
        if site_profile.get('is_spa', False):
            return 'playwright'
        elif site_profile.get('has_dynamic_content', False):
            return 'hybrid'  
        else:
            return 'scrapy'  # Default for news sites
```

**File: `crawler_layer/content_extraction/scrapy_engine.py`**
```python
class ScrapyEngine:
    """Ultra-fast Scrapy engine for static content"""
    
    async def crawl_batch(self, urls: List[str]) -> List[Article]:
        """
        Batch crawl multiple URLs concurrently
        Target: 50-100 articles per minute
        """
        # Use Scrapy with custom pipelines for speed
        # Async + connection pooling
        pass
```

### **📋 News Sites Configuration**

**File: `config/news_sources.yaml`**
```yaml
# Optimized for Vietnamese news sites
vnexpress:
  rss_feeds:
    - "https://vnexpress.net/rss/kinh-doanh.rss"
    - "https://vnexpress.net/rss/chung-khoan.rss"
  strategy: "scrapy"  # Static content
  selectors:
    title: "h1.title-detail"
    content: ".fck_detail"
    author: ".author"
  crawl_delay: 1
  max_concurrent: 5

cafef:
  rss_feeds:
    - "https://cafef.vn/rss/thi-truong-chung-khoan.rss"
  strategy: "scrapy"
  selectors:
    title: "h1"
    content: ".detail-content" 
  crawl_delay: 2
  max_concurrent: 3

dantri:
  rss_feeds:
    - "https://dantri.com.vn/kinh-doanh.rss"
  strategy: "hybrid"  # Has some dynamic elements
  crawl_delay: 1.5
```

---

## 💾 **2. STORAGE LAYER - KIẾN TRÚC MỚI**

### **🔥 Vấn đề hiện tại**:
- Single PostgreSQL table → không scale tốt với large data
- Không có data lifecycle management
- Query performance chưa tối ưu
- Thiếu caching layer hiệu quả

### **💡 Giải pháp: Tiered Storage Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                 NEW STORAGE ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│  HOT DATA (Recent, Frequently Accessed)                    │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │ Redis Cache     │    │ PostgreSQL      │               │
│  │ - Recent articles│───▶│ - Hot partition │               │
│  │ - Query cache   │    │ - Last 30 days  │               │
│  │ - Session data  │    │ - Full indexes  │               │
│  └─────────────────┘    └─────────────────┘               │
│           │                       │                        │
│           ▼                       ▼                        │
│  WARM DATA (Historical, Less Frequent)                     │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │ PostgreSQL      │    │ MinIO/S3        │               │
│  │ - Warm partition│───▶│ - Raw HTML      │               │
│  │ - 1-12 months   │    │ - Full content  │               │
│  │ - Basic indexes │    │ - Compressed    │               │
│  └─────────────────┘    └─────────────────┘               │
│           │                                                │
│           ▼                                                │
│  COLD DATA (Archive, Backup)                              │
│  ┌─────────────────────────────────────────────────────────┤
│  │ Compressed Archive (S3 Glacier/Local)                  │
│  │ - Data > 1 year old                                    │
│  │ - Batch access only                                    │
│  └─────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

### **🛠️ Implementation Plan**

#### **A. Database Schema Redesign**

**File: `storage_layer/database/models_v2.py`**
```python
# Partitioned tables for better performance
class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        # Partition by month for better query performance
        {"postgresql_partition_by": "RANGE (created_at)"},
        {"schema": "raw_data"}
    )
    
    # Optimized fields
    id = Column(UUID, primary_key=True)
    url_hash = Column(String(64), unique=True, index=True)  # Fast dedup
    source = Column(String(50), nullable=False, index=True)
    title = Column(Text, nullable=False)
    content_summary = Column(Text)  # First 500 chars for quick preview
    
    # Timestamps for partitioning
    created_at = Column(DateTime, nullable=False, index=True)
    published_at = Column(DateTime, nullable=False, index=True)
    
    # Storage references
    full_content_key = Column(String(255))  # MinIO key for full content
    raw_html_key = Column(String(255))      # MinIO key for raw HTML
    
    # Quick access metadata
    word_count = Column(Integer)
    reading_time = Column(Integer) 
    language = Column(String(10), default='vi')
    quality_score = Column(Numeric(3,2))
    
    # Processing status
    processing_status = Column(String(20), default='pending', index=True)

# Separate table for full content (stored in MinIO)
class ArticleContent(Base):
    __tablename__ = "article_contents"
    __table_args__ = {"schema": "raw_data"}
    
    article_id = Column(UUID, ForeignKey('raw_data.articles.id'), primary_key=True)
    full_content = Column(Text)  # Only for recent articles
    raw_html = Column(Text)      # Raw HTML backup
    extracted_images = Column(JSON)
    extracted_links = Column(JSON)
```

**File: `storage_layer/database/partitions.sql`**
```sql
-- Auto-create monthly partitions
CREATE TABLE articles_2024_01 PARTITION OF articles
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE articles_2024_02 PARTITION OF articles  
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Auto-partition creation function
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
-- Function to auto-create partitions
$$;
```

#### **B. Caching Layer**

**File: `storage_layer/cache/redis_manager.py`**
```python
class RedisManager:
    """High-performance Redis caching"""
    
    async def cache_recent_articles(self, articles: List[Article]):
        """Cache last 1000 articles for instant access"""
        pipeline = self.redis.pipeline()
        for article in articles:
            key = f"article:{article.url_hash}"
            pipeline.setex(key, 3600, json.dumps(article.to_dict()))
        await pipeline.execute()
    
    async def get_cached_article(self, url_hash: str) -> Optional[dict]:
        """Sub-millisecond article retrieval"""
        cached = await self.redis.get(f"article:{url_hash}")
        return json.loads(cached) if cached else None
```

#### **C. Object Storage Integration**

**File: `storage_layer/object_storage/minio_manager.py`**
```python
class MinIOManager:
    """Efficient object storage for large content"""
    
    async def store_article_content(self, article_id: str, content: str, html: str):
        """Store full content and raw HTML"""
        
        # Compress content before storage
        compressed_content = gzip.compress(content.encode('utf-8'))
        compressed_html = gzip.compress(html.encode('utf-8'))
        
        # Generate keys
        content_key = f"articles/{article_id}/content.gz"
        html_key = f"articles/{article_id}/raw.html.gz" 
        
        # Store concurrently
        await asyncio.gather(
            self.client.put_object("content", content_key, compressed_content),
            self.client.put_object("raw-html", html_key, compressed_html)
        )
        
        return content_key, html_key
```

#### **D. Data Access Layer**

**File: `storage_layer/data_access/article_repository.py`**
```python
class ArticleRepository:
    """High-performance data access with smart caching"""
    
    async def get_article(self, url_hash: str) -> Optional[Article]:
        """
        Smart retrieval:
        1. Try Redis cache first (fastest)
        2. Try PostgreSQL (fast)  
        3. Retrieve full content from MinIO if needed
        """
        
        # Try cache first
        cached = await self.redis_manager.get_cached_article(url_hash)
        if cached:
            return Article.from_dict(cached)
            
        # Try database
        article = await self.db.query(Article).filter_by(url_hash=url_hash).first()
        if article:
            # Cache for next time
            await self.redis_manager.cache_article(article)
            return article
            
        return None
    
    async def bulk_insert_articles(self, articles: List[Article]):
        """High-performance bulk insert with deduplication"""
        
        # Deduplicate by URL hash
        existing_hashes = set(await self.get_existing_url_hashes([a.url_hash for a in articles]))
        new_articles = [a for a in articles if a.url_hash not in existing_hashes]
        
        if new_articles:
            # Bulk insert to PostgreSQL
            await self.db.bulk_insert_mappings(Article, [a.to_dict() for a in new_articles])
            
            # Store full content to MinIO concurrently
            storage_tasks = [
                self.minio_manager.store_article_content(a.id, a.content, a.raw_html)
                for a in new_articles
            ]
            await asyncio.gather(*storage_tasks)
            
            # Cache recent articles
            await self.redis_manager.cache_recent_articles(new_articles[-100:])
```

---

## 📁 **3. FILE STRUCTURE MỚI**

```
crawler_layer/
├── link_discovery/
│   ├── __init__.py
│   ├── rss_crawler.py          # RSS feed crawler
│   ├── sitemap_crawler.py      # Sitemap.xml parser
│   ├── category_crawler.py     # Category page crawler
│   ├── link_processor.py       # Link filtering & prioritization
│   └── link_queue.py          # Crawl queue management
│
├── content_extraction/
│   ├── __init__.py
│   ├── strategy_router.py      # Intelligent routing
│   ├── scrapy_engine.py       # Fast Scrapy engine
│   ├── playwright_engine.py   # Browser automation
│   ├── hybrid_engine.py       # Combined approach
│   └── content_processor.py   # Content cleaning
│
├── core/
│   ├── __init__.py
│   ├── crawler_orchestrator.py # Main coordinator
│   ├── rate_limiter.py        # Rate limiting
│   └── metrics_collector.py   # Performance metrics
│
└── utils/
    ├── __init__.py
    ├── url_utils.py           # URL manipulation
    ├── content_utils.py       # Content processing
    └── async_utils.py         # Async helpers

storage_layer/
├── database/
│   ├── __init__.py
│   ├── models_v2.py           # New optimized models
│   ├── partitions.sql         # Partition management
│   ├── indexes.sql            # Performance indexes
│   └── migrations/            # Database migrations
│
├── cache/
│   ├── __init__.py
│   ├── redis_manager.py       # Redis caching
│   └── cache_strategies.py    # Caching patterns
│
├── object_storage/
│   ├── __init__.py
│   ├── minio_manager.py       # MinIO integration
│   └── compression_utils.py   # Content compression
│
└── data_access/
    ├── __init__.py
    ├── article_repository.py   # Article data access
    ├── query_optimizer.py     # Query optimization
    └── data_lifecycle.py      # Data lifecycle management

config/
├── crawler_profiles/          # Per-site configurations
│   ├── vnexpress.yaml
│   ├── cafef.yaml
│   ├── dantri.yaml
│   └── generic.yaml
│
├── storage_config.yaml        # Storage layer config
└── performance_targets.yaml   # Performance benchmarks
```

---

## 🎯 **4. PERFORMANCE TARGETS**

### **Crawler Performance**:
- **Link Discovery**: 1000+ links trong 30 giây
- **Content Extraction**: 50-100 articles/phút (từ hiện tại ~10 articles/phút)
- **Success Rate**: >95% cho news sites
- **Memory Usage**: <2GB cho 1000 articles

### **Storage Performance**:
- **Insert Speed**: 1000 articles/giây (bulk insert)  
- **Query Speed**: <100ms cho recent articles (cached)
- **Cache Hit Rate**: >80% cho frequent queries
- **Storage Efficiency**: 70% compression ratio

### **System Reliability**:
- **Uptime**: >99.5%
- **Error Recovery**: Auto-retry với exponential backoff
- **Data Consistency**: 100% (no data loss)

---

## ⚡ **5. IMPLEMENTATION ROADMAP**

### **Week 1-2: Foundation**
- [ ] Setup new file structure
- [ ] Implement RSS crawler (fastest wins)
- [ ] Create basic link queue system

### **Week 3-4: Fast Crawler**  
- [ ] Implement Scrapy engine
- [ ] Create strategy router
- [ ] Test with VnExpress, CafeF

### **Week 5-6: Storage Optimization**
- [ ] Implement partitioned tables
- [ ] Setup Redis caching layer
- [ ] MinIO integration for large content

### **Week 7-8: Integration & Testing**
- [ ] Connect crawler với new storage
- [ ] Performance testing
- [ ] Optimization based on results

---

## 🎯 **6. SUCCESS METRICS**

### **Before vs After**:
| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Crawl Speed | ~10 articles/min | 50-100 articles/min | 5-10x |
| Memory Usage | ~1GB/100 articles | <2GB/1000 articles | 5x efficient |
| Query Speed | ~500ms | <100ms (cached) | 5x faster |
| Storage Space | Raw text only | 70% compressed | 3x efficient |
| Success Rate | ~80% | >95% | +15% |

### **Cost Efficiency**:
- **Server Costs**: Reduced by 50% through better resource utilization
- **Storage Costs**: Reduced by 70% through compression and tiering
- **Maintenance Time**: Reduced by 60% through better error handling

---

**🚀 KẾT LUẬN**: Với architecture mới này, chúng ta sẽ có hệ thống crawl nhanh hơn 5-10x, hiệu quả storage hơn 3-5x, và đáng tin cậy hơn nhiều cho việc crawl news sites.