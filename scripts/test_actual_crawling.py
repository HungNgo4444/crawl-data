#!/usr/bin/env python3
"""
Test Actual URL Crawling from Vietnamese News Domains
Crawls real article URLs from the domains and saves to JSON
"""

import asyncio
import aiohttp
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urljoin, urlparse
import time

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/actual_crawling_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NewsArticleCrawler:
    """
    Crawler to extract actual article URLs from Vietnamese news domains
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.target_domains = [
            {"name": "soha.vn", "base_url": "https://soha.vn"},
            {"name": "vietnamnet.vn", "base_url": "https://vietnamnet.vn"},
            {"name": "vietnamplus.vn", "base_url": "https://vietnamplus.vn"},
            {"name": "tuoitre.vn", "base_url": "https://tuoitre.vn"},
            {"name": "vov.vn", "base_url": "https://vov.vn"},
            {"name": "24h.com.vn", "base_url": "https://www.24h.com.vn"},
            {"name": "thanhnien.vn", "base_url": "https://thanhnien.vn"},
            {"name": "cafef.vn", "base_url": "https://cafef.vn"},
            {"name": "thainguyen.vn", "base_url": "https://thainguyen.vn"},
            {"name": "vnexpress.net", "base_url": "https://vnexpress.net"},
            {"name": "genk.vn", "base_url": "https://genk.vn"}
        ]
        
        # Article URL patterns for each domain
        self.url_patterns = {
            "soha.vn": [r"\/[\w\-]+\.htm$", r"\/[\w\-]+\-\d+\.htm$"],
            "vietnamnet.vn": [r"\/[\w\-]+\-\d+\.html$", r"\/[\w\-]+\.html$"],
            "vietnamplus.vn": [r"\/[\w\-]+\-\d+\.vnp$", r"\/[\w\-]+\.vnp$"],
            "tuoitre.vn": [r"\/[\w\-]+\-\d+\.htm$", r"\/[\w\-]+\-\d+\.html$"],
            "vov.vn": [r"\/[\w\-]+\-\d+\.vov$", r"\/[\w\-]+\.html$"],
            "24h.com.vn": [r"\/[\w\-]+\-c\d+a\d+\.html$", r"\/[\w\-]+\.html$"],
            "thanhnien.vn": [r"\/[\w\-]+\-\d+\.htm$", r"\/[\w\-]+\.htm$"],
            "cafef.vn": [r"\/[\w\-]+\-\d+\.chn$", r"\/[\w\-]+\.html$"],
            "thainguyen.vn": [r"\/[\w\-]+\-\d+\.aspx$", r"\/[\w\-]+\.html$"],
            "vnexpress.net": [r"\/[\w\-]+\-\d+\.html$", r"\/sport\/[\w\-]+\-\d+\.html$"],
            "genk.vn": [r"\/[\w\-]+\-\d+\.chn$", r"\/[\w\-]+\.html$"]
        }
        
        self.crawl_results = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=headers
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def is_article_url(self, url: str, domain_name: str) -> bool:
        """Check if URL matches article patterns for the domain"""
        if domain_name not in self.url_patterns:
            return False
        
        patterns = self.url_patterns[domain_name]
        for pattern in patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def extract_urls_from_html(self, html: str, base_url: str, domain_name: str) -> Set[str]:
        """Extract article URLs from HTML content"""
        article_urls = set()
        
        # Simple regex to find href attributes
        href_pattern = r'href=["\']([^"\']+)["\']'
        matches = re.findall(href_pattern, html, re.IGNORECASE)
        
        for match in matches:
            # Handle relative URLs
            if match.startswith('/'):
                full_url = urljoin(base_url, match)
            elif match.startswith('http'):
                # Only accept URLs from the same domain
                parsed = urlparse(match)
                if domain_name in parsed.netloc:
                    full_url = match
                else:
                    continue
            else:
                continue
            
            # Check if it's an article URL
            if self.is_article_url(full_url, domain_name):
                article_urls.add(full_url)
        
        return article_urls
    
    async def crawl_domain_homepage(self, domain: Dict[str, str]) -> List[str]:
        """Crawl homepage and main sections of a domain to find article URLs"""
        domain_name = domain["name"]
        base_url = domain["base_url"]
        
        logger.info(f"Crawling domain: {domain_name}")
        
        article_urls = set()
        
        try:
            # Crawl homepage
            logger.info(f"Crawling homepage: {base_url}")
            async with self.session.get(base_url) as response:
                if response.status == 200:
                    html = await response.text()
                    urls = self.extract_urls_from_html(html, base_url, domain_name)
                    article_urls.update(urls)
                    logger.info(f"Found {len(urls)} article URLs on homepage")
                else:
                    logger.warning(f"Homepage returned HTTP {response.status}")
            
            # Try common section pages
            common_sections = [
                '/tin-tuc', '/thoi-su', '/the-gioi', '/kinh-te', '/giai-tri', 
                '/the-thao', '/cong-nghe', '/suc-khoe', '/du-lich', '/news',
                '/world', '/business', '/sports', '/tech', '/health', '/travel',
                '/trang-chu', '/home'
            ]
            
            for section in common_sections[:5]:  # Limit to first 5 sections
                section_url = base_url + section
                try:
                    logger.info(f"Crawling section: {section_url}")
                    async with self.session.get(section_url) as response:
                        if response.status == 200:
                            html = await response.text()
                            urls = self.extract_urls_from_html(html, base_url, domain_name)
                            article_urls.update(urls)
                            logger.info(f"Found {len(urls)} article URLs in section {section}")
                        await asyncio.sleep(1)  # Be respectful with delays
                except Exception as e:
                    logger.warning(f"Error crawling section {section}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error crawling domain {domain_name}: {e}")
        
        return list(article_urls)
    
    async def crawl_all_domains(self) -> Dict[str, List[str]]:
        """Crawl all target domains and collect article URLs"""
        logger.info("Starting to crawl all domains for article URLs")
        
        for domain in self.target_domains:
            domain_name = domain["name"]
            
            try:
                urls = await self.crawl_domain_homepage(domain)
                self.crawl_results[domain_name] = {
                    "base_url": domain["base_url"],
                    "article_urls": urls,
                    "total_urls": len(urls),
                    "crawl_timestamp": datetime.now().isoformat(),
                    "status": "success"
                }
                
                logger.info(f"Domain {domain_name}: Found {len(urls)} article URLs")
                
                # Add delay between domains to be respectful
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Failed to crawl domain {domain_name}: {e}")
                self.crawl_results[domain_name] = {
                    "base_url": domain["base_url"],
                    "article_urls": [],
                    "total_urls": 0,
                    "crawl_timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": str(e)
                }
        
        return self.crawl_results
    
    def save_results_to_json(self, filename: Optional[str] = None) -> str:
        """Save crawling results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vietnamese_news_article_urls_{timestamp}.json"
        
        filepath = f"scripts/{filename}"
        
        # Calculate summary
        summary = {
            "crawl_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_domains": len(self.crawl_results),
                "successful_domains": len([d for d in self.crawl_results.values() if d["status"] == "success"]),
                "failed_domains": len([d for d in self.crawl_results.values() if d["status"] == "error"]),
                "total_urls_found": sum(d["total_urls"] for d in self.crawl_results.values()),
                "domains_with_urls": {name: data["total_urls"] for name, data in self.crawl_results.items()}
            },
            "domain_results": self.crawl_results
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return ""

async def main():
    """Main crawling execution function"""
    logger.info("Starting Vietnamese News Article URL Crawler")
    
    async with NewsArticleCrawler() as crawler:
        try:
            # Start crawling all domains
            results = await crawler.crawl_all_domains()
            
            # Save results to JSON file
            output_file = crawler.save_results_to_json()
            
            # Print summary
            print("\n" + "="*80)
            print("VIETNAMESE NEWS ARTICLE URL CRAWLING SUMMARY")
            print("="*80)
            
            total_domains = len(results)
            successful = len([d for d in results.values() if d["status"] == "success"])
            failed = total_domains - successful
            total_urls = sum(d["total_urls"] for d in results.values())
            
            print(f"Total domains crawled: {total_domains}")
            print(f"Successful: {successful}, Failed: {failed}")
            print(f"Total article URLs found: {total_urls}")
            print(f"Results saved to: {output_file}")
            print("\nURLs found per domain:")
            
            for domain_name, data in results.items():
                status = data["status"]
                url_count = data["total_urls"]
                print(f"  {domain_name}: {url_count} URLs ({'SUCCESS' if status == 'success' else 'FAILED'})")
            
            print("="*80)
            
        except Exception as e:
            logger.error(f"Crawling execution failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())