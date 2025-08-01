# ⚙️ Configuration Layer

**Centralized Configuration Management cho Enhanced Crawler v2**

Tầng configuration quản lý tất cả các settings, site profiles, và performance parameters để tối ưu crawler performance cho từng news source cụ thể.

## 🏗️ **Configuration Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                CONFIGURATION LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  GLOBAL CONFIGURATION                                       │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │ News Sources    │    │ Performance     │               │
│  │ • Priority      │    │ • Concurrency   │               │
│  │ • RSS Feeds     │    │ • Rate Limits   │               │
│  │ • Strategies    │    │ • Timeouts      │               │
│  └─────────────────┘    └─────────────────┘               │
│           │                       │                        │
│           ▼                       ▼                        │
│  SITE-SPECIFIC PROFILES                                    │
│  ┌─────────────────────────────────────────┐               │
│  │           Site Profiles                 │               │
│  │  • VnExpress: Static, Fast              │               │
│  │  • CafeF: Mixed Content                 │               │
│  │  • DanTri: Dynamic, Hybrid              │               │
│  │  • Generic: Fallback Profile            │               │
│  └─────────────────────────────────────────┘               │
│           │                                                │
│           ▼                                                │
│  RUNTIME CONFIGURATION                                     │
│  ┌─────────────────────────────────────────┐               │
│  │        Environment Variables            │               │
│  │  • Database URLs                        │               │
│  │  • API Keys                             │               │
│  │  • Performance Tuning                  │               │
│  └─────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## 📁 **Configuration Structure**

```
config/
├── news_sources_v2.yaml         # 🌐 Global sources configuration
├── crawler_profiles/            # 📋 Site-specific profiles
│   ├── vnexpress.yaml          # VnExpress optimizations
│   ├── cafef.yaml              # CafeF settings  
│   ├── dantri.yaml             # DanTri configurations
│   └── generic.yaml            # Fallback profile
├── env.example                  # 🔧 Environment template
└── README.md                    # This file
```

## 🌐 **Global Configuration** (`news_sources_v2.yaml`)

**Chức năng**: Centralized management của tất cả news sources

```yaml
# Enhanced news sources configuration
sources:
  # Tier 1: High priority financial news
  vnexpress:
    name: "vnexpress"
    domain: "vnexpress.net" 
    priority: 10              # Highest priority
    enabled: true
    profile_file: "vnexpress.yaml"
    
  cafef:
    name: "cafef"
    domain: "cafef.vn"
    priority: 9
    enabled: true
    profile_file: "cafef.yaml"
    
  # Tier 2: General business news
  dantri:
    name: "dantri"
    domain: "dantri.com.vn"
    priority: 8
    enabled: true
    profile_file: "dantri.yaml"

# Global crawler settings
global_settings:
  link_discovery:
    max_links_per_source: 100
    link_cache_ttl: 3600
    duplicate_threshold: 0.8
    
  content_extraction:
    batch_size: 10
    max_concurrent_extractions: 20
    extraction_timeout: 30
    
  quality_control:
    min_content_length: 100
    min_title_length: 10
    quality_score_threshold: 3.0
    
  rate_limiting:
    default_delay: 1.0
    max_requests_per_minute: 60

# Content categories với priority bonuses
content_categories:
  financial:
    keywords: ["chứng khoán", "cổ phiếu", "đầu tư", "tài chính"]
    priority_bonus: 5.0
    
  business:
    keywords: ["kinh doanh", "doanh nghiệp", "công ty", "thị trường"]
    priority_bonus: 3.0
    
  real_estate:
    keywords: ["bất động sản", "nhà đất", "căn hộ"]
    priority_bonus: 4.0

# Performance targets
performance_targets:
  link_discovery_speed: 1000  # links per 30 seconds
  content_extraction_speed: 100  # articles per minute
  success_rate: 0.95
  memory_usage_mb: 2000
```

## 📋 **Site Profiles** (`crawler_profiles/`)

### **VnExpress Profile** (`vnexpress.yaml`)

**Optimized cho static content với Scrapy strategy**

