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
        
        # Set UTF-8 encoding cho toàn bộ environment
        import sys
        import os
        import locale
        
        # Fix encoding environment variables
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
        
        # Set console encoding if supported
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            # Python < 3.7 compatibility
            pass
        
        # Set locale to UTF-8 if possible
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'C.UTF-8')
            except locale.Error:
                pass
        
        print(f"Analyzing domain structure for {domain_name}")
        print(f"Using URL example: {url_example}")
        
        try:
            # Crawl trang để analyze structure với proper UTF-8 handling
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
        
        except UnicodeEncodeError as e:
            return {"error": f"Unicode encoding error: {e}. Try using UTF-8 console."}
        except Exception as e:
            return {"error": f"Analysis error: {e}"}
    
    async def test_with_existing_html(self, html_file_path: str, url: str) -> Dict:
        """
        Test selectors với HTML file đã có sẵn
        
        Args:
            html_file_path: Path to HTML file  
            url: Original URL
            
        Returns:
            Dict: Working selectors for each field
        """
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html = f.read()
            return await self._test_selectors(html, url)
        except Exception as e:
            return {"error": f"Failed to read HTML file: {e}"}
    
    async def _test_selectors(self, html: str, url: str) -> Dict:
        """
        Test các CSS selectors trên HTML để tìm selectors hoạt động
        """
        working_selectors = {}
        
        # Set UTF-8 encoding
        import sys
        import os
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
        
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass
        
        # Test tất cả selectors cùng lúc với 1 schema duy nhất
        all_fields = []
        field_mapping = {}
        
        for field_name, selectors in self.selector_patterns.items():
            working_selectors[field_name] = []
            
            for i, selector in enumerate(selectors):
                field_id = f"{field_name}_{i}"
                field_mapping[field_id] = {"field_name": field_name, "selector": selector}
                
                field_config = {
                    "name": field_id,
                    "selector": selector,
                    "type": "text" if field_name != "images" else "list"
                }
                
                if field_name == "images":
                    field_config["fields"] = [
                        {"name": "src", "selector": "", "type": "attribute", "attribute": "src"}
                    ]
                
                all_fields.append(field_config)
        
        # Test tất cả với 1 schema
        test_schema = {
            "name": "test_all",
            "baseSelector": "body",
            "fields": all_fields
        }
        
        try:
            from crawl4ai import CrawlerRunConfig
            
            extraction_strategy = JsonCssExtractionStrategy(test_schema)
            config = CrawlerRunConfig(extraction_strategy=extraction_strategy)
            
            async with AsyncWebCrawler(verbose=False) as crawler:
                test_result = await crawler.aprocess_html(
                    url=url,
                    html=html,
                    extracted_content="",
                    screenshot_data=None,
                    pdf_data=None,
                    verbose=False,
                    config=config
                )
                
                if test_result.extracted_content:
                    data = json.loads(test_result.extracted_content)
                    if isinstance(data, list) and data:
                        result_data = data[0]
                        
                        for field_id, field_info in field_mapping.items():
                            test_value = result_data.get(field_id)
                            if test_value:
                                field_name = field_info["field_name"]
                                selector = field_info["selector"]
                                
                                working_selectors[field_name].append(selector)
                                
        except Exception as e:
            print(f"Selector testing error: {e}")
        
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
            schema["fields"].append({
                "name": "title",
                "selector": working_selectors["title"][0],
                "type": "text"
            })
        
        # Add author field
        if working_selectors.get("author"):
            schema["fields"].append({
                "name": "author",
                "selector": working_selectors["author"][0],
                "type": "text"
            })
        
        # Add category field
        if working_selectors.get("category"):
            schema["fields"].append({
                "name": "category",
                "selector": working_selectors["category"][0],
                "type": "text"
            })
        
        # Add publish_date field
        if working_selectors.get("publish_date"):
            schema["fields"].append({
                "name": "publish_date",
                "selector": working_selectors["publish_date"][0],
                "type": "text",
                "attribute": "datetime"
            })
        
        # Add content field
        if working_selectors.get("content"):
            schema["fields"].append({
                "name": "content",
                "selector": working_selectors["content"][0],
                "type": "text"
            })
        
        # Add images field
        if working_selectors.get("images"):
            schema["fields"].append({
                "name": "images",
                "selector": working_selectors["images"][0],
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
        import subprocess
        
        try:
            # Get domains using Docker exec như các method khác
            cmd = [
                'docker', 'exec', '-e', 'PGPASSWORD=crawler123',
                'crawler_postgres', 'psql', 
                '-h', 'localhost', '-U', 'crawler_user', '-d', 'crawler_db',
                '-t', '-c', 
                "SELECT name FROM domains WHERE url_example IS NOT NULL AND status = 'ACTIVE' ORDER BY name;"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return [{"error": f"Database query error: {result.stderr}"}]
            
            # Parse domain names
            domains = []
            for line in result.stdout.strip().split('\n'):
                domain = line.strip()
                if domain and domain != '':
                    domains.append(domain)
            
        except Exception as e:
            return [{"error": f"Database error: {e}"}]
        
        # Analyze từng domain
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
        import subprocess
        
        try:
            # Get domains using Docker exec
            cmd = [
                'docker', 'exec', '-e', 'PGPASSWORD=crawler123',
                'crawler_postgres', 'psql', 
                '-h', 'localhost', '-U', 'crawler_user', '-d', 'crawler_db',
                '-t', '-c', 
                "SELECT name FROM domains WHERE url_example IS NOT NULL AND status = 'ACTIVE' ORDER BY name;"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return [{"error": f"Database query error: {result.stderr}"}]
            
            # Parse domain names
            domains = []
            for line in result.stdout.strip().split('\n'):
                domain = line.strip()
                if domain and domain != '':
                    domains.append(domain)
            
        except Exception as e:
            return [{"error": f"Database error: {e}"}]
        
        # Analyze và save từng domain
        results = []
        for domain_name in domains:
            print(f"\n=== Processing {domain_name} ===")
            result = await self.analyze_and_save_domain(domain_name)
            results.append(result)
        
        return results


# Example usage
if __name__ == "__main__":
    import os
    import sys
    import locale
    
    # Fix encoding cho Windows - comprehensive UTF-8 setup
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
    
    # Set console encoding to UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 fallback
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    
    # Set locale to UTF-8 if possible
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except locale.Error:
            print("Warning: Could not set UTF-8 locale")
    
    print("UTF-8 encoding configured successfully")
    
    async def generate_all_schemas():
        """Generate schemas cho tất cả domains có url_example trong database"""
        analyzer = DomainAnalyzer()
        
        # Query tất cả domains có url_example từ database thay vì hardcode
        import subprocess
        
        try:
            # Get all domains có url_example từ database
            cmd = [
                'docker', 'exec', '-e', 'PGPASSWORD=crawler123',
                'crawler_postgres', 'psql', 
                '-h', 'localhost', '-U', 'crawler_user', '-d', 'crawler_db',
                '-t', '-c', 
                "SELECT name FROM domains WHERE url_example IS NOT NULL AND status = 'ACTIVE' ORDER BY name;"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Database query error: {result.stderr}")
                return
            
            # Parse domain names từ database result
            domains = []
            for line in result.stdout.strip().split('\n'):
                domain = line.strip()
                if domain and domain != '':
                    domains.append(domain)
            
            if not domains:
                print("No domains with url_example found in database")
                return
                
            print(f"Found {len(domains)} domains to analyze: {domains}")
            
        except Exception as e:
            print(f"Error querying domains: {e}")
            return
        
        # Analyze từng domain sử dụng REAL analysis thay vì mock
        for domain_name in domains:
            print(f"\n=== Processing {domain_name} ===")
            
            try:
                # Sử dụng real analysis method thay vì mock data
                result = await analyzer.analyze_and_save_domain(domain_name)
                
                if "error" in result:
                    print(f"[ERROR] {result['error']}")
                    continue
                
                if result.get("saved_to_db"):
                    print(f"[OK] Real schema analyzed and saved for {domain_name}")
                    print(f"URL analyzed: {result.get('url_example', 'N/A')}")
                    
                    # Show working selectors count only
                    working_selectors = result.get("working_selectors", {})
                    total_selectors = sum(len(selectors) for selectors in working_selectors.values())
                    print(f"  Found {total_selectors} working selectors")
                else:
                    print(f"[ERROR] Failed to save schema for {domain_name}")
                    
            except Exception as e:
                print(f"[ERROR] Exception analyzing {domain_name}: {e}")
                continue
        
        print(f"\n=== Completed real analysis for all {len(domains)} domains ===")
    
    asyncio.run(generate_all_schemas())