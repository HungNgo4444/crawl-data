import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ..models.domain_config import DomainConfig
from ..models.monitor_models import DomainMonitor, MonitoringStatus, MonitoringReport
from ..integration.domain_database import DomainDatabaseManager
from ..monitor.url_extractor import URLExtractor
from ..integration.queue_manager import QueueManager, QueuePriority
from ..integration.newspaper4k_client import Newspaper4kClient
from ..integration.status_tracker import StatusTracker
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class DomainMonitorManager:
    """Core domain monitoring logic"""
    
    def __init__(self, 
                 domain_db_manager: DomainDatabaseManager,
                 url_extractor: URLExtractor,
                 queue_manager: QueueManager,
                 newspaper4k_client: Newspaper4kClient,
                 status_tracker: StatusTracker):
        self.domain_db_manager = domain_db_manager
        self.url_extractor = url_extractor
        self.queue_manager = queue_manager
        self.newspaper4k_client = newspaper4k_client
        self.status_tracker = status_tracker
        
        self.settings = get_settings()
        self.active_monitors: Dict[int, DomainMonitor] = {}
        self._monitoring_tasks: Dict[int, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()
    
    async def start_monitoring(self) -> bool:
        """Start monitoring service"""
        try:
            logger.info("Starting domain monitoring service...")
            
            # Load domain configurations
            domain_configs = await self._load_domain_configurations()
            if not domain_configs:
                logger.warning("No domains found for monitoring")
                return False
            
            # Initialize domain monitors
            for config in domain_configs:
                monitor = DomainMonitor(
                    domain_id=config.id,
                    domain_name=config.name,
                    status=MonitoringStatus.STARTING,
                    monitoring_interval=config.monitoring_interval or self.settings.monitoring_interval_seconds
                )
                self.active_monitors[config.id] = monitor
            
            # Start monitoring tasks for each domain
            await self._start_domain_monitoring_tasks()
            
            # Start background maintenance tasks
            asyncio.create_task(self._cleanup_maintenance_task())
            asyncio.create_task(self._health_check_task())
            
            logger.info(f"Domain monitoring started for {len(domain_configs)} domains")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            return False
    
    async def stop_monitoring(self) -> bool:
        """Stop monitoring service"""
        try:
            logger.info("Stopping domain monitoring service...")
            
            # Signal shutdown
            self._shutdown_event.set()
            
            # Update all monitors to stopping status
            for monitor in self.active_monitors.values():
                monitor.status = MonitoringStatus.STOPPING
            
            # Cancel all monitoring tasks
            for task in self._monitoring_tasks.values():
                task.cancel()
            
            # Wait for tasks to finish
            if self._monitoring_tasks:
                await asyncio.gather(*self._monitoring_tasks.values(), return_exceptions=True)
            
            # Update monitors to stopped status
            for monitor in self.active_monitors.values():
                monitor.status = MonitoringStatus.STOPPED
            
            logger.info("Domain monitoring stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            return False
    
    async def _load_domain_configurations(self) -> List[DomainConfig]:
        """Load domain configurations from database"""
        try:
            return self.domain_db_manager.load_domain_configs()
        except Exception as e:
            logger.error(f"Failed to load domain configurations: {e}")
            return []
    
    async def _start_domain_monitoring_tasks(self):
        """Start monitoring tasks for all domains"""
        for domain_id, monitor in self.active_monitors.items():
            try:
                task = asyncio.create_task(
                    self._monitor_domain_loop(domain_id),
                    name=f"monitor_domain_{domain_id}"
                )
                self._monitoring_tasks[domain_id] = task
                monitor.status = MonitoringStatus.RUNNING
                
            except Exception as e:
                logger.error(f"Failed to start monitoring task for domain {domain_id}: {e}")
                monitor.status = MonitoringStatus.ERROR
                monitor.last_error = str(e)
    
    async def _monitor_domain_loop(self, domain_id: int):
        """Main monitoring loop for a single domain"""
        monitor = self.active_monitors.get(domain_id)
        if not monitor:
            return
        
        logger.info(f"Starting monitoring loop for domain {domain_id} ({monitor.domain_name})")
        
        while not self._shutdown_event.is_set():
            try:
                # Check if monitoring is paused
                if monitor.status == MonitoringStatus.PAUSED:
                    await asyncio.sleep(60)  # Check every minute
                    continue
                
                # Get domain configuration
                domain_config = self.domain_db_manager.get_domain_by_id(domain_id)
                if not domain_config:
                    logger.error(f"Domain configuration not found: {domain_id}")
                    monitor.status = MonitoringStatus.ERROR
                    monitor.last_error = "Domain configuration not found"
                    break
                
                # Perform monitoring cycle
                await self._perform_monitoring_cycle(domain_config, monitor)
                
                # Update next scheduled time
                monitor.last_monitored_at = datetime.now()
                monitor.next_scheduled_at = monitor.last_monitored_at + timedelta(
                    seconds=monitor.monitoring_interval
                )
                
                # Wait for next cycle
                await asyncio.sleep(monitor.monitoring_interval)
                
            except asyncio.CancelledError:
                logger.info(f"Monitoring cancelled for domain {domain_id}")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop for domain {domain_id}: {e}")
                monitor.status = MonitoringStatus.ERROR
                monitor.last_error = str(e)
                monitor.error_count += 1
                
                # Wait before retrying
                await asyncio.sleep(min(300, 60 * monitor.error_count))  # Exponential backoff
        
        logger.info(f"Monitoring loop stopped for domain {domain_id}")
    
    async def _perform_monitoring_cycle(self, domain_config: DomainConfig, monitor: DomainMonitor):
        """Perform single monitoring cycle for domain"""
        try:
            logger.debug(f"Starting monitoring cycle for {domain_config.name}")
            
            # 1. Extract URLs using crawl4ai
            extraction_report = await self.url_extractor.extract_urls_for_domain(domain_config)
            
            # 2. Update statistics
            urls_discovered = extraction_report.total_urls_discovered
            new_urls = extraction_report.new_urls_found
            
            monitor.update_statistics(
                urls_discovered=urls_discovered,
                urls_processed=0,  # Will be updated after processing
                success=True
            )
            
            # 3. Add new URLs to processing queue if any found
            if new_urls > 0:
                # Get the actual URLs from the report (simplified - in production get from database)
                queue_count = await self.queue_manager.add_urls_to_queue(
                    urls=[],  # Would get URLs from extraction report
                    domain_id=domain_config.id,
                    priority=QueuePriority.NORMAL
                )
                
                logger.info(f"Domain {domain_config.name}: {new_urls} new URLs discovered, "
                           f"{queue_count} added to queue")
            
            # 4. Process queued URLs if queue has items
            await self._process_queued_urls(domain_config, monitor)
            
            # 5. Update domain metadata in database
            await self._update_domain_metadata(domain_config, monitor, extraction_report)
            
            logger.debug(f"Monitoring cycle completed for {domain_config.name}")
            
        except Exception as e:
            logger.error(f"Monitoring cycle error for {domain_config.name}: {e}")
            monitor.update_statistics(success=False, error=str(e))
            raise
    
    async def _process_queued_urls(self, domain_config: DomainConfig, monitor: DomainMonitor):
        """Process queued URLs for domain"""
        try:
            # Get next batch from queue
            batch = await self.queue_manager.get_next_batch(
                domain_id=domain_config.id,
                batch_size=self.settings.queue_batch_size
            )
            
            if not batch:
                return  # No URLs to process
            
            logger.info(f"Processing batch of {len(batch.urls)} URLs for {domain_config.name}")
            
            # Process URLs with newspaper4k
            results = await self.newspaper4k_client.extract_urls_concurrent(
                urls=batch.urls,
                domain_id=domain_config.id,
                max_concurrent=self.settings.queue_max_concurrent
            )
            
            # Update status tracking
            await self.status_tracker.update_processing_status(results)
            
            # Update queue status
            success_urls = [r.url for r in results if r.success]
            failed_urls = [r.url for r in results if not r.success]
            
            await self.queue_manager.mark_batch_completed(batch, success_urls, failed_urls)
            
            # Update monitor statistics
            monitor.update_statistics(
                urls_processed=len(results),
                success=len(success_urls) > len(failed_urls)
            )
            
            logger.info(f"Batch processing completed: {len(success_urls)} successful, "
                       f"{len(failed_urls)} failed")
            
        except Exception as e:
            logger.error(f"Queue processing error for {domain_config.name}: {e}")
            raise
    
    async def _update_domain_metadata(self, domain_config: DomainConfig, 
                                    monitor: DomainMonitor, report: MonitoringReport):
        """Update domain metadata in database"""
        try:
            metadata = {
                'last_monitored_at': monitor.last_monitored_at.isoformat() if monitor.last_monitored_at else None,
                'urls_discovered': monitor.total_urls_discovered,
                'urls_processed': monitor.total_urls_processed,
                'success_rate': monitor.success_rate,
                'error_count': monitor.error_count
            }
            
            await self.domain_db_manager.update_monitoring_metadata(domain_config.id, metadata)
            
        except Exception as e:
            logger.error(f"Error updating domain metadata for {domain_config.name}: {e}")
    
    async def _cleanup_maintenance_task(self):
        """Background maintenance task"""
        while not self._shutdown_event.is_set():
            try:
                logger.debug("Running maintenance tasks...")
                
                # Cleanup expired URL tracking
                await self.status_tracker.cleanup_expired_tracking()
                
                # Cleanup old queue entries
                await self.queue_manager.cleanup_old_queue_entries(
                    days_old=self.settings.queue_cleanup_days
                )
                
                # Wait for next maintenance cycle (24 hours)
                await asyncio.sleep(self.settings.dedup_cleanup_interval_hours * 3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Maintenance task error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def _health_check_task(self):
        """Background health check task"""
        while not self._shutdown_event.is_set():
            try:
                # Check newspaper4k service health
                is_healthy, health_data = await self.newspaper4k_client.check_service_health()
                
                if not is_healthy:
                    logger.warning(f"Newspaper4k service unhealthy: {health_data}")
                    # Could pause processing or send alerts
                
                # Check memory usage
                await self._check_memory_usage()
                
                # Wait for next health check
                await asyncio.sleep(self.settings.monitoring_health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _check_memory_usage(self):
        """Check memory usage and log warnings"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb > self.settings.max_memory_usage_mb:
                logger.warning(f"High memory usage: {memory_mb:.1f} MB "
                             f"(limit: {self.settings.max_memory_usage_mb} MB)")
        except ImportError:
            pass  # psutil not available
        except Exception as e:
            logger.debug(f"Memory check error: {e}")
    
    # Public API methods
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get overall monitoring status"""
        return {
            'service_status': 'running' if not self._shutdown_event.is_set() else 'stopped',
            'active_domains': len(self.active_monitors),
            'domain_statuses': {
                domain_id: {
                    'name': monitor.domain_name,
                    'status': monitor.status.value,
                    'last_monitored_at': monitor.last_monitored_at.isoformat() if monitor.last_monitored_at else None,
                    'next_scheduled_at': monitor.next_scheduled_at.isoformat() if monitor.next_scheduled_at else None,
                    'total_urls_discovered': monitor.total_urls_discovered,
                    'total_urls_processed': monitor.total_urls_processed,
                    'success_rate': monitor.success_rate,
                    'error_count': monitor.error_count,
                    'last_error': monitor.last_error
                }
                for domain_id, monitor in self.active_monitors.items()
            }
        }
    
    async def pause_domain_monitoring(self, domain_id: int) -> bool:
        """Pause monitoring for specific domain"""
        try:
            monitor = self.active_monitors.get(domain_id)
            if monitor:
                monitor.status = MonitoringStatus.PAUSED
                logger.info(f"Paused monitoring for domain {domain_id} ({monitor.domain_name})")
                return True
            return False
        except Exception as e:
            logger.error(f"Error pausing domain monitoring: {e}")
            return False
    
    async def resume_domain_monitoring(self, domain_id: int) -> bool:
        """Resume monitoring for specific domain"""
        try:
            monitor = self.active_monitors.get(domain_id)
            if monitor and monitor.status == MonitoringStatus.PAUSED:
                monitor.status = MonitoringStatus.RUNNING
                logger.info(f"Resumed monitoring for domain {domain_id} ({monitor.domain_name})")
                return True
            return False
        except Exception as e:
            logger.error(f"Error resuming domain monitoring: {e}")
            return False
    
    async def trigger_domain_monitoring(self, domain_id: int) -> Optional[MonitoringReport]:
        """Manually trigger monitoring for specific domain"""
        try:
            domain_config = self.domain_db_manager.get_domain_by_id(domain_id)
            if not domain_config:
                return None
            
            logger.info(f"Manually triggering monitoring for domain {domain_id}")
            
            # Extract URLs
            report = await self.url_extractor.extract_urls_for_domain(domain_config)
            
            # Update monitor statistics if exists
            if domain_id in self.active_monitors:
                monitor = self.active_monitors[domain_id]
                monitor.update_statistics(
                    urls_discovered=report.total_urls_discovered,
                    success=report.failed_tasks == 0
                )
            
            return report
            
        except Exception as e:
            logger.error(f"Error triggering domain monitoring: {e}")
            return None