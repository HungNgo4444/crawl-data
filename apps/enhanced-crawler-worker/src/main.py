"""
Enhanced Crawler Worker - Main Entry Point

This module provides the main entry point for the enhanced crawler worker
with proper initialization, configuration, and graceful shutdown handling.
"""

import asyncio
import os
import signal
import sys
from typing import Optional
import uvloop
import structlog

# Configure structured logging
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
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class EnhancedCrawlerWorkerApp:
    """Main application class for Enhanced Crawler Worker."""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.tasks = []
        
    async def startup(self):
        """Initialize application services."""
        try:
            logger.info("Starting Enhanced Crawler Worker...")
            
            # Initialize crawl4ai integration
            await self._init_crawl4ai()
            
            # Initialize worker services
            await self._init_services()
            
            # Setup health check endpoint
            await self._setup_health_check()
            
            logger.info("Enhanced Crawler Worker started successfully")
            
        except Exception as e:
            logger.error("Failed to start Enhanced Crawler Worker", error=str(e))
            raise
    
    async def _init_crawl4ai(self):
        """Initialize Crawl4AI integration."""
        try:
            # Import crawl4ai components (installed via pip)
            import crawl4ai
            logger.info(f"Crawl4AI initialized, version: {crawl4ai.__version__}")
        except Exception as e:
            logger.error("Failed to initialize Crawl4AI", error=str(e))
            raise
    
    async def _init_services(self):
        """Initialize worker services."""
        # Import worker components with correct paths
        import sys
        sys.path.append('/app/src')
        from workers.url_discovery_coordinator import URLDiscoveryCoordinator
        from workers.crawl4ai_content_extractor import Crawl4AIContentExtractor
        
        # Initialize coordinators
        self.url_coordinator = URLDiscoveryCoordinator()
        self.content_extractor = Crawl4AIContentExtractor()
        
        logger.info("Worker services initialized")
    
    async def _setup_health_check(self):
        """Setup health check endpoint."""
        from aiohttp import web
        
        async def health_check(request):
            return web.json_response({
                "status": "healthy",
                "service": "enhanced-crawler-worker",
                "version": "1.0.0"
            })
        
        app = web.Application()
        app.router.add_get('/health', health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        
        logger.info("Health check endpoint started on port 8080")
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down Enhanced Crawler Worker...")
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
            
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Cleanup resources
        if hasattr(self, 'url_coordinator'):
            # Cleanup coordinators if they have close methods
            pass
            
        if hasattr(self, 'content_extractor'):
            await self.content_extractor.close()
        
        logger.info("Enhanced Crawler Worker shutdown complete")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig_num, frame):
            logger.info(f"Received signal {sig_num}, initiating shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Main application loop."""
        self.setup_signal_handlers()
        
        try:
            await self.startup()
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error("Application error", error=str(e))
            raise
        finally:
            await self.shutdown()

async def main():
    """Main entry point."""
    # Use uvloop for better performance on Linux
    if sys.platform != 'win32':
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    app = EnhancedCrawlerWorkerApp()
    
    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error("Application failed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())