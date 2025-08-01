# 💾 Storage Layer

**Tiered Storage Architecture với Smart Caching**

Tầng storage quản lý việc lưu trữ và truy xuất dữ liệu với 3 tiers: Hot (Redis), Warm (PostgreSQL), và Cold (MinIO) để tối ưu performance và cost.

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                            │
├─────────────────────────────────────────────────────────────┤
│  HOT TIER (Fast Access)                                    │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │ Redis Cache     │    │ Query Cache     │               │
│  │ • Recent Items  │    │ • Search Results│               │
│  │ • <10ms access  │    │ • Aggregations  │               │
│  │ • 80%+ hit rate │    │ • 10min TTL     │               │
│  └─────────────────┘    └─────────────────┘               │
│           │                       │                        │
│           ▼                       ▼                        │
│  WARM TIER (Structured Data)                              │
│  ┌─────────────────────────────────────────┐               │
│  │            PostgreSQL                   │               │
│  │  • Partitioned by Month                 │               │
│  │  • Optimized Indexes                    │               │
│  │  • ACID Transactions                    │               │
│  │  • <100ms queries                       │               │
│  └─────────────────────────────────────────┘               │
│           │                                                │
│           ▼                                                │
│  COLD TIER (Object Storage)                               │
│  ┌─────────────────────────────────────────┐               │
│  │            MinIO Storage                │               │
│  │  • Full Content (Compressed)            │               │
│  │  • Raw HTML Backup                      │               │
│  │  • 70% Compression Ratio                │               │  
│  │  • S3-Compatible API                    │               │
│  └─────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## 📁 **Module Structure**

```
storage_layer/
├── database/                   # 🗄️ PostgreSQL Management
│   ├── models_v2.py           # Optimized database models
│   ├── partitions.sql         # Monthly partitioning setup
│   └── init/                  # Database initialization
├── cache/                     # ⚡ Redis Caching
│   ├── __init__.py
│   ├── redis_manager.py       # High-performance caching
│   └── cache_strategies.py    # Caching patterns
├── object_storage/            # 📦 MinIO Integration
│   ├── __init__.py
│   ├── minio_manager.py       # Object storage management
│   └── compression_utils.py   # Content compression
└── data_access/               # 🔍 Data Access Layer
    ├── __init__.py
    ├── article_repository.py  # Smart data access
    └── query_optimizer.py     # Query optimization
```

## 🗄️ **Database Layer** (`database/`)

### **Models v2** (`models_v2.py`)

**Performance Optimizations:**
- Monthly partitioning cho better query performance
- Composite indexes cho common patterns
- JSONB fields cho flexible metadata
- UUID primary keys cho distributed systems

```python
from storage_layer.database.models_v2 import Article, ArticleContent

# Partitioned table với optimized indexes
class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        {"postgresql_partition_by": "RANGE (created_at)"},
        Index("idx_articles_source_published", "source", "published_at"),
        Index("idx_articles_quality", "quality_score"),
    )
    
    # Core fields
    id = Column(UUID, primary_key=True)
    url_hash = Column(String(64), unique=True, index=True)
    source = Column(String(50), nullable=False, index=True)
    title = Column(Text, nullable=False)
    
    # Storage references
    full_content_key = Column(String(255))  # MinIO key
    raw_html_key = Column(String(255))      # MinIO key
    
    # Metadata
    word_count = Column(Integer, default=0)
    quality_score = Column(Numeric(3,2), index=True)
    processing_status = Column(String(20), default='pending', index=True)
```

### **Partitioning** (`partitions.sql`)

**Auto-partitioning by month:**

```sql
-- Create monthly partitions automatically
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
BEGIN
    -- Generate partition table
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS raw_data.%I 
        PARTITION OF raw_data.%I
        FOR VALUES FROM (%L) TO (%L)',
        table_name || '_' || TO_CHAR(start_date, 'YYYY_MM'),
        table_name, start_date, 
        date_trunc('month', start_date) + interval '1 month'
    );
END;
$$ LANGUAGE plpgsql;

-- Auto-create partitions for next 6 months
SELECT create_future_partitions(6);
```

**Benefits:**
- **Query Performance**: 5-10x faster queries trên specific date ranges
- **Maintenance**: Easier backup/restore của individual partitions  
- **Storage**: Automatic old partition cleanup
- **Concurrency**: Better concurrent access patterns

## ⚡ **Cache Layer** (`cache/`)

### **Redis Manager** (`redis_manager.py`)

**Performance Targets**: >80% hit rate, <10ms response time

```python
from storage_layer.cache import RedisManager

# Initialize high-performance caching
redis_manager = RedisManager(
    host='localhost',
    port=6379,
    max_connections=100
)

# Cache article (auto-serialization)
await redis_manager.cache_article(article_data, ttl=3600)

# Get cached article (sub-10ms)
cached_article = await redis_manager.get_article(url_hash)

# Bulk cache recent articles
await redis_manager.cache_recent_articles(articles, ttl=7200)

# Cache query results
await redis_manager.cache_query_result(query_key, results, ttl=600)
```

