#!/usr/bin/env python3
"""Test script for Newspaper4k Content Extractor"""

import sys
import os
import json
from datetime import datetime

# Add the newspaper4k-extractor to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'newspaper4k-extractor', 'src'))

# Import directly without the relative imports issue
from extractor.article_processor import ArticleProcessor


def test_single_domain(domain_name: str, max_articles: int = 5):
    """Test extraction for a single domain"""
    print(f"\n=== Testing domain: {domain_name} ===")
    
    processor = ArticleProcessor()
    result = processor.process_domain(domain_name, max_articles)
    
    if result.get('success'):
        print(f"Successfully extracted {result['success_count']} articles")
        print(f"  Processing time: {result['processing_time']} seconds")
        
        if result['articles']:
            print("\nSample article:")
            sample = result['articles'][0]
            try:
                print(f"  Title: {sample['title'][:100]}...")
            except UnicodeEncodeError:
                print(f"  Title: [Vietnamese content - {len(sample['title'])} chars]")
            print(f"  URL: {sample['url']}")
            print(f"  Content length: {len(sample['content'])} chars")
            print(f"  Authors: {sample['author']}")
            print(f"  Image: {sample['url_image']}")
    else:
        print(f"Failed: {result.get('error', 'Unknown error')}")
    
    return result


def test_multiple_domains(max_articles_per_domain: int = 3):
    """Test extraction for multiple domains"""
    print("\n=== Testing Multiple Domains ===")
    
    processor = ArticleProcessor()
    
    # Get all active domains
    domains = processor.get_all_domains()
    print(f"Found {len(domains)} active domains in database")
    
    results = []
    
    # Test first few domains
    test_domains = domains[:5]  # Test first 5 domains
    
    for domain in test_domains:
        result = test_single_domain(domain['name'], max_articles_per_domain)
        results.append(result)
    
    return results


def export_results_to_json(results, filename=None):
    """Export extraction results to JSON file"""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"newspaper4k_extraction_results_{timestamp}.json"
    
    filepath = os.path.join(os.path.dirname(__file__), filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\nResults exported to: {filepath}")
    return filepath


def test_single_url(url: str):
    """Test extraction for a single URL"""
    print(f"\n=== Testing single URL ===")
    print(f"URL: {url}")
    
    processor = ArticleProcessor()
    result = processor.extract_single_url(url)
    
    if result.get('success'):
        print(f"Successfully extracted article")
        print(f"  Processing time: {result['processing_time']} seconds")
        
        if result['articles']:
            article = result['articles'][0]
            try:
                print(f"  Title: {article['title'][:100]}...")
            except UnicodeEncodeError:
                print(f"  Title: [Vietnamese content - {len(article['title'])} chars]")
            print(f"  Content length: {len(article['content'])} chars")
            print(f"  Authors: {len(article['author'])} authors")
            print(f"  Image: {'Yes' if article['url_image'] else 'No'}")
    else:
        print(f"Failed: {result.get('error', 'Unknown error')}")
    
    return result


def main():
    """Main test function with options"""
    print("Testing Newspaper4k Content Extractor")
    print("=" * 50)
    
    try:
        # Test database connection
        processor = ArticleProcessor()
        if not processor.db.test_connection():
            print("Database connection failed!")
            return
        
        print("Database connection successful")
        
        # Ask user for test type
        print("\nChoose test type:")
        print("1. Test domains (multiple articles from domains)")
        print("2. Test single URL (extract one specific article)")
        print("3. Both")
        
        choice = input("\nEnter choice (1/2/3): ").strip()
        
        all_results = []
        
        if choice in ['1', '3']:
            print("\n" + "=" * 30)
            print("TESTING DOMAINS")
            print("=" * 30)
            
            # Test specific domains (from database)
            test_domains = ['vnexpress.net', 'dantri.com.vn', 'tuoitre.vn']
            
            for domain in test_domains:
                result = test_single_domain(domain, max_articles=3)
                all_results.append(result)
        
        if choice in ['2', '3']:
            print("\n" + "=" * 30)
            print("TESTING SINGLE URLs")
            print("=" * 30)
            
            # Test specific URLs
            test_urls = [
                "https://thanhnien.vn/thu-tuong-yeu-cau-xem-lai-tinh-trang-thieu-giao-vien-nhung-con-bien-che-chua-tuyen-dung-185250822195656634.htm"
            ]
            
            for url in test_urls:
                result = test_single_url(url)
                all_results.append(result)
        
        # Export results
        export_results_to_json(all_results)
        
        # Summary
        total_articles = sum(r.get('success_count', 0) for r in all_results)
        total_errors = sum(len(r.get('errors', [])) for r in all_results)
        
        print("\n" + "=" * 50)
        print("SUMMARY:")
        print(f"   Total articles extracted: {total_articles}")
        print(f"   Total errors: {total_errors}")
        print(f"   Success rate: {total_articles/(total_articles+total_errors)*100:.1f}%" if (total_articles+total_errors) > 0 else "N/A")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
