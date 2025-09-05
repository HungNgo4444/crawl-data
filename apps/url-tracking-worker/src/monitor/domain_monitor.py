"""
Domain monitoring service for URL tracking
"""
import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from ..utils.database_utils import DatabaseManager
from .url_extractor import URLExtractor

logger = logging.getLogger(__name__)

class DomainMonitor:
    """Main domain monitoring service"""
    
    def __init__(self, db_manager: DatabaseManager, url_extractor: URLExtractor):
        self.db_manager = db_manager
        self.url_extractor = url_extractor
        
        # Optimized settings for better performance
        self.MAX_CONCURRENT_DOMAINS = 10  # Increased concurrent processing 
        self.REQUEST_DELAY = 0            # Removed delay for faster processing
        # ✅ Fixed: Per-domain locking instead of global lock
        self._domain_locks = {}
        self._locks_lock = threading.Lock()  # Lock for the locks dictionary
        
    def _get_domain_lock(self, domain_id: str) -> threading.Lock:
        """Get or create a lock for specific domain"""
        with self._locks_lock:
            if domain_id not in self._domain_locks:
                self._domain_locks[domain_id] = threading.Lock()
            return self._domain_locks[domain_id]
        
    async def monitor_all_domains(self) -> Dict[str, Any]:
        """Monitor all active domains and extract URLs with concurrent processing"""
        logger.info("Starting concurrent monitoring cycle for all domains")
        
        # Get domains ready for monitoring
        domains = self.db_manager.get_domains_for_monitoring()
        
        if not domains:
            logger.warning("No domains found for monitoring")
            return {
                'status': 'completed',
                'total_domains': 0,
                'processed_domains': 0,
                'total_urls_found': 0,
                'total_urls_added': 0
            }
        
        logger.info(f"Found {len(domains)} domains for concurrent monitoring (max {self.MAX_CONCURRENT_DOMAINS} at a time)")
        
        total_urls_found = 0
        total_urls_added = 0
        successful_domains = 0
        failed_domains = 0
        
        # Process domains concurrently using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT_DOMAINS) as executor:
            # Submit all domain monitoring tasks
            future_to_domain = {
                executor.submit(self._monitor_single_domain_sync, domain): domain
                for domain in domains
            }
            
            # Process results as they complete
            for future in as_completed(future_to_domain):
                domain = future_to_domain[future]
                domain_name = domain.get('name', 'unknown')
                
                # Process result for domain
                logger.debug(f"Processing result for domain: {domain_name}")
                
                try:
                    result = future.result()
                    
                    if result.get('status') == 'success':
                        successful_domains += 1
                        total_urls_found += result.get('urls_found', 0)
                        total_urls_added += result.get('urls_added', 0)
                        
                        logger.info(f"Domain {domain_name}: {result.get('urls_found', 0)} URLs found, {result.get('urls_added', 0)} added")
                    else:
                        failed_domains += 1
                        error_msg = result.get('error', 'Unknown error')
                        logger.error(f"Domain {domain_name} failed: {error_msg}")
                    
                    # No delay - optimized for speed (removed time.sleep)
                    
                except Exception as e:
                    failed_domains += 1
                    logger.error(f"Exception processing {domain_name}: {e}")
                    continue
        
        processed_domains = successful_domains + failed_domains
        logger.info(f"Monitoring completed: {successful_domains} successful, {failed_domains} failed, {processed_domains}/{len(domains)} total")
        
        return {
            'status': 'completed',
            'total_domains': len(domains),
            'processed_domains': processed_domains,
            'successful_domains': successful_domains,
            'failed_domains': failed_domains,
            'total_urls_found': total_urls_found,
            'total_urls_added': total_urls_added,
            'timestamp': datetime.now().isoformat(),
            'concurrent_workers': self.MAX_CONCURRENT_DOMAINS
        }
    
    def _monitor_single_domain_sync(self, domain: Dict[str, Any]) -> Dict[str, Any]:
        """Simplified synchronous wrapper for monitor_single_domain"""
        domain_name = domain.get('name', 'unknown')
        
        logger.debug(f"Processing domain: {domain_name} (Thread: {threading.current_thread().name})")
        
        try:
            # ✅ Fixed: Simplified event loop management
            # Just create a new loop and run the coroutine
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self.monitor_single_domain(domain))
                return result
            finally:
                loop.close()  # Always close the loop
                
        except Exception as e:
            logger.error(f"Error processing domain {domain_name}: {e}")
            return {
                'domain_id': domain.get('id', ''),
                'domain_name': domain_name,
                'urls_found': 0,
                'urls_added': 0,
                'status': 'error',
                'error': str(e)
            }
    
    async def monitor_single_domain(self, domain: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor a single domain for new URLs with thread-safe database operations"""
        domain_id = domain['id']
        domain_name = domain['name']
        base_url = domain['base_url']
        
        logger.debug(f"Starting domain monitoring: {domain_name} (ID: {domain_id})")
        
        try:
            # Set domain context for immediate database saves during deep crawl
            self.url_extractor._current_domain_id = domain_id
            self.url_extractor._current_db_manager = self.db_manager
            
            # Extract URLs using domain data with immediate database save capability
            article_urls = self.url_extractor.extract_article_urls_from_domain_data(
                base_url, domain_name, domain
            )
            
            # Clear context after extraction
            self.url_extractor._current_domain_id = None
            self.url_extractor._current_db_manager = None
            
            # ✅ Fixed: Per-domain locking for better concurrency
            domain_lock = self._get_domain_lock(domain_id)
            with domain_lock:
                # Filter out URLs already in database (incremental crawling)
                new_urls_only = self.db_manager.filter_new_urls_only(article_urls, domain_id)
                
                # Add only new URLs to tracking table
                urls_added = self.db_manager.bulk_add_urls_to_tracking(
                    new_urls_only, domain_id, 'concurrent-monitoring'
                )
                
                # Update monitoring timestamp
                self.db_manager.update_monitoring_timestamp(domain_id)
            
            logger.info(f"Completed {domain_name}: {len(article_urls)} URLs found, {len(new_urls_only)} new, {urls_added} added")
            
            return {
                'domain_id': domain_id,
                'domain_name': domain_name,
                'urls_found': len(article_urls),
                'urls_added': urls_added,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error monitoring {domain_name}: {e}")
            return {
                'domain_id': domain_id,
                'domain_name': domain_name,
                'urls_found': 0,
                'urls_added': 0,
                'status': 'error',
                'error': str(e)
            }
    
    async def monitor_domain_by_id(self, domain_id: str) -> Dict[str, Any]:
        """Monitor specific domain by ID"""
        domain = self.db_manager.get_domain_by_id(domain_id)
        if not domain:
            return {
                'status': 'error',
                'error': f'Domain {domain_id} not found'
            }
        
        return await self.monitor_single_domain(domain)
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        try:
            domains = self.db_manager.get_domains_for_monitoring()
            total_urls = self.db_manager.get_url_tracking_count()
            
            return {
                'total_domains': len(domains),
                'total_tracked_urls': total_urls,
                'domains_with_data': len([d for d in domains if d.get('rss_feeds') or d.get('sitemaps')]),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting monitoring stats: {e}")
            return {
                'total_domains': 0,
                'total_tracked_urls': 0,
                'error': str(e)
            }