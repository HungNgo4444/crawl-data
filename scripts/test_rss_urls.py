#!/usr/bin/env python3
"""
Simple RSS URL Extractor Test
Just extract URLs from RSS feeds and export them
"""

import asyncio
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import httpx

async def extract_urls_from_rss(rss_url):
    """Extract URLs from RSS feed."""
    print(f"Fetching RSS: {rss_url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(rss_url)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            urls = []
            
            # Extract links from RSS items
            if root.tag == 'rss':
                for item in root.findall('.//item'):
                    link = item.find('link')
                    if link is not None and link.text:
                        urls.append(link.text.strip())
            
            print(f"SUCCESS: Found {len(urls)} URLs")
            return {
                'urls': urls,
                'count': len(urls),
                'status': 'success',
                'error': None
            }
            
        except httpx.TimeoutException:
            error_msg = f"Timeout accessing {rss_url}"
            print(f"ERROR: {error_msg}")
            return {
                'urls': [],
                'count': 0,
                'status': 'timeout',
                'error': error_msg
            }
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} error for {rss_url}"
            print(f"ERROR: {error_msg}")
            return {
                'urls': [],
                'count': 0,
                'status': 'http_error',
                'error': error_msg
            }
        except ET.ParseError as e:
            error_msg = f"XML parse error for {rss_url}: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {
                'urls': [],
                'count': 0,
                'status': 'xml_error',
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error for {rss_url}: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {
                'urls': [],
                'count': 0,
                'status': 'error',
                'error': error_msg
            }

async def main():
    print("RSS URL Extractor Test")
    print("="*30)
    
    # Test RSS feeds - Vietnamese news sites
    rss_feeds = [
        # VnExpress
        "https://vnexpress.net/rss/tin-moi-nhat.rss",
        "https://vnexpress.net/rss/thoi-su.rss",
        "https://vnexpress.net/rss/kinh-doanh.rss",
        
        # Dân Trí  
        "https://dantri.com.vn/rss/trangchu.rss",
        "https://dantri.com.vn/rss/xa-hoi.rss",
        "https://dantri.com.vn/rss/kinh-doanh.rss",
        
        # Tuổi Trẻ
        "https://tuoitre.vn/rss/tin-moi-nhat.rss",
        "https://tuoitre.vn/rss/thoi-su.rss",
        
        # Thanh Niên
        "https://thanhnien.vn/rss/home.rss",
        "https://thanhnien.vn/rss/thoi-su.rss",
        
        # 24H
        "https://www.24h.com.vn/upload/rss/tintuc24h.rss",
        "https://www.24h.com.vn/upload/rss/bongda.rss",
        
        # VOV
        "https://vov.vn/rss/tin-moi-nhat.rss",
        
        # Zing News
        "https://zingnews.vn/rss/tin-moi.rss",
        
        # CafeF
        "https://cafef.vn/rss/trang-chu.rss",
        
        # Báo Mới
        "https://baomoi.com/rss/tin-moi.rss"
    ]
    
    all_results = {}
    successful_feeds = 0
    failed_feeds = 0
    
    # Process feeds concurrently for better performance
    print(f"Processing {len(rss_feeds)} RSS feeds...\n")
    
    for rss_url in rss_feeds:
        result = await extract_urls_from_rss(rss_url)
        
        # Create feed name from URL
        feed_name = rss_url.split('/')[-1].replace('.rss', '')
        domain = rss_url.split('//')[1].split('/')[0]
        
        all_results[f"{domain}_{feed_name}"] = {
            "rss_url": rss_url,
            "domain": domain,
            "urls": result['urls'],
            "count": result['count'],
            "status": result['status'],
            "error": result['error']
        }
        
        if result['status'] == 'success':
            successful_feeds += 1
        else:
            failed_feeds += 1
    
    # Export results
    output_file = f"scripts/rss_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    export_data = {
        "extracted_at": datetime.now().isoformat(),
        "total_feeds": len(rss_feeds),
        "successful_feeds": successful_feeds,
        "failed_feeds": failed_feeds,
        "results": all_results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    # Summary
    total_urls = sum(r["count"] for r in all_results.values())
    print(f"\n{'='*50}")
    print(f"SUMMARY:")
    print(f"{'='*50}")
    print(f"Total feeds processed: {len(rss_feeds)}")
    print(f"SUCCESS: Successful feeds: {successful_feeds}")
    print(f"FAILED: Failed feeds: {failed_feeds}")
    print(f"TOTAL: Total URLs extracted: {total_urls}")
    print(f"FILE: Results saved to: {output_file}")
    
    # Show detailed results
    print(f"\n{'='*50}")
    print(f"DETAILED RESULTS:")
    print(f"{'='*50}")
    
    for feed_name, data in all_results.items():
        status_icon = "SUCCESS" if data['status'] == 'success' else "FAILED"
        print(f"\n[{status_icon}] {data['domain']}")
        print(f"   Feed: {feed_name}")
        print(f"   URLs: {data['count']}")
        print(f"   Status: {data['status']}")
        
        if data['error']:
            print(f"   Error: {data['error']}")
        
        # Show sample URLs for successful feeds
        if data['status'] == 'success' and data['urls']:
            print(f"   Sample URLs:")
            for url in data['urls'][:3]:
                print(f"     - {url}")
    
    print(f"\n{'='*50}")
    print(f"COMPLETE: Export complete! Check {output_file} for full results.")

if __name__ == "__main__":
    asyncio.run(main())