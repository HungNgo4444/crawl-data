"""
Database models v2 with partitioning and optimization
Designed for high-performance article storage and retrieval
"""

from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Numeric, JSON, Boolean,
    Index, ForeignKey, UUID, BigInteger, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from datetime import datetime
import uuid
import hashlib

Base = declarative_base()

class Article(Base):
    """
    Main articles table with monthly partitioning
    Optimized for fast queries and bulk inserts
    """
    __tablename__ = "articles"
    __table_args__ = (
        # Partition by month for better query performance
        {"postgresql_partition_by": "RANGE (created_at)"},
        {"schema": "raw_data"},
        # Indexes for common queries
        Index("idx_articles_url_hash", "url_hash"),
        Index("idx_articles_source_created", "source", "created_at"),
        Index("idx_articles_published", "published_at"),
        Index("idx_articles_status", "processing_status"),
        Index("idx_articles_quality", "quality_score"),
        # Composite indexes for common query patterns
        Index("idx_articles_source_published", "source", "published_at"),
        Index("idx_articles_created_status", "created_at", "processing_status"),
    )
    
    # Primary key and identifiers
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(2000), nullable=False)
    url_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    # Basic article information
    source = Column(String(50), nullable=False, index=True)
    title = Column(Text, nullable=False)
    content_summary = Column(Text)  # First 500 chars for quick preview
    
    # Timestamps for partitioning and queries
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    published_at = Column(DateTime, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Storage references for full content
    full_content_key = Column(String(255))  # MinIO key for full content
    raw_html_key = Column(String(255))      # MinIO key for raw HTML
    
    # Content metadata for quick access
    word_count = Column(Integer, default=0)
    reading_time = Column(Integer, default=0)  # minutes
    language = Column(String(10), default='vi')
    quality_score = Column(Numeric(3,2), default=0.0, index=True)
    
    # Processing status and metadata
    processing_status = Column(String(20), default='pending', index=True)
    extraction_strategy = Column(String(20))  # scrapy, playwright, hybrid
    extraction_metadata = Column(JSONB)  # Processing details
    
    # Article classification
    category = Column(String(50))
    tags = Column(JSONB)  # Array of tags
    
    # Author and source information
    author = Column(String(200))
    author_metadata = Column(JSONB)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.url_hash and self.url:
            self.url_hash = hashlib.md5(self.url.encode()).hexdigest()
    
    def to_dict(self):
        """Convert to dictionary for caching"""
        return {
            'id': str(self.id),
            'url': self.url,
            'url_hash': self.url_hash,
            'source': self.source,
            'title': self.title,
            'content_summary': self.content_summary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'word_count': self.word_count,
            'reading_time': self.reading_time,
            'language': self.language,
            'quality_score': float(self.quality_score) if self.quality_score else 0.0,
            'processing_status': self.processing_status,
            'category': self.category,
            'author': self.author
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary (for cache retrieval)"""
        instance = cls()
        for key, value in data.items():
            if key in ['created_at', 'published_at'] and value:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if key == 'id':
                value = uuid.UUID(value)
            setattr(instance, key, value)
        return instance

class ArticleContent(Base):
    """
    Full article content stored separately for performance
    Links to main Article table
    """
    __tablename__ = "article_contents"
    __table_args__ = (
        {"schema": "raw_data"},
        Index("idx_content_article_id", "article_id"),
    )
    
    article_id = Column(PG_UUID(as_uuid=True), ForeignKey('raw_data.articles.id'), primary_key=True)
    
    # Full content (only for recent articles, others in MinIO)
    full_content = Column(Text)
    raw_html = Column(Text)
    
    # Extracted structured data
    extracted_images = Column(JSONB)  # Image URLs and metadata
    extracted_links = Column(JSONB)   # Links found in content
    extracted_entities = Column(JSONB)  # Named entities, keywords
    
    # Content processing metadata
    processing_notes = Column(JSONB)
    content_fingerprint = Column(String(64))  # For duplicate detection
    
    # Relationship
    article = relationship("Article", backref="content")

class CrawlStats(Base):
    """
    Track crawling statistics and performance metrics
    """
    __tablename__ = "crawl_stats"
    __table_args__ = (
        {"schema": "monitoring"},
        Index("idx_crawl_stats_date", "crawl_date"),
        Index("idx_crawl_stats_source", "source"),
    )
    
    id = Column(BigInteger, primary_key=True)
    crawl_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    source = Column(String(50), nullable=False)
    
    # Performance metrics
    links_discovered = Column(Integer, default=0)
    articles_extracted = Column(Integer, default=0)
    extraction_errors = Column(Integer, default=0)
    avg_extraction_time = Column(Numeric(8,3))  # seconds
    
    # Success rates
    success_rate = Column(Numeric(5,4))  # 0.0 to 1.0
    quality_score_avg = Column(Numeric(3,2))
    
    # Resource usage
    memory_usage_mb = Column(Integer)
    cpu_usage_percent = Column(Numeric(5,2))
    
    # Strategy effectiveness
    strategy_used = Column(String(20))
    strategy_metadata = Column(JSONB)

class LinkQueue(Base):
    """
    Persistent link queue for crawling pipeline
    """
    __tablename__ = "link_queue"
    __table_args__ = (
        {"schema": "processing"},
        Index("idx_queue_priority", "priority"),
        Index("idx_queue_status", "status"),
        Index("idx_queue_source", "source"),
        Index("idx_queue_created", "created_at"),
    )
    
    id = Column(BigInteger, primary_key=True)
    url = Column(String(2000), nullable=False)
    url_hash = Column(String(64), nullable=False, index=True)
    
    # Queue metadata
    source = Column(String(50), nullable=False)
    priority = Column(Numeric(6,2), default=0.0, index=True)
    status = Column(String(20), default='pending', index=True)  # pending, processing, completed, failed
    
    # Timing information
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(Text)
    
    # Link metadata
    title = Column(Text)
    description = Column(Text)
    published_at = Column(DateTime)
    discovery_metadata = Column(JSONB)

# Monthly partition tables (example for 2024)
class Articles202401(Article):
    __tablename__ = "articles_2024_01"
    __table_args__ = (
        {"postgresql_inherits": "raw_data.articles"},
        {"postgresql_partition_by": "FOR VALUES FROM ('2024-01-01') TO ('2024-02-01')"},
    )

class Articles202402(Article):
    __tablename__ = "articles_2024_02" 
    __table_args__ = (
        {"postgresql_inherits": "raw_data.articles"},
        {"postgresql_partition_by": "FOR VALUES FROM ('2024-02-01') TO ('2024-03-01')"},
    )

# Function to create partition tables automatically
def create_monthly_partitions(engine, year, month):
    """Create monthly partition tables"""
    from sqlalchemy import text
    
    # Calculate date ranges
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1}-01-01"
    else:
        end_date = f"{year}-{month+1:02d}-01"
    
    partition_name = f"articles_{year}_{month:02d}"
    
    create_partition_sql = text(f"""
        CREATE TABLE IF NOT EXISTS raw_data.{partition_name} 
        PARTITION OF raw_data.articles
        FOR VALUES FROM ('{start_date}') TO ('{end_date}');
    """)
    
    with engine.connect() as conn:
        conn.execute(create_partition_sql)
        conn.commit()

# Indexes for partitioned tables
def create_partition_indexes(engine, partition_name):
    """Create indexes on partition tables"""
    from sqlalchemy import text
    
    indexes = [
        f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_url_hash ON raw_data.{partition_name} (url_hash);",
        f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_source ON raw_data.{partition_name} (source);",
        f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_published ON raw_data.{partition_name} (published_at);",
        f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_quality ON raw_data.{partition_name} (quality_score);",
    ]
    
    with engine.connect() as conn:
        for idx_sql in indexes:
            conn.execute(text(idx_sql))
        conn.commit()

# Database initialization
def init_database_v2(engine):
    """Initialize database with all tables and partitions"""
    
    # Create schemas
    from sqlalchemy import text
    
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw_data;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS processing;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS monitoring;"))
        conn.commit()
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create initial partitions for current year
    current_year = datetime.now().year
    for month in range(1, 13):
        create_monthly_partitions(engine, current_year, month)
        partition_name = f"articles_{current_year}_{month:02d}"
        create_partition_indexes(engine, partition_name)