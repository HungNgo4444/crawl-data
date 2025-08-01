# 🕷️ Crawler Layer

**Multi-Stage Hybrid Crawler với Intelligent Content Extraction**

Tầng crawler chịu trách nhiệm cho việc thu thập dữ liệu với 2 giai đoạn chính: Link Discovery và Content Extraction.

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    CRAWLER LAYER                            │
├─────────────────────────────────────────────────────────────┤
│  STAGE 1: LINK DISCOVERY                                   │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │ RSS Crawler     │───▶│ Link Processor  │               │
│  │ • Multi-source  │    │ • Smart Filter  │               │
│  │ • Async Crawl   │    │ • Deduplication │               │
│  │ • 1000+/30s     │    │ • Priority Score│               │
│  └─────────────────┘    └─────────────────┘               │
│           │                       │                        │
│           ▼                       ▼                        │
│  ┌─────────────────────────────────────────┐               │
│  │            Link Queue                   │               │
│  │  • Priority Queue                       │               │
│  │  • Rate Limiting                        │               │
│  │  • Retry Logic                          │               │
│  └─────────────────────────────────────────┘               │
│                     │                                       │
│                     ▼                                       │
│  STAGE 2: CONTENT EXTRACTION                               │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │ Strategy Router │───▶│ Multi-Engine    │               │
│  │ • Site Profiles │    │ • Scrapy (Fast) │               │
│  │ • Auto Detection│    │ • Playwright    │               │
│  │ • Load Balancing│    │ • Hybrid Mode   │               │
│  └─────────────────┘    └─────────────────┘               │
│           │                       │                        │
│           ▼                       ▼                        │
│  ┌─────────────────────────────────────────┐               │
│  │        Content Processor                │               │
│  │  • AI-powered Cleaning                  │               │
│  │  • Quality Scoring                      │               │
│  │  • Language Detection                   │               │
│  └─────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## 📁 **Module Structure**

```
crawler_layer/
├── link_discovery/              # 🔍 Stage 1: Link Discovery
│   ├── __init__.py
│   ├── rss_crawler.py          # RSS feed crawler
│   ├── link_processor.py       # Smart filtering & prioritization
│   └── link_queue.py           # Priority queue management
├── content_extraction/         # ⚡ Stage 2: Content Extraction  
│   ├── __init__.py
│   ├── strategy_router.py      # Intelligent routing
│   ├── scrapy_engine.py        # Fast static content crawling
│   └── content_processor.py    # Content cleaning & analysis
├── core/                       # 🔧 Core Components
│   ├── base_crawler.py         # Base crawler class
│   └── browser_manager.py      # Browser management
├── utils/                      # 🛠️ Utilities
│   ├── url_utils.py           # URL manipulation
│   ├── content_utils.py       # Content processing
│   └── async_utils.py         # Async helpers
└── main.py                     # 🚀 Application entry point
```

## 🔍 **Stage 1: Link Discovery**

### **RSS Crawler** (`rss_crawler.py`)

**Performance Target**: 1000+ links trong 30 giây

```python
from crawler_layer.link_discovery import RSSCrawler

# Initialize RSS crawler
rss_crawler = RSSCrawler(max_concurrent=20)

# Crawl multiple sources
sources = [
    {
        'name': 'vnexpress',
        'rss_feeds': ['https://vnexpress.net/rss/kinh-doanh.rss']
    }
]

# Fast link collection
links = await rss_crawler.crawl_feeds(sources)
print(f"Collected {len(links)} links")
```

**Key Features:**
- **Concurrent Processing**: 20+ RSS feeds đồng thời
- **Smart Parsing**: feedparser cho RSS/Atom feeds
- **Priority Scoring**: Tự động scoring dựa vào keywords và freshness
- **Error Handling**: Robust retry logic cho failed feeds

### **Link Processor** (`link_processor.py`)

**Chức năng**: Smart filtering và prioritization

```python
from crawler_layer.link_discovery import LinkProcessor

processor = LinkProcessor()

# Process raw links
filtered_links = processor.filter_and_prioritize(raw_links)

# Features:
# - Duplicate detection (URL hash + title similarity)
# - Quality filtering (spam, promotional content)
# - Priority scoring (financial keywords, source authority)
# - Content type detection
```

**Filtering Rules:**
- ❌ **Exclude**: `/video/`, `/photo/`, `/tag/`, social media links
- ✅ **Prioritize**: Financial keywords, business content, fresh articles
- 🔄 **Deduplicate**: URL hash + 80% title similarity threshold

### **Link Queue** (`link_queue.py`)

**Chức năng**: Priority queue với rate limiting