```yaml
# VnExpress.net crawler configuration
name: "vnexpress"
domain: "vnexpress.net"
strategy: "scrapy"  # Static content - fast extraction

# RSS feeds for link discovery
rss_feeds:
  - "https://vnexpress.net/rss/kinh-doanh.rss"
  - "https://vnexpress.net/rss/chung-khoan.rss"
  - "https://vnexpress.net/rss/bat-dong-san.rss"
  - "https://vnexpress.net/rss/ebank.rss"

# Content extraction selectors
selectors:
  title: "h1.title-detail"
  content: ".fck_detail"
  author: ".author_mail a"
  publish_time: ".date"
  description: ".description"

# Site characteristics
site_config:
  is_spa: false
  has_dynamic_content: false
  requires_js: false
  anti_bot_protection: false

# Performance settings
crawl_settings:
  delay: 1.0            # seconds between requests
  max_concurrent: 5     # concurrent requests
  timeout: 15           # request timeout
  retry_attempts: 3     # max retries

# Custom headers
headers:
  User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
  Accept-Language: "vi-VN,vi;q=0.9,en;q=0.8"

# Quality control
quality_rules:
  min_word_count: 100
  min_title_length: 10
  max_title_length: 200
  required_content_indicators: ["kinh doanh", "tài chính", "chứng khoán"]

# Priority scoring  
priority_config:
  domain_authority: 10.0
  financial_keywords_bonus: 5.0
  business_keywords_bonus: 3.0
  recency_bonus_hours: 6
```

### **CafeF Profile** (`cafef.yaml`)

**Mixed content strategy với conservative settings**

```yaml
# CafeF.vn crawler configuration
name: "cafef"
domain: "cafef.vn"
strategy: "scrapy"  # Mostly static with some dynamic elements

# RSS feeds
rss_feeds:
  - "https://cafef.vn/rss/thi-truong-chung-khoan.rss"
  - "https://cafef.vn/rss/dau-tu.rss"
  - "https://cafef.vn/rss/tai-chinh-ngan-hang.rss"

# Content selectors với fallbacks
selectors:
  title: "h1, .title"
  content: ".detail-content, .content"
  author: ".author, .byline"
  publish_time: ".pdate, .date"

# Site characteristics
site_config:
  is_spa: false
  has_dynamic_content: true   # Some dynamic elements
  requires_js: false
  anti_bot_protection: false

# Conservative crawl settings
crawl_settings:
  delay: 2.0          # Slower for stability
  max_concurrent: 3   # Lower concurrency
  timeout: 20
  retry_attempts: 3

# Custom headers with referer
headers:
  User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  Referer: "https://cafef.vn/"
  Accept-Language: "vi-VN,vi;q=0.9,en;q=0.8"

# Quality rules
quality_rules:
  min_word_count: 150
  min_title_length: 15  
  required_content_indicators: ["chứng khoán", "đầu tư", "tài chính"]

# Priority configuration
priority_config:
  domain_authority: 8.0
  financial_keywords_bonus: 6.0
  recency_bonus_hours: 8
```

### **DanTri Profile** (`dantri.yaml`)

**Hybrid strategy cho dynamic content**

```yaml
# Dantri.com.vn crawler configuration
name: "dantri"
domain: "dantri.com.vn"
strategy: "hybrid"  # Mixed content, some JS required

# RSS feeds
rss_feeds:
  - "https://dantri.com.vn/kinh-doanh.rss"
  - "https://dantri.com.vn/bat-dong-san.rss"

# Content selectors
selectors:
  title: "h1.title-page, h1.article-title"
  content: ".singular-content, .article-content"
  author: ".author-name, .author"
  publish_time: ".news-time, .time"

# Site characteristics
site_config:
  is_spa: false
  has_dynamic_content: true
  requires_js: true     # Some content loaded via JS
  anti_bot_protection: false

# Moderate crawl settings
crawl_settings:
  delay: 1.5
  max_concurrent: 4
  timeout: 25          # Longer timeout for JS loading
  retry_attempts: 2

# Headers
headers:
  User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  Referer: "https://dantri.com.vn/"

# Quality rules
quality_rules:
  min_word_count: 120
  required_content_indicators: ["kinh tế", "doanh nghiệp"]

# Priority settings
priority_config:
  domain_authority: 8.0
  business_keywords_bonus: 5.0
  recency_bonus_hours: 12
```

### **Generic Profile** (`generic.yaml`)

**Safe fallback cho unknown sites**

