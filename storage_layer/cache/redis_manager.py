"""
High-performance Redis caching manager
Target: >80% cache hit rate, <10ms response time
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
import pickle
import hashlib
from dataclasses import asdict, is_dataclass

logger = logging.getLogger(__name__)

class RedisManager:
    """High-performance Redis caching with smart strategies"""
    
    def __init__(
        self, 
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 100
    ):
        self.connection_pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            decode_responses=False  # Handle encoding manually for flexibility
        )
        self.redis_client = redis.Redis(connection_pool=self.connection_pool)
        
        # Cache configuration
        self.default_ttl = 3600  # 1 hour
        self.key_prefix = "crawler:"
        
        # Performance metrics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'errors': 0
        }
    
    async def get_article(self, url_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached article by URL hash"""
        try:
            key = f"{self.key_prefix}article:{url_hash}"
            cached_data = await self.redis_client.get(key)
            
            if cached_data:
                self.stats['hits'] += 1
                # Try JSON first, fallback to pickle
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    return pickle.loads(cached_data)
            else:
                self.stats['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error getting article from cache: {e}")
            self.stats['errors'] += 1
            return None
    
    async def cache_article(self, article_data: Union[Dict, Any], ttl: Optional[int] = None) -> bool:
        """Cache single article with automatic serialization"""
        try:
            # Extract URL hash for key
            if isinstance(article_data, dict):
                url_hash = article_data.get('url_hash')
                data_to_cache = article_data
            elif hasattr(article_data, 'url_hash'):
                url_hash = article_data.url_hash
                # Convert dataclass/model to dict
                if is_dataclass(article_data):
                    data_to_cache = asdict(article_data)
                elif hasattr(article_data, 'to_dict'):
                    data_to_cache = article_data.to_dict()
                else:
                    data_to_cache = article_data.__dict__
            else:
                logger.warning(f"Cannot extract url_hash from article data: {type(article_data)}")
                return False
            
            if not url_hash:
                logger.warning("No url_hash found in article data")
                return False
            
            key = f"{self.key_prefix}article:{url_hash}"
            
            # Serialize data
            try:
                # Try JSON first (faster)
                serialized_data = json.dumps(data_to_cache, default=str)
            except (TypeError, ValueError):
                # Fallback to pickle for complex objects
                serialized_data = pickle.dumps(data_to_cache)
            
            # Set with TTL
            cache_ttl = ttl or self.default_ttl
            await self.redis_client.setex(key, cache_ttl, serialized_data)
            
            self.stats['sets'] += 1
            logger.debug(f"Cached article {url_hash} with TTL {cache_ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Error caching article: {e}")
            self.stats['errors'] += 1
            return False
    
    async def cache_recent_articles(self, articles: List[Any], ttl: int = 7200) -> int:
        """Cache multiple recent articles for instant access"""
        if not articles:
            return 0
        
        successful_caches = 0
        
        # Use pipeline for better performance
        pipeline = self.redis_client.pipeline()
        
        try:
            for article in articles:
                # Prepare article data
                if isinstance(article, dict):
                    url_hash = article.get('url_hash')
                    data_to_cache = article
                elif hasattr(article, 'url_hash'):
                    url_hash = article.url_hash
                    if is_dataclass(article):
                        data_to_cache = asdict(article)
                    elif hasattr(article, 'to_dict'):
                        data_to_cache = article.to_dict()
                    else:
                        data_to_cache = article.__dict__
                else:
                    continue
                
                if not url_hash:
                    continue
                
                key = f"{self.key_prefix}article:{url_hash}"
                
                # Serialize
                try:
                    serialized_data = json.dumps(data_to_cache, default=str)
                except (TypeError, ValueError):
                    serialized_data = pickle.dumps(data_to_cache)
                
                # Add to pipeline
                pipeline.setex(key, ttl, serialized_data)
                successful_caches += 1
            
            # Execute pipeline
            await pipeline.execute()
            
            self.stats['sets'] += successful_caches
            logger.info(f"Cached {successful_caches} recent articles")
            
        except Exception as e:
            logger.error(f"Error in bulk caching: {e}")
            self.stats['errors'] += 1
        
        return successful_caches
    
    async def cache_query_result(self, query_key: str, result_data: Any, ttl: int = 600) -> bool:
        """Cache database query results"""
        try:
            key = f"{self.key_prefix}query:{query_key}"
            
            # Serialize result
            try:
                serialized_data = json.dumps(result_data, default=str)
            except (TypeError, ValueError):
                serialized_data = pickle.dumps(result_data)
            
            await self.redis_client.setex(key, ttl, serialized_data)
            
            self.stats['sets'] += 1
            logger.debug(f"Cached query result: {query_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching query result: {e}")
            self.stats['errors'] += 1
            return False
    
    async def get_cached_query(self, query_key: str) -> Optional[Any]:
        """Get cached query result"""
        try:
            key = f"{self.key_prefix}query:{query_key}"
            cached_data = await self.redis_client.get(key)
            
            if cached_data:
                self.stats['hits'] += 1
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    return pickle.loads(cached_data)
            else:
                self.stats['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error getting cached query: {e}")
            self.stats['errors'] += 1
            return None
    
    async def cache_link_batch(self, links: List[Dict], ttl: int = 1800) -> int:
        """Cache discovered links for duplicate detection"""
        if not links:
            return 0
        
        pipeline = self.redis_client.pipeline()
        cached_count = 0
        
        try:
            for link in links:
                url_hash = link.get('url_hash')
                if not url_hash:
                    continue
                
                key = f"{self.key_prefix}link:{url_hash}"
                link_data = json.dumps(link, default=str)
                
                pipeline.setex(key, ttl, link_data)
                cached_count += 1
            
            await pipeline.execute()
            self.stats['sets'] += cached_count
            logger.debug(f"Cached {cached_count} links")
            
        except Exception as e:
            logger.error(f"Error caching links: {e}")
            self.stats['errors'] += 1
        
        return cached_count
    
    async def check_link_exists(self, url_hash: str) -> bool:
        """Check if link already exists in cache"""
        try:
            key = f"{self.key_prefix}link:{url_hash}"
            exists = await self.redis_client.exists(key)
            
            if exists:
                self.stats['hits'] += 1
            else:
                self.stats['misses'] += 1
                
            return bool(exists)
            
        except Exception as e:
            logger.error(f"Error checking link existence: {e}")
            self.stats['errors'] += 1
            return False
    
    async def invalidate_article(self, url_hash: str) -> bool:
        """Remove article from cache"""
        try:
            key = f"{self.key_prefix}article:{url_hash}"
            deleted = await self.redis_client.delete(key)
            return bool(deleted)
            
        except Exception as e:
            logger.error(f"Error invalidating article: {e}")
            return False
    
    async def flush_cache(self, pattern: str = None) -> int:
        """Flush cache entries matching pattern"""
        try:
            if pattern:
                pattern_key = f"{self.key_prefix}{pattern}"
                keys = await self.redis_client.keys(pattern_key)
                if keys:
                    deleted = await self.redis_client.delete(*keys)
                    logger.info(f"Deleted {deleted} cache entries matching {pattern}")
                    return deleted
            else:
                # Flush entire database
                await self.redis_client.flushdb()
                logger.info("Flushed entire cache database")
                return -1  # Unknown count
            
        except Exception as e:
            logger.error(f"Error flushing cache: {e}")
            return 0
        
        return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            # Redis info
            redis_info = await self.redis_client.info('memory')
            
            # Calculate hit rate
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'hit_rate_percent': round(hit_rate, 2),
                'total_hits': self.stats['hits'],
                'total_misses': self.stats['misses'],
                'total_sets': self.stats['sets'],
                'total_errors': self.stats['errors'],
                'memory_used_mb': redis_info.get('used_memory', 0) / 1024 / 1024,
                'total_keys': await self.redis_client.dbsize(),
                'redis_version': redis_info.get('redis_version', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return self.stats
    
    async def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def close(self):
        """Close Redis connection"""
        try:
            await self.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
    
    def generate_query_key(self, query_type: str, **params) -> str:
        """Generate consistent cache key for queries"""
        # Create a hash of the parameters for consistent keys
        param_str = json.dumps(params, sort_keys=True, default=str)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"{query_type}:{param_hash}"