```python
from crawler_layer.link_discovery import LinkQueue

queue = LinkQueue(max_size=10000)

# Add prioritized links
await queue.add_links(filtered_links)

# Get next batch for processing
batch = await queue.get_next_batch(batch_size=10)

# Mark completion
await queue.mark_completed(url_hash, success=True)
```

**Features:**
- **Priority Queue**: Heapq-based với custom priority scoring
- **Rate Limiting**: Respect site-specific crawl delays
- **Retry Logic**: Exponential backoff cho failed URLs
- **Monitoring**: Queue size, processing stats

## ⚡ **Stage 2: Content Extraction**

### **Strategy Router** (`strategy_router.py`)

**Chức năng**: Intelligent routing cho optimal performance

```python
from crawler_layer.content_extraction import StrategyRouter

router = StrategyRouter()

# Auto-select best strategy
config = router.get_crawl_config(url)

# Strategies:
# - 'scrapy': Static content (5x faster)
# - 'playwright': Dynamic content, SPA sites
# - 'hybrid': Mixed approach
```

**Site Profiles:**
```python
# VnExpress profile
{
    'strategy': 'scrapy',  # Static content
    'selectors': {
        'title': 'h1.title-detail',
        'content': '.fck_detail'
    },
    'crawl_delay': 1.0,
    'max_concurrent': 5
}
```

### **Scrapy Engine** (`scrapy_engine.py`)

**Performance Target**: 50-100 articles/phút

```python
from crawler_layer.content_extraction import ScrapyEngine

engine = ScrapyEngine(max_concurrent=10)

# Batch crawl with configs
crawl_configs = [
    {
        'url': 'https://vnexpress.net/article.html',
        'site_profile': vnexpress_profile,
        'selectors': {...}
    }
]

articles = await engine.crawl_batch(crawl_configs)
```

**Key Features:**
- **Ultra Fast**: aiohttp + BeautifulSoup cho static content
- **Concurrent Processing**: 10-20 simultaneous requests
- **Smart Extraction**: Fallback selectors cho robust parsing
- **Content Validation**: Quality checks trước khi return

### **Content Processor** (`content_processor.py`)

**Chức năng**: AI-powered content cleaning và analysis

```python
from crawler_layer.content_extraction import ContentProcessor

processor = ContentProcessor()

# Process raw content
result = processor.process_content(raw_content, content_type='article')

# Returns:
{
    'cleaned_content': 'Clean article text...',
    'word_count': 543,
    'reading_time': 3,  # minutes
    'quality_score': 8.5,  # 0-10
    'language': 'vi',
    'has_ads': False
}
```

**Processing Pipeline:**
1. **Basic Cleaning**: HTML tags, encoding issues
2. **Noise Removal**: Ads, navigation, promotional content
3. **Structure Normalization**: Paragraphs, sentences
4. **Quality Scoring**: Length, information density, language
5. **Metadata Extraction**: Word count, reading time, language

## 🔧 **Core Components**

### **Base Crawler** (`core/base_crawler.py`)

**Chức năng**: Abstract base class cho tất cả crawlers

```python
from crawler_layer.core import BaseCrawler

class CustomCrawler(BaseCrawler):
    async def extract_content(self, url: str) -> Dict:
        # Implement custom extraction logic
        pass
    
    async def process_batch(self, urls: List[str]) -> List[Dict]:
        # Batch processing implementation
        pass
```

### **Browser Manager** (`core/browser_manager.py`)

**Chức năng**: Playwright browser lifecycle management

```python
from crawler_layer.core import BrowserManager

async with BrowserManager() as browser:
    page = await browser.new_page()
    await page.goto(url)
    content = await page.content()
```

## 🚀 **Usage Examples**

### **Full Crawler Pipeline**

```python
import asyncio
from crawler_layer.main import CrawlerApplication

async def main():
    # Initialize crawler application
    app = CrawlerApplication()
    
    # Start crawling
    await app.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### **Link Discovery Only**

```python
from crawler_layer.link_discovery import RSSCrawler, LinkProcessor

async def discover_links():
    # Configure sources
    sources = [
        {'name': 'vnexpress', 'rss_feeds': ['https://vnexpress.net/rss/kinh-doanh.rss']},
        {'name': 'cafef', 'rss_feeds': ['https://cafef.vn/rss/thi-truong-chung-khoan.rss']}
    ]
    
    # Crawl RSS feeds
    crawler = RSSCrawler(max_concurrent=20)
    raw_links = await crawler.crawl_feeds(sources)
    
    # Process and filter
    processor = LinkProcessor()
    filtered_links = processor.filter_and_prioritize(raw_links)
    
    print(f"Discovered {len(filtered_links)} high-quality links")
    return filtered_links
