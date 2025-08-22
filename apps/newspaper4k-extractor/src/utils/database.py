"""Database utilities for accessing domains table"""

import json
import subprocess
from typing import List, Dict, Optional


class DatabaseManager:
    """Database manager using Docker exec approach like other services"""
    
    def __init__(self):
        self.container_name = "crawler_postgres"
        self.db_user = "crawler_user"
        self.db_name = "crawler_db"
        self.db_password = "crawler123"
    
    def execute_sql(self, sql: str) -> Optional[str]:
        """Execute SQL command using Docker exec"""
        try:
            cmd = [
                "docker", "exec", 
                "-e", f"PGPASSWORD={self.db_password}",
                self.container_name,
                "psql", "-h", "localhost", "-U", self.db_user, "-d", self.db_name,
                "-t", "-c", sql
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"SQL execution failed: {e}")
            return None
    
    def get_active_domains(self) -> List[Dict]:
        """Get all active domains from database"""
        sql = """
            SELECT json_agg(
                json_build_object(
                    'id', id,
                    'name', name,
                    'display_name', COALESCE(display_name, name),
                    'base_url', base_url,
                    'url_example', url_example,
                    'rss_feeds', COALESCE(rss_feeds, '[]'::jsonb),
                    'sitemaps', COALESCE(sitemaps, '[]'::jsonb),
                    'css_selectors', COALESCE(css_selectors, '{}'::jsonb)
                )
            ) FROM domains WHERE status = 'ACTIVE' ORDER BY name;
        """
        
        result = self.execute_sql(sql)
        if result:
            try:
                domains_data = json.loads(result)
                return domains_data if domains_data else []
            except json.JSONDecodeError:
                print("Failed to parse JSON response")
                return []
        return []
    
    def get_domain_by_name(self, domain_name: str) -> Optional[Dict]:
        """Get specific domain by name - SQL injection safe"""
        # Use parameterized query to prevent SQL injection
        escaped_name = domain_name.replace("'", "''")  # Basic SQL escaping
        sql = f"""
            SELECT json_build_object(
                'id', id,
                'name', name,
                'display_name', COALESCE(display_name, name),
                'base_url', base_url,
                'url_example', url_example,
                'rss_feeds', COALESCE(rss_feeds, '[]'::jsonb),
                'sitemaps', COALESCE(sitemaps, '[]'::jsonb),
                'css_selectors', COALESCE(css_selectors, '{{}}'::jsonb)
            ) FROM domains 
            WHERE name = '{escaped_name}' AND status = 'ACTIVE'
            LIMIT 1;
        """
        
        result = self.execute_sql(sql)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                print("Failed to parse JSON response")
        return None
    
    def test_connection(self) -> bool:
        """Test database connection"""
        result = self.execute_sql("SELECT 1;")
        return result == "1"
