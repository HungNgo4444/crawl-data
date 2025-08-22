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

async def test_sitemap_crawler():
    """Test the sitemap crawler with Vietnamese news domains."""
    print("Sitemap Crawler Test")
    print("=" * 40)
    
    # Initialize the sitemap crawler
    logger = logging.getLogger("SITEMAP_TEST")
    crawler = SitemapCrawler(logger=logger)
    
    # Test domains - Vietnamese news sites
    test_domains = [
        {
            "domain": "vnexpress.net",
            "base_url": "https://vnexpress.net",
            "max_urls": 10  # Limit for testing
        },
        {
            "domain": "dantri.com.vn", 
            "base_url": "https://dantri.com.vn",
            "max_urls": 10
        },
        {
            "domain": "tuoitre.vn",
            "base_url": "https://tuoitre.vn",
            "max_urls": 10
        }
    ]
    
    all_results = []
    successful_domains = 0
    total_urls = 0
    total_images_found = 0
    
    try:
        for domain_info in test_domains:
            print(f"\nTesting: {domain_info['domain']}")
            print(f"Base URL: {domain_info['base_url']}")
            
            # Create sitemap config
            config = SitemapConfig(
                domain=domain_info['domain'],
                base_url=domain_info['base_url'],
                max_urls=domain_info['max_urls'],
                crawl_full_content=True,  # Enable full content crawling
                auto_detect=True
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
                    
                    # Check if full content was crawled
                    if url_obj.crawled_content:
                        content_length = len(url_obj.crawled_content)
                        print(f"   Full Content: {content_length} characters crawled")
                        print(f"   Crawl Success: {url_obj.crawl_metadata.get('success', False)}")
                    else:
                        print(f"   Full Content: Not crawled")
                    
                    if url_obj.url_image:
                        total_images_found += 1
                    
                    # Add to results
                    url_data = {
                        "url": url_obj.url,
                        "lastmod": url_obj.lastmod.isoformat() if url_obj.lastmod else None,
                        "changefreq": url_obj.changefreq,
                        "priority": url_obj.priority,
                        "url_image": url_obj.url_image,
                        "content_length": len(url_obj.crawled_content) if url_obj.crawled_content else 0,
                        "crawl_metadata": url_obj.crawl_metadata
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