**Caching Strategies:**

1. **Article Caching**: Recent articles với 1-2 hour TTL
2. **Query Caching**: Search results, aggregations với 10-minute TTL
3. **Link Caching**: Discovered links cho duplicate detection
4. **Session Caching**: User sessions và preferences

**Advanced Features:**
- **Smart Serialization**: JSON first, pickle fallback
- **Pipeline Operations**: Batch cache operations cho performance  
- **TTL Management**: Dynamic TTL based on data type
- **Memory Optimization**: LRU eviction với memory limits

### **Cache Statistics**

```python
# Get detailed cache performance
stats = await redis_manager.get_cache_stats()

# Returns:
{
    'hit_rate_percent': 85.3,
    'total_hits': 12543,
    'total_misses': 2187,
    'memory_used_mb': 156.7,
    'total_keys': 8934
}
```

## 📦 **Object Storage** (`object_storage/`)

### **MinIO Manager** (`minio_manager.py`)

**Performance Target**: 70% compression ratio, scalable storage

```python
from storage_layer.object_storage import MinIOManager

# Initialize object storage
minio_manager = MinIOManager(
    endpoint="localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin123"
)

# Store article content with compression
content_key, html_key = await minio_manager.store_article_content(
    article_id="123e4567-e89b-12d3-a456-426614174000",
    content="Full article content...",
    raw_html="<html>Raw HTML...</html>"
)

# Retrieve compressed content
full_content = await minio_manager.retrieve_article_content(content_key)
raw_html = await minio_manager.retrieve_raw_html(html_key)
```

**Storage Features:**
- **Compression**: gzip với 70% compression ratio
- **Bucket Organization**: Separate buckets cho content types
- **Metadata**: Rich metadata cho content management
- **Lifecycle**: Automatic cleanup của old content
- **Monitoring**: Storage usage và performance metrics

### **Compression Utils** (`compression_utils.py`)

**Multi-algorithm compression:**

```python
from storage_layer.object_storage import CompressionUtils

compressor = CompressionUtils()

# Auto-select best compression
algorithm = compressor.auto_select_compression(content, 'html')

# Compress content
compressed_data, metadata = compressor.compress_content(
    content, 
    content_type='html',
    algorithm=CompressionType.GZIP
)

# Compression stats
{
    'original_size': 12543,
    'compressed_size': 3876, 
    'compression_ratio': 0.31,
    'compression_percent': 69.1
}
```

**Supported Algorithms:**
- **GZIP**: Best for HTML/JSON (fast, good ratio)
- **BZIP2**: Better compression, slower
- **LZMA**: Best compression, slowest
- **ZLIB**: Fastest, moderate compression

## 🔍 **Data Access Layer** (`data_access/`)

### **Article Repository** (`article_repository.py`)

**Performance Target**: <100ms cached queries, 1000 articles/second bulk insert

```python
from storage_layer.data_access import ArticleRepository

# Initialize with all storage layers
repository = ArticleRepository(
    database_url="postgresql+asyncpg://...",
    redis_manager=redis_manager,
    minio_manager=minio_manager
)

# Smart retrieval (cache → DB → MinIO)
article = await repository.get_article_by_url_hash(
    url_hash="abc123",
    include_content=True  # Load from MinIO if needed
)

# High-performance bulk insert
inserted_count = await repository.bulk_insert_articles(articles_data)

# Efficient queries with caching
articles = await repository.get_articles_by_source(
    source="vnexpress",
    limit=100,
    start_date=datetime(2024, 1, 1)
)
```

**Smart Data Access:**

1. **L1 Cache**: Redis lookup first (fastest)
2. **L2 Database**: PostgreSQL query (fast)
3. **L3 Storage**: MinIO content retrieval (as needed)
4. **Auto-caching**: Cache results cho future requests

### **Bulk Operations**

```python
# High-performance bulk insert với deduplication
async def bulk_insert_articles(self, articles: List[Dict]) -> int:
    # 1. Check existing URLs (batch query)
    existing = await self._get_existing_url_hashes(url_hashes)
    
    # 2. Filter duplicates
    new_articles = [a for a in articles if a['url_hash'] not in existing]
    
    # 3. Bulk insert to PostgreSQL
    await session.execute(pg_insert(Article).values(new_articles))
    
    # 4. Store content in MinIO (concurrent)
    minio_tasks = [
        self.minio_manager.store_article_content(id, content, html)
        for id, content, html in content_data
    ]
    await asyncio.gather(*minio_tasks)
    
    # 5. Cache recent articles
    await self.redis_manager.cache_recent_articles(new_articles[-100:])
```

## 📊 **Performance Monitoring**

### **Storage Metrics**

```python
# Repository performance stats
stats = await repository.get_repository_stats()

# Returns comprehensive metrics:
{
    'performance_stats': {
        'cache_hits': 1543,
        'cache_misses': 287,
        'db_queries': 156,
        'bulk_inserts': 23,
        'minio_retrievals': 45
    },
    'cache_stats': {
        'hit_rate_percent': 84.3,
        'memory_used_mb': 145.6
    },
    'storage_stats': {
        'total_objects': 12543,
        'total_size_mb': 2876.4,
        'compression_ratio': 0.32
    }
}
```