```

### **Content Extraction Only**

```python
from crawler_layer.content_extraction import StrategyRouter, ScrapyEngine

async def extract_content(urls):
    router = StrategyRouter()
    engine = ScrapyEngine()
    
    # Prepare crawl configs
    configs = []
    for url in urls:
        config = router.get_crawl_config(url)
        config['url'] = url
        configs.append(config)
    
    # Extract content
    articles = await engine.crawl_batch(configs)
    
    print(f"Extracted {len(articles)} articles")
    return articles
```

## 📊 **Performance Monitoring**

### **Key Metrics**

```python
# Link Discovery Performance
rss_crawler.get_stats()
# Returns: {
#   'feeds_crawled': 15,
#   'links_discovered': 1200,
#   'crawl_time_seconds': 28.5,
#   'links_per_second': 42.1
# }

# Content Extraction Performance  
scrapy_engine.get_stats()
# Returns: {
#   'articles_extracted': 87,
#   'extraction_time_seconds': 52.3,
#   'articles_per_minute': 99.8,
#   'success_rate': 0.94
# }

# Queue Statistics
link_queue.get_stats()
# Returns: {
#   'queue_size': 450,
#   'in_progress': 12,
#   'completed_count': 1200,
#   'failed_count': 23
# }
```

### **Health Checks**

```python
# Component health
await rss_crawler.health_check()
await scrapy_engine.health_check()
await strategy_router.health_check()

# Overall crawler health
crawler_healthy = all([
    await component.health_check() 
    for component in [rss_crawler, engine, router]
])
```

## ⚙️ **Configuration**

### **Environment Variables**

```bash
# Crawler performance settings
MAX_CONCURRENT_CRAWLS=20
RSS_CRAWL_INTERVAL=300
SCRAPY_MAX_CONCURRENT=10

# Rate limiting
DEFAULT_CRAWL_DELAY=1.0
MAX_REQUESTS_PER_MINUTE=60

# Quality control
MIN_CONTENT_LENGTH=100
MIN_QUALITY_SCORE=3.0
```

### **Site Profiles** (via `config/crawler_profiles/`)

```yaml
# vnexpress.yaml
name: "vnexpress"
strategy: "scrapy"
crawl_delay: 1.0
max_concurrent: 5
selectors:
  title: "h1.title-detail"
  content: ".fck_detail"
  author: ".author_mail"
quality_rules:
  min_word_count: 100
  required_keywords: ["kinh doanh", "tài chính"]
```

## 🛠️ **Development**

### **Adding New Crawler Strategy**

```python
# 1. Create new engine
class CustomEngine:
    async def crawl_batch(self, configs: List[Dict]) -> List[Article]:
        # Implementation
        pass

# 2. Register in strategy router
router.add_strategy('custom', CustomEngine)

# 3. Update site profiles
# strategy: "custom"
```

### **Testing**

```python
# Unit tests
pytest crawler_layer/tests/unit/

# Integration tests
pytest crawler_layer/tests/integration/

# Performance tests
pytest crawler_layer/tests/performance/
```

### **Debugging**

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug mode
os.environ['CRAWLER_DEBUG'] = 'true'

# Detailed logging
logger = logging.getLogger('crawler_layer')
logger.setLevel(logging.DEBUG)
```

## 🚨 **Error Handling**

### **Common Issues**

**RSS Feed Failures:**
```python
# Auto-retry with exponential backoff
# Skip failed feeds after 3 attempts
# Continue with successful feeds
```

**Content Extraction Failures:**
```python
# Fallback selectors
# Strategy switching (scrapy → playwright)
# Graceful degradation
```

**Rate Limiting:**
```python
# Respect robots.txt
# Dynamic delay adjustment
# 429 status code handling
```

### **Recovery Strategies**

- **Circuit Breaker**: Temporarily disable problematic sources
- **Fallback Modes**: Switch strategies on repeated failures
- **Graceful Degradation**: Continue with partial results
- **Retry Logic**: Exponential backoff với max attempts

---

## 📈 **Performance Tuning**

### **Optimization Tips**

1. **Concurrent Settings**: Adjust based on target site capabilities
2. **Memory Management**: Use generators cho large datasets
3. **Connection Pooling**: Reuse HTTP connections
4. **Batch Processing**: Group similar operations
5. **Async/Await**: Proper async patterns cho I/O operations

### **Scaling**

- **Horizontal**: Multiple crawler instances
- **Load Balancing**: Distribute URLs across instances  
- **Queue-based**: Use message queues cho large scale
- **Resource Limits**: Monitor CPU/memory usage

**🎯 Crawler Layer cung cấp foundation mạnh mẽ cho việc thu thập dữ liệu với tốc độ cao và độ tin cậy tối ưu!**