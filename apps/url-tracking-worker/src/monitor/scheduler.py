"""
Monitoring scheduler service with timeout-based scheduling
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
from .domain_monitor_async import AsyncDomainMonitor
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
            
            # Choose monitoring implementation based on config
            if self.config.get('use_pure_async', False):
                logger.info("🔄 Using Pure Async Domain Monitor (Option 2)")
                self.domain_monitor = AsyncDomainMonitor(self.db_manager, url_extractor)
            else:
                logger.info("🔄 Using Thread-based Domain Monitor with Timeout (Option 1)")
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
            # Add timeout-based monitoring job (Option 1)
            monitoring_interval = self.config['monitoring_interval_minutes']
            self.scheduler.add_job(
                self._monitoring_job_with_timeout,
                trigger=IntervalTrigger(minutes=monitoring_interval),
                id='domain_monitoring',
                name='Domain URL Monitoring with Timeout',
                max_instances=2,  # Allow 1 backup instance to prevent gaps
                misfire_grace_time=300,  # 5 minute grace period for delayed starts
                coalesce=True,  # Merge multiple missed runs into single execution
                replace_existing=True
            )
            
            logger.info(f"Timeout-based monitoring configured: {monitoring_interval}min interval, {self.config.get('monitoring_timeout_seconds', 840)}s timeout")
            
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
    
    async def _monitoring_job_with_timeout(self):
        """Option 1: Timeout-based monitoring job to prevent gaps"""
        job_start_time = datetime.now()
        timeout_seconds = self.config.get('monitoring_timeout_seconds', 840)  # 14 minutes default
        logger.info(f"🚀 Starting timeout-protected monitoring job (timeout: {timeout_seconds}s)")
        
        try:
            if not self.domain_monitor:
                logger.error("Domain monitor not initialized")
                return
            
            # Run monitoring with timeout protection
            try:
                result = await asyncio.wait_for(
                    self.domain_monitor.monitor_all_domains(),
                    timeout=timeout_seconds
                )
                
                # Store successful run result
                duration = (datetime.now() - job_start_time).total_seconds()
                self.last_run_result = {
                    **result,
                    'job_start_time': job_start_time.isoformat(),
                    'job_duration': duration,
                    'timeout_used': timeout_seconds,
                    'completed_within_timeout': True
                }
                
                logger.info(f"✅ Timeout-protected monitoring completed in {duration:.1f}s: {result}")
                
            except asyncio.TimeoutError:
                duration = (datetime.now() - job_start_time).total_seconds()
                logger.warning(f"⏰ Monitoring cycle timeout after {duration:.1f}s - ensuring next cycle runs")
                
                # Store timeout result but don't fail completely
                self.last_run_result = {
                    'status': 'timeout',
                    'job_start_time': job_start_time.isoformat(),
                    'job_duration': duration,
                    'timeout_used': timeout_seconds,
                    'completed_within_timeout': False,
                    'message': 'Monitoring cycle exceeded timeout but next cycle will run'
                }
                
        except Exception as e:
            duration = (datetime.now() - job_start_time).total_seconds()
            logger.error(f"💥 Error in timeout-protected monitoring job: {e}")
            self.last_run_result = {
                'status': 'error',
                'error': str(e),
                'job_start_time': job_start_time.isoformat(),
                'job_duration': duration,
                'timeout_used': timeout_seconds,
                'completed_within_timeout': False
            }
    
    async def _monitoring_job(self):
        """Legacy monitoring job (kept for compatibility)"""
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