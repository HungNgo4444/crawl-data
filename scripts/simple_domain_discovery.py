#!/usr/bin/env python3
"""
Simple Domain Auto-Discovery Test
Standalone script to test domain discovery with database integration
"""

import asyncio
import logging
from datetime import datetime
import json
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleDomainDiscovery:
    """Simple domain discovery using Crawl4AI"""
    
    def __init__(self):
        # Vietnamese article patterns
        self.vn_article_patterns = [
            r'\/[\w\-]+\-\d+\.html?$',
            r'\/[\w\-]+\-\d+\.htm$',
            r'\/[\w\-]+\-c\d+a\d+\.html$',
            r'\/[\w\-]+\-\d+\.vnp$',
            r'\/[\w\-]+\-\d+\.vov$',
            r'\/[\w\-]+\-\d+\.chn$',
            r'\/[\w\-]+\-\d+\.aspx$',
        ]
        
        # Vietnamese categories
        self.vn_categories = [
            'tin-tuc', 'thoi-su', 'the-gioi', 'kinh-te', 'giai-tri', 
            'the-thao', 'cong-nghe', 'suc-khoe', 'phap-luat'
        ]
    
    async def discover_domain_resources(self, domain_name: str) -> Dict[str, Any]:
        """Discover domain resources"""
        
        # Normalize domain
        if not domain_name.startswith(('http://', 'https://')):
            base_url = f"https://{domain_name}"
        else:
            parsed = urlparse(domain_name)
            domain_name = parsed.netloc
            base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        logger.info(f"Discovering resources for: {domain_name}")
        
        result = {
            'domain_name': domain_name,
            'base_url': base_url,
            'homepage_title': '',
            'rss_feeds': [],
            'sitemaps': [],
            'category_pages': [],
            'confidence_score': 0.0,
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_errors': []
        }
        
        browser_config = {
            'headless': True,
            'browser_type': 'chromium',
            'viewport_width': 1920,
            'viewport_height': 1080,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'verbose': False
        }
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # 1. Analyze homepage
                await self._analyze_homepage(crawler, result)
                await asyncio.sleep(2)
                
                # 2. Check RSS feeds
                await self._discover_rss_feeds(crawler, result)
                await asyncio.sleep(2)
                
                # 3. Check sitemaps
                await self._discover_sitemaps(crawler, result)
                await asyncio.sleep(2)
                
                # 4. Check categories
                await self._discover_categories(crawler, result)
                
            # Calculate confidence
            result['confidence_score'] = self._calculate_confidence(result)
            
        except Exception as e:
            error_msg = f"Discovery failed: {str(e)}"
            result['analysis_errors'].append(error_msg)
            logger.error(f"Error discovering {domain_name}: {e}")
        
        return result
    
    async def _analyze_homepage(self, crawler, result):
        """Analyze homepage"""
        try:
            logger.info(f"Analyzing homepage: {result['base_url']}")
            
            config = {'page_timeout': 30000, 'word_count_threshold': 10}
            crawl_result = await crawler.arun(url=result['base_url'], config=config)
            
            if crawl_result.success:
                # Extract title
                if hasattr(crawl_result, 'title') and crawl_result.title:
                    result['homepage_title'] = crawl_result.title
                
                logger.info(f"Homepage analyzed successfully: {result['homepage_title'][:50]}...")
                
            else:
                error_msg = f"Homepage crawl failed"
                result['analysis_errors'].append(error_msg)
                logger.warning(error_msg)
                
        except Exception as e:
            error_msg = f"Homepage analysis error: {str(e)}"
            result['analysis_errors'].append(error_msg)
            logger.error(error_msg)
    
    async def _discover_rss_feeds(self, crawler, result):
        """Discover RSS feeds"""
        rss_feeds = set()
        
        # Common RSS paths
        common_rss_paths = [
            '/rss', '/rss.xml', '/feed', '/feed.xml', '/atom.xml',
            '/rss/news', '/rss/tin-tuc', '/index.xml'
        ]
        
        try:
            for path in common_rss_paths:
                rss_url = urljoin(result['base_url'], path)
                
                if await self._validate_rss(crawler, rss_url):
                    rss_feeds.add(rss_url)
                    logger.info(f"Found RSS feed: {rss_url}")
                
                await asyncio.sleep(1)  # Be respectful
            
            result['rss_feeds'] = list(rss_feeds)
            logger.info(f"Total RSS feeds: {len(result['rss_feeds'])}")
            
        except Exception as e:
            error_msg = f"RSS discovery error: {str(e)}"
            result['analysis_errors'].append(error_msg)
            logger.error(error_msg)
    
    async def _discover_sitemaps(self, crawler, result):
        """Discover sitemaps"""
        sitemaps = set()
        
        try:
            # Check robots.txt
            robots_url = urljoin(result['base_url'], '/robots.txt')
            
            config = {'page_timeout': 15000}
            robots_result = await crawler.arun(url=robots_url, config=config)
            
            if robots_result.success and hasattr(robots_result, 'markdown'):
                content = robots_result.markdown or ''
                import re
                sitemap_matches = re.findall(r'Sitemap:\s*(.+)', content, re.IGNORECASE)
                for sitemap_url in sitemap_matches:
                    sitemaps.add(sitemap_url.strip())
                    logger.info(f"Found sitemap in robots.txt: {sitemap_url.strip()}")
            
            # Check common sitemap paths
            common_paths = ['/sitemap.xml', '/sitemap_index.xml', '/sitemaps.xml']
            
            for path in common_paths:
                sitemap_url = urljoin(result['base_url'], path)
                
                if await self._validate_sitemap(crawler, sitemap_url):
                    sitemaps.add(sitemap_url)
                    logger.info(f"Found sitemap: {sitemap_url}")
                
                await asyncio.sleep(1)
            
            result['sitemaps'] = list(sitemaps)
            logger.info(f"Total sitemaps: {len(result['sitemaps'])}")
            
        except Exception as e:
            error_msg = f"Sitemap discovery error: {str(e)}"
            result['analysis_errors'].append(error_msg)
            logger.error(error_msg)
    
    async def _discover_categories(self, crawler, result):
        """Discover category pages"""
        categories = set()
        
        try:
            for category in self.vn_categories:
                category_url = urljoin(result['base_url'], f'/{category}')
                
                if await self._validate_category(crawler, category_url):
                    categories.add(category_url)
                    logger.info(f"Found category: {category_url}")
                
                await asyncio.sleep(1)
            
            result['category_pages'] = list(categories)
            logger.info(f"Total categories: {len(result['category_pages'])}")
            
        except Exception as e:
            error_msg = f"Category discovery error: {str(e)}"
            result['analysis_errors'].append(error_msg)
            logger.error(error_msg)
    
    async def _validate_rss(self, crawler, url):
        """Validate RSS feed"""
        try:
            config = {'page_timeout': 10000}
            result = await crawler.arun(url=url, config=config)
            
            if result.success and hasattr(result, 'markdown'):
                content = result.markdown or ''
                return any(tag in content.lower() for tag in ['<rss', '<feed', '<channel', '<item'])
        except:
            pass
        return False
    
    async def _validate_sitemap(self, crawler, url):
        """Validate sitemap"""
        try:
            config = {'page_timeout': 10000}
            result = await crawler.arun(url=url, config=config)
            
            if result.success and hasattr(result, 'markdown'):
                content = result.markdown or ''
                return any(tag in content.lower() for tag in ['<urlset', '<sitemapindex', '<sitemap'])
        except:
            pass
        return False
    
    async def _validate_category(self, crawler, url):
        """Validate category page"""
        try:
            config = {'page_timeout': 10000}
            result = await crawler.arun(url=url, config=config)
            return result.success
        except:
            pass
        return False
    
    def _calculate_confidence(self, result):
        """Calculate confidence score"""
        score = 0.0
        
        if result['rss_feeds']:
            score += 0.3
        if result['sitemaps']:
            score += 0.2
        if result['category_pages']:
            score += 0.3
        if result['homepage_title']:
            score += 0.1
        if not result['analysis_errors']:
            score += 0.1
            
        return min(score, 1.0)

