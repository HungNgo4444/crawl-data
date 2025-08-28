import logging
import httpx
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from ..models.url_models import URLBatch, ProcessingResult, URLStatus

logger = logging.getLogger(__name__)


class Newspaper4kClient:
    """Client for newspaper4k_extractor API"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:8001",
                 timeout: int = 30,
                 max_retries: int = 3,
                 retry_delay: float = 2.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # HTTP client configuration
        self.client_config = {
            'timeout': httpx.Timeout(timeout),
            'limits': httpx.Limits(max_keepalive_connections=10, max_connections=20),
            'follow_redirects': True
        }
    
    async def extract_single_url(self, url: str, domain_id: int) -> ProcessingResult:
        """Extract content from single URL"""
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                # Prepare request data
                request_data = {
                    'url': url,
                    'domain_id': domain_id,
                    'extract_images': True,
                    'extract_links': True,
                    'clean_html': True
                }
                
                response = await client.post(
                    f"{self.base_url}/extract",
                    json=request_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                response.raise_for_status()
                result_data = response.json()
                
                return ProcessingResult(
                    url=url,
                    success=True,
                    extracted_data=result_data,
                    processing_time=result_data.get('processing_time', 0.0)
                )
                
        except httpx.TimeoutException:
            error_msg = f"Timeout extracting URL: {url}"
            logger.warning(error_msg)
            return ProcessingResult(url=url, success=False, error=error_msg)
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} extracting URL: {url}"
            logger.error(error_msg)
            return ProcessingResult(url=url, success=False, error=error_msg)
            
        except Exception as e:
            error_msg = f"Error extracting URL {url}: {str(e)}"
            logger.error(error_msg)
            return ProcessingResult(url=url, success=False, error=error_msg)
    
    async def extract_batch_urls(self, url_batch: URLBatch) -> List[ProcessingResult]:
        """Extract content from batch of URLs"""
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                # Prepare batch request
                request_data = {
                    'urls': url_batch.urls,
                    'domain_id': url_batch.domain_id,
                    'batch_id': url_batch.batch_id or f"batch_{int(datetime.now().timestamp())}",
                    'extract_images': True,
                    'extract_links': False,  # Reduce payload size for batch
                    'clean_html': True
                }
                
                response = await client.post(
                    f"{self.base_url}/extract/batch",
                    json=request_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=httpx.Timeout(self.timeout * 2)  # Longer timeout for batch
                )
                
                response.raise_for_status()
                batch_results = response.json()
                
                # Convert results to ProcessingResult objects
                results = []
                for result_data in batch_results.get('results', []):
                    result = ProcessingResult(
                        url=result_data.get('url'),
                        success=result_data.get('success', False),
                        extracted_data=result_data.get('data') if result_data.get('success') else None,
                        error=result_data.get('error'),
                        processing_time=result_data.get('processing_time', 0.0)
                    )
                    results.append(result)
                
                return results
                
        except Exception as e:
            error_msg = f"Batch extraction error: {str(e)}"
            logger.error(error_msg)
            
            # Return failed results for all URLs
            return [
                ProcessingResult(url=url, success=False, error=error_msg)
                for url in url_batch.urls
            ]
    
    async def extract_with_retries(self, url: str, domain_id: int) -> ProcessingResult:
        """Extract URL with automatic retry on failure"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await self.extract_single_url(url, domain_id)
                
                if result.success:
                    if attempt > 0:
                        logger.info(f"URL {url} succeeded on attempt {attempt + 1}")
                    return result
                else:
                    last_error = result.error
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1} failed for URL {url}: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(delay)
        
        return ProcessingResult(
            url=url,
            success=False,
            error=f"Failed after {self.max_retries + 1} attempts. Last error: {last_error}"
        )
    
    async def check_service_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Check if newspaper4k_extractor service is healthy"""
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=httpx.Timeout(5.0)
                )
                
                response.raise_for_status()
                health_data = response.json()
                
                return True, health_data
                
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return False, {'error': error_msg, 'status': 'unhealthy'}
    
    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get processing statistics from newspaper4k_extractor service"""
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/stats",
                    timeout=httpx.Timeout(10.0)
                )
                
                response.raise_for_status()
                stats_data = response.json()
                
                return stats_data
                
        except Exception as e:
            error_msg = f"Statistics retrieval failed: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}
    
    async def extract_urls_concurrent(self, urls: List[str], domain_id: int, 
                                    max_concurrent: int = 5) -> List[ProcessingResult]:
        """Extract multiple URLs with concurrency control"""
        if not urls:
            return []
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_semaphore(url: str):
            async with semaphore:
                return await self.extract_with_retries(url, domain_id)
        
        # Create tasks
        tasks = [extract_with_semaphore(url) for url in urls]
        
        # Execute with proper error handling
        results = []
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append(result)
            except Exception as e:
                logger.error(f"Concurrent extraction task failed: {e}")
                # Add a failed result for this URL
                results.append(ProcessingResult(
                    url="unknown", 
                    success=False, 
                    error=str(e)
                ))
        
        return results
    
    def create_url_batch(self, urls: List[str], domain_id: int, 
                        priority: int = 1, batch_size: int = 10) -> List[URLBatch]:
        """Create URL batches for efficient processing"""
        if not urls:
            return []
        
        batches = []
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            batch = URLBatch(
                domain_id=domain_id,
                urls=batch_urls,
                priority=priority,
                batch_id=f"batch_{domain_id}_{int(datetime.now().timestamp())}_{i}"
            )
            batches.append(batch)
        
        return batches
    
    async def process_url_batches(self, batches: List[URLBatch]) -> Dict[str, List[ProcessingResult]]:
        """Process multiple URL batches"""
        results = {}
        
        # Sort batches by priority
        sorted_batches = sorted(batches, key=lambda b: b.priority)
        
        for batch in sorted_batches:
            try:
                logger.info(f"Processing batch {batch.batch_id} with {len(batch.urls)} URLs")
                
                batch_results = await self.extract_batch_urls(batch)
                results[batch.batch_id] = batch_results
                
                # Log results summary
                successful = sum(1 for r in batch_results if r.success)
                failed = len(batch_results) - successful
                logger.info(f"Batch {batch.batch_id}: {successful} successful, {failed} failed")
                
                # Small delay between batches
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Batch processing error for {batch.batch_id}: {e}")
                results[batch.batch_id] = [
                    ProcessingResult(url=url, success=False, error=str(e))
                    for url in batch.urls
                ]
        
        return results