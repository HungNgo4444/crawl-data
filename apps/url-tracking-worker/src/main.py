"""
Main application for URL Tracking Worker
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

from .monitor.scheduler import MonitoringScheduler
from .config.worker_config import get_worker_config

# Setup logging
config = get_worker_config()
logging.basicConfig(
    level=getattr(logging, config['log_level']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('url_tracking_worker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class URLTrackingWorker:
    """Main URL Tracking Worker application"""
    
    def __init__(self):
        self.scheduler: Optional[MonitoringScheduler] = None
        self.is_running = False
        
    async def start(self):
        """Start the URL tracking worker"""
        logger.info("Starting URL Tracking Worker...")
        
        try:
            # Initialize scheduler
            self.scheduler = MonitoringScheduler()
            
            # Initialize scheduler components
            if not await self.scheduler.initialize():
                logger.error("Failed to initialize monitoring scheduler")
                return False
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("URL Tracking Worker started successfully")
            
            # Run an initial monitoring cycle
            logger.info("Running initial monitoring cycle...")
            initial_result = await self.scheduler.trigger_manual_run()
            logger.info(f"Initial monitoring result: {initial_result}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting URL Tracking Worker: {e}")
            return False
    
    async def stop(self):
        """Stop the URL tracking worker"""
        logger.info("Stopping URL Tracking Worker...")
        
        try:
            if self.scheduler:
                self.scheduler.stop()
            
            self.is_running = False
            logger.info("URL Tracking Worker stopped")
            
        except Exception as e:
            logger.error(f"Error stopping URL Tracking Worker: {e}")
    
    def get_status(self):
        """Get worker status"""
        status = {
            'worker_status': 'running' if self.is_running else 'stopped',
            'timestamp': datetime.now().isoformat()
        }
        
        if self.scheduler:
            status['scheduler'] = self.scheduler.get_status()
        
        return status

# Global worker instance
worker: Optional[URLTrackingWorker] = None

async def main():
    """Main application entry point"""
    global worker
    
    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        if worker:
            asyncio.create_task(worker.stop())
        sys.exit(0)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start worker
    worker = URLTrackingWorker()
    
    if not await worker.start():
        logger.error("Failed to start URL Tracking Worker")
        return 1
    
    try:
        # Keep the application running
        logger.info("URL Tracking Worker is running... Press Ctrl+C to stop")
        
        while worker.is_running:
            await asyncio.sleep(60)  # Check every minute
            
            # Print status every 10 minutes
            if datetime.now().minute % 10 == 0:
                status = worker.get_status()
                logger.info(f"Worker status: {status}")
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await worker.stop()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Application interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)