```yaml
# Generic crawler configuration
name: "generic" 
domain: "_default"
strategy: "playwright"  # Safe approach for unknown sites

# Generic selectors với multiple fallbacks
selectors:
  title: "h1, .title, .headline, .post-title, .article-title"
  content: ".content, .article-content, .post-content, .entry-content, article"
  author: ".author, .byline, .author-name, .post-author"
  publish_time: ".date, .time, .published, .post-date"

# Conservative site config
site_config:
  is_spa: false
  has_dynamic_content: true
  requires_js: true    # Be safe with unknown sites
  anti_bot_protection: false

# Very conservative settings
crawl_settings:
  delay: 2.0
  max_concurrent: 2    # Very conservative
  timeout: 30
  retry_attempts: 1

# Generic headers
headers:
  User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Relaxed quality rules
quality_rules:
  min_word_count: 50
  min_title_length: 5
  required_content_indicators: []

# Low priority for unknown sites
priority_config:
  domain_authority: 1.0
  recency_bonus_hours: 24
```

## 🔧 **Environment Configuration** (`env.example`)

**Template cho environment variables**

```bash
# ============================================================================
# Enhanced Crawler v2 Environment Configuration
# ============================================================================

# Database Configuration
DATABASE_URL=postgresql+asyncpg://crawler_user:crawler_pass@localhost:5432/crawler_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis Configuration  
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_MAX_CONNECTIONS=100

# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_SECURE=false

# Crawler Performance Settings
CRAWLER_MODE=hybrid
MAX_CONCURRENT_CRAWLS=20
RSS_CRAWL_INTERVAL=300
BULK_INSERT_BATCH_SIZE=100
LINK_DISCOVERY_ENABLED=true

# Cache Settings
CACHE_TTL=3600
CACHE_MAX_MEMORY=1gb

# Quality Control
MIN_CONTENT_LENGTH=100
MIN_QUALITY_SCORE=3.0
DUPLICATE_THRESHOLD=0.8

# Monitoring & Logging
LOG_LEVEL=INFO
SENTRY_DSN=
PROMETHEUS_ENABLED=true
GRAFANA_PASSWORD=admin123

# Performance Targets
TARGET_CRAWL_SPEED=100    # articles per minute
TARGET_CACHE_HIT_RATE=80  # percent
TARGET_SUCCESS_RATE=95    # percent
```

## 📊 **Configuration Usage**

### **Loading Configuration**

```python
from config import load_config, get_site_profile

# Load global configuration
config = load_config()

# Get site-specific profile
profile = get_site_profile('vnexpress')

# Environment variables
database_url = config.get('database_url')
redis_host = config.get('redis_host')
```

### **Dynamic Configuration Updates**

```python
from crawler_layer.content_extraction import StrategyRouter

router = StrategyRouter()

# Add new site profile
new_profile = SiteProfile(
    name='newssite',
    strategy='scrapy',
    crawl_delay=1.5
)
router.add_site_profile('newssite.com', new_profile)

# Update existing profile
router.update_profile('vnexpress', {'crawl_delay': 0.5})
```

### **Configuration Validation**

```python
def validate_site_profile(profile):
    """Validate site profile configuration"""
    required_fields = ['name', 'domain', 'strategy']
    
    for field in required_fields:
        if not profile.get(field):
            raise ValueError(f"Missing required field: {field}")
    
    # Validate strategy
    valid_strategies = ['scrapy', 'playwright', 'hybrid']
    if profile['strategy'] not in valid_strategies:
        raise ValueError(f"Invalid strategy: {profile['strategy']}")
    
    # Validate crawl settings
    settings = profile.get('crawl_settings', {})
    if settings.get('delay', 0) < 0.1:
        raise ValueError("Crawl delay must be >= 0.1 seconds")
```

## ⚙️ **Configuration Management**

### **Priority-based Loading**

1. **Environment Variables** (highest priority)
2. **Site-specific Profiles** 
3. **Global Configuration**
4. **Default Values** (lowest priority)

### **Profile Selection Logic**

```python
def select_profile(url: str) -> dict:
    """Select appropriate profile for URL"""
    domain = extract_domain(url)
    
    # 1. Try exact domain match
    for profile_domain, profile in site_profiles.items():
        if profile_domain == domain:
            return profile
    
    # 2. Try partial domain match
    for profile_domain, profile in site_profiles.items():
        if profile_domain in domain:
            return profile
    
    # 3. Use generic fallback
    return site_profiles['_default']
```

