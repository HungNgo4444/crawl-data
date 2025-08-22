#!/usr/bin/env python3
"""
Sitemap Crawler Test
Extract sitemap data: url, title, lastmod, changefreq, priority, url_image
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the worker source path to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "enhanced-crawler-worker" / "src"))

from workers.sitemap_crawler import SitemapCrawler, SitemapConfig
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_domains_from_database():
    """Get domains with sitemap data from database."""
    # Data extracted from database using docker exec
    return [
        {
            'name': 'vov.vn',
            'base_url': 'https://vov.vn',
            'sitemaps': [
                "https://vov.vn/maps/sitemap.xml", 
                "https://vov.vn/sitemap.xml", 
                "https://vov.vn/sitemaps/posts.xml", 
                "https://vov.vn/content/sitemap.xml", 
                "https://vov.vn/feed/sitemap.xml", 
                "https://vov.vn/sitemap-news.xml", 
                "https://vov.vn/sitemaps/newsindex.xml", 
                "https://vov.vn/sitemaps/news.xml", 
                "https://vov.vn/sitemap.html", 
                "https://vov.vn/sitemap-content.xml", 
                "https://vov.vn/sitemap-pages.xml", 
                "https://vov.vn/maps/site-map.xml", 
                "https://vov.vn/sitemap.htm", 
                "https://vov.vn/pages/sitemap.xml", 
                "https://vov.vn/rss/sitemap.xml"
            ]
        },
        {
            'name': 'laodong.vn',
            'base_url': 'https://laodong.vn',
            'sitemaps': [
                "https://laodong.vn/site-map.xml", 
                "https://laodong.vn/sitemaps.xml", 
                "https://laodong.vn/post-sitemap.xml", 
                "https://laodong.vn/content/sitemap.xml", 
                "https://laodong.vn/wp-sitemap.xml", 
                "https://laodong.vn/rss/sitemap.xml", 
                "https://laodong.vn/sitemap.xml", 
                "https://laodong.vn/sitemap_index.xml", 
                "https://laodong.vn/maps/sitemap.xml", 
                "https://laodong.vn/sitemap-pages.xml", 
                "https://laodong.vn/sitemap/sitemap.xml", 
                "https://laodong.vn/sitemap-news.xml", 
                "https://laodong.vn/sitemaps/sitemap.xml", 
                "https://laodong.vn/pages/sitemap.xml", 
                "https://laodong.vn/feed/sitemap.xml"
            ]
        },
        {
            'name': 'sggp.org.vn',
            'base_url': 'https://sggp.org.vn',
            'sitemaps': [
                "https://www.sggp.org.vn/sitemaps/index.xml", 
                "https://www.sggp.org.vn/sitemaps.xml", 
                "https://www.sggp.org.vn/sitemaps/posts.xml", 
                "https://www.sggp.org.vn/sitemap.xml", 
                "https://www.sggp.org.vn/sitemaps/sitemap.xml", 
                "https://www.sggp.org.vn/sitemaps/main.xml", 
                "https://www.sggp.org.vn/sitemaps/articles.xml", 
                "https://www.sggp.org.vn/sitemaps/google-news.xml", 
                "https://www.sggp.org.vn/sitemaps/newsindex.xml", 
                "https://www.sggp.org.vn/sitemaps/news.xml"
            ]
        }
    ]

async def test_sitemap_crawler():
    """Test the sitemap crawler with domains from database."""
    print("Sitemap Crawler Test - Using Database Sitemaps")
    print("=" * 50)
    
    # Get domains from database
    db_domains = get_domains_from_database()
    
    if not db_domains:
        print("No domains with sitemaps found in database!")
        return
    
    print(f"Found {len(db_domains)} domains with sitemap data in database:")
    for domain in db_domains:
        sitemap_count = len(domain['sitemaps']) if domain['sitemaps'] else 0
        print(f"  - {domain['name']}: {sitemap_count} sitemaps")
    
    # Initialize the sitemap crawler
    logger = logging.getLogger("SITEMAP_TEST")
    crawler = SitemapCrawler(logger=logger)
    
    # Convert database domains to test format
    test_domains = []
    for domain in db_domains:
        test_domains.append({
            "domain": domain['name'],
            "base_url": domain['base_url'],
            "sitemaps": domain['sitemaps'],
            "max_urls": 10  # Limit for testing
        })
    
    all_results = []
    successful_domains = 0
    total_urls = 0
    total_images_found = 0
    
    try:
        for domain_info in test_domains:
            print(f"\nTesting: {domain_info['domain']}")
            print(f"Base URL: {domain_info['base_url']}")
            print(f"Sitemaps from DB: {len(domain_info.get('sitemaps', []))}")
            
            # Create sitemap config with database sitemaps
            config = SitemapConfig(
                domain=domain_info['domain'],
                base_url=domain_info['base_url'],
                max_urls=domain_info['max_urls'],
                crawl_full_content=False,  # Disable full content crawling for testing
                auto_detect=False,  # Use provided sitemaps, don't auto-detect
                sitemap_urls=domain_info.get('sitemaps', [])
            )
            
            # Test sitemap crawling
            result = await crawler.crawl_sitemaps(config)
            
            if result.success:
                successful_domains += 1
                print(f"SUCCESS: Found {len(result.discovered_urls)} URLs")
                
                domain_result = {
                    "domain_info": domain_info,
                    "success": True,
                    "total_sitemaps_processed": result.total_sitemaps_processed,
                    "total_urls_found": result.total_urls_found,
                    "execution_time": result.execution_time,
                    "urls": []
                }
                
                # Process each URL
                for i, url_obj in enumerate(result.discovered_urls, 1):
                    print(f"\nURL {i}:")
                    print(f"   URL: {url_obj.url}")
                    print(f"   Last Modified: {url_obj.lastmod or 'N/A'}")
                    print(f"   Change Frequency: {url_obj.changefreq or 'N/A'}")
                    print(f"   Priority: {url_obj.priority or 'N/A'}")
                    print(f"   Image URL: {url_obj.url_image or 'N/A'}")
                    
                    if url_obj.url_image:
                        total_images_found += 1
                    
                    # Add to results
                    url_data = {
                        "url": url_obj.url,
                        "lastmod": url_obj.lastmod.isoformat() if url_obj.lastmod else None,
                        "changefreq": url_obj.changefreq,
                        "priority": url_obj.priority,
                        "url_image": url_obj.url_image
                    }
                    domain_result["urls"].append(url_data)
                
                total_urls += len(result.discovered_urls)
                all_results.append(domain_result)
                
            else:
                print(f"FAILED: {result.error}")
                all_results.append({
                    "domain_info": domain_info,
                    "success": False,
                    "error": result.error,
                    "execution_time": result.execution_time
                })
    
    finally:
        # Clean up crawler resources
        await crawler.close()
    
    # Export detailed results
    output_file = f"scripts/sitemap_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    export_data = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "total_domains_tested": len(test_domains),
            "successful_domains": successful_domains,
            "failed_domains": len(test_domains) - successful_domains,
            "total_urls_found": total_urls,
            "total_images_found": total_images_found,
            "image_extraction_rate": f"{(total_images_found/total_urls)*100:.1f}%" if total_urls > 0 else "0%"
        },
        "results": all_results
    }
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total domains tested: {len(test_domains)}")
    print(f"Successful domains: {successful_domains}")
    print(f"Failed domains: {len(test_domains) - successful_domains}")
    print(f"Total URLs found: {total_urls}")
    print(f"Images found: {total_images_found}")
    print(f"Image extraction rate: {(total_images_found/total_urls)*100:.1f}%" if total_urls > 0 else "0%")
    print(f"Results saved to: {output_file}")
    
    print(f"\nTest completed! Check {output_file} for detailed results.")

async def main():
    """Main test function."""
    try:
        await test_sitemap_crawler()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test
    asyncio.run(main())