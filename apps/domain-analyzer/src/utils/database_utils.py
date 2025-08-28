"""
Database utility functions for domain analyzer
"""
import psycopg2
import psycopg2.extras
from typing import Dict, Any, List, Optional
import logging
import hashlib
from urllib.parse import urljoin, urlparse
from config.database_config import get_database_config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.config = get_database_config()
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            # Try with explicit connection parameters
            self.connection = psycopg2.connect(
                host='127.0.0.1',  # Force IPv4
                port=self.config['port'], 
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database']
            )
            self.connection.autocommit = True
            logger.info("Database connection established")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            logger.error(f"Config: {self.config}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def get_active_domains(self) -> List[Dict[str, Any]]:
        """Get all active domains from database"""
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, name, display_name, base_url, rss_feeds, sitemaps, css_selectors, 
                           last_analyzed_at, analysis_model, url_example, generated_schema
                    FROM domains 
                    WHERE status = 'ACTIVE'
                    ORDER BY name
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching active domains: {e}")
            return []
    
    def get_domain_by_name(self, domain_name: str) -> Optional[Dict[str, Any]]:
        """Get domain by name"""
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, name, display_name, base_url, rss_feeds, sitemaps, css_selectors, 
                           last_analyzed_at, analysis_model, url_example, generated_schema
                    FROM domains 
                    WHERE name = %s AND status = 'ACTIVE'
                """, (domain_name,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error fetching domain {domain_name}: {e}")
            return None
    
    def update_domain_analysis(self, domain_id: str, analysis_data: Dict[str, Any]):
        """Update domain analysis results"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE domains 
                    SET rss_feeds = %s, sitemaps = %s, homepage_urls = %s, category_urls = %s,
                        css_selectors = %s, last_analyzed_at = NOW(), analysis_model = %s
                    WHERE id = %s
                """, (
                    psycopg2.extras.Json(analysis_data.get('rss_feeds', [])),
                    psycopg2.extras.Json(analysis_data.get('sitemaps', [])),
                    psycopg2.extras.Json(analysis_data.get('homepage_urls', [])),
                    psycopg2.extras.Json(analysis_data.get('category_urls', [])),
                    psycopg2.extras.Json(analysis_data.get('css_selectors', {})),
                    'newspaper4k-v1.0',
                    domain_id
                ))
                logger.info(f"Domain analysis updated for {domain_id}")
                return True
        except Exception as e:
            logger.error(f"Error updating domain analysis: {e}")
            return False
    
    def add_url_to_tracking(self, url: str, domain_id: str, source_type: str = 'discovered') -> bool:
        """Add URL to url_tracking table"""
        try:
            # Create URL hash
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            
            # Normalize URL (remove fragment, normalize path)
            parsed = urlparse(url)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized_url += f"?{parsed.query}"
            
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
                    normalized_url,
                    domain_id,
                    psycopg2.extras.Json({'source_type': source_type, 'discovered_by': 'newspaper4k'})
                ))
                return True
        except Exception as e:
            logger.error(f"Error adding URL to tracking: {e}")
            return False
    
    def bulk_add_urls_to_tracking(self, urls: List[str], domain_id: str, source_type: str = 'discovered') -> int:
        """Bulk add URLs to url_tracking table"""
        success_count = 0
        for url in urls:
            if self.add_url_to_tracking(url, domain_id, source_type):
                success_count += 1
        return success_count