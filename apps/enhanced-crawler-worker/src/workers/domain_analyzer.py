"""
Domain Analyzer - Generate CSS Selectors Schema từ Database
Query url_example từ domains table -> Analyze structure -> Generate JsonCssExtractionStrategy schema
"""

import asyncio
import json
import psycopg2
from typing import Dict, List, Optional
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy


class DomainAnalyzer:
    """
    Analyze domain structure từ database và generate CSS selectors schema
    """
    
    def __init__(self, db_config: Dict = None):
        # Use Docker exec connection instead of direct connection
        self.use_docker_exec = True
        
        # Common Vietnamese news selectors patterns
        self.selector_patterns = {
            "title": [
                "h1", "h1.title", "h1.title-detail", ".title", ".headline", 
                ".post-title", ".news-title", ".article-title", ".entry-title"
            ],
            "author": [
                ".author", ".byline", ".writer", ".journalist", ".post-author", 
                ".tac-gia", ".author-name", ".reporter", ".nguoi-viet"
            ],
            "category": [
                ".category", ".section", ".topic", ".breadcrumb a:last-child", 
                ".tag", ".category-name", ".chuyen-muc"
            ],
            "publish_date": [
                ".date", ".published", ".timestamp", ".post-date", "time", 
                ".ngay-dang", ".publication-date", ".created-date"
            ],
            "content": [
                ".content", ".article-content", ".post-content", ".news-content", 
                ".body", ".detail", ".fck_detail", ".entry-content", ".article-body"
            ],
            "images": [
                ".content img", ".article-content img", ".post-content img", 
                ".news-content img", ".fck_detail img", ".fig-picture img"
            ]
        }
    
    def get_domain_url_example(self, domain_name: str) -> Optional[str]:
        """
        Query url_example từ domains table
        
        Args:
            domain_name: Tên domain (e.g., 'vnexpress.net')
            
        Returns:
            URL example hoặc None
        """
        import subprocess
        import json
        
        try:
            # Query using Docker exec
            cmd = [
                'docker', 'exec', '-e', 'PGPASSWORD=crawler123',
                'crawler_postgres', 'psql', 
                '-h', 'localhost', '-U', 'crawler_user', '-d', 'crawler_db',
                '-t', '-c', 
                f"SELECT url_example FROM domains WHERE name = '{domain_name}' AND url_example IS NOT NULL;"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                url = result.stdout.strip()
                return url if url and url != '' else None
            else:
                print(f"Database query error: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Database error: {e}")
            return None
    
    async def analyze_domain_structure(self, domain_name: str) -> Dict:
        """
        Analyze domain structure từ url_example và generate CSS selectors schema
        
        Args:
            domain_name: Tên domain trong database
            
        Returns:
            Dict: Generated JsonCssExtractionStrategy schema
        """
        # Lấy URL example từ database
        url_example = self.get_domain_url_example(domain_name)
        if not url_example:
            return {"error": f"No url_example found for domain: {domain_name}"}
        
        print(f"Analyzing domain structure for {domain_name}")
        print(f"Using URL example: {url_example}")
        
        # Crawl trang để analyze structure với verbose=False
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url_example)
            
            if not result.success:
                return {"error": f"Failed to crawl URL: {url_example}"}
            
            # Test các selector patterns để tìm selectors hoạt động
            working_selectors = await self._test_selectors(result.html, url_example)
            
            # Generate schema từ working selectors
            schema = self._generate_schema(domain_name, working_selectors)
            
            return {
                "domain": domain_name,
                "url_example": url_example,
                "schema": schema,
                "working_selectors": working_selectors
            }
    
    async def _test_selectors(self, html: str, url: str) -> Dict:
        """
        Test các CSS selectors trên HTML để tìm selectors hoạt động
        
        Args:
            html: HTML content
            url: URL gốc
            
        Returns:
            Dict: Working selectors for each field
        """
        working_selectors = {}
        
        for field_name, selectors in self.selector_patterns.items():
            working_selectors[field_name] = []
            
            for selector in selectors:
                # Test từng selector với temporary schema
                test_schema = {
                    "name": "test",
                    "baseSelector": "body",
                    "fields": [
                        {
                            "name": "test_field",
                            "selector": selector,
                            "type": "text" if field_name != "images" else "list",
                        }
                    ]
                }
                
                if field_name == "images":
                    test_schema["fields"][0]["fields"] = [
                        {"name": "src", "selector": "", "type": "attribute", "attribute": "src"}
                    ]
                
                try:
                    # Test selector với Crawl4AI
                    extraction_strategy = JsonCssExtractionStrategy(test_schema)
                    
                    async with AsyncWebCrawler(verbose=False) as crawler:
                        test_result = await crawler.aprocess_html(
                            url=url,
                            html=html,
                            extracted_content="",
                            config=None,
                            extraction_strategy=extraction_strategy
                        )
                        
                        if test_result.extracted_content:
                            data = json.loads(test_result.extracted_content)
                            if isinstance(data, list) and data:
                                test_value = data[0].get("test_field")
                                if test_value:  # Selector có data
                                    working_selectors[field_name].append({
                                        "selector": selector,
                                        "sample_data": str(test_value)[:100] + "..." if len(str(test_value)) > 100 else str(test_value)
                                    })
                                    
                except Exception as e:
                    # Selector không hoạt động, bỏ qua
                    continue
        
        return working_selectors
    
    def _generate_schema(self, domain_name: str, working_selectors: Dict) -> Dict:
        """
        Generate JsonCssExtractionStrategy schema từ working selectors
        
        Args:
            domain_name: Tên domain
            working_selectors: Dict của working selectors
            
        Returns:
            JsonCssExtractionStrategy schema
        """
        schema = {
            "name": f"{domain_name}_article",
            "baseSelector": "article, .article, .post, .news-item, .content, main, body",
            "fields": []
        }
        
        # Add title field
        if working_selectors.get("title"):
            best_title_selector = working_selectors["title"][0]["selector"]
            schema["fields"].append({
                "name": "title",
                "selector": best_title_selector,
                "type": "text"
            })
        
        # Add author field
        if working_selectors.get("author"):
            best_author_selector = working_selectors["author"][0]["selector"]
            schema["fields"].append({
                "name": "author",
                "selector": best_author_selector,
                "type": "text"
            })
        
        # Add category field
        if working_selectors.get("category"):
            best_category_selector = working_selectors["category"][0]["selector"]
            schema["fields"].append({
                "name": "category",
                "selector": best_category_selector,
                "type": "text"
            })
        
        # Add publish_date field
        if working_selectors.get("publish_date"):
            best_date_selector = working_selectors["publish_date"][0]["selector"]
            schema["fields"].append({
                "name": "publish_date",
                "selector": best_date_selector,
                "type": "text",
                "attribute": "datetime"
            })
        
        # Add content field
        if working_selectors.get("content"):
            best_content_selector = working_selectors["content"][0]["selector"]
            schema["fields"].append({
                "name": "content",
                "selector": best_content_selector,
                "type": "text"
            })
        
        # Add images field
        if working_selectors.get("images"):
            best_image_selector = working_selectors["images"][0]["selector"]
            schema["fields"].append({
                "name": "images",
                "selector": best_image_selector,
                "type": "list",
                "fields": [
                    {
                        "name": "src",
                        "selector": "",
                        "type": "attribute",
                        "attribute": "src"
                    },
                    {
                        "name": "alt",
                        "selector": "",
                        "type": "attribute",
                        "attribute": "alt"
                    }
                ]
            })
        
        return schema
    
    async def analyze_all_domains(self) -> List[Dict]:
        """
        Analyze tất cả domains có url_example trong database
        
        Returns:
            List: Analysis results cho tất cả domains
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute(
                "SELECT name FROM domains WHERE url_example IS NOT NULL ORDER BY name;"
            )
            
            domains = [row[0] for row in cur.fetchall()]
            
        except Exception as e:
            return [{"error": f"Database error: {e}"}]
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
        
        results = []
        for domain_name in domains:
            result = await self.analyze_domain_structure(domain_name)
            results.append(result)
        
        return results
    
    def save_schema_to_database(self, domain_name: str, schema: Dict) -> bool:
        """
        Lưu generated schema vào database domains table
        
        Args:
            domain_name: Tên domain
            schema: Generated JsonCssExtractionStrategy schema
            
        Returns:
            bool: Success status
        """
        import subprocess
        
        try:
            # Escape JSON for SQL
            schema_json = json.dumps(schema, ensure_ascii=False).replace("'", "''")
            
            # Update using Docker exec
            cmd = [
                'docker', 'exec', '-e', 'PGPASSWORD=crawler123',
                'crawler_postgres', 'psql', 
                '-h', 'localhost', '-U', 'crawler_user', '-d', 'crawler_db',
                '-c', 
                f"UPDATE domains SET generated_schema = '{schema_json}' WHERE name = '{domain_name}';"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Successfully saved schema for {domain_name}")
                return True
            else:
                print(f"Database update error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Database error: {e}")
            return False
    
    async def analyze_and_save_domain(self, domain_name: str) -> Dict:
        """
        Analyze domain structure và save schema vào database
        
        Args:
            domain_name: Tên domain
            
        Returns:
            Dict: Analysis results với save status
        """
        result = await self.analyze_domain_structure(domain_name)
        
        if "error" not in result and result.get("schema"):
            success = self.save_schema_to_database(domain_name, result["schema"])
            result["saved_to_db"] = success
        else:
            result["saved_to_db"] = False
        
        return result
    
    async def analyze_and_save_all_domains(self) -> List[Dict]:
        """
        Analyze tất cả domains và save schemas vào database
        
        Returns:
            List: Analysis results với save status cho tất cả domains
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute(
                "SELECT name FROM domains WHERE url_example IS NOT NULL ORDER BY name;"
            )
            
            domains = [row[0] for row in cur.fetchall()]
            
        except Exception as e:
            return [{"error": f"Database error: {e}"}]
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
        
        results = []
        for domain_name in domains:
            print(f"\n=== Processing {domain_name} ===")
            result = await self.analyze_and_save_domain(domain_name)
            results.append(result)
        
        return results


# Example usage
if __name__ == "__main__":
    async def main():
        analyzer = DomainAnalyzer()
        
        # Test single domain first
        print("Testing single domain: vnexpress.net")
        result = await analyzer.analyze_and_save_domain("vnexpress.net")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # # Analyze all domains và save schemas
        # results = await analyzer.analyze_and_save_all_domains()
        # print(f"\nProcessed {len(results)} domains")
        
        # success_count = sum(1 for r in results if r.get("saved_to_db"))
        # print(f"Successfully saved schemas for {success_count} domains")
    
    asyncio.run(main())