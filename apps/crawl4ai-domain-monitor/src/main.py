import asyncio
import logging
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import our components
from .config.settings import get_settings
from .utils.database import DatabaseManager
from .utils.crawl4ai_utils import Crawl4AIRateLimiter
from .monitor.crawl4ai_wrapper import Crawl4aiWrapper
from .monitor.url_deduplicator import URLDeduplicator
from .monitor.url_extractor import URLExtractor
from .monitor.domain_monitor import DomainMonitorManager
from .integration.domain_database import DomainDatabaseManager
from .integration.queue_manager import QueueManager
from .integration.newspaper4k_client import Newspaper4kClient
from .integration.status_tracker import StatusTracker
from .models.url_models import URLStatus
from .models.monitor_models import MonitoringStatus

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.value),
    format=settings.log_format,
    filename=settings.log_file if settings.log_file else None
)

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components
db_manager: Optional[DatabaseManager] = None
domain_monitor_manager: Optional[DomainMonitorManager] = None


async def get_database_manager() -> DatabaseManager:
    """Dependency to get database manager"""
    global db_manager
    if db_manager is None:
        db_config = settings.get_database_config()
        db_manager = DatabaseManager(**db_config)
        
        # Test connection
        logger.info("Database manager created, testing connection...")
        try:
            if not db_manager.test_connection():
                logger.warning("Database connection test failed, continuing anyway for now")
        except Exception as e:
            logger.error(f"Database test connection error: {e}")
            # For now, continue anyway to test if the service starts
    
    return db_manager


