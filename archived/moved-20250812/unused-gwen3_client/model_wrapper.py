"""
GWEN-3 Model Wrapper
High-level interface for Vietnamese content analysis with caching and optimization
Author: James (Dev Agent)
Date: 2025-08-11
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

from .ollama_client import OllamaGWEN3Client, AnalysisResult
from .config import config

@dataclass
class CachedAnalysis:
    """Cached analysis result with expiration"""
    result: AnalysisResult
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = None
    
    def is_expired(self) -> bool:
        """Check if cached result has expired"""
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if cached result is still valid"""
        return not self.is_expired() and self.result.confidence_score >= config.analysis.min_confidence_score

class GWEN3ModelWrapper:
    """
    High-level wrapper for GWEN-3 model with caching, batching, and optimization
    """
    
    def __init__(self, cache_ttl_hours: int = 24, max_cache_size: int = 1000):
        """
        Initialize model wrapper
        
        Args:
            cache_ttl_hours: How long to cache analysis results (hours)
            max_cache_size: Maximum number of cached results
        """
        self.client = OllamaGWEN3Client()
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.max_cache_size = max_cache_size
        
        # Analysis cache
        self._analysis_cache: Dict[str, CachedAnalysis] = {}
        self._cache_lock = asyncio.Lock()
        
        # Batch processing
        self._batch_queue: List[Tuple[str, str, asyncio.Future]] = []
        self._batch_lock = asyncio.Lock()
        self._batch_processor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._stats = {
            "total_analyses": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "batch_processed": 0,
            "errors": 0
        }
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("GWEN-3 model wrapper initialized")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.client.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._batch_processor_task:
            self._batch_processor_task.cancel()
            try:
                await self._batch_processor_task
            except asyncio.CancelledError:
                pass
        
        await self.client.disconnect()
    
    def _generate_cache_key(self, domain_name: str, content_hash: str) -> str:
        """Generate cache key for analysis result"""
        return f"{domain_name}_{content_hash[:16]}"
    
    def _hash_content(self, content: str) -> str:
        """Generate hash for content to use as cache key"""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def analyze_domain(self, domain_name: str, content: str, 
                           sample_urls: Optional[List[str]] = None,
                           use_cache: bool = True, 
                           force_refresh: bool = False) -> AnalysisResult:
        """
        Analyze domain with caching support
        
        Args:
            domain_name: Domain to analyze
            content: HTML content for analysis
            sample_urls: Optional sample URLs for context
            use_cache: Whether to use cached results
            force_refresh: Force refresh cached result
            
        Returns:
            AnalysisResult with parsing template
        """
        start_time = time.time()
        content_hash = self._hash_content(content)
        cache_key = self._generate_cache_key(domain_name, content_hash)
        
        try:
            # Check cache first (if enabled)
            if use_cache and not force_refresh:
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    self._stats["cache_hits"] += 1
                    duration = time.time() - start_time
                    self.logger.info(f"Cache hit for {domain_name} (retrieved in {duration:.3f}s)")
                    return cached_result.result
            
            self._stats["cache_misses"] += 1
            
            # Perform analysis
            self.logger.info(f"Performing fresh analysis for {domain_name}")
            result = await self.client.analyze_domain_structure(domain_name, content, sample_urls)
            
            # Cache result if successful
            if use_cache and result.confidence_score >= config.analysis.min_confidence_score:
                await self._cache_result(cache_key, result)
            
            self._stats["total_analyses"] += 1
            duration = time.time() - start_time
            self.logger.info(f"Analysis completed for {domain_name} in {duration:.2f}s (confidence: {result.confidence_score:.2f})")
            
            return result
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"Analysis failed for {domain_name}: {e}")
            raise
    
    async def analyze_batch(self, analyses: List[Tuple[str, str]], 
                          batch_size: int = 3) -> List[AnalysisResult]:
        """
        Analyze multiple domains in batches for better performance
        
        Args:
            analyses: List of (domain_name, content) tuples
            batch_size: Number of concurrent analyses
            
        Returns:
            List of AnalysisResult objects
        """
        self.logger.info(f"Starting batch analysis of {len(analyses)} domains")
        results = []
        
        # Process in batches to manage resource usage
        for i in range(0, len(analyses), batch_size):
            batch = analyses[i:i + batch_size]
            
            # Create coroutines for this batch
            batch_coroutines = [
                self.analyze_domain(domain, content)
                for domain, content in batch
            ]
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(*batch_coroutines, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    domain_name = batch[j][0]
                    self.logger.error(f"Batch analysis failed for {domain_name}: {result}")
                    
                    # Create error result
                    error_result = AnalysisResult(
                        domain_name=domain_name,
                        analysis_id=f"batch_error_{int(time.time())}",
                        timestamp=datetime.now(),
                        analysis_duration_seconds=0.0,
                        model_name=config.ollama.model_name,
                        model_version=None,
                        confidence_score=0.0,
                        language_detected="unknown",
                        parsing_template={},
                        structure_hash="",
                        headline_selectors=[],
                        content_selectors=[],
                        metadata_selectors={},
                        navigation_patterns=[],
                        extraction_accuracy=0.0,
                        template_complexity=0,
                        errors=[str(result)],
                        warnings=[]
                    )
                    results.append(error_result)
                else:
                    results.append(result)
            
            self._stats["batch_processed"] += len(batch)
            
            # Small delay between batches to prevent overwhelming the model
            if i + batch_size < len(analyses):
                await asyncio.sleep(1)
        
        success_count = sum(1 for r in results if r.confidence_score > 0)
        self.logger.info(f"Batch analysis completed: {success_count}/{len(analyses)} successful")
        
        return results
    
    async def _get_cached_result(self, cache_key: str) -> Optional[CachedAnalysis]:
        """Get cached analysis result if valid"""
        async with self._cache_lock:
            cached = self._analysis_cache.get(cache_key)
            
            if not cached:
                return None
            
            if cached.is_expired():
                # Remove expired entry
                del self._analysis_cache[cache_key]
                return None
            
            if not cached.is_valid():
                # Remove invalid entry
                del self._analysis_cache[cache_key]
                return None
            
            # Update access statistics
            cached.access_count += 1
            cached.last_accessed = datetime.now()
            
            return cached
    
    async def _cache_result(self, cache_key: str, result: AnalysisResult) -> None:
        """Cache analysis result with expiration"""
        async with self._cache_lock:
            # Clean up cache if it's getting too large
            if len(self._analysis_cache) >= self.max_cache_size:
                await self._cleanup_cache()
            
            # Create cached entry
            cached = CachedAnalysis(
                result=result,
                created_at=datetime.now(),
                expires_at=datetime.now() + self.cache_ttl,
                access_count=0,
                last_accessed=datetime.now()
            )
            
            self._analysis_cache[cache_key] = cached
            self.logger.debug(f"Cached analysis result for key: {cache_key}")
    
    async def _cleanup_cache(self) -> None:
        """Remove expired and least recently used cache entries"""
        now = datetime.now()
        
        # Remove expired entries first
        expired_keys = [
            key for key, cached in self._analysis_cache.items()
            if cached.is_expired()
        ]
        
        for key in expired_keys:
            del self._analysis_cache[key]
        
        # If still too large, remove least recently used
        if len(self._analysis_cache) >= self.max_cache_size:
            # Sort by last accessed time
            sorted_items = sorted(
                self._analysis_cache.items(),
                key=lambda x: x[1].last_accessed or x[1].created_at
            )
            
            # Remove oldest entries
            entries_to_remove = len(self._analysis_cache) - (self.max_cache_size // 2)
            for i in range(entries_to_remove):
                key = sorted_items[i][0]
                del self._analysis_cache[key]
        
        self.logger.info(f"Cache cleanup completed, {len(self._analysis_cache)} entries remaining")
    
    async def verify_model_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Verify model health and return status information"""
        try:
            # Check model availability
            is_available, availability_msg = await self.client.verify_model_availability()
            
            if not is_available:
                return False, {"error": availability_msg, "model_loaded": False}
            
            # Get model information
            model_info = await self.client.get_model_info()
            
            # Perform quick analysis test
            test_content = """
            <html>
            <head><title>Test Vietnamese News</title></head>
            <body>
                <h1 class="headline">Tin tức test</h1>
                <div class="content">Nội dung bài viết test bằng tiếng Việt.</div>
                <span class="author">Tác giả: Test Reporter</span>
                <time class="date">2025-01-01</time>
            </body>
            </html>
            """
            
            test_result = await self.analyze_domain("test.vn", test_content, use_cache=False)
            
            health_info = {
                "model_loaded": True,
                "model_name": config.ollama.model_name,
                "model_info": model_info.get("details", {}),
                "test_analysis_successful": test_result.confidence_score > 0,
                "test_confidence": test_result.confidence_score,
                "active_requests": self.client.get_active_requests_count(),
                "cache_size": len(self._analysis_cache),
                "statistics": self._stats.copy()
            }
            
            return True, health_info
            
        except Exception as e:
            return False, {"error": str(e), "model_loaded": False}
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self._stats["cache_hits"] + self._stats["cache_misses"]
        hit_rate = (self._stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self._analysis_cache),
            "max_cache_size": self.max_cache_size,
            "cache_hit_rate": hit_rate,
            "total_requests": total_requests,
            "cache_hits": self._stats["cache_hits"],
            "cache_misses": self._stats["cache_misses"]
        }
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get overall performance statistics"""
        return {
            "total_analyses": self._stats["total_analyses"],
            "batch_processed": self._stats["batch_processed"],
            "errors": self._stats["errors"],
            "cache_statistics": self.get_cache_statistics(),
            "active_requests": self.client.get_active_requests_count()
        }
    
    async def clear_cache(self) -> None:
        """Clear all cached analysis results"""
        async with self._cache_lock:
            self._analysis_cache.clear()
            self.logger.info("Analysis cache cleared")
    
    async def export_analysis_results(self, output_path: Path, 
                                    format: str = "json") -> None:
        """
        Export cached analysis results to file
        
        Args:
            output_path: Path to output file
            format: Export format ("json" or "csv")
        """
        async with self._cache_lock:
            if format.lower() == "json":
                # Export as JSON
                export_data = {
                    "export_timestamp": datetime.now().isoformat(),
                    "total_entries": len(self._analysis_cache),
                    "results": []
                }
                
                for cache_key, cached in self._analysis_cache.items():
                    if cached.is_valid():
                        result_data = cached.result.to_dict()
                        result_data["cache_info"] = {
                            "created_at": cached.created_at.isoformat(),
                            "expires_at": cached.expires_at.isoformat(),
                            "access_count": cached.access_count
                        }
                        export_data["results"].append(result_data)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
        
        self.logger.info(f"Analysis results exported to {output_path}")