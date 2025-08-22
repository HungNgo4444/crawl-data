#!/usr/bin/env python3
"""
Enhanced RSS Data Extractor Test
Extract full RSS data: url, title, category, author, description, publish date, content, url_image
"""

import asyncio
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import httpx
import re
from urllib.parse import urljoin, urlparse

async def extract_data_from_rss(rss_url):
    """Extract full data from RSS feed."""
    print(f"Fetching RSS: {rss_url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(rss_url)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            items = []
            
            # Extract full data from RSS items
            if root.tag == 'rss':
                for item_elem in root.findall('.//item'):
                    # Basic fields
                    title_elem = item_elem.find('title')
                    title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                    
                    link_elem = item_elem.find('link')
                    url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                    
                    desc_elem = item_elem.find('description')
                    description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else None
                    
                    # Author
                    author_elem = item_elem.find('author') or item_elem.find('dc:creator', {'dc': 'http://purl.org/dc/elements/1.1/'})
                    author = author_elem.text.strip() if author_elem is not None and author_elem.text else None
                    
                    # Categories
                    categories = []
                    for cat_elem in item_elem.findall('category'):
                        if cat_elem.text:
                            categories.append(cat_elem.text.strip())
                    
                    # Publish date
                    pub_date_elem = item_elem.find('pubDate')
                    publish_date = pub_date_elem.text.strip() if pub_date_elem is not None and pub_date_elem.text else None
                    
                    # Content
                    content_elem = item_elem.find('content:encoded', {'content': 'http://purl.org/rss/1.0/modules/content/'})
                    content = content_elem.text.strip() if content_elem is not None and content_elem.text else None
                    
                    # Extract image URL
                    url_image = None
                    image_sources = [
                        item_elem.find('enclosure[@type="image/jpeg"]'),
                        item_elem.find('enclosure[@type="image/png"]'),
                        item_elem.find('media:content[@medium="image"]', {'media': 'http://search.yahoo.com/mrss/'}),
                        item_elem.find('media:thumbnail', {'media': 'http://search.yahoo.com/mrss/'}),
                        item_elem.find('image')
                    ]
                    
                    for img_elem in image_sources:
                        if img_elem is not None:
                            img_url = img_elem.get('url') or img_elem.get('src') or img_elem.get('href')
                            if img_url:
                                if not img_url.startswith('http'):
                                    base_url = f"{urlparse(rss_url).scheme}://{urlparse(rss_url).netloc}"
                                    img_url = urljoin(base_url, img_url)
                                url_image = img_url
                                break
                    
                    # Extract image from description or content if not found
                    if not url_image and (description or content):
                        text_to_search = content or description
                        img_pattern = r'<img[^>]+src=["\'"]([^"\'">]+)["\'"]'
                        img_matches = re.findall(img_pattern, text_to_search, re.IGNORECASE)
                        if img_matches:
                            img_url = img_matches[0]
                            if not img_url.startswith('http'):
                                base_url = f"{urlparse(rss_url).scheme}://{urlparse(rss_url).netloc}"
                                img_url = urljoin(base_url, img_url)
                            url_image = img_url
                    
                    if title and url:
                        items.append({
                            'title': title,
                            'url': url,
                            'author': author,
                            'categories': categories,
                            'description': description,
                            'publish_date': publish_date,
                            'content': content,
                            'url_image': url_image
                        })
            
            print(f"SUCCESS: Found {len(items)} items")
            return {
                'items': items,
                'count': len(items),
                'status': 'success',
                'error': None
            }
            
        except httpx.TimeoutException:
            error_msg = f"Timeout accessing {rss_url}"
            print(f"ERROR: {error_msg}")
            return {
                'items': [],
                'count': 0,
                'status': 'timeout',
                'error': error_msg
            }
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} error for {rss_url}"
            print(f"ERROR: {error_msg}")
            return {
                'items': [],
                'count': 0,
                'status': 'http_error',
                'error': error_msg
            }
        except ET.ParseError as e:
            error_msg = f"XML parse error for {rss_url}: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {
                'items': [],
                'count': 0,
                'status': 'xml_error',
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error for {rss_url}: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {
                'items': [],
                'count': 0,
                'status': 'error',
                'error': error_msg
            }

async def main():
    print("Enhanced RSS Data Extractor Test")
    print("="*40)
    
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
        result = await extract_data_from_rss(rss_url)
        
        # Create feed name from URL
        feed_name = rss_url.split('/')[-1].replace('.rss', '')
        domain = rss_url.split('//')[1].split('/')[0]
        
        all_results[f"{domain}_{feed_name}"] = {
            "rss_url": rss_url,
            "domain": domain,
            "items": result.get('items', []),
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
    total_items = sum(r["count"] for r in all_results.values())
    total_images = sum(len([item for item in r.get("items", []) if item.get("url_image")]) for r in all_results.values())
    print(f"\n{'='*50}")
    print(f"SUMMARY:")
    print(f"{'='*50}")
    print(f"Total feeds processed: {len(rss_feeds)}")
    print(f"Successful feeds: {successful_feeds}")
    print(f"Failed feeds: {failed_feeds}")
    print(f"Total items extracted: {total_items}")
    print(f"Items with images: {total_images}")
    print(f"Results saved to: {output_file}")
    
    # Show detailed results
    print(f"\n{'='*50}")
    print(f"DETAILED RESULTS:")
    print(f"{'='*50}")
    
    for feed_name, data in all_results.items():
        status_icon = "SUCCESS" if data['status'] == 'success' else "FAILED"
        print(f"\n[{status_icon}] {data['domain']}")
        print(f"   Feed: {feed_name}")
        print(f"   Items: {data['count']}")
        print(f"   Status: {data['status']}")
        
        if data['error']:
            print(f"   Error: {data['error']}")
        
        # Show sample items for successful feeds
        if data['status'] == 'success' and data['items']:
            print(f"   Sample items:")
            for item in data['items'][:2]:
                print(f"     - Title: {item['title'][:60]}...")
                print(f"       Author: {item['author'] or 'N/A'}")
                print(f"       Categories: {', '.join(item['categories']) if item['categories'] else 'N/A'}")
                print(f"       Image: {'Yes' if item['url_image'] else 'No'}")
                print()
    
    print(f"Export complete! Check {output_file} for full results.")

if __name__ == "__main__":
    asyncio.run(main())