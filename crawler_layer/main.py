"""
Main entry point for Enhanced Crawler v2
Multi-stage hybrid crawler with tiered storage
"""

import asyncio
import logging
import signal
from typing import Optional
from datetime import datetime

from .core.crawler_orchestrator import CrawlerOrchestrator
from .link_discovery import RSSCrawler, LinkProcessor, LinkQueue
from .content_extraction import StrategyRouter, ScrapyEngine
from ..storage_layer.cache import RedisManager
from ..storage_layer.object_storage import MinIOManager
from ..storage_layer.data_access import ArticleRepository
from ..config import load_config, setup_logging

logger = logging.getLogger(__name__)

class CrawlerApplication:
    """Main crawler application with graceful shutdown"""
    
    def __init__(self):
        self.config = None
        self.orchestrator: Optional[CrawlerOrchestrator] = None
        self.running = False
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize all components"""
        try:
            # Load configuration
            self.config = load_config()
            setup_logging(self.config.get('log_level', 'INFO'))
            
            logger.info("Initializing Enhanced Crawler v2...")
            
            # Initialize storage managers
            redis_manager = RedisManager(
                host=self.config.get('redis_host', 'localhost'),
                port=self.config.get('redis_port', 6379),
                db=self.config.get('redis_db', 0)
            )
            
            minio_manager = MinIOManager(
                endpoint=self.config.get('minio_endpoint', 'localhost:9000'),
                access_key=self.config.get('minio_access_key', 'minioadmin'),
                secret_key=self.config.get('minio_secret_key', 'minioadmin'),
                secure=self.config.get('minio_secure', False)
            )
            
            # Initialize MinIO buckets
            await minio_manager.initialize()
            
            # Initialize repository
            repository = ArticleRepository(
                database_url=self.config.get('database_url'),
                redis_manager=redis_manager,
                minio_manager=minio_manager
            )
            
            # Initialize crawler components
            rss_crawler = RSSCrawler(
                max_concurrent=self.config.get('rss_max_concurrent', 20)
            )
            
            link_processor = LinkProcessor()
            link_queue = LinkQueue(max_size=self.config.get('queue_max_size', 10000))
            
            strategy_router = StrategyRouter()
            scrapy_engine = ScrapyEngine(
                max_concurrent=self.config.get('scrapy_max_concurrent', 10)
            )
            
            # Initialize orchestrator
            self.orchestrator = CrawlerOrchestrator(
                rss_crawler=rss_crawler,
                link_processor=link_processor,
                link_queue=link_queue,
                strategy_router=strategy_router,
                scrapy_engine=scrapy_engine,
                repository=repository,
                config=self.config
            )
            
            logger.info("Enhanced Crawler v2 initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize crawler: {e}")
            return False
    
    async def start(self):
        """Start the crawler application"""
        if not await self.initialize():
            return False
        
        try:
            self.running = True
            logger.info("Starting Enhanced Crawler v2...")
            
            # Start the orchestrator
            await self.orchestrator.start()
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            return True
            
        except Exception as e:
            logger.error(f"Error running crawler: {e}")
            return False
        finally:
            await self.cleanup()
    
    async def stop(self):
        """Stop the crawler gracefully"""
        logger.info("Shutting down Enhanced Crawler v2...")
        self.running = False
        
        if self.orchestrator:
            await self.orchestrator.stop()
        
        self.shutdown_event.set()
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")
        
        if self.orchestrator:
            await self.orchestrator.cleanup()
        
        logger.info("Cleanup completed")
    
    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.stop())

def load_config():
    """Load application configuration"""
    import os
    
    config = {
        # Database
        'database_url': os.getenv('DATABASE_URL', 'postgresql+asyncpg://crawler_user:crawler_pass@localhost:5432/crawler_db'),
        
        # Redis
        'redis_host': os.getenv('REDIS_HOST', 'localhost'),
        'redis_port': int(os.getenv('REDIS_PORT', 6379)),
        'redis_db': int(os.getenv('REDIS_DB', 0)),
        
        # MinIO
        'minio_endpoint': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
        'minio_access_key': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
        'minio_secret_key': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
        'minio_secure': os.getenv('MINIO_SECURE', 'false').lower() == 'true',
        
        # Crawler settings
        'crawler_mode': os.getenv('CRAWLER_MODE', 'hybrid'),
        'max_concurrent_crawls': int(os.getenv('MAX_CONCURRENT_CRAWLS', 20)),
        'rss_crawl_interval': int(os.getenv('RSS_CRAWL_INTERVAL', 300)),
        'bulk_insert_batch_size': int(os.getenv('BULK_INSERT_BATCH_SIZE', 100)),
        
        # Performance
        'rss_max_concurrent': int(os.getenv('RSS_MAX_CONCURRENT', 20)),
        'scrapy_max_concurrent': int(os.getenv('SCRAPY_MAX_CONCURRENT', 10)),
        'queue_max_size': int(os.getenv('QUEUE_MAX_SIZE', 10000)),
        'cache_ttl': int(os.getenv('CACHE_TTL', 3600)),
        
        # Logging
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    }
    
    return config

def setup_logging(log_level: str = 'INFO'):
    """Setup structured logging"""
    import structlog
    
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

async def main():
    """Main entry point"""
    app = CrawlerApplication()
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, app.handle_signal)
    signal.signal(signal.SIGINT, app.handle_signal)
    
    # Start the application
    success = await app.start()
    
    if success:
        logger.info("Enhanced Crawler v2 completed successfully")
    else:
        logger.error("Enhanced Crawler v2 failed")
        exit(1)

if __name__ == "__main__":
    # Use uvloop for better performance on Unix systems
    try:
        import uvloop
        uvloop.install()
        logger.info("Using uvloop for enhanced performance")
    except ImportError:
        logger.info("uvloop not available, using default event loop")
    
    asyncio.run(main())