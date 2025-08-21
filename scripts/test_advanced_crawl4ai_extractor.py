"""
Test script for Advanced Crawl4AI Content Extractor
Using the AdvancedCrawl4AIExtractor class with intelligent fallback
"""

import asyncio
import sys
import os
from pathlib import Path
import json
from datetime import datetime
import logging
from typing import List, Dict, Any

# Set UTF-8 encoding for Windows console
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
sys.stderr.reconfigure(encoding='utf-8', errors='ignore')

# Add the parent directory to the Python path  
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import our advanced extractor  
sys.path.append(os.path.join(parent_dir, 'apps', 'enhanced-crawler-worker', 'src', 'workers'))
from crawl4ai_content_extractor import AdvancedCrawl4AIExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_test_urls():
    """Load test URLs from RSS JSON file."""
    rss_file = Path(__file__).parent / "rss_urls_20250821_170314.json"
    
    try:
        with open(rss_file, 'r', encoding='utf-8') as f:
            rss_data = json.load(f)
        
        urls_by_domain = {}
        
        # Group URLs by domain
        for feed_name, feed_data in rss_data.get("results", {}).items():
            if feed_data.get("urls") and feed_data.get("status") == "success":
                domain = feed_data.get("domain", "unknown")
                if domain not in urls_by_domain:
                    urls_by_domain[domain] = []
                urls_by_domain[domain].extend(feed_data["urls"])
        
        # Take 2 URLs per domain
        test_urls = []
        for domain, urls in urls_by_domain.items():
            for url in urls[:2]:  # Only take first 2 URLs
                test_urls.append({
                    "url": url,
                    "domain": domain
                })
        
        return test_urls
        
    except Exception as e:
        logger.error(f"Error loading RSS URLs: {e}")
        return []


async def test_url_extraction(url_info):
    """Test content extraction using AdvancedCrawl4AIExtractor."""
    url = url_info["url"]
    domain = url_info["domain"]
    
    try:
        # Initialize the advanced extractor
        extractor = AdvancedCrawl4AIExtractor(
            logger=logger,
            enable_llm=False
        )
        
        # Extract single URL
        article = await extractor._extract_single_url(url, use_cache=False)
        
        if article and article.success:
            # Build response in expected format
            final_data = {
                "url": url,
                "title": article.title or "No Title",
                "content": article.content or "",
                "author": article.author,
                "publish_date": article.publish_date,
                "category": article.category,
                "image_url": article.image_url
            }
            
            # Validate fields
            field_check = {
                "url": bool(final_data["url"]),
                "title": bool(final_data["title"] and final_data["title"] != "No Title"),
                "content": bool(final_data["content"] and len(final_data["content"]) > 100),
                "author": bool(final_data["author"]),
                "publish_date": bool(final_data["publish_date"]),
                "category": bool(final_data["category"]),
                "image_url": bool(final_data["image_url"])
            }
            
            return {
                "url": url,
                "domain": domain,
                "success": True,
                "extracted_data": final_data,
                "field_check": field_check,
                "fields_present": sum(field_check.values()),
                "content_length": len(final_data["content"]),
                "word_count": len(final_data["content"].split()) if final_data["content"] else 0,
                "extraction_method": article.extraction_method,
                "extraction_time": article.extraction_time
            }
        else:
            error_msg = article.error if article else "No content extracted"
            return {
                "url": url,
                "domain": domain,
                "success": False,
                "error": error_msg,
                "extracted_data": {}
            }
            
    except Exception as e:
        return {
            "url": url,
            "domain": domain,
            "success": False,
            "error": str(e),
            "extracted_data": {}
        }


async def run_extraction_tests():
    """Run extraction tests on multiple URLs."""
    print("CRAWL4AI CONTENT EXTRACTOR TEST")
    print("=" * 50)
    
    # Load test URLs
    test_urls = load_test_urls()
    if not test_urls:
        print("No test URLs found!")
        return
    
    print(f"Testing {len(test_urls)} URLs from RSS feeds...")
    
    # Run tests
    results = []
    successful = 0
    failed = 0
    
    for i, url_info in enumerate(test_urls, 1):
        print(f"\n[{i}/{len(test_urls)}] Testing: {url_info['domain']}")
        print(f"URL: {url_info['url'][:80]}...")
        
        result = await test_url_extraction(url_info)
        results.append(result)
        
        if result["success"]:
            successful += 1
            data = result["extracted_data"]
            
            print(f"SUCCESS - Fields: {result['fields_present']}/7")
            print(f"  Title: {data['title'][:50]}..." if data['title'] else "  Title: None")
            print(f"  Author: {data['author'] or 'None'}")
            print(f"  Date: {data['publish_date'] or 'None'}")
            print(f"  Category: {data['category'] or 'None'}")
            print(f"  Content: {result['word_count']} words")
            print(f"  Image: {'Yes' if data['image_url'] else 'None'}")
        else:
            failed += 1
            print(f"FAILED - {result['error']}")
    
    # Summary
    print(f"\n" + "="*50)
    print(f"SUMMARY")
    print(f"="*50)
    print(f"Total URLs: {len(test_urls)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(successful/len(test_urls)*100):.1f}%")
    
    # Field coverage
    if successful > 0:
        print(f"\nFIELD COVERAGE:")
        field_totals = {"url": 0, "title": 0, "content": 0, "author": 0, 
                       "publish_date": 0, "category": 0, "image_url": 0}
        
        for result in results:
            if result["success"]:
                for field in field_totals:
                    if result["field_check"][field]:
                        field_totals[field] += 1
        
        for field, count in field_totals.items():
            percentage = (count / successful) * 100
            print(f"  {field}: {count}/{successful} ({percentage:.1f}%)")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path(__file__).parent / f"crawl4ai_test_results_{timestamp}.json"
    
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_urls": len(test_urls),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful/len(test_urls)*100) if test_urls else 0
        },
        "results": results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(run_extraction_tests())