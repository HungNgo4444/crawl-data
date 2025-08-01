"""
High-performance article repository with smart caching
Target: <100ms for cached queries, 1000 articles/second bulk insert
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert, update, delete, func, and_, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..database.models_v2 import Article, ArticleContent, LinkQueue
from ..cache.redis_manager import RedisManager
from ..object_storage.minio_manager import MinIOManager

logger = logging.getLogger(__name__)

class ArticleRepository:
    """High-performance data access with smart caching and tiered storage"""
    
    def __init__(
        self,
        database_url: str,
        redis_manager: RedisManager,
        minio_manager: MinIOManager
    ):
        # Database setup
        self.engine = create_async_engine(
            database_url,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            echo=False  # Set to True for SQL debugging
        )
        
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Storage managers
        self.redis_manager = redis_manager
        self.minio_manager = minio_manager
        
        # Performance tracking
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'db_queries': 0,
            'bulk_inserts': 0,
            'minio_retrievals': 0
        }
    
    async def get_article_by_url_hash(self, url_hash: str, include_content: bool = False) -> Optional[Article]:
        """
        Smart retrieval with caching:
        1. Try Redis cache first (fastest)
        2. Try PostgreSQL (fast)
        3. Retrieve full content from MinIO if needed
        """
        try:
            # Step 1: Try cache first
            cached_article = await self.redis_manager.get_article(url_hash)
            if cached_article:
                self.stats['cache_hits'] += 1
                logger.debug(f"Cache hit for article {url_hash}")
                
                article = Article.from_dict(cached_article)
                
                # If full content is requested and not in cache, get from MinIO
                if include_content and not hasattr(article, 'full_content'):
                    await self._load_full_content(article)
                
                return article
            
            # Step 2: Try database
            self.stats['cache_misses'] += 1
            async with self.async_session() as session:
                self.stats['db_queries'] += 1
                
                query = select(Article).where(Article.url_hash == url_hash)
                result = await session.execute(query)
                article = result.scalar_one_or_none()
                
                if article:
                    # Cache for next time
                    await self.redis_manager.cache_article(article)
                    
                    # Load full content if requested
                    if include_content:
                        await self._load_full_content(article)
                    
                    logger.debug(f"Database hit for article {url_hash}")
                    return article
            
            # Not found
            logger.debug(f"Article not found: {url_hash}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving article {url_hash}: {e}")
            return None
    
    async def get_articles_by_source(
        self, 
        source: str, 
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Article]:
        """Get articles by source with optional date filtering"""
        try:
            # Generate cache key for this query
            cache_key = self.redis_manager.generate_query_key(
                'articles_by_source',
                source=source,
                limit=limit,
                offset=offset,
                start_date=start_date.isoformat() if start_date else None,
                end_date=end_date.isoformat() if end_date else None
            )
            
            # Try cache first
            cached_result = await self.redis_manager.get_cached_query(cache_key)
            if cached_result:
                self.stats['cache_hits'] += 1
                return [Article.from_dict(article_data) for article_data in cached_result]
            
            # Query database 
            async with self.async_session() as session:
                self.stats['db_queries'] += 1
                
                query = select(Article).where(Article.source == source)
                
                # Add date filters if provided
                if start_date:
                    query = query.where(Article.published_at >= start_date)
                if end_date:
                    query = query.where(Article.published_at <= end_date)
                
                # Order by published date (newest first)
                query = query.order_by(Article.published_at.desc())
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                articles = result.scalars().all()
                
                # Cache result
                if articles:
                    article_dicts = [article.to_dict() for article in articles]
                    await self.redis_manager.cache_query_result(cache_key, article_dicts, ttl=600)
                
                self.stats['cache_misses'] += 1
                return list(articles)
                
        except Exception as e:
            logger.error(f"Error getting articles by source {source}: {e}")
            return []
    
    async def bulk_insert_articles(self, articles_data: List[Dict[str, Any]]) -> int:
        """
        High-performance bulk insert with deduplication
        Target: 1000 articles/second
        """
        if not articles_data:
            return 0
        
        try:
            # Step 1: Extract URL hashes for deduplication check
            url_hashes = [article.get('url_hash') for article in articles_data if article.get('url_hash')]
            
            if not url_hashes:
                logger.warning("No valid URL hashes in articles data")
                return 0
            
            # Step 2: Check existing articles
            existing_hashes = await self._get_existing_url_hashes(url_hashes)
            
            # Step 3: Filter out duplicates
            new_articles = [
                article for article in articles_data 
                if article.get('url_hash') not in existing_hashes
            ]
            
            if not new_articles:
                logger.info("No new articles to insert (all duplicates)")
                return 0
            
            inserted_count = 0
            
            # Step 4: Bulk insert to PostgreSQL
            async with self.async_session() as session:
                try:
                    # Prepare articles for database insert
                    db_articles = []
                    content_articles = []
                    minio_tasks = []
                    
                    for article_data in new_articles:
                        # Separate content for MinIO storage
                        full_content = article_data.pop('full_content', '')
                        raw_html = article_data.pop('raw_html', '')
                        
                        # Create Article record
                        article_record = article_data.copy()
                        article_record['created_at'] = datetime.utcnow()
                        
                        if not article_record.get('published_at'):
                            article_record['published_at'] = datetime.utcnow()
                        
                        db_articles.append(article_record)
                        
                        # Prepare MinIO storage task if content exists
                        if full_content or raw_html:
                            article_id = article_record['id']
                            minio_task = self.minio_manager.store_article_content(
                                str(article_id), full_content, raw_html
                            )
                            minio_tasks.append((article_id, minio_task))
                    
                    # Bulk insert articles
                    if db_articles:
                        stmt = pg_insert(Article).values(db_articles)
                        stmt = stmt.on_conflict_do_nothing(index_elements=['url_hash'])
                        await session.execute(stmt)
                        
                        inserted_count = len(db_articles)
                        self.stats['bulk_inserts'] += 1
                    
                    # Commit database transaction
                    await session.commit()
                    
                    # Store content in MinIO concurrently (after DB commit)
                    if minio_tasks:
                        minio_results = await asyncio.gather(
                            *[task for _, task in minio_tasks], 
                            return_exceptions=True
                        )
                        
                        # Update articles with MinIO keys
                        updates = []
                        for i, (article_id, _) in enumerate(minio_tasks):
                            if i < len(minio_results) and not isinstance(minio_results[i], Exception):
                                content_key, html_key = minio_results[i]
                                if content_key and html_key:
                                    updates.append({
                                        'id': article_id,
                                        'full_content_key': content_key,
                                        'raw_html_key': html_key,
                                        'processing_status': 'completed'
                                    })
                        
                        # Update with MinIO keys
                        if updates:
                            async with self.async_session() as update_session:
                                for update_data in updates:
                                    stmt = update(Article).where(
                                        Article.id == update_data['id']
                                    ).values({
                                        'full_content_key': update_data['full_content_key'],
                                        'raw_html_key': update_data['raw_html_key'],
                                        'processing_status': update_data['processing_status']
                                    })
                                    await update_session.execute(stmt)
                                
                                await update_session.commit()
                    
                    # Cache recent articles
                    if inserted_count > 0:
                        recent_articles = db_articles[-100:]  # Cache last 100
                        await self.redis_manager.cache_recent_articles(recent_articles)
                    
                    logger.info(f"Bulk inserted {inserted_count} articles")
                    return inserted_count
                    
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Database error in bulk insert: {e}")
                    return 0
                    
        except Exception as e:
            logger.error(f"Error in bulk insert: {e}")
            return 0
    
    async def update_article_status(self, url_hash: str, status: str, metadata: Optional[Dict] = None) -> bool:
        """Update article processing status"""
        try:
            async with self.async_session() as session:
                update_data = {'processing_status': status}
                if metadata:
                    update_data['extraction_metadata'] = metadata
                
                stmt = update(Article).where(
                    Article.url_hash == url_hash
                ).values(update_data)
                
                result = await session.execute(stmt)
                await session.commit()
                
                # Invalidate cache
                await self.redis_manager.invalidate_article(url_hash)
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating article status: {e}")
            return False
    
    async def get_articles_for_processing(self, limit: int = 100) -> List[Article]:
        """Get articles that need processing"""
        try:
            async with self.async_session() as session:
                query = select(Article).where(
                    Article.processing_status == 'pending'
                ).order_by(Article.created_at.desc()).limit(limit)
                
                result = await session.execute(query)
                articles = result.scalars().all()
                
                self.stats['db_queries'] += 1
                return list(articles)
                
        except Exception as e:
            logger.error(f"Error getting articles for processing: {e}")
            return []
    
    async def get_quality_stats(self, source: Optional[str] = None) -> Dict[str, Any]:
        """Get article quality statistics"""
        try:
            async with self.async_session() as session:
                query = select(
                    func.count(Article.id).label('total_articles'),
                    func.avg(Article.quality_score).label('avg_quality'),
                    func.avg(Article.word_count).label('avg_word_count'),
                    func.count().filter(Article.quality_score >= 7.0).label('high_quality'),
                    func.count().filter(Article.processing_status == 'completed').label('completed')
                )
                
                if source:
                    query = query.where(Article.source == source)
                
                result = await session.execute(query)
                stats = result.first()
                
                return {
                    'total_articles': stats.total_articles or 0,
                    'avg_quality_score': float(stats.avg_quality or 0),
                    'avg_word_count': int(stats.avg_word_count or 0),
                    'high_quality_count': stats.high_quality or 0,
                    'completed_count': stats.completed or 0,
                    'source': source
                }
                
        except Exception as e:
            logger.error(f"Error getting quality stats: {e}")
            return {}
    
    async def _get_existing_url_hashes(self, url_hashes: List[str]) -> set:
        """Get existing URL hashes from database"""
        try:
            async with self.async_session() as session:
                query = select(Article.url_hash).where(
                    Article.url_hash.in_(url_hashes)
                )
                result = await session.execute(query)
                existing = result.scalars().all()
                
                return set(existing)
                
        except Exception as e:
            logger.error(f"Error checking existing URL hashes: {e}")
            return set()
    
    async def _load_full_content(self, article: Article):
        """Load full content from MinIO if available"""
        try:
            if article.full_content_key:
                self.stats['minio_retrievals'] += 1
                full_content = await self.minio_manager.retrieve_article_content(
                    article.full_content_key
                )
                if full_content:
                    article.full_content = full_content
                    
        except Exception as e:
            logger.error(f"Error loading full content for article {article.id}: {e}")
    
    async def get_repository_stats(self) -> Dict[str, Any]:
        """Get repository performance statistics"""
        try:
            cache_stats = await self.redis_manager.get_cache_stats()
            minio_stats = await self.minio_manager.get_storage_stats()
            
            return {
                'performance_stats': self.stats,
                'cache_stats': cache_stats,
                'storage_stats': minio_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting repository stats: {e}")
            return self.stats
    
    async def cleanup_old_articles(self, days_old: int = 365) -> int:
        """Clean up old articles (data retention)"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            async with self.async_session() as session:
                # Get articles to delete
                query = select(Article).where(Article.created_at < cutoff_date)
                result = await session.execute(query)
                old_articles = result.scalars().all()
                
                deleted_count = 0
                for article in old_articles:
                    # Delete from MinIO first
                    if article.full_content_key and article.raw_html_key:
                        await self.minio_manager.delete_article_content(
                            article.full_content_key,
                            article.raw_html_key
                        )
                    
                    # Delete from cache
                    await self.redis_manager.invalidate_article(article.url_hash)
                    
                    deleted_count += 1
                
                # Delete from database
                if old_articles:
                    stmt = delete(Article).where(Article.created_at < cutoff_date)
                    await session.execute(stmt)
                    await session.commit()
                
                logger.info(f"Cleaned up {deleted_count} old articles")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old articles: {e}")
            return 0