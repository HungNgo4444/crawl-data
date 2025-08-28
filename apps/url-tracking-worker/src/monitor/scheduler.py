"""
Monitoring scheduler service
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..utils.database_utils import DatabaseManager
from .url_extractor import URLExtractor
from .domain_monitor import DomainMonitor
from ..config.worker_config import get_worker_config

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    """Scheduler for automated domain monitoring"""
    
    def __init__(self):
        self.config = get_worker_config()
        self.scheduler = AsyncIOScheduler()
        self.db_manager = None
        self.domain_monitor = None
        self.is_running = False
        self.last_run_result = None
        
    async def initialize(self):
        """Initialize scheduler components"""
        try:
            # Initialize database manager
            self.db_manager = DatabaseManager()
            if not self.db_manager.connect():
                raise Exception("Failed to connect to database")
            
            # Initialize URL extractor and domain monitor
            url_extractor = URLExtractor()
            self.domain_monitor = DomainMonitor(self.db_manager, url_extractor)
            
            logger.info("Monitoring scheduler initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing scheduler: {e}")
            return False
    
    def start(self):
        """Start the monitoring scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            # Add monitoring job
            self.scheduler.add_job(
                self._monitoring_job,
                trigger=IntervalTrigger(minutes=self.config['monitoring_interval_minutes']),
                id='domain_monitoring',
                name='Domain URL Monitoring',
                max_instances=1,  # Prevent overlapping runs
                replace_existing=True
            )
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"Monitoring scheduler started with {self.config['monitoring_interval_minutes']} minute intervals")
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            raise
    
    def stop(self):
        """Stop the monitoring scheduler"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            
            if self.db_manager:
                self.db_manager.disconnect()
            
            logger.info("Monitoring scheduler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    async def _monitoring_job(self):
        """The main monitoring job executed by scheduler"""
        job_start_time = datetime.now()
        logger.info("Starting scheduled domain monitoring job")
        
        try:
            if not self.domain_monitor:
                logger.error("Domain monitor not initialized")
                return
            
            # Run monitoring for all domains
            result = await self.domain_monitor.monitor_all_domains()
            
            # Store last run result
            self.last_run_result = {
                **result,
                'job_start_time': job_start_time.isoformat(),
                'job_duration': (datetime.now() - job_start_time).total_seconds()
            }
            
            logger.info(f"Scheduled monitoring job completed: {result}")
            
        except Exception as e:
            logger.error(f"Error in scheduled monitoring job: {e}")
            self.last_run_result = {
                'status': 'error',
                'error': str(e),
                'job_start_time': job_start_time.isoformat(),
                'job_duration': (datetime.now() - job_start_time).total_seconds()
            }
    
    async def trigger_manual_run(self) -> Dict[str, Any]:
        """Manually trigger a monitoring run"""
        logger.info("Manual monitoring run triggered")
        
        if not self.domain_monitor:
            return {
                'status': 'error',
                'error': 'Domain monitor not initialized'
            }
        
        try:
            result = await self.domain_monitor.monitor_all_domains()
            logger.info(f"Manual monitoring run completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in manual monitoring run: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            'is_running': self.is_running,
            'monitoring_interval_minutes': self.config['monitoring_interval_minutes'],
            'last_run_result': self.last_run_result,
            'scheduler_jobs': len(self.scheduler.get_jobs()) if self.is_running else 0,
            'next_run_time': str(self.scheduler.get_job('domain_monitoring').next_run_time) if self.is_running else None
        }