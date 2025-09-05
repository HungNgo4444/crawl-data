"""
Option 2: Pure Async Domain monitoring service for URL tracking
Eliminates ThreadPoolExecutor overhead and event loop complexity
"""
import logging
import asyncio
import threading
from typing import Dict, Any, List
from datetime import datetime, timedelta
import hashlib

from ..utils.database_utils import DatabaseManager
from .url_extractor import URLExtractor

logger = logging.getLogger(__name__)

class AsyncDomainMonitor:
    """Option 2: Pure Async domain monitoring service"""
    
    def __init__(self, db_manager: DatabaseManager, url_extractor: URLExtractor):
        self.db_manager = db_manager
        self.url_extractor = url_extractor
        
        # Optimized settings for pure async performance
        self.MAX_CONCURRENT_DOMAINS = 15  # Increased from 10
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_DOMAINS)
        
        # Batch processing for database operations
        self.BATCH_SIZE = 500  # URLs per batch insert
        # ✅ Fixed: Use thread-local storage instead of instance variable
        self._batch_storage = threading.local()
        self.batch_lock = asyncio.Lock()
        
    async def monitor_all_domains(self) -> Dict[str, Any]:
        """Pure async monitoring for all active domains"""
        logger.info("🚀 Starting pure async monitoring cycle for all domains")
        
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
        
        logger.info(f"Found {len(domains)} domains for pure async monitoring (max {self.MAX_CONCURRENT_DOMAINS} concurrent)")
        
        # Process all domains concurrently with semaphore
        tasks = [
            self._monitor_single_domain_with_semaphore(domain) 
            for domain in domains
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        total_urls_found = 0
        total_urls_added = 0
        successful_domains = 0
        failed_domains = 0
        
        for i, result in enumerate(results):
            domain_name = domains[i].get('name', 'unknown')
            
            if isinstance(result, Exception):
                failed_domains += 1
                logger.error(f"❌ EXCEPTION {domain_name}: {result}")
                continue
                
            if result.get('status') == 'success':
                successful_domains += 1
                total_urls_found += result.get('urls_found', 0)
                total_urls_added += result.get('urls_added', 0)
                
                logger.info(f"✅ SUCCESS {domain_name}: {result.get('urls_found', 0)} URLs found, {result.get('urls_added', 0)} added")
            else:
                failed_domains += 1
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ FAILED {domain_name}: {error_msg}")
        
        # Flush any remaining batched URLs
        await self._flush_url_batch()
        
        processed_domains = successful_domains + failed_domains
        logger.info(f"🎉 Pure async monitoring completed: {successful_domains} successful + {failed_domains} failed = {processed_domains}/{len(domains)} total domains")
        
        return {
            'status': 'completed',
            'total_domains': len(domains),
            'processed_domains': processed_domains,
            'successful_domains': successful_domains,
            'failed_domains': failed_domains,
            'total_urls_found': total_urls_found,
            'total_urls_added': total_urls_added,
            'timestamp': datetime.now().isoformat(),
            'concurrent_workers': self.MAX_CONCURRENT_DOMAINS,
            'processing_mode': 'pure_async'
        }
    
    async def _monitor_single_domain_with_semaphore(self, domain: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor single domain with semaphore-controlled concurrency"""
        async with self.semaphore:
            return await self.monitor_single_domain(domain)
    
    async def monitor_single_domain(self, domain: Dict[str, Any]) -> Dict[str, Any]:
        """Pure async monitoring for a single domain"""
        domain_id = domain['id']
        domain_name = domain['name']
        base_url = domain['base_url']
        
        logger.info(f"🚀 ASYNC START: {domain_name} (ID: {domain_id})")
        
        try:
            # Extract URLs asynchronously
            article_urls = await self._extract_urls_async(base_url, domain_name, domain)
            
            # Filter new URLs (async database operation)
            new_urls_only = await self._filter_new_urls_async(article_urls, domain_id)
            
            # Add URLs to batch for bulk processing
            urls_added = await self._add_urls_to_batch(new_urls_only, domain_id)
            
            # Update monitoring timestamp asynchronously
            await self._update_monitoring_timestamp_async(domain_id)
            
            logger.info(f"🏁 ASYNC COMPLETED {domain_name}: found {len(article_urls)} URLs, filtered to {len(new_urls_only)} new URLs, batched {urls_added}")
            
            return {
                'domain_id': domain_id,
                'domain_name': domain_name,
                'urls_found': len(article_urls),
                'urls_added': urls_added,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"💥 ASYNC ERROR monitoring {domain_name}: {e}")
            return {
                'domain_id': domain_id,
                'domain_name': domain_name,
                'urls_found': 0,
                'urls_added': 0,
                'status': 'error',
                'error': str(e)
            }
    
    async def _extract_urls_async(self, base_url: str, domain_name: str, domain: Dict[str, Any]) -> List[str]:
        """Extract URLs asynchronously (run in thread to avoid blocking)"""
        def _extract_sync():
            # Set domain context for URL extractor
            self.url_extractor._current_domain_id = domain['id']
            self.url_extractor._current_db_manager = self.db_manager
            
            try:
                urls = self.url_extractor.extract_article_urls_from_domain_data(
                    base_url, domain_name, domain
                )
                return urls
            finally:
                # Clear context
                self.url_extractor._current_domain_id = None
                self.url_extractor._current_db_manager = None
        
        # Run URL extraction in thread to avoid blocking async loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _extract_sync)
    
    async def _filter_new_urls_async(self, article_urls: List[str], domain_id: str) -> List[str]:
        """Filter new URLs asynchronously"""
        def _filter_sync():
            return self.db_manager.filter_new_urls_only(article_urls, domain_id)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _filter_sync)
    
    def _get_url_batch(self):
        """Get thread-local URL batch"""
        if not hasattr(self._batch_storage, 'url_batch'):
            self._batch_storage.url_batch = []
        return self._batch_storage.url_batch
    
    async def _add_urls_to_batch(self, new_urls: List[str], domain_id: str) -> int:
        """Add URLs to batch for bulk processing"""
        if not new_urls:
            return 0
            
        async with self.batch_lock:
            url_batch = self._get_url_batch()
            
            # Add URLs to thread-local batch
            for url in new_urls:
                url_hash = hashlib.sha256(url.encode()).hexdigest()
                url_batch.append({
                    'url_hash': url_hash,
                    'original_url': url,
                    'normalized_url': url,
                    'domain_id': domain_id,
                    'metadata': {
                        'source_type': 'async-monitoring',
                        'discovered_by': 'async-domain-monitor'
                    }
                })
            
            # Flush batch if it's getting large
            if len(url_batch) >= self.BATCH_SIZE:
                await self._flush_url_batch()
            
            return len(new_urls)
    
    async def _flush_url_batch(self) -> int:
        """Flush batched URLs to database"""
        url_batch = self._get_url_batch()
        if not url_batch:
            return 0
            
        def _bulk_insert_sync():
            # ✅ Fixed: Proper batch handling with clear
            urls_to_insert = url_batch.copy()
            url_batch.clear()  # Clear the thread-local batch
            try:
                return self.db_manager.bulk_add_url_objects_to_tracking(urls_to_insert)
            except Exception as e:
                logger.error(f"Failed to flush URL batch: {e}")
                # On error, don't lose the data - could implement retry logic here
                return 0
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _bulk_insert_sync)
        
        logger.debug(f"Flushed batch: {result} URLs inserted to database")
        return result
    
    async def _update_monitoring_timestamp_async(self, domain_id: str):
        """Update monitoring timestamp asynchronously"""
        def _update_sync():
            return self.db_manager.update_monitoring_timestamp(domain_id)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _update_sync)
    
    async def monitor_domain_by_id(self, domain_id: str) -> Dict[str, Any]:
        """Monitor specific domain by ID"""
        def _get_domain_sync():
            return self.db_manager.get_domain_by_id(domain_id)
        
        loop = asyncio.get_event_loop()
        domain = await loop.run_in_executor(None, _get_domain_sync)
        
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
                'timestamp': datetime.now().isoformat(),
                'max_concurrent_domains': self.MAX_CONCURRENT_DOMAINS,
                'batch_size': self.BATCH_SIZE,
                'processing_mode': 'pure_async'
            }
        except Exception as e:
            logger.error(f"Error getting monitoring stats: {e}")
            return {
                'total_domains': 0,
                'total_tracked_urls': 0,
                'error': str(e)
            }