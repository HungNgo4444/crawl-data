import logging
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from .crawl4ai_wrapper import Crawl4aiWrapper
from .url_deduplicator import URLDeduplicator
from ..models.domain_config import DomainConfig
from ..models.monitor_models import MonitoringTask, MonitoringReport

logger = logging.getLogger(__name__)


class URLExtractor:
    """URL extraction using crawl4ai AsyncWebCrawler with deduplication"""
    
    def __init__(self, crawl4ai_wrapper: Crawl4aiWrapper, url_deduplicator: URLDeduplicator):
        self.crawl4ai_wrapper = crawl4ai_wrapper
        self.url_deduplicator = url_deduplicator
    
    async def extract_urls_for_domain(self, domain_config: DomainConfig) -> MonitoringReport:
        """Extract new URLs for a domain and return monitoring report"""
        session_id = f"extract_{domain_config.name}_{int(datetime.now().timestamp())}"
        
        report = MonitoringReport(
            session_id=session_id,
            domain_id=domain_config.id,
            domain_name=domain_config.name,
            started_at=datetime.now()
        )
        
        try:
            # Create monitoring tasks for different sources
            tasks = []
            
            # Homepage and category pages
            for url in domain_config.monitoring_pages:
                if url:
                    task = MonitoringTask(
                        task_id=f"{session_id}_page_{len(tasks)}",
                        domain_id=domain_config.id,
                        domain_name=domain_config.name,
                        task_type="homepage",
                        url=url,
                        priority=1
                    )
                    tasks.append(task)
            
            # RSS feeds
            for rss_url in domain_config.rss_feeds:
                if rss_url:
                    task = MonitoringTask(
                        task_id=f"{session_id}_rss_{len(tasks)}",
                        domain_id=domain_config.id,
                        domain_name=domain_config.name,
                        task_type="rss",
                        url=rss_url,
                        priority=2
                    )
                    tasks.append(task)
            
            # Sitemaps
            for sitemap_url in domain_config.sitemaps:
                if sitemap_url:
                    task = MonitoringTask(
                        task_id=f"{session_id}_sitemap_{len(tasks)}",
                        domain_id=domain_config.id,
                        domain_name=domain_config.name,
                        task_type="sitemap",
                        url=sitemap_url,
                        priority=3
                    )
                    tasks.append(task)
            
            # Execute tasks
            all_discovered_urls = []
            
            for task in tasks:
                task.started_at = datetime.now()
                task.status = "running"
                
                try:
                    discovered_urls = await self._execute_extraction_task(task, domain_config)
                    
                    # Deduplication check
                    new_urls, duplicate_urls = self.url_deduplicator.add_discovered_urls(
                        discovered_urls, domain_config.id
                    )
                    
                    # Update task results
                    task.urls_discovered = len(discovered_urls)
                    task.metadata = {
                        'new_urls': len(new_urls),
                        'duplicate_urls': len(duplicate_urls),
                        'total_discovered': len(discovered_urls)
                    }
                    task.status = "completed"
                    task.completed_at = datetime.now()
                    
                    all_discovered_urls.extend(new_urls)
                    
                    logger.info(f"Task {task.task_id}: discovered {len(discovered_urls)} URLs, "
                              f"{len(new_urls)} new, {len(duplicate_urls)} duplicates")
                    
                except Exception as e:
                    task.status = "failed"
                    task.error_message = str(e)
                    task.completed_at = datetime.now()
                    logger.error(f"Task {task.task_id} failed: {e}")
                
                report.add_task(task)
                
                # Small delay between tasks
                await asyncio.sleep(1.0)
            
            # Finalize report
            report.new_urls_found = len(all_discovered_urls)
            report.finalize_report()
            
            logger.info(f"Domain {domain_config.name}: extracted {report.new_urls_found} new URLs "
                       f"in {report.duration:.1f} seconds")
            
            return report
            
        except Exception as e:
            logger.error(f"URL extraction error for domain {domain_config.name}: {e}")
            report.errors.append(f"Extraction failed: {str(e)}")
            report.finalize_report()
            return report
    
    async def _execute_extraction_task(self, task: MonitoringTask, domain_config: DomainConfig) -> List[str]:
        """Execute single extraction task based on task type"""
        try:
            if task.task_type == "rss":
                return await self.crawl4ai_wrapper.discover_urls_from_rss(task.url, domain_config)
            elif task.task_type in ["homepage", "category", "sitemap"]:
                return await self.crawl4ai_wrapper.discover_urls_from_page(task.url, domain_config)
            else:
                logger.warning(f"Unknown task type: {task.task_type}")
                return []
                
        except Exception as e:
            logger.error(f"Task execution error for {task.task_id}: {e}")
            raise
    
    async def extract_urls_batch(self, domain_configs: List[DomainConfig]) -> Dict[int, MonitoringReport]:
        """Extract URLs for multiple domains concurrently"""
        reports = {}
        
        # Create tasks for each domain
        tasks = []
        for domain_config in domain_configs:
            task = self.extract_urls_for_domain(domain_config)
            tasks.append((domain_config.id, task))
        
        # Execute with limited concurrency
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent domains
        
        async def execute_with_semaphore(domain_id, task):
            async with semaphore:
                return domain_id, await task
        
        # Run all tasks
        results = await asyncio.gather(*[
            execute_with_semaphore(domain_id, task) 
            for domain_id, task in tasks
        ], return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch extraction error: {result}")
                continue
            
            domain_id, report = result
            reports[domain_id] = report
        
        return reports
    
    async def validate_discovered_urls(self, urls: List[str], sample_size: int = 10) -> Dict[str, Any]:
        """Validate a sample of discovered URLs for accessibility"""
        if not urls:
            return {'valid': 0, 'invalid': 0, 'total': 0, 'sample_size': 0}
        
        # Take a sample for validation
        import random
        sample_urls = random.sample(urls, min(sample_size, len(urls)))
        
        valid_count = 0
        invalid_count = 0
        validation_results = []
        
        for url in sample_urls:
            try:
                is_accessible, error = await self.crawl4ai_wrapper.test_url_accessibility(url)
                
                if is_accessible:
                    valid_count += 1
                else:
                    invalid_count += 1
                    validation_results.append({
                        'url': url,
                        'error': error
                    })
                
                # Small delay between validation requests
                await asyncio.sleep(0.5)
                
            except Exception as e:
                invalid_count += 1
                validation_results.append({
                    'url': url,
                    'error': str(e)
                })
        
        return {
            'valid': valid_count,
            'invalid': invalid_count,
            'total': len(urls),
            'sample_size': len(sample_urls),
            'validation_rate': (valid_count / len(sample_urls)) * 100 if sample_urls else 0,
            'errors': validation_results
        }
    
    async def get_extraction_statistics(self, domain_id: Optional[int] = None) -> Dict[str, Any]:
        """Get extraction and deduplication statistics"""
        try:
            dedup_stats = self.url_deduplicator.get_statistics(domain_id)
            
            return {
                'deduplication': dedup_stats,
                'extraction_active': True,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Statistics error: {e}")
            return {
                'error': str(e),
                'extraction_active': False,
                'last_updated': datetime.now().isoformat()
            }