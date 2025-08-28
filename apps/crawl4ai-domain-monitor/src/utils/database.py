import psycopg2
import psycopg2.extras
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager using native PostgreSQL connection"""
    
    def __init__(self, host: str = "postgres", port: int = 5432,
                 database: str = "crawler_db", user: str = "crawler_user", 
                 password: str = "crawler123"):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        
    def execute_sql(self, sql: str, params: tuple = ()) -> Optional[List[Dict[str, Any]]]:
        """Execute SQL command using native PostgreSQL connection"""
        try:
            with psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            ) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(sql, params)
                    
                    # If it's a SELECT query, fetch results
                    if sql.strip().upper().startswith('SELECT'):
                        results = cursor.fetchall()
                        return [dict(row) for row in results]
                    else:
                        # For INSERT/UPDATE/DELETE, return empty list but commit changes
                        conn.commit()
                        return []
                        
        except psycopg2.Error as e:
            logger.error(f"Database error: {e}")
            return None
        except Exception as e:
            logger.error(f"Database execution error: {e}")
            return None
    
    def run_migration(self, migration_file: str) -> bool:
        """Run database migration from file"""
        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            result = self.execute_sql(sql)
            return result is not None
        except Exception as e:
            logger.error(f"Migration error: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test database connection"""
        result = self.execute_sql("SELECT 1 as test;")
        return result is not None and len(result) > 0
    
    def get_domains(self, status: str = "ACTIVE") -> List[Dict[str, Any]]:
        """Get all domains with specified status"""
        sql = "SELECT * FROM domains WHERE status = %s ORDER BY name;"
        return self.execute_sql(sql, (status,)) or []
    
    def get_domain_by_name(self, domain_name: str) -> Optional[Dict[str, Any]]:
        """Get domain by name"""
        sql = "SELECT * FROM domains WHERE name = %s;"
        results = self.execute_sql(sql, (domain_name,))
        return results[0] if results else None
    
    def update_domain_crawl_data(self, domain_id: int, crawl_data: Dict[str, Any]) -> bool:
        """Update domain with crawl4ai extracted data"""
        try:
            sql = """
                UPDATE domains SET 
                    generated_schema = %s,
                    last_analyzed_at = CURRENT_TIMESTAMP,
                    analysis_model = 'crawl4ai-v1'
                WHERE id = %s;
            """
            result = self.execute_sql(sql, (json.dumps(crawl_data), domain_id))
            return result is not None
        except Exception as e:
            logger.error(f"Error updating domain crawl data: {e}")
            return False
    
    def get_pending_domains(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get domains that need crawl4ai analysis"""
        sql = """
            SELECT * FROM domains 
            WHERE status = 'ACTIVE' 
            AND (analysis_model IS NULL OR analysis_model != 'crawl4ai-v1')
            ORDER BY created_at ASC
            LIMIT %s;
        """
        return self.execute_sql(sql, (limit,)) or []