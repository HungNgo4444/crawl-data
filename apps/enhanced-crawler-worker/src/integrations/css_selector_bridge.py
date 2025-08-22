"""
CSS Selector Bridge - Integration bridge between domain_analyzer và content extractor

This module bridges domain_analyzer CSS selector generation với Crawl4AI JsonCssExtractionStrategy,
providing seamless integration cho structured data extraction workflow.

Features:
- Transform domain_analyzer schema to JsonCssExtractionStrategy format
- Retrieve CSS selectors từ database generated_schema column
- Fallback selector patterns cho Vietnamese news sites
- Selector effectiveness tracking và automatic refresh triggers
- Integration testing và validation
"""

import asyncio
import json
import logging
import psycopg2
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SelectorSchema:
    """CSS selector schema for JsonCssExtractionStrategy"""
    name: str
    base_selector: str
    fields: List[Dict[str, Any]]
    confidence_score: float = 0.0
    domain_name: str = ""
    generated_at: Optional[str] = None

class CSSelectorBridge:
    """Bridge between domain_analyzer và crawl4ai_content_extractor"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Fallback selectors cho Vietnamese news sites
        self.fallback_selectors = {
            'title': [
                'h1', 'h1.title', 'h1.title-detail', '.title', '.headline', 
                '.post-title', '.news-title', '.article-title', '.entry-title',
                '.tieu-de', '.title-news'
            ],
            'content': [
                '.content', '.article-content', '.post-content', '.fck_detail',
                '.detail-content', '.news-content', '.article-body', 'article',
                '.noi-dung', '.chi-tiet', '.Normal'
            ],
            'author': [
                '.author', '.byline', '.writer', '.journalist', '.post-author', 
                '.tac-gia', '.author-name', '.reporter', '.nguoi-viet',
                '[rel="author"]'
            ],
            'publish_date': [
                '.date', '.published', '.timestamp', '.post-date', 'time', 
                '.ngay-dang', '.publication-date', '[datetime]',
                '.time', '.date-time'
            ],
            'category': [
                '.category', '.section', '.topic', '.breadcrumb a:last-child', 
                '.tag', '.category-name', '.chuyen-muc', '.section-name'
            ],
            'images': [
                '.content img', '.article-content img', '.post-content img',
                '.featured-image img', 'article img', '.detail-content img'
            ]
        }
    
    async def get_domain_selectors(self, domain_name: str) -> Optional[SelectorSchema]:
        """Retrieve CSS selectors từ domain analysis results"""
        
        try:
            # Query generated_schema từ domains table using Docker exec
            domain_schema = await self._get_domain_schema_from_db(domain_name)
            
            if domain_schema and domain_schema.get('fields'):
                # Transform domain_analyzer schema to JsonCssExtractionStrategy format
                return self._transform_to_extraction_schema(domain_schema, domain_name)
            
            self.logger.warning(f"No schema found for domain {domain_name}, using fallback selectors")
            return self._create_fallback_schema(domain_name)
            
        except Exception as e:
            self.logger.error(f"Error retrieving selectors for {domain_name}: {e}")
            return self._create_fallback_schema(domain_name)
    
    async def _get_domain_schema_from_db(self, domain_name: str) -> Optional[Dict[str, Any]]:
        """Get domain schema from database using Docker exec"""
        
        try:
            # Use Docker exec to query database
            query = f"SELECT generated_schema FROM domains WHERE name = '{domain_name}' AND generated_schema IS NOT NULL;"
            
            cmd = [
                'docker', 'exec', '-e', 'PGPASSWORD=crawler123', 
                'crawler_postgres', 'psql', '-h', 'localhost', 
                '-U', 'crawler_user', '-d', 'crawler_db', 
                '-t', '-c', query
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse JSON result
                json_str = result.stdout.strip()
                if json_str and json_str != '':
                    return json.loads(json_str)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Database query failed for {domain_name}: {e}")
            return None
    
    def _transform_to_extraction_schema(
        self, 
        domain_schema: Dict[str, Any], 
        domain_name: str
    ) -> SelectorSchema:
        """Transform domain_analyzer schema to Crawl4AI JsonCssExtractionStrategy format"""
        
        # Extract base selector (default to article containers)
        base_selector = domain_schema.get('baseSelector', 'article, .article, main, .content, .post')
        
        # Transform fields
        fields = []
        confidence_scores = []
        
        for field_name in ['title', 'content', 'author', 'publish_date', 'category', 'images']:
            selector = self._get_best_selector(domain_schema, field_name)
            
            if selector:
                field_config = {
                    "name": field_name,
                    "selector": selector,
                    "type": "text"
                }
                
                # Special handling for specific field types
                if field_name == 'publish_date':
                    field_config["attribute"] = "datetime"
                elif field_name == 'images':
                    field_config["type"] = "list"
                    field_config["fields"] = [
                        {"name": "src", "selector": "", "type": "attribute", "attribute": "src"},
                        {"name": "alt", "selector": "", "type": "attribute", "attribute": "alt"}
                    ]
                
                fields.append(field_config)
                
                # Track confidence for this field
                field_confidence = self._get_field_confidence(domain_schema, field_name)
                confidence_scores.append(field_confidence)
        
        # Calculate overall confidence
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return SelectorSchema(
            name=f"{domain_name}_extraction_schema",
            base_selector=base_selector,
            fields=fields,
            confidence_score=overall_confidence,
            domain_name=domain_name,
            generated_at=datetime.now().isoformat()
        )
    
    def _get_best_selector(self, schema: Dict[str, Any], field_name: str) -> str:
        """Get best CSS selector for field từ domain analysis results"""
        
        # Look for field in schema fields
        for field in schema.get('fields', []):
            if field.get('name') == field_name:
                return field.get('selector', '')
        
        # Fallback to predefined selectors cho Vietnamese news sites
        fallback_list = self.fallback_selectors.get(field_name, [])
        return ', '.join(fallback_list[:3]) if fallback_list else ''
    
    def _get_field_confidence(self, schema: Dict[str, Any], field_name: str) -> float:
        """Get confidence score for specific field"""
        
        for field in schema.get('fields', []):
            if field.get('name') == field_name:
                return field.get('confidence', 0.5)
        
        return 0.3  # Default confidence for fallback selectors
    
    def _create_fallback_schema(self, domain_name: str) -> SelectorSchema:
        """Create fallback schema using Vietnamese news patterns"""
        
        fields = []
        
        for field_name, selectors in self.fallback_selectors.items():
            field_config = {
                "name": field_name,
                "selector": ', '.join(selectors[:3]),  # Use top 3 selectors
                "type": "text"
            }
            
            # Special handling for specific field types
            if field_name == 'publish_date':
                field_config["attribute"] = "datetime"
            elif field_name == 'images':
                field_config["type"] = "list"
                field_config["fields"] = [
                    {"name": "src", "selector": "", "type": "attribute", "attribute": "src"},
                    {"name": "alt", "selector": "", "type": "attribute", "attribute": "alt"}
                ]
            
            fields.append(field_config)
        
        return SelectorSchema(
            name=f"{domain_name}_fallback_schema",
            base_selector="article, .article, main, .content, .post, .news-detail",
            fields=fields,
            confidence_score=0.3,  # Lower confidence for fallback
            domain_name=domain_name,
            generated_at=datetime.now().isoformat()
        )
    
    def to_crawl4ai_schema(self, selector_schema: SelectorSchema) -> Dict[str, Any]:
        """Convert SelectorSchema to Crawl4AI JsonCssExtractionStrategy format"""
        
        return {
            "name": selector_schema.name,
            "baseSelector": selector_schema.base_selector,
            "fields": selector_schema.fields
        }
    
    async def validate_selector_effectiveness(
        self, 
        domain_name: str, 
        test_url: str,
        selector_schema: SelectorSchema
    ) -> Dict[str, Any]:
        """Test selector effectiveness on actual URL"""
        
        try:
            # Import here to avoid circular dependency
            from .crawl4ai_content_extractor import Crawl4AIContentExtractor
            
            extractor = Crawl4AIContentExtractor()
            css_schema = self.to_crawl4ai_schema(selector_schema)
            
            # Test extraction
            result = await extractor.extract_single_content(
                url=test_url,
                domain_config={'name': domain_name},
                css_selectors=css_schema
            )
            
            # Analyze effectiveness
            effectiveness = {
                'domain_name': domain_name,
                'test_url': test_url,
                'extraction_success': result.success,
                'quality_score': result.quality_score,
                'extraction_method': result.extraction_method,
                'fields_extracted': {},
                'overall_effectiveness': 0.0
            }
            
            # Check which fields were successfully extracted
            field_success_count = 0
            total_fields = len(selector_schema.fields)
            
            for field in selector_schema.fields:
                field_name = field['name']
                field_value = getattr(result, field_name, None)
                field_success = bool(field_value and str(field_value).strip())
                
                effectiveness['fields_extracted'][field_name] = {
                    'success': field_success,
                    'value_length': len(str(field_value)) if field_value else 0
                }
                
                if field_success:
                    field_success_count += 1
            
            # Calculate overall effectiveness
            effectiveness['overall_effectiveness'] = (
                field_success_count / total_fields if total_fields > 0 else 0.0
            )
            
            return effectiveness
            
        except Exception as e:
            self.logger.error(f"Selector validation failed for {domain_name}: {e}")
            return {
                'domain_name': domain_name,
                'test_url': test_url,
                'extraction_success': False,
                'error': str(e),
                'overall_effectiveness': 0.0
            }
    
    async def trigger_schema_refresh(self, domain_name: str) -> bool:
        """Trigger domain_analyzer to refresh schema for domain"""
        
        try:
            # Import domain analyzer
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'workers'))
            
            from domain_analyzer import DomainAnalyzer
            
            analyzer = DomainAnalyzer()
            
            # Re-analyze domain to generate fresh schema
            result = await analyzer.analyze_and_save_domain(domain_name)
            
            if result and result.get('success'):
                self.logger.info(f"Schema refreshed successfully for {domain_name}")
                return True
            else:
                self.logger.warning(f"Schema refresh failed for {domain_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Schema refresh error for {domain_name}: {e}")
            return False
    
    async def get_all_domains_with_schemas(self) -> List[str]:
        """Get list of all domains that have generated schemas"""
        
        try:
            query = "SELECT name FROM domains WHERE generated_schema IS NOT NULL AND status = 'ACTIVE';"
            
            cmd = [
                'docker', 'exec', '-e', 'PGPASSWORD=crawler123', 
                'crawler_postgres', 'psql', '-h', 'localhost', 
                '-U', 'crawler_user', '-d', 'crawler_db', 
                '-t', '-c', query
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0 and result.stdout.strip():
                domains = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                return domains
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get domains with schemas: {e}")
            return []
    
    async def bulk_validate_schemas(self, limit: int = 10) -> Dict[str, Any]:
        """Validate schemas for multiple domains"""
        
        domains = await self.get_all_domains_with_schemas()
        validation_results = []
        
        # Limit processing for performance
        domains_to_process = domains[:limit]
        
        for domain_name in domains_to_process:
            try:
                # Get domain schema
                selector_schema = await self.get_domain_selectors(domain_name)
                
                if selector_schema:
                    # Get test URL (you might want to implement this)
                    test_url = await self._get_test_url_for_domain(domain_name)
                    
                    if test_url:
                        # Validate effectiveness
                        effectiveness = await self.validate_selector_effectiveness(
                            domain_name, test_url, selector_schema
                        )
                        validation_results.append(effectiveness)
                
            except Exception as e:
                self.logger.error(f"Bulk validation error for {domain_name}: {e}")
        
        # Summarize results
        total_domains = len(validation_results)
        successful_extractions = sum(1 for r in validation_results if r.get('extraction_success', False))
        avg_effectiveness = sum(r.get('overall_effectiveness', 0) for r in validation_results) / total_domains if total_domains > 0 else 0
        
        return {
            'total_domains_tested': total_domains,
            'successful_extractions': successful_extractions,
            'success_rate': successful_extractions / total_domains if total_domains > 0 else 0,
            'average_effectiveness': avg_effectiveness,
            'results': validation_results
        }
    
    async def _get_test_url_for_domain(self, domain_name: str) -> Optional[str]:
        """Get test URL for domain from database"""
        
        try:
            query = f"SELECT url_example FROM domains WHERE name = '{domain_name}';"
            
            cmd = [
                'docker', 'exec', '-e', 'PGPASSWORD=crawler123', 
                'crawler_postgres', 'psql', '-h', 'localhost', 
                '-U', 'crawler_user', '-d', 'crawler_db', 
                '-t', '-c', query
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get test URL for {domain_name}: {e}")
            return None

# Export main class
__all__ = ['CSSelectorBridge', 'SelectorSchema']