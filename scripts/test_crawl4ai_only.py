#!/usr/bin/env python3
"""
Test Crawl4AI domain discovery only (without database)
"""

import asyncio
import logging
from datetime import datetime
import json
from urllib.parse import urljoin, urlparse

from crawl4ai import AsyncWebCrawler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_domain_discovery(domain_name: str):
    """Test Crawl4AI domain discovery"""
    
    # Normalize domain
    if not domain_name.startswith(('http://', 'https://')):
        base_url = f"https://{domain_name}"
    else:
        parsed = urlparse(domain_name)
        domain_name = parsed.netloc
        base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    logger.info(f"Testing discovery for: {domain_name}")
    
    result = {
        'domain_name': domain_name,
        'base_url': base_url,
        'homepage_title': '',
        'rss_feeds': [],
        'sitemaps': [],
        'category_pages': [],
        'analysis_timestamp': datetime.now().isoformat(),
        'analysis_errors': []
    }
    
    # Browser config
    browser_config = {
        'headless': True,
        'browser_type': 'chromium',
        'verbose': False
    }
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            
            # 1. Test homepage
            logger.info(f"Testing homepage: {base_url}")
            
            config = {'page_timeout': 30000, 'word_count_threshold': 10}
            crawl_result = await crawler.arun(url=base_url, config=config)
            
            if crawl_result.success:
                if hasattr(crawl_result, 'title') and crawl_result.title:
                    result['homepage_title'] = crawl_result.title
                logger.info(f"Homepage OK: {result['homepage_title'][:50]}...")
            else:
                result['analysis_errors'].append("Homepage crawl failed")
            
            await asyncio.sleep(2)
            
            # 2. Test common RSS paths
            rss_paths = ['/rss', '/rss.xml', '/feed', '/feed.xml']
            
            for path in rss_paths:
                rss_url = urljoin(base_url, path)
                
                try:
                    config = {'page_timeout': 10000}
                    rss_result = await crawler.arun(url=rss_url, config=config)
                    
                    if rss_result.success and hasattr(rss_result, 'markdown'):
                        content = rss_result.markdown or ''
                        if any(tag in content.lower() for tag in ['<rss', '<feed', '<channel', '<item']):
                            result['rss_feeds'].append(rss_url)
                            logger.info(f"Found RSS: {rss_url}")
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.debug(f"RSS test failed for {rss_url}: {e}")
            
            # 3. Test sitemaps
            sitemap_paths = ['/sitemap.xml', '/sitemap_index.xml']
            
            for path in sitemap_paths:
                sitemap_url = urljoin(base_url, path)
                
                try:
                    config = {'page_timeout': 10000}
                    sitemap_result = await crawler.arun(url=sitemap_url, config=config)
                    
                    if sitemap_result.success and hasattr(sitemap_result, 'markdown'):
                        content = sitemap_result.markdown or ''
                        if any(tag in content.lower() for tag in ['<urlset', '<sitemapindex', '<sitemap']):
                            result['sitemaps'].append(sitemap_url)
                            logger.info(f"Found sitemap: {sitemap_url}")
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.debug(f"Sitemap test failed for {sitemap_url}: {e}")
            
            # 4. Test categories
            vn_categories = ['tin-tuc', 'thoi-su', 'the-gioi', 'kinh-te', 'giai-tri']
            
            for category in vn_categories:
                category_url = urljoin(base_url, f'/{category}')
                
                try:
                    config = {'page_timeout': 10000}
                    category_result = await crawler.arun(url=category_url, config=config)
                    
                    if category_result.success:
                        result['category_pages'].append(category_url)
                        logger.info(f"Found category: {category_url}")
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.debug(f"Category test failed for {category_url}: {e}")
        
        # Calculate confidence
        confidence = 0.0
        if result['rss_feeds']:
            confidence += 0.3
        if result['sitemaps']:
            confidence += 0.2
        if result['category_pages']:
            confidence += 0.3
        if result['homepage_title']:
            confidence += 0.1
        if not result['analysis_errors']:
            confidence += 0.1
        
        result['confidence_score'] = min(confidence, 1.0)
        
    except Exception as e:
        error_msg = f"Discovery failed: {str(e)}"
        result['analysis_errors'].append(error_msg)
        logger.error(f"Error: {e}")
    
    return result

async def main():
    """Main test function"""
    import sys
    
    domain_name = sys.argv[1] if len(sys.argv) > 1 else 'vnexpress.net'
    
    print(f"Testing Crawl4AI domain discovery for: {domain_name}")
    print("=" * 80)
    
    result = await test_domain_discovery(domain_name)
    
    # Print results
    print(f"\nDOMAIN DISCOVERY RESULTS")
    print("=" * 50)
    print(f"Domain: {result['domain_name']}")
    print(f"Base URL: {result['base_url']}")
    print(f"Homepage Title: {result['homepage_title']}")
    print(f"Confidence Score: {result['confidence_score']:.2f}")
    print(f"Analysis Time: {result['analysis_timestamp']}")
    
    print(f"\nRSS FEEDS ({len(result['rss_feeds'])}):")
    for i, rss in enumerate(result['rss_feeds'], 1):
        print(f"  {i}. {rss}")
    
    print(f"\nSITEMAPS ({len(result['sitemaps'])}):")
    for i, sitemap in enumerate(result['sitemaps'], 1):
        print(f"  {i}. {sitemap}")
    
    print(f"\nCATEGORIES ({len(result['category_pages'])}):")
    for i, category in enumerate(result['category_pages'], 1):
        print(f"  {i}. {category}")
    
    if result['analysis_errors']:
        print(f"\nERRORS ({len(result['analysis_errors'])}):")
        for i, error in enumerate(result['analysis_errors'], 1):
            print(f"  {i}. {error}")
    
    print("=" * 80)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"scripts/crawl4ai_test_{domain_name.replace('.', '_')}_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())