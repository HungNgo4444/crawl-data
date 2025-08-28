"""
Database utility functions for URL tracking worker
"""
import psycopg2
import psycopg2.extras
from typing import Dict, Any, List, Optional
import logging
import hashlib
from urllib.parse import urljoin, urlparse
from ..config.database_config import get_database_config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.config = get_database_config()
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            # Connect to database (use environment config)
            self.connection = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'], 
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database']
            )
            self.connection.autocommit = True
            logger.info("URL tracking worker database connection established")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def get_domains_for_monitoring(self) -> List[Dict[str, Any]]:
        """Get domains that have analysis data and ready for URL monitoring"""
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, name, display_name, base_url, rss_feeds, sitemaps, 
                           homepage_urls, category_urls, css_selectors, 
                           last_analyzed_at, analysis_model
                    FROM domains 
                    WHERE status = 'ACTIVE' 
                      AND analysis_model IS NOT NULL 
                      AND (
                          jsonb_array_length(rss_feeds) > 0 OR 
                          jsonb_array_length(sitemaps) > 0 OR 
                          jsonb_array_length(homepage_urls) > 0 OR 
                          jsonb_array_length(category_urls) > 0
                      )
                    ORDER BY last_analyzed_at DESC
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching domains for monitoring: {e}")
            return []
    
    def get_domain_by_id(self, domain_id: str) -> Optional[Dict[str, Any]]:
        """Get domain by ID"""
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, name, display_name, base_url, rss_feeds, sitemaps, 
                           homepage_urls, category_urls, css_selectors,
                           last_analyzed_at, analysis_model
                    FROM domains 
                    WHERE id = %s AND status = 'ACTIVE'
                """, (domain_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error fetching domain {domain_id}: {e}")
            return None
    
    def add_url_to_tracking(self, url: str, domain_id: str, source_type: str = 'monitoring') -> bool:
        """Add URL to url_tracking table"""
        try:
            # Create URL hash for deduplication
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO url_tracking 
                    (url_hash, original_url, normalized_url, domain_id, status, metadata)
                    VALUES (%s, %s, %s, %s, 'discovered', %s)
                    ON CONFLICT (url_hash) DO UPDATE SET
                        metadata = EXCLUDED.metadata,
                        domain_id = EXCLUDED.domain_id
                """, (
                    url_hash,
                    url,
                    url,  # Store original URL as normalized_url too
                    domain_id,
                    psycopg2.extras.Json({'source_type': source_type, 'discovered_by': 'url-tracking-worker'})
                ))
                return True
        except Exception as e:
            logger.error(f"Error adding URL to tracking: {e}")
            return False
    
    def bulk_add_urls_to_tracking(self, urls: List[str], domain_id: str, source_type: str = 'monitoring') -> int:
        """Bulk add URLs to url_tracking table"""
        success_count = 0
        for url in urls:
            if self.add_url_to_tracking(url, domain_id, source_type):
                success_count += 1
        return success_count
    
    def get_existing_url_hashes(self, domain_id: str, urls: List[str]) -> set:
        """Get hashes of URLs already in database for incremental crawling"""
        if not urls:
            return set()
        
        try:
            # Create hashes for all URLs
            url_hashes = [hashlib.sha256(url.encode()).hexdigest() for url in urls]
            
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT url_hash FROM url_tracking 
                    WHERE domain_id = %s AND url_hash = ANY(%s)
                """, (domain_id, url_hashes))
                
                existing_hashes = set(row[0] for row in cursor.fetchall())
                logger.info(f"Found {len(existing_hashes)} existing URLs out of {len(urls)} checked")
                return existing_hashes
                
        except Exception as e:
            logger.error(f"Error checking existing URL hashes: {e}")
            return set()
    
    def filter_new_urls_only(self, urls: List[str], domain_id: str) -> List[str]:
        """Filter out URLs already in database - for incremental crawling"""
        if not urls:
            return []
        
        try:
            # Get existing URL hashes
            existing_hashes = self.get_existing_url_hashes(domain_id, urls)
            
            # Filter new URLs only
            new_urls = []
            for url in urls:
                url_hash = hashlib.sha256(url.encode()).hexdigest()
                if url_hash not in existing_hashes:
                    new_urls.append(url)
            
            logger.info(f"Filtered {len(new_urls)} new URLs from {len(urls)} total URLs for incremental crawling")
            return new_urls
            
        except Exception as e:
            logger.error(f"Error filtering new URLs: {e}")
            # Return all URLs if filtering fails (fallback)
            return urls
    
    def get_url_tracking_count(self, domain_id: str = None) -> int:
        """Get count of URLs in tracking table"""
        try:
            with self.connection.cursor() as cursor:
                if domain_id:
                    cursor.execute("SELECT COUNT(*) FROM url_tracking WHERE domain_id = %s", (domain_id,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM url_tracking")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting URL tracking count: {e}")
            return 0
    
    def update_monitoring_timestamp(self, domain_id: str):
        """Update last monitoring timestamp for domain"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE domains 
                    SET updated_at = NOW() 
                    WHERE id = %s
                """, (domain_id,))
                return True
        except Exception as e:
            logger.error(f"Error updating monitoring timestamp: {e}")
            return False