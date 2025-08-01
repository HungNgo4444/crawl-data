import logging
import asyncio
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from aiohttp import ClientSession

from storage_layer.database.database_manager import get_db_session
from storage_layer.database.models import Article, CrawlerSession, CrawlerStrategyStats
from config.settings import settings

logger = logging.getLogger(__name__)

class CrawlerResult:
    """Container for crawler results with metadata."""
    
    def __init__(self):
        self.articles: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, Any] = {}
    
    def add_article(self, article_data: Dict[str, Any]):
        """Add an article to the results."""
        self.articles.append(article_data)
    
    def add_error(self, error_message: str):
        """Add an error to the results."""
        self.errors.append(error_message)
        logger.error(f"Crawler error: {error_message}")
    
    def set_metadata(self, key: str, value: Any):
        """Set metadata for the crawl session."""
        self.metadata[key] = value
    
    def set_performance_metric(self, key: str, value: Any):
        """Set performance metric for the crawl session."""
        self.performance_metrics[key] = value

class BaseCrawler(ABC):
    """
    Enhanced Base Class for all crawlers with automatic storage and monitoring.

    This class provides:
    - Automatic database storage with deduplication
    - Performance monitoring and statistics
    - Error handling and retry mechanisms
    - Session tracking for debugging
    - Integration with multiple crawling strategies
    """

    # Plugin metadata (must be defined by subclasses)
    PLUGIN_NAME: str = "base"
    VERSION: str = "1.0.0"
    AUTHOR: str = "Unknown"
    SUPPORTED_SOURCES: List[str] = []
    CAPABILITIES: List[str] = []

    def __init__(self, source_name: str, config: Dict[str, Any]):
        """
        Initialize the crawler with source configuration.
        
        Args:
            source_name: Unique identifier for the news source
            config: Configuration dictionary from news_sources.yaml
        """
        self.source_name = source_name
        self.config = config
        self.session_id: Optional[str] = None
        self.start_time: Optional[float] = None
        
        # Configuration with defaults
        self.max_retries = config.get('max_retries', 3)
        self.rate_limit = config.get('rate_limit', 10)  # requests per minute
        self.timeout = config.get('timeout', 30)
        self.delay_between_requests = config.get('delay_between_requests', 1.0)
        
        # Quality control
        self.min_content_length = config.get('min_content_length', 100)
        self.max_content_length = config.get('max_content_length', 50000)
        
        # Storage settings
        self.auto_save = config.get('auto_save', True)
        self.check_duplicates = config.get('check_duplicates', True)
        
        logger.info(f"Initialized {self.PLUGIN_NAME} crawler for source: {source_name}")

    async def crawl(self, session: Optional[ClientSession] = None) -> CrawlerResult:
        """
        Main crawl method that orchestrates the entire process.
        
        Args:
            session: Optional aiohttp session for HTTP requests
            
        Returns:
            CrawlerResult containing articles, errors, and metadata
        """
        self.start_time = time.time()
        result = CrawlerResult()
        
        # Create crawler session for tracking
        crawler_session = await self._create_session()
        self.session_id = str(crawler_session.id)
        
        try:
            logger.info(f"Starting crawl for {self.source_name} using {self.PLUGIN_NAME}")
            
            # Fetch raw articles
            raw_articles = await self.fetch_articles(session)
            result.set_metadata('raw_articles_count', len(raw_articles))
            
            if not raw_articles:
                result.add_error("No articles found")
                await self._update_session(crawler_session, result, success=False)
                return result
            
            # Process each article
            processed_articles = []
            for raw_article in raw_articles:
                try:
                    processed_article = await self._process_article(raw_article, session)
                    if processed_article:
                        processed_articles.append(processed_article)
                        result.add_article(processed_article)
                except Exception as e:
                    result.add_error(f"Error processing article: {str(e)}")
                    continue
                
                # Rate limiting
                await asyncio.sleep(self.delay_between_requests)
            
            # Save articles to database
            if self.auto_save and processed_articles:
                saved_count, duplicate_count = await self._save_articles(processed_articles)
                result.set_metadata('saved_articles', saved_count)
                result.set_metadata('duplicate_articles', duplicate_count)
                
                # Update session with results
                crawler_session.articles_found = len(raw_articles)
                crawler_session.articles_saved = saved_count
                crawler_session.articles_duplicated = duplicate_count
            
            # Update performance metrics
            duration = time.time() - self.start_time
            result.set_performance_metric('duration', duration)
            result.set_performance_metric('articles_per_second', len(processed_articles) / duration if duration > 0 else 0)
            
            await self._update_session(crawler_session, result, success=True)
            await self._update_strategy_stats(success=True, duration=duration, articles_count=len(processed_articles))
            
            logger.info(f"Crawl completed for {self.source_name}: {len(processed_articles)} articles processed")
            
        except Exception as e:
            error_msg = f"Crawl failed for {self.source_name}: {str(e)}"
            result.add_error(error_msg)
            logger.error(error_msg, exc_info=True)
            
            await self._update_session(crawler_session, result, success=False, error_message=str(e))
            await self._update_strategy_stats(success=False, duration=time.time() - self.start_time, error_message=str(e))
        
        return result

    @abstractmethod
    async def fetch_articles(self, session: Optional[ClientSession]) -> List[Dict[str, Any]]:
        """
        Fetch raw article data from the source.
        
        This method must be implemented by each specific crawler.
        
        Args:
            session: Optional aiohttp session for HTTP requests
            
        Returns:
            List of dictionaries containing raw article data
        """
        pass

    async def _process_article(self, raw_article: Dict[str, Any], session: Optional[ClientSession]) -> Optional[Dict[str, Any]]:
        """
        Process a single raw article into standardized format.
        
        Args:
            raw_article: Raw article data from fetch_articles
            session: Optional aiohttp session
            
        Returns:
            Processed article dictionary or None if processing failed
        """
        try:
            # Validate required fields
            if not raw_article.get('url'):
                logger.warning("Article missing URL, skipping")
                return None
            
            # Standard article structure
            processed = {
                'source': self.source_name,
                'url': raw_article['url'],
                'title': raw_article.get('title', '').strip(),
                'content': raw_article.get('content', '').strip(),
                'author': raw_article.get('author', '').strip(),
                'published_at': self._parse_date(raw_article.get('published_at')),
                'language': raw_article.get('language', 'vi'),
                'category': raw_article.get('category'),
                'tags': raw_article.get('tags', []),
                'meta_description': raw_article.get('meta_description'),
                'meta_keywords': raw_article.get('meta_keywords', []),
                'images': raw_article.get('images', []),
                'crawler_strategy': self.PLUGIN_NAME
            }
            
            # Quality checks
            content = processed['content']
            if len(content) < self.min_content_length:
                logger.warning(f"Article content too short ({len(content)} chars), skipping")
                return None
            
            if len(content) > self.max_content_length:
                logger.warning(f"Article content too long ({len(content)} chars), truncating")
                processed['content'] = content[:self.max_content_length]
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None

    async def _save_articles(self, articles: List[Dict[str, Any]]) -> tuple[int, int]:
        """
        Save articles to database with deduplication.
        
        Args:
            articles: List of processed articles
            
        Returns:
            Tuple of (saved_count, duplicate_count)
        """
        saved_count = 0
        duplicate_count = 0
        
        try:
            with get_db_session() as db:
                for article_data in articles:
                    try:
                        # Check for duplicates if enabled
                        if self.check_duplicates:
                            url_hash = Article._generate_url_hash(article_data['url'])
                            existing = db.query(Article).filter(Article.url_hash == url_hash).first()
                            
                            if existing:
                                duplicate_count += 1
                                logger.debug(f"Duplicate article found: {article_data['url']}")
                                continue
                        
                        # Create new article
                        article = Article(**article_data)
                        db.add(article)
                        saved_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error saving individual article: {e}")
                        continue
                
                db.commit()
                logger.info(f"Saved {saved_count} articles, {duplicate_count} duplicates found")
                
        except Exception as e:
            logger.error(f"Error saving articles to database: {e}")
            raise
        
        return saved_count, duplicate_count

    async def _create_session(self) -> CrawlerSession:
        """Create a new crawler session for tracking."""
        try:
            with get_db_session() as db:
                session = CrawlerSession(
                    source_name=self.source_name,
                    strategy_used=self.PLUGIN_NAME,
                    config_snapshot=self.config
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                return session
        except Exception as e:
            logger.error(f"Error creating crawler session: {e}")
            raise

    async def _update_session(self, session: CrawlerSession, result: CrawlerResult, 
                            success: bool, error_message: Optional[str] = None):
        """Update crawler session with final results."""
        try:
            with get_db_session() as db:
                # Refresh session from database
                db_session = db.query(CrawlerSession).filter(CrawlerSession.id == session.id).first()
                if db_session:
                    db_session.mark_completed(success=success, error_message=error_message)
                    if hasattr(result, 'errors') and result.errors:
                        db_session.articles_failed = len(result.errors)
                    db.commit()
        except Exception as e:
            logger.error(f"Error updating crawler session: {e}")

    async def _update_strategy_stats(self, success: bool, duration: float, 
                                   articles_count: int = 0, error_message: Optional[str] = None):
        """Update strategy statistics for performance tracking."""
        try:
            with get_db_session() as db:
                stats = db.query(CrawlerStrategyStats).filter(
                    CrawlerStrategyStats.source_name == self.source_name,
                    CrawlerStrategyStats.strategy_name == self.PLUGIN_NAME
                ).first()
                
                if not stats:
                    stats = CrawlerStrategyStats(
                        source_name=self.source_name,
                        strategy_name=self.PLUGIN_NAME
                    )
                    db.add(stats)
                
                stats.record_attempt(success, duration, articles_count, error_message)
                db.commit()
                
        except Exception as e:
            logger.error(f"Error updating strategy stats: {e}")

    def _parse_date(self, date_input: Any) -> Optional[datetime]:
        """Parse various date formats into datetime object."""
        if not date_input:
            return None
        
        if isinstance(date_input, datetime):
            return date_input
        
        if isinstance(date_input, str):
            try:
                # Try common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                    try:
                        return datetime.strptime(date_input, fmt)
                    except ValueError:
                        continue
                
                # Use dateparser for more complex formats
                try:
                    import dateparser
                    return dateparser.parse(date_input)
                except ImportError:
                    logger.warning("dateparser not available for complex date parsing")
                    
            except Exception as e:
                logger.warning(f"Could not parse date: {date_input} - {e}")
        
        return None

    def __repr__(self):
        return f"<{self.__class__.__name__}(source='{self.source_name}', plugin='{self.PLUGIN_NAME}')>" 