def save_to_database(result: Dict[str, Any]) -> bool:
    """Save results to database"""
    try:
        with psycopg2.connect(
            host="localhost",
            port=5432,
            database="crawler_db", 
            user="crawler_user",
            password="crawler123",
            options="-c client_encoding=utf8"
        ) as conn:
            with conn.cursor() as cursor:
                
                # Update domains table
                update_sql = """
                    UPDATE domains 
                    SET 
                        rss_feeds = %s,
                        sitemaps = %s,
                        last_analyzed_at = %s,
                        analysis_model = %s
                    WHERE name = %s
                """
                
                rss_feeds_json = json.dumps(result['rss_feeds'])
                sitemaps_json = json.dumps(result['sitemaps'])
                
                cursor.execute(update_sql, (
                    rss_feeds_json,
                    sitemaps_json,
                    datetime.now(),
                    'crawl4ai-auto-discovery',
                    result['domain_name']
                ))
                
                rows_affected = cursor.rowcount
                conn.commit()
                
                if rows_affected > 0:
                    logger.info(f"Successfully updated database for {result['domain_name']}")
                    return True
                else:
                    logger.warning(f"No rows updated for {result['domain_name']}")
                    return False
                    
    except Exception as e:
        logger.error(f"Database save error: {e}")
        return False