async def get_domain_monitor_manager() -> DomainMonitorManager:
    """Dependency to get domain monitor manager"""
    global domain_monitor_manager
    if domain_monitor_manager is None:
        raise HTTPException(status_code=500, detail="Monitoring service not initialized")
    return domain_monitor_manager


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global domain_monitor_manager
    
    try:
        logger.info(f"Starting {settings.app_name} v{settings.app_version}")
        
        # Initialize database manager
        db_manager = await get_database_manager()
        
        # Run migrations
        migration_files = [
            "sql/migrations/001_create_url_tracking.sql",
            "sql/migrations/002_create_indexes.sql"
        ]
        
        for migration_file in migration_files:
            try:
                success = db_manager.run_migration(migration_file)
                if success:
                    logger.info(f"Migration applied: {migration_file}")
                else:
                    logger.warning(f"Migration failed or already applied: {migration_file}")
            except Exception as e:
                logger.warning(f"Migration error for {migration_file}: {e}")
        
        # Initialize components
        domain_db_manager = DomainDatabaseManager(db_manager)
        
        # URL deduplication
        url_deduplicator = URLDeduplicator(
            db_manager, 
            ttl_days=settings.dedup_ttl_days
        )
        
        # Crawl4AI wrapper
        rate_limiter = Crawl4AIRateLimiter(
            requests_per_minute=settings.crawl4ai_requests_per_minute,
            burst_limit=settings.crawl4ai_burst_limit
        )
        crawl4ai_wrapper = Crawl4aiWrapper(rate_limiter=rate_limiter)
        
        # URL extractor
        url_extractor = URLExtractor(crawl4ai_wrapper, url_deduplicator)
        
        # Queue manager
        queue_manager = QueueManager(
            db_manager, 
            max_queue_size=settings.queue_max_size
        )
        
        # Newspaper4k client
        newspaper4k_config = settings.get_newspaper4k_config()
        newspaper4k_client = Newspaper4kClient(**newspaper4k_config)
        
        # Status tracker
        status_tracker = StatusTracker(db_manager)
        
        # Domain monitor manager
        domain_monitor_manager = DomainMonitorManager(
            domain_db_manager=domain_db_manager,
            url_extractor=url_extractor,
            queue_manager=queue_manager,
            newspaper4k_client=newspaper4k_client,
            status_tracker=status_tracker
        )
        
        # Start monitoring service
        success = await domain_monitor_manager.start_monitoring()
        if success:
            logger.info("Domain monitoring service started successfully")
        else:
            logger.error("Failed to start domain monitoring service")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global domain_monitor_manager
    
    try:
        logger.info("Shutting down monitoring service...")
        
        if domain_monitor_manager:
            await domain_monitor_manager.stop_monitoring()
        
        logger.info("Shutdown completed")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_manager = await get_database_manager()
    db_healthy = db_manager.test_connection()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.app_version,
        "database": "connected" if db_healthy else "disconnected"
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check"""
    db_manager = await get_database_manager()
    monitor_manager = await get_domain_monitor_manager()
    
    # Database check
    db_healthy = db_manager.test_connection()
    
    # Monitoring service check
    monitoring_status = await monitor_manager.get_monitoring_status()
    monitoring_healthy = monitoring_status['service_status'] == 'running'
    
    return {
        "status": "healthy" if (db_healthy and monitoring_healthy) else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.app_version,
        "components": {
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "connected": db_healthy
            },
            "monitoring": {
                "status": "healthy" if monitoring_healthy else "unhealthy",
                "active_domains": monitoring_status.get('active_domains', 0),
                "service_status": monitoring_status.get('service_status', 'unknown')
            }
        }
    }


# Monitoring endpoints
@app.get("/monitor/status")
async def get_monitoring_status(
    monitor_manager: DomainMonitorManager = Depends(get_domain_monitor_manager)
):
    """Get monitoring status"""
    return await monitor_manager.get_monitoring_status()


@app.post("/monitor/domains/{domain_id}/pause")
async def pause_domain_monitoring(
    domain_id: int,
    monitor_manager: DomainMonitorManager = Depends(get_domain_monitor_manager)
):
    """Pause monitoring for specific domain"""
    success = await monitor_manager.pause_domain_monitoring(domain_id)
    if not success:
        raise HTTPException(status_code=404, detail="Domain not found or cannot be paused")
    
    return {"message": f"Domain {domain_id} monitoring paused", "success": True}


@app.post("/monitor/domains/{domain_id}/resume")
async def resume_domain_monitoring(
    domain_id: int,
    monitor_manager: DomainMonitorManager = Depends(get_domain_monitor_manager)
):
    """Resume monitoring for specific domain"""
    success = await monitor_manager.resume_domain_monitoring(domain_id)
    if not success:
        raise HTTPException(status_code=404, detail="Domain not found or cannot be resumed")
    
    return {"message": f"Domain {domain_id} monitoring resumed", "success": True}


@app.post("/monitor/domains/{domain_id}/trigger")
async def trigger_domain_monitoring(
    domain_id: int,
    monitor_manager: DomainMonitorManager = Depends(get_domain_monitor_manager)
):
    """Manually trigger monitoring for specific domain"""
    report = await monitor_manager.trigger_domain_monitoring(domain_id)
    if not report:
        raise HTTPException(status_code=404, detail="Domain not found or monitoring failed")
    
    return {
        "message": f"Domain {domain_id} monitoring triggered",
        "report": {
            "session_id": report.session_id,
            "total_urls_discovered": report.total_urls_discovered,
            "new_urls_found": report.new_urls_found,
            "successful_tasks": report.successful_tasks,
            "failed_tasks": report.failed_tasks,
            "duration": report.duration
        }
    }


# Queue management endpoints
@app.get("/monitor/queue")
async def get_queue_status(
    domain_id: Optional[int] = None,
    db_manager: DatabaseManager = Depends(get_database_manager)
):
    """View URL processing queue"""
    queue_manager = QueueManager(db_manager)
    stats = await queue_manager.get_queue_statistics(domain_id)
    return stats


@app.get("/monitor/queue/{domain_id}")
async def get_domain_queue(
    domain_id: int,
    limit: int = 100,
    db_manager: DatabaseManager = Depends(get_database_manager)
):
    """Get processing queue for specific domain"""
    from .monitor.url_deduplicator import URLDeduplicator
    deduplicator = URLDeduplicator(db_manager)
    queue = deduplicator.get_processing_queue(domain_id, limit)
    return {"domain_id": domain_id, "queue": queue}


# Statistics endpoints
@app.get("/monitor/stats")
async def get_monitoring_statistics(
    domain_id: Optional[int] = None,
    days_back: int = 7,
    db_manager: DatabaseManager = Depends(get_database_manager)
):
    """Get monitoring statistics"""
    status_tracker = StatusTracker(db_manager)
    
    if domain_id:
        stats = await status_tracker.get_domain_processing_stats(domain_id, days_back)
    else:
        # Get overall statistics
        stats = {
            "message": "Overall statistics not implemented yet",
            "domain_id": None,
            "days_back": days_back
        }
    
    return stats


@app.get("/monitor/stats/failures")
async def get_recent_failures(
    domain_id: Optional[int] = None,
    limit: int = 50,
    db_manager: DatabaseManager = Depends(get_database_manager)
):
    """Get recent failed processing attempts"""
    status_tracker = StatusTracker(db_manager)
    failures = await status_tracker.get_recent_failures(domain_id, limit)
    return {"failures": failures}


# URL management endpoints
@app.get("/monitor/dedup/{url_hash}")
async def check_url_deduplication(
    url_hash: str,
    db_manager: DatabaseManager = Depends(get_database_manager)
):
    """Check if URL already processed"""
    status_tracker = StatusTracker(db_manager)
    # This would need the original URL, simplified for now
    return {"url_hash": url_hash, "message": "URL deduplication check"}


@app.post("/monitor/dedup/cleanup")
async def trigger_dedup_cleanup(
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends(get_database_manager)
):
    """Trigger expired URL cleanup"""
    async def cleanup_task():
        from .monitor.url_deduplicator import URLDeduplicator
        deduplicator = URLDeduplicator(db_manager)
        count = deduplicator.cleanup_expired()
        logger.info(f"Cleaned up {count} expired URL records")
    
    background_tasks.add_task(cleanup_task)
    return {"message": "Cleanup task scheduled", "success": True}


# Configuration endpoints
@app.get("/config")
async def get_configuration():
    """Get current configuration"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "mode": settings.mode,
        "monitoring": settings.get_monitoring_config(),
        "queue": settings.get_queue_config(),
        "deduplication": settings.get_deduplication_config()
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        log_level=settings.log_level.value.lower(),
        reload=settings.debug
    )