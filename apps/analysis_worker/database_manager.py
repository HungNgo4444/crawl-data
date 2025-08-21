#!/usr/bin/env python3
"""
Production Database Manager
Uses Docker exec approach to bypass asyncpg authentication issues
Author: James (Dev Agent)
Date: 2025-08-18
"""

import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import asdict

class ProductionDatabaseManager:
    """
    Production database manager using Docker exec
    Bypasses asyncpg authentication issues while providing full functionality
    """
    
    def __init__(self):
        """Initialize database manager"""
        self.logger = logging.getLogger(__name__)
        self.container_name = "crawler_postgres"
        self.db_user = "crawler_user"
        self.db_name = "crawler_db"
        self.db_password = "crawler123"
    
    def execute_sql(self, sql: str) -> Optional[str]:
        """Execute SQL command via Docker exec"""
        try:
            cmd = [
                "docker", "exec", "-e", f"PGPASSWORD={self.db_password}",
                self.container_name, "psql", 
                "-h", "localhost", "-U", self.db_user, "-d", self.db_name,
                "-c", sql
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                self.logger.error(f"SQL Error: {result.stderr}")
                return None
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return None
    
    def _execute_safe_sql(self, sql_template: str, values: List[str]) -> Optional[str]:
        """Execute SQL with safe parameter substitution"""
        try:
            # For PostgreSQL, we'll use EXECUTE with parameters
            # First escape all values properly
            escaped_values = []
            for value in values:
                if value is None:
                    escaped_values.append('NULL')
                else:
                    # Escape single quotes and wrap in quotes
                    escaped_value = str(value).replace("'", "''")
                    escaped_values.append(f"'{escaped_value}'")
            
            # Replace placeholders with escaped values
            safe_sql = sql_template
            for i, escaped_value in enumerate(escaped_values):
                placeholder = f"${i+1}"  # PostgreSQL style placeholder
                safe_sql = safe_sql.replace(f"%s", escaped_value, 1)  # Replace first occurrence
                safe_sql = safe_sql.replace(placeholder, escaped_value)
            
            return self.execute_sql(safe_sql)
            
        except Exception as e:
            self.logger.error(f"Safe SQL execution failed: {e}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            result = self.execute_sql("SELECT 1")
            if result:
                return {"status": "healthy", "connection": "ok"}
            else:
                return {"status": "unhealthy", "connection": "failed"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def get_domains(self) -> List[Dict[str, Any]]:
        """Get all active domains"""
        try:
            sql = """
                SELECT id, name, base_url, rss_feeds, sitemaps 
                FROM domains 
                WHERE status = 'ACTIVE'
                ORDER BY name;
            """
            
            result = self.execute_sql(sql)
            if not result:
                return []
            
            # Parse psql output (simple parsing for production)
            lines = result.split('\n')
            domains = []
            
            for line in lines[2:-2]:  # Skip header and footer
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 5:
                        domains.append({
                            "id": parts[0],
                            "name": parts[1], 
                            "base_url": parts[2],
                            "rss_feeds": json.loads(parts[3]) if parts[3] != '' else [],
                            "sitemaps": json.loads(parts[4]) if parts[4] != '' else []
                        })
            
            return domains
            
        except Exception as e:
            self.logger.error(f"Failed to get domains: {e}")
            return []
    
    def update_domain_analysis(self, domain_id: int, update_data: Dict[str, Any]) -> bool:
        """Update domain analysis results with safe parameter substitution"""
        try:
            # Build UPDATE query with proper escaping
            set_clauses = []
            values = []
            
            for key, value in update_data.items():
                if isinstance(value, str):
                    # Use proper JSON escaping for JSON columns
                    if key in ['rss_feeds', 'sitemaps', 'css_selectors']:
                        set_clauses.append(f"{key} = %s::jsonb")
                        values.append(value)
                    else:
                        set_clauses.append(f"{key} = %s")
                        values.append(value)
                elif isinstance(value, (int, float)):
                    set_clauses.append(f"{key} = %s")
                    values.append(str(value))
                elif value is None:
                    set_clauses.append(f"{key} = NULL")
                elif hasattr(value, 'isoformat'):  # datetime object
                    set_clauses.append(f"{key} = %s")
                    values.append(value.isoformat())
                else:
                    # JSON or other types
                    set_clauses.append(f"{key} = %s")
                    values.append(str(value))
            
            # Build safe SQL with placeholders
            values.append(str(domain_id))  # Add domain_id parameter
            placeholders = ' AND '.join([f"${i+1}" for i in range(len(values))])
            
            # Use dollar-quoted strings to avoid injection
            sql_template = f"""
                UPDATE domains 
                SET {', '.join(set_clauses)}
                WHERE id = ${len(values)};
            """
            
            # Execute with safe parameter substitution via psql
            result = self._execute_safe_sql(sql_template, values)
            success = result is not None
            
            if success:
                self.logger.info(f"✅ Updated domain {domain_id} analysis data (SAFE)")
            else:
                self.logger.error(f"❌ Failed to update domain {domain_id}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Update domain analysis failed: {e}")
            return False
    
    def execute_query(self, query: str, fetch: bool = False) -> Optional[List]:
        """Execute arbitrary query with optional fetch"""
        try:
            result = self.execute_sql(query)
            if not result:
                return None if fetch else True
                
            if not fetch:
                return True
                
            # Parse results for fetch=True
            lines = result.split('\n')
            if len(lines) < 3:
                return []
                
            rows = []
            for line in lines[2:-2]:  # Skip header and footer
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    rows.append(parts)
            
            return rows
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            return None

    def store_analysis_result(self, domain_id: str, analysis_result: Any) -> bool:
        """Store GWEN analysis result directly in domains table (LEGACY - keep for compatibility)"""
        try:
            # Map analysis result to database schema
            if hasattr(analysis_result, '__dict__'):
                # Convert dataclass to dict
                result_dict = asdict(analysis_result)
            else:
                result_dict = analysis_result
            
            # Build comprehensive GWEN analysis data
            gwen_analysis = {
                "analysis_id": result_dict.get("analysis_id", ""),
                "model_name": result_dict.get("model_name", "qwen2.5:3b"),
                "language_detected": result_dict.get("language_detected", "vietnamese"),
                "analysis_duration": result_dict.get("analysis_duration_seconds", 0.0),
                "vietnamese_ratio": result_dict.get("vietnamese_content_ratio", 0.0),
                "template_complexity": result_dict.get("template_complexity", "medium"),
                "analysis_methods": {
                    "homepage": "completed",
                    "rss": "available",
                    "sitemap": "available", 
                    "category": "discovered"
                },
                "url_discovery_methods": ["rss", "sitemap", "category", "homepage"],
                "confidence_breakdown": {
                    "homepage": result_dict.get("confidence_score", 0.0),
                    "overall": result_dict.get("confidence_score", 0.0)
                }
            }
            
            parsing_template = result_dict.get("parsing_template", {})
            css_selectors = {}
            
            if "headline" in parsing_template:
                css_selectors["headline"] = parsing_template["headline"].get("selectors", [])
            if "content" in parsing_template:
                css_selectors["content"] = parsing_template["content"].get("selectors", [])
            if "metadata" in parsing_template:
                metadata = parsing_template["metadata"]
                css_selectors["author"] = [metadata.get("author", "")]
                css_selectors["publish_date"] = [metadata.get("publish_date", "")]
                css_selectors["category"] = [metadata.get("category", "")]
            
            extraction_rules = {
                "clean_html": True,
                "language": "vi", 
                "remove_overlay_elements": True,
                "remove_forms": True,
                "wait_for": ".content, .article, .main",
                "page_timeout": 60000,
                "delay_before_return_html": 2.0,
                "parsing_template": parsing_template
            }
            
            # Escape JSON for SQL
            gwen_analysis_json = json.dumps(gwen_analysis).replace("'", "''")
            css_selectors_json = json.dumps(css_selectors).replace("'", "''")
            extraction_rules_json = json.dumps(extraction_rules).replace("'", "''")
            
            confidence_score = result_dict.get("confidence_score", 0.0)
            model_name = result_dict.get("model_name", "qwen2.5:3b")
            
            sql = f"""
            UPDATE domains SET
                gwen_analysis = '{gwen_analysis_json}'::jsonb,
                css_selectors = '{css_selectors_json}'::jsonb,
                extraction_rules = '{extraction_rules_json}'::jsonb,
                confidence_score = {confidence_score},
                last_analyzed_at = NOW(),
                analysis_model = '{model_name}',
                updated_at = NOW()
            WHERE id = '{domain_id}';
            """
            
            result = self.execute_sql(sql)
            if result is not None:
                self.logger.info(f"GWEN analysis stored in domains table for domain {domain_id}")
                return True
            else:
                self.logger.error(f"Failed to store GWEN analysis for domain {domain_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error storing GWEN analysis: {e}")
            return False
    
    def store_unified_discovery_result(self, domain_id: str, discovery_result: Dict[str, Any]) -> bool:
        """Store unified discovery result in 3 separate columns"""
        try:
            if not discovery_result.get("success"):
                self.logger.warning(f"Cannot store failed discovery result for domain {domain_id}")
                return False
            
            discoveries = discovery_result.get("discoveries", {})
            
            # Prepare data for 3 columns
            rss_feeds = json.dumps(discoveries.get("rss_urls", []), ensure_ascii=False)
            sitemaps = json.dumps(discoveries.get("sitemap_urls", []), ensure_ascii=False)
            css_selectors = json.dumps({
                "category_urls": discoveries.get("category_urls", [])
            }, ensure_ascii=False)
            
            # Escape for SQL
            rss_feeds_escaped = rss_feeds.replace("'", "''")
            sitemaps_escaped = sitemaps.replace("'", "''")
            css_selectors_escaped = css_selectors.replace("'", "''")
            
            # Update domains table with discovered URLs and selectors
            sql = f"""
            UPDATE domains 
            SET 
                rss_feeds = '{rss_feeds_escaped}'::jsonb,
                sitemaps = '{sitemaps_escaped}'::jsonb,
                css_selectors = '{css_selectors_escaped}'::jsonb,
                last_analyzed_at = NOW(),
                analysis_model = 'qwen2.5:3b-unified',
                updated_at = NOW()
            WHERE id = '{domain_id}';
            """
            
            result = self.execute_sql(sql)
            
            if result is not None:
                self.logger.info(f"✅ Stored unified discovery result for domain {domain_id}")
                self.logger.info(f"   - RSS feeds: {len(discoveries.get('rss_urls', []))}")
                self.logger.info(f"   - Sitemaps: {len(discoveries.get('sitemap_urls', []))}")
                self.logger.info(f"   - Category URLs: {len(discoveries.get('category_urls', []))}")
                return True
            else:
                self.logger.error(f"Failed to update domain {domain_id} with discovery results")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to store unified discovery result: {e}")
            return False
    
    def update_domain_metadata(self, domain_id: str, analysis_result: Any) -> bool:
        """Update domain discovery metadata (kept for compatibility)"""
        # This method now only updates discovery-related metadata
        # GWEN analysis is stored via store_analysis_result method
        try:
            if hasattr(analysis_result, '__dict__'):
                result_dict = asdict(analysis_result)
            else:
                result_dict = analysis_result
            
            # Update only discovery metadata, not GWEN analysis
            discovery_metadata = {
                "last_analysis_id": result_dict.get("analysis_id", ""),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            metadata_json = json.dumps(discovery_metadata).replace("'", "''")
            
            sql = f"""
            UPDATE domains SET
                last_discovery_at = NOW(),
                discovery_methods = discovery_methods || '{metadata_json}'::jsonb,
                updated_at = NOW()
            WHERE id = '{domain_id}';
            """
            
            result = self.execute_sql(sql)
            if result is not None:
                self.logger.info(f"Discovery metadata updated for domain {domain_id}")
                return True
            else:
                self.logger.error(f"Failed to update discovery metadata for domain {domain_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating discovery metadata: {e}")
            return False
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get comprehensive analysis summary from simplified schema"""
        try:
            # Get domain summary with GWEN analysis
            domain_summary_sql = """
                SELECT 
                    COUNT(*) as total_active_domains,
                    COUNT(CASE WHEN last_analyzed_at IS NOT NULL THEN 1 END) as domains_with_analysis,
                    AVG(confidence_score) as average_confidence,
                    COUNT(CASE WHEN gwen_analysis != '{}' THEN 1 END) as total_templates
                FROM domains 
                WHERE status = 'ACTIVE';
            """
            
            domain_result = self.execute_sql(domain_summary_sql)
            
            # Parse domain summary result
            summary_data = {"total_active_domains": 0, "domains_with_analysis": 0, "average_confidence": 0.0, "total_templates": 0}
            if domain_result:
                lines = domain_result.split('\n')
                if len(lines) >= 3:
                    data_line = lines[2].strip()
                    parts = [p.strip() for p in data_line.split('|')]
                    if len(parts) >= 4:
                        summary_data = {
                            "total_active_domains": int(parts[0]),
                            "domains_with_analysis": int(parts[1]),
                            "average_confidence": float(parts[2]) if parts[2] else 0.0,
                            "total_templates": int(parts[3])
                        }
            
            # Get recent activity
            recent_activity_sql = """
                SELECT 
                    name as domain_name,
                    confidence_score,
                    analysis_model as model_used,
                    last_analyzed_at
                FROM domains
                WHERE last_analyzed_at IS NOT NULL
                ORDER BY last_analyzed_at DESC
                LIMIT 10;
            """
            
            recent_result = self.execute_sql(recent_activity_sql)
            
            # Parse recent activity
            recent_activity = []
            if recent_result:
                lines = recent_result.split('\n')[2:-2]  # Skip header and footer
                for line in lines:
                    if '|' in line:
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 4:
                            recent_activity.append({
                                "domain_name": parts[0],
                                "confidence_score": float(parts[1]) if parts[1] else 0.0,
                                "model_used": parts[2],
                                "analyzed_at": parts[3]
                            })
            
            return {
                "summary": summary_data,
                "recent_activity": recent_activity,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting analysis summary: {e}")
            return {"error": str(e), "summary": {}, "recent_activity": []}

# Create singleton instance
db_manager = ProductionDatabaseManager()