### **Database Performance**

```sql
-- Partition usage monitoring
SELECT * FROM monitoring.partition_info;

-- Query performance analysis
EXPLAIN ANALYZE SELECT * FROM articles 
WHERE source = 'vnexpress' 
AND created_at >= '2024-01-01';

-- Index usage statistics
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read 
FROM pg_stat_user_indexes 
WHERE schemaname = 'raw_data';
```

## ⚙️ **Configuration**

### **Database Settings**

```bash
# Connection pooling
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_POOL_PRE_PING=true

# Query optimization
DATABASE_ECHO=false  # Set true for SQL debugging
DATABASE_QUERY_CACHE_SIZE=1000
```

### **Redis Configuration**

```bash
# Connection settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_MAX_CONNECTIONS=100

# Memory management
REDIS_MAXMEMORY=1gb
REDIS_MAXMEMORY_POLICY=allkeys-lru

# Performance
REDIS_TCP_KEEPALIVE=60
REDIS_TIMEOUT=5
```

### **MinIO Settings**

```bash
# Connection
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_SECURE=false

# Performance  
MINIO_CHUNK_SIZE=65536  # 64KB chunks
MINIO_COMPRESSION_LEVEL=6
MINIO_CONCURRENT_UPLOADS=10
```

## 🛠️ **Development**

### **Database Migrations**

```python
# Create new partition
from storage_layer.database.models_v2 import create_monthly_partitions

await create_monthly_partitions(engine, 2024, 12)

# Initialize database
from storage_layer.database.models_v2 import init_database_v2

await init_database_v2(engine)
```

### **Cache Management**

```python
# Clear specific cache patterns
await redis_manager.flush_cache('article:*')
await redis_manager.flush_cache('query:*')

# Cache warming
await redis_manager.cache_recent_articles(recent_articles)

# Cache statistics
stats = await redis_manager.get_cache_stats()
print(f"Hit rate: {stats['hit_rate_percent']}%")
```

### **Storage Testing**

```python
# Test MinIO connectivity
health_ok = await minio_manager.health_check()

# Test compression
compressed, metadata = compressor.compress_content(test_content)
decompressed = compressor.decompress_content(compressed, algorithm)

# Test repository operations
articles = await repository.get_articles_by_source('test_source')
```

## 🚨 **Error Handling & Recovery**

### **Database Resilience**

- **Connection Pooling**: Auto-reconnect on connection failures
- **Partition Recovery**: Auto-create missing partitions
- **Transaction Rollback**: ACID compliance cho data integrity
- **Backup Strategy**: Automated partition-level backups

### **Cache Resilience**

- **Redis Failover**: Graceful degradation khi Redis unavailable
- **Memory Pressure**: Automatic eviction với LRU policy
- **Connection Recovery**: Auto-reconnect với exponential backoff
- **Data Consistency**: Cache invalidation on data updates

### **Storage Resilience**

- **MinIO Clustering**: Multi-node setup cho high availability
- **Data Replication**: Configurable replication factor
- **Compression Fallback**: Graceful fallback khi compression fails
- **Integrity Checks**: Content verification on retrieval

## 📈 **Scaling Strategies**

### **Database Scaling**

- **Read Replicas**: Scale read operations
- **Partition Pruning**: Automatic old partition cleanup  
- **Connection Pooling**: Efficient connection management
- **Query Optimization**: Regular index maintenance

### **Cache Scaling**

- **Redis Cluster**: Horizontal scaling với sharding
- **Memory Tiering**: Hot/warm cache tiers
- **TTL Optimization**: Smart expiration policies
- **Cache Warming**: Proactive data loading

### **Storage Scaling**

- **Distributed MinIO**: Multi-node object storage
- **Bucket Sharding**: Distribute load across buckets
- **Compression Tuning**: Balance speed vs storage efficiency
- **Lifecycle Policies**: Automatic data archival

---

## 🎯 **Best Practices**

### **Performance**

1. **Query Patterns**: Use composite indexes cho common queries
2. **Bulk Operations**: Batch database operations khi possible
3. **Cache Strategy**: Cache frequently accessed data với appropriate TTL
4. **Storage Tiering**: Use appropriate tier cho data access patterns

### **Reliability**

1. **Health Checks**: Regular component health monitoring
2. **Backup Strategy**: Regular backups của critical data
3. **Error Recovery**: Graceful degradation strategies
4. **Data Validation**: Validate data integrity at all layers

### **Maintenance**

1. **Partition Management**: Regular partition maintenance
2. **Cache Cleanup**: Monitor cache memory usage
3. **Storage Monitoring**: Track storage usage và compression ratios
4. **Performance Tuning**: Regular query và index optimization

**💾 Storage Layer cung cấp foundation mạnh mẽ cho việc lưu trữ và truy xuất dữ liệu với performance cao và scalability tối ưu!**