async def test_domain(domain_name: str):
    """Test discovery for single domain"""
    
    discovery = SimpleDomainDiscovery()
    
    # Run discovery
    result = await discovery.discover_domain_resources(domain_name)
    
    # Save to database
    saved = save_to_database(result)
    
    # Print results
    print(f"\n{'='*80}")
    print(f"DOMAIN AUTO-DISCOVERY RESULTS: {domain_name}")
    print(f"{'='*80}")
    print(f"Base URL: {result['base_url']}")
    print(f"Homepage Title: {result['homepage_title']}")
    print(f"Confidence Score: {result['confidence_score']:.2f}")
    print(f"Database Saved: {'YES' if saved else 'NO'}")
    
    print(f"\n📡 RSS FEEDS ({len(result['rss_feeds'])}):")
    for i, rss in enumerate(result['rss_feeds'], 1):
        print(f"  {i}. {rss}")
    
    print(f"\n🗺️ SITEMAPS ({len(result['sitemaps'])}):")
    for i, sitemap in enumerate(result['sitemaps'], 1):
        print(f"  {i}. {sitemap}")
    
    print(f"\n📂 CATEGORIES ({len(result['category_pages'])}):")
    for i, category in enumerate(result['category_pages'][:10], 1):  # Show first 10
        print(f"  {i}. {category}")
    
    if result['analysis_errors']:
        print(f"\n❌ ERRORS ({len(result['analysis_errors'])}):")
        for i, error in enumerate(result['analysis_errors'], 1):
            print(f"  {i}. {error}")
    
    print(f"\n{'='*80}")
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"scripts/discovery_{domain_name.replace('.', '_')}_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to: {output_file}")
    
    return result

async def test_all_domains():
    """Test discovery for all active domains"""
    
    # Get domains from database
    try:
        with psycopg2.connect(
            host="localhost",
            port=5432,
            database="crawler_db", 
            user="crawler_user",
            password="crawler123",
            options="-c client_encoding=utf8"
        ) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT name FROM domains WHERE status = 'ACTIVE' ORDER BY name")
                domains = [row['name'] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Database query error: {e}")
        return
    
    if not domains:
        print("No active domains found in database")
        return
    
    print(f"Found {len(domains)} active domains: {', '.join(domains)}")
    
    results = {}
    discovery = SimpleDomainDiscovery()
    
    for domain_name in domains:
        try:
            logger.info(f"Processing domain: {domain_name}")
            result = await discovery.discover_domain_resources(domain_name)
            save_to_database(result)
            results[domain_name] = result
            
            # Respectful delay between domains
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Failed to process {domain_name}: {e}")
            continue
    
    # Print summary
    print(f"\n{'='*100}")
    print(f"AUTO-DISCOVERY SUMMARY - ALL DOMAINS")
    print(f"{'='*100}")
    print(f"Domains processed: {len(results)}")
    
    total_rss = sum(len(r['rss_feeds']) for r in results.values())
    total_sitemaps = sum(len(r['sitemaps']) for r in results.values())
    total_categories = sum(len(r['category_pages']) for r in results.values())
    avg_confidence = sum(r['confidence_score'] for r in results.values()) / len(results) if results else 0
    
    print(f"Total RSS feeds: {total_rss}")
    print(f"Total sitemaps: {total_sitemaps}")
    print(f"Total categories: {total_categories}")
    print(f"Average confidence: {avg_confidence:.2f}")
    
    print(f"\n📊 DETAILED BREAKDOWN:")
    for domain_name, result in results.items():
        confidence = result['confidence_score']
        status = "✅" if confidence > 0.5 else "⚠️" if confidence > 0.2 else "❌"
        print(f"  {status} {domain_name:15} | RSS: {len(result['rss_feeds']):2d} | Sitemaps: {len(result['sitemaps']):2d} | Categories: {len(result['category_pages']):2d} | Confidence: {confidence:.2f}")
    
    # Save all results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"scripts/all_domains_discovery_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nAll results saved to: {output_file}")
    print(f"{'='*100}")

async def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        # Test single domain
        domain_name = sys.argv[1]
        await test_domain(domain_name)
    else:
        # Test all domains
        await test_all_domains()

if __name__ == "__main__":
    asyncio.run(main())