### **Performance Tuning**

```yaml
# Performance optimization based on site characteristics
performance_profiles:
  high_volume:      # For sites với many articles
    max_concurrent: 10
    batch_size: 20
    cache_ttl: 7200
    
  slow_response:    # For sites với slow response times
    max_concurrent: 2
    timeout: 45
    retry_attempts: 1
    
  dynamic_heavy:    # For sites với lots of JS
    strategy: "playwright"
    timeout: 30
    requires_js: true
```

## 🔍 **Configuration Monitoring**

### **Performance Metrics per Profile**

```python
# Track performance by site profile
profile_stats = {
    'vnexpress': {
        'avg_response_time': 1.2,  # seconds
        'success_rate': 0.97,
        'articles_per_minute': 85
    },
    'cafef': {
        'avg_response_time': 2.1,
        'success_rate': 0.91,
        'articles_per_minute': 45
    }
}
```

### **Configuration Health Checks**

```python
async def validate_configuration():
    """Validate all configuration settings"""
    
    # Check RSS feeds accessibility
    for source, config in sources.items():
        for rss_url in config['rss_feeds']:
            try:
                await test_rss_feed(rss_url)
            except Exception as e:
                logger.warning(f"RSS feed {rss_url} not accessible: {e}")
    
    # Check selectors validity
    for profile in site_profiles.values():
        await validate_selectors(profile['selectors'])
    
    # Check performance settings
    validate_performance_settings(global_settings)
```

## 🛠️ **Development Tools**

### **Configuration Generator**

```python
def generate_site_profile(domain: str, sample_urls: List[str]) -> dict:
    """Auto-generate site profile from sample URLs"""
    
    # Analyze site structure
    site_analysis = analyze_site_structure(sample_urls)
    
    # Generate selectors
    selectors = extract_common_selectors(sample_urls)
    
    # Determine strategy
    strategy = 'scrapy' if site_analysis['is_static'] else 'playwright'
    
    # Create profile
    profile = {
        'name': domain.replace('.', '_'),
        'domain': domain,
        'strategy': strategy,
        'selectors': selectors,
        'crawl_settings': {
            'delay': 1.0,
            'max_concurrent': 5 if strategy == 'scrapy' else 2
        }
    }
    
    return profile
```

### **Configuration Testing**

```bash
# Test site profile
python -m config.test_profile vnexpress --urls sample_urls.txt

# Validate all configurations
python -m config.validate_all

# Performance benchmark
python -m config.benchmark --profile vnexpress --duration 60
```

## 📈 **Best Practices**

### **Profile Design**

1. **Conservative Defaults**: Start với conservative settings
2. **Gradual Optimization**: Tăng performance parameters từ từ
3. **Error Monitoring**: Track error rates khi adjust settings
4. **A/B Testing**: Test performance changes trước khi deploy

### **Configuration Security**

1. **Environment Variables**: Store sensitive data trong env vars
2. **Secret Management**: Use secure secret management systems
3. **Access Control**: Limit access đến configuration files
4. **Audit Logging**: Log configuration changes

### **Maintenance**

1. **Regular Reviews**: Review và update profiles định kỳ
2. **Performance Monitoring**: Track metrics per profile
3. **Site Changes**: Monitor target sites cho structural changes
4. **Documentation**: Keep configuration documented và up-to-date

---

## 🎯 **Configuration Optimization Guide**

### **Performance Tuning Steps**

1. **Baseline Measurement**: Measure current performance
2. **Bottleneck Identification**: Find performance bottlenecks
3. **Incremental Changes**: Make small configuration adjustments
4. **A/B Testing**: Compare performance before/after changes
5. **Monitoring**: Monitor performance sau optimization

### **Common Optimizations**

- **Increase Concurrency**: For fast, stable sites
- **Reduce Delays**: For sites that can handle faster requests
- **Strategy Switching**: Move from playwright → scrapy khi possible
- **Selector Optimization**: Use more specific, faster selectors
- **Cache Tuning**: Adjust TTL based on content update frequency

**⚙️ Configuration Layer cung cấp flexible và powerful management cho tất cả aspects của crawler behavior, optimized cho từng news source!**