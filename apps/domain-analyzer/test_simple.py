"""
Simple test script without emojis
"""
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from analyzer.newspaper4k_analyzer import Newspaper4kDomainAnalyzer
from utils.database_utils import DatabaseManager

def test_simple():
    print("\nTesting URL Tracking Flow")
    print("=" * 40)
    
    db = DatabaseManager()
    if not db.connect():
        print("Cannot connect to database")
        return
    
    # Get a domain
    domains = db.get_active_domains()
    if not domains:
        print("No domains found")
        return
    
    domain = domains[0]
    print(f"Testing with: {domain['name']}")
    print(f"Base URL: {domain['base_url']}")
    
    # Show domain data structure
    print(f"\nDomain columns available:")
    for key, value in domain.items():
        if key in ['rss_feeds', 'sitemaps', 'homepage_urls', 'category_urls']:
            print(f"  {key}: {len(value) if value else 0} items")
        else:
            print(f"  {key}: {str(value)[:50]}..." if len(str(value)) > 50 else f"  {key}: {value}")
    
    # Extract URLs
    analyzer = Newspaper4kDomainAnalyzer()
    analysis_result = {
        'rss_feeds': domain.get('rss_feeds', []),
        'sitemaps': domain.get('sitemaps', []),
        'homepage_urls': domain.get('homepage_urls', []),
        'category_urls': domain.get('category_urls', [])
    }
    
    print(f"\nExtracting article URLs...")
    article_urls = analyzer.extract_all_article_urls(
        domain['base_url'], 
        domain['name'], 
        analysis_result
    )
    
    print(f"Found {len(article_urls)} article URLs")
    
    # Show samples
    print(f"\nSample URLs:")
    for i, url in enumerate(article_urls[:3]):
        print(f"  {i+1}. {url}")
    
    # Save to database
    print(f"\nSaving to url_tracking...")
    success = db.bulk_add_urls_to_tracking(
        article_urls, 
        domain['id'], 
        'test-run'
    )
    
    print(f"Saved {success}/{len(article_urls)} URLs")
    
    db.disconnect()
    print("Test completed!")

if __name__ == "__main__":
    test_simple()