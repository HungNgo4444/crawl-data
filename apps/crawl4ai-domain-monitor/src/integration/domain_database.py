import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.domain_config import DomainConfig
from ..utils.database import DatabaseManager

logger = logging.getLogger(__name__)


class DomainDatabaseManager:
    """Manage domain configurations from existing database"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    def load_domain_configs(self) -> List[DomainConfig]:
        """Load monitoring config from existing domains table"""
        try:
            sql = """
            SELECT 
                id, name, display_name, base_url, 
                rss_feeds, sitemaps, css_selectors,
                status, created_at, updated_at,
                url_example
            FROM domains 
            WHERE status = 'ACTIVE'
            ORDER BY name;
            """
            
            results = self.db_manager.execute_sql(sql)
            
            if not results:
                logger.warning("No active domains found in database")
                return []
            
            domain_configs = []
            for row in results:
                try:
                    config = self._row_to_domain_config(row)
                    domain_configs.append(config)
                except Exception as e:
                    logger.error(f"Error processing domain row {row.get('name', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Loaded {len(domain_configs)} domain configurations")
            return domain_configs
            
        except Exception as e:
            logger.error(f"Load domain configs error: {e}")
            return []
    
    def _row_to_domain_config(self, row: Dict[str, Any]) -> DomainConfig:
        """Convert database row to DomainConfig"""
        try:
            # Parse JSON fields if they exist
            rss_feeds = self._parse_json_field(row.get('rss_feeds', '[]'))
            sitemaps = self._parse_json_field(row.get('sitemaps', '[]'))
            css_selectors = self._parse_json_field(row.get('css_selectors', '{}'))
            
            # Extract monitoring pages from base_url and examples
            monitoring_pages = [row.get('base_url')]
            
            # Add example URL if exists 
            if row.get('url_example'):
                example_url = row.get('url_example')
                base_path = '/'.join(example_url.split('/')[:-1])  # Get directory path
                if base_path not in monitoring_pages:
                    monitoring_pages.append(base_path)
            
            # Generate URL patterns based on domain
            domain_name = row.get('name', '')
            url_patterns = [
                f"https://{domain_name}/.*",
                f"https://www.{domain_name}/.*",
            ]
            
            # Vietnamese news pattern
            if domain_name.endswith('.vn') or '.com.vn' in domain_name:
                url_patterns.append(r'.*-\d+\.html?$')
            
            # Standard exclude patterns for Vietnamese news
            exclude_patterns = [
                '/tag/', '/category/', '/search/', '/login/', '/register/',
                '?utm_', '?fbclid=', '#', '/video/', '/live-blog/'
            ]
            
            return DomainConfig(
                id=int(row.get('id')),
                name=domain_name,
                display_name=row.get('display_name'),
                base_url=row.get('base_url'),
                status=row.get('status', 'ACTIVE'),
                monitoring_pages=monitoring_pages,
                rss_feeds=rss_feeds,
                sitemaps=sitemaps,
                url_patterns=url_patterns,
                exclude_patterns=exclude_patterns,
                created_at=self._parse_datetime(row.get('created_at')),
                updated_at=self._parse_datetime(row.get('updated_at'))
            )
            
        except Exception as e:
            logger.error(f"Row to domain config conversion error: {e}")
            raise
    
    def _parse_json_field(self, field_value: Any) -> List[str]:
        """Parse JSON field from database"""
        try:
            if isinstance(field_value, list):
                return field_value
            elif isinstance(field_value, str):
                if field_value.strip() in ['', '[]', '{}']:
                    return []
                # Simple JSON parsing - in production use proper JSON parser
                if field_value.startswith('[') and field_value.endswith(']'):
                    # Remove brackets and split by comma
                    content = field_value[1:-1]
                    if not content.strip():
                        return []
                    items = [item.strip().strip('"\'') for item in content.split(',')]
                    return [item for item in items if item]
                return [field_value]  # Single value
            else:
                return []
        except Exception as e:
            logger.error(f"JSON field parsing error: {e}")
            return []
    
    def _parse_datetime(self, dt_value: Any) -> Optional[datetime]:
        """Parse datetime field from database"""
        try:
            if isinstance(dt_value, datetime):
                return dt_value
            elif isinstance(dt_value, str):
                # Simple datetime parsing - in production use proper parser
                return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
            else:
                return None
        except Exception:
            return None
    
    def update_monitoring_metadata(self, domain_id: int, metadata: Dict[str, Any]) -> bool:
        """Update domains table with monitoring stats"""
        try:
            # Update last_analyzed_at and any monitoring metadata
            update_fields = []
            params = []
            
            if 'last_monitored_at' in metadata:
                update_fields.append("last_analyzed_at = %s")
                params.append(metadata['last_monitored_at'])
            
            if 'urls_discovered' in metadata:
                # Could add a column for monitoring stats
                pass
            
            if not update_fields:
                return True  # Nothing to update
                
            sql = f"""
            UPDATE domains 
            SET {', '.join(update_fields)}, updated_at = NOW()
            WHERE id = %s;
            """
            params.append(domain_id)
            
            result = self.db_manager.execute_sql(sql, tuple(params))
            return result is not None
            
        except Exception as e:
            logger.error(f"Update monitoring metadata error: {e}")
            return False
    
    def get_domain_by_id(self, domain_id: int) -> Optional[DomainConfig]:
        """Get domain configuration by ID"""
        try:
            sql = """
            SELECT 
                id, name, display_name, base_url, 
                rss_feeds, sitemaps, css_selectors,
                status, created_at, updated_at,
                url_example
            FROM domains 
            WHERE id = %s;
            """
            
            results = self.db_manager.execute_sql(sql, (domain_id,))
            
            if results and len(results) > 0:
                return self._row_to_domain_config(results[0])
            else:
                return None
                
        except Exception as e:
            logger.error(f"Get domain by ID error: {